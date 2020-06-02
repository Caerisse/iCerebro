# imports
from instapy import InstaPy
from instapy import smart_run
import random
import argparse
import sys

ap = argparse.ArgumentParser()
ap.add_argument("-a", "--account", required=True, help="folder with account data")
args = vars(ap.parse_args())

sys.path.append('./{}'.format(args['account']))

# Login credentials
from credentials import insta_username, insta_password

# Account config
from config import similar_accounts, friend_list, ignored_users, like_tag_list, photo_comments, dont_like

# get an InstaPy session
# set headless_browser=True to run InstaPy in the background
session = InstaPy(username=insta_username,
                  password=insta_password,
                  want_check_browser=False,
                  headless_browser=True)

with smart_run(session):
    """ Activity flow """


    ### general settings ###

    # quality of account to classify for being followed
    session.set_relationship_bounds(enabled=True,
                                    delimit_by_numbers=True,
                                    max_followers=50000,
                                    min_followers=30,
                                    min_following=10,
                                    min_posts=10)


    # dont stop following these people
    session.set_dont_include(friend_list)

    # dont like anything with these
    session.set_dont_like(dont_like)


    # Quota and delay settings
    # TODO: hook to a simple AI
    session.set_quota_supervisor(   enabled=True, 
                                    sleep_after=["likes", "comments_d", "follows", "unfollows", "server_calls_h"], 
                                    sleepyhead=True, stochastic_flow=True, notify_me=True,
                                    peak_likes_hourly=20,
                                    peak_likes_daily=200,
                                    peak_comments_hourly=10,
                                    peak_comments_daily=100,
                                    peak_follows_hourly=20,
                                    peak_follows_daily=100,
                                    peak_unfollows_hourly=40,
                                    peak_unfollows_daily=400,
                                    peak_server_calls_hourly=200,
                                    peak_server_calls_daily=2000)

    session.set_action_delays(  enabled=True, 
                                like=15,
                                comment=30,
                                follow=30,
                                unfollow=20,
                                story=15,
                                randomize=True, 
                                random_range_from=100, 
                                random_range_to=200     )

    

    # Ignore everything from these users
    session.set_ignore_users(ignored_users)

    # Not interact with post not in latin caracters
    session.set_mandatory_language(enabled=True, character_set=['LATIN'])

    # Not unfollow anyone whi interacted with the account
    session.set_dont_unfollow_active_users(enabled=True, posts=3)

    # Some interactions with the page can be simulated via interaction with the API instead of the ui, safer disabled
    session.set_simulation(enabled=False, percentage=66)

    # Skip certains users (In this case will not interact with private accounts 80 percent of the time 
    # and not at all with no profile pics account)
    session.set_skip_users( skip_private=True,
                            private_percentage=80,
                            skip_no_profile_pic=True,
                            no_profile_pic_percentage=100,
                            skip_business=True,
		            skip_non_business=False,
                            business_percentage=100,
                            skip_business_categories=[],
                            dont_skip_business_categories=['Creators & Celebrities']    )

    # Limit of previous liking in post to allow interact
    session.set_delimit_liking( enabled=True, max_likes=None, min_likes=50 )

    

    # Activity settings
    session.set_comments(photo_comments, media = 'Photo')
    session.set_do_comment(enabled=False, percentage=0)
    session.set_do_like(enabled=True, percentage=70)
    session.set_do_follow(enabled=True, percentage=50, times=2)
    session.set_user_interact(amount=3, randomize=False, percentage=60, media='Photo')
    session.set_do_story(enabled = True, percentage = 50, simulate = False)
    
    
    
    ### Activities ###


    # Remove outgoing unapproved follow requests from private accounts
    #session.remove_follow_requests(amount=200, sleep_delay=600)
    
    #Accept follow requests
    session.accept_follow_requests(amount=100, sleep_delay=1)

    # Follow some users of given account followers
    session.follow_user_followers(  random.sample(similar_accounts, 2), 
                                    amount=random.randint(2, 10), 
                                    randomize=True, 
                                    interact=True)

    # Like post of given tags and interact with users in the process (Follow some, and or like more post of same users)
    session.like_by_tags(   random.sample(like_tag_list, 5), 
                            amount=random.randint(5, 20),
                            skip_top_posts=False, 
                            interact=True )
    
    # Unfollow some users who dont follow back after 90 hours
    session.unfollow_users( amount=60, instapy_followed_enabled=True, 
                            instapy_followed_param="nonfollowers", style="RANDOM", 
                            unfollow_after=90*60*60, sleep_delay=501    )

 

