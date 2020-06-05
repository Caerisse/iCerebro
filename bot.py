# Imports
from instapy import InstaPy
from instapy import smart_run
from instapy import set_workspace
#from instapy_cli import client
from upload import upload
import random
import argparse
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("-a", "--account", required=True, help="folder with account data")
ap.add_argument("-u", "--upload", required=False, help="upload post", default="false")
ap.add_argument("-i", "--interact", required=False, help="interact with posts and accounts", default="true")
args = vars(ap.parse_args())

if args['account'].endswith('/'): args['account'] = args['account'][0:-1]
sys.path.append('./{}'.format(args['account']))

# Login credentials
from credentials import insta_username, insta_password

# Account config
import config

# Load ignored users
config.ignored_users.append(config.source)
if (os.path.exists("./{}/ignored_users.txt".format(args['account']))):
    with open("./{}/ignored_users.txt".format(args['account']), "r") as f:
        for line in f:
            config.ignored_users.append(line.strip())


# ---------------------------------------------------------------------------- #
#                                  InstaPy-cli                                 #
# ---------------------------------------------------------------------------- #

# This was a test to autoupload post, instapy-cli is no longer working properly

if args['upload'] == "true":
    #cookie_file = './{}/cookie.json'.format(insta_username)
    #with client(insta_username, insta_password, cookie_file=cookie_file, write_cookie_file=True) as cli:
        path = './{}/posts_source/'.format(insta_username)
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        files.sort()
        post = []
        delete = []
        text = ""
        base_name = files[0][0:files[0].index('.')]
        for file_name in files:
            if file_name.startswith(base_name):
                delete.append(path + file_name)
                if file_name.endswith('.txt'):
                    text = open(path + file_name, "r").read().strip()
                elif file_name.endswith('.jpg') or file_name.endswith('.mp4'):
                    post.append(path + file_name)
            else:
                break
        #cli.upload(post, text)
        upload(post[0], text, insta_username, insta_password)
        for file_name in  delete:
            os.remove(file_name)


# ---------------------------------------------------------------------------- #
#                                    InstaPy                                   #
# ---------------------------------------------------------------------------- #

if args['interact'] == "true":
    # get an InstaPy session
    # set headless_browser=True to run InstaPy in the background
    session = InstaPy(username=insta_username,
                      password=insta_password,
                      want_check_browser=False,
                      headless_browser=config.headless_browser,
                      geckodriver_path='./{}/geckodriver'.format(insta_username))
    
    while True:
        with smart_run(session):

# ---------------------------------------------------------------------------- #
#                               General Settings                               #
# ---------------------------------------------------------------------------- #
    
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
            session.set_relationship_bounds(enabled=True,
                                            delimit_by_numbers=True,
                                            max_followers=config.max_followers,
                                            min_followers=config.min_followers,
                                            min_following=config.min_following,
                                            min_posts=config.min_posts          )
            
    
            # Ignore everything from these users
            session.set_ignore_users(config.ignored_users)
    
            # Not interact with post not in latin caracters
            session.set_mandatory_language(enabled=True, character_set=['LATIN'])
    
            # Not unfollow anyone whi interacted with the account
            session.set_dont_unfollow_active_users(enabled=True, posts=3)
    
            # Some interactions with the page can be simulated via interaction with the API instead of the ui, safer disabled
            session.set_simulation(enabled=False, percentage=0)
    
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
            session.set_delimit_liking( enabled=True, max_likes=None, min_likes=50 )
    
    
    # ---------------------------------------------------------------------------- #
    #                               Activity Settings                              #
    # ---------------------------------------------------------------------------- #
    
            session.set_comments(       config.photo_comments, 
                                        media = 'Photo' )

            session.set_do_comment(     enabled = False,
                                        percentage = config.do_comment_percentage   )

            session.set_do_like(        enabled = True, 
                                        percentage = config.do_like_percentage      )

            session.set_do_follow(      enabled = True, 
                                        percentage = config.do_follow_percentage, 
                                        times = config.do_follow_times              )

            session.set_do_story(       enabled = True, 
                                        percentage = config.do_story_percentage, 
                                        simulate = False                            )

            session.set_user_interact(  percentage = config.user_interact_percentage, 
                                        amount = random.randint(config.user_interact_amount,
                                                                config.user_interact_amount*3),
                                        randomize = False,  
                                        media = 'Photo'                             )
            
            
    # ---------------------------------------------------------------------------- #
    #                              Perform Activities                              #
    # ---------------------------------------------------------------------------- #
    
            # Remove outgoing unapproved follow requests from private accounts
            # session.remove_follow_requests(amount=200, sleep_delay=600)
            
            #Accept follow requests
            session.accept_follow_requests( amount=config.accept_follow_requests_amount, 
                                            sleep_delay=config.accept_follow_requests_sleep_delay)
            # Follow some users of given account followers
            session.follow_user_followers(  random.sample(config.similar_accounts, 
                                                random.randint( config.follow_user_followers_amount_of_accounts,
                                                                config.follow_user_followers_amount_of_accounts*2   )), 
                                            amount=random.randint(  config.follow_user_followers_amount,
                                                                    config.follow_user_followers_amount*2   ), 
                                            randomize=True, 
                                            interact=True)
            
            # Like post of given tags and interact with users in the process (Follow some, and or like more post of same users)
            session.like_by_tags(   random.sample(like_tag_list, 
                                        random.randint( config.like_by_tags_amount_of_tags,
                                                        config.like_by_tags_amount_of_tags*2    )), 
                                    amount=random.randint(  config.like_by_tags_amount, 
                                                            config.like_by_tags_amount*2    ),
                                    skip_top_posts=False, 
                                    interact=True )


            # Unfollow some users who dont follow back after 3-5 days
            session.unfollow_users( amount=60, instapy_followed_enabled=True, 
                                    instapy_followed_param="nonfollowers", style="RANDOM", 
                                    unfollow_after=random.randint(72, 120)*60*60, sleep_delay=random.randint(403,501))
    

            # Join pods, Topics allowed are {'general', 'fashion', 'food', 'travel', 'sports', 'entertainment'}.
            # TODO: move to config files
            session.join_pods(topic='fashion', engagement_mode='normal')
            session.join_pods(topic='travel', engagement_mode='normal')
     
    
    