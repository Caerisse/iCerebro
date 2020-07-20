# Imports
import random

from iCerebro import ICerebro

args = {'account': 'testingaccount2020', 'no-interact': False}

# Login credentials
from testingaccount2020.credentials import insta_username, insta_password
# Account config
import testingaccount2020.config as config

# ---------------------------------------------------------------------------- #
#                               General Settings                               #
# ---------------------------------------------------------------------------- #

# get an InstaPy session and login
# set headless_browser=True to run InstaPy in the background
session = ICerebro( username=insta_username,
                    password=insta_password,
                    want_check_browser=False,
                    headless_browser=config.headless_browser,
                    geckodriver_path='./{}/geckodriver'.format(args['account']))

session.login()

# Scrap start
# session.set_use_image_analysis(False)
# session.set_store_in_database(True)
# session.complete_user_relationships_of_users_already_in_db()
# session.complete_posts_of_users_already_in_db()
# exit()
# Scrap end

session.set_use_image_analysis(True)
session.set_store_in_database(True)

# dont stop following these people
session.set_dont_include(config.friend_list)
    
# dont like anything with these
session.set_dont_like(config.dont_like)
    
# Quota and delay settings
# TODO: hook to a simple AI
session.set_quota_supervisor(   enabled=True,
                                sleep_after=["likes", "comments_d", "follows", "unfollows", "server_calls_h"], 
                                sleepyhead=True, stochastic_flow=True, notify_me=True,
                                peak_likes_hourly=config.peak_likes_hourly,
                                peak_likes_daily=config.peak_likes_daily,
                                peak_comments_hourly=config.peak_comments_hourly,
                                peak_comments_daily=config.peak_comments_daily,
                                peak_follows_hourly=config.peak_follows_hourly,
                                peak_follows_daily=config.peak_follows_daily,
                                peak_unfollows_hourly=config.peak_unfollows_hourly,
                                peak_unfollows_daily=config.peak_unfollows_daily,
                                peak_server_calls_hourly=config.peak_server_calls_hourly,
                                peak_server_calls_daily=config.peak_server_calls_daily,      )
    
session.set_action_delays(      enabled=True, 
                                like=config.like,
                                comment=config.comment,
                                follow=config.follow,
                                unfollow=config.unfollow,
                                story=config.story,
                                randomize=True, 
                                random_range_from=100, 
                                random_range_to=200         )
    

# quality of account to classify for being followed
# session.set_relationship_bounds(enabled=True,
#                                 delimit_by_numbers=True,
#                                 max_followers=1000000,
#                                 min_followers=0,
#                                 min_following=0,
#                                 min_posts=1          )

# Ignore everything from these users
session.set_ignore_users(config.ignored_users)

# Not interact with post not in latin characters
session.set_mandatory_language(enabled=True, character_set=['LATIN'])

# Not unfollow anyone whi interacted with the account
# session.set_dont_unfollow_active_users(enabled=True, posts=3)

# Skip certains users (In this case will not interact with private accounts 80 percent of the time 
# and not at all with no profile pics account)
session.set_skip_users( skip_private=config.skip_private,
                        private_percentage=config.private_percentage,
                        skip_no_profile_pic=config.skip_no_profile_pic,
                        no_profile_pic_percentage=config.no_profile_pic_percentage,
                        skip_business=config.skip_business,
                        skip_non_business=config.skip_non_business,
                        business_percentage=config.business_percentage,
                        skip_business_categories=config.skip_business_categories,
                        dont_skip_business_categories=config.dont_skip_business_categories  )

# Limit of previous liking in post to allow interact
# session.set_delimit_liking( enabled=True, max_likes=None, min_likes=50 )
    
# ---------------------------------------------------------------------------- #
#                               Activity Settings                              #
# ---------------------------------------------------------------------------- #

session.set_comments(       config.photo_comments, 
                            media = 'Photo' )

session.set_do_comment(     enabled = True,
                            percentage = 0   )

session.set_do_like(        enabled = True, 
                            percentage = 100      )

session.set_do_follow(      enabled = True, 
                            percentage = 100, 
                            times = config.do_follow_times              )

session.set_do_story(       enabled = True, 
                            percentage = config.do_story_percentage, 
                            simulate = False                            )

session.set_user_interact(  percentage = 100,
                            amount = 3,
                            randomize = False,  
                            media = 'Photo'                             )


# ---------------------------------------------------------------------------- #
#                                   Start Run                                  #
# ---------------------------------------------------------------------------- #

try:
        # ---------------------------------------------------------------------------- #
        #                              Perform Activities                              #
        # ---------------------------------------------------------------------------- #

        if not args['no-interact']:

            # Remove outgoing unapproved follow requests from private accounts
            # session.remove_follow_requests(amount=200, sleep_delay=600)
            
            #Accept follow requests
            # session.accept_follow_requests( amount=config.accept_follow_requests_amount,
            #                                 sleep_delay=config.accept_follow_requests_sleep_delay)

            # Follow some users of given account followers
            # session.nf_follow_user_follow(  "followers",
            #                                 random.sample(config.similar_accounts, 1),
            #                                 amount=50,
            #                                 randomize=True)

            # Like post of given tags and interact with users in the process (Follow some, and or like more post of same users)
            session.nf_like_by_tags(random.sample(config.like_tag_list, 1),
                                    amount=10,
                                    skip_top_posts=False)
            session.nf_like_by_users(random.sample(config.similar_accounts, 1), amount=10)
            session.nf_like_by_feed(amount=10)


            # Unfollow some users who dont follow back after 3-5 days
            # session.nf_unfollow_users(amount=20, instapy_followed_enabled=True,
            #                         instapy_followed_param="nonfollowers", style="RANDOM",
            #                         unfollow_after=random.randint(72, 120)*60*60, sleep_delay=random.randint(403,501))

        
except KeyboardInterrupt:
    pass
except ConnectionRefusedError:
    print("User: {} was blocked by instagram".format(insta_username))
finally:
    session.end()
