# Imports
#from natural_flow import MyInstaPy
from instapy import InstaPy
from upload import upload_single_image
import random
import argparse
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--account", required=True, help="folder with account data")
ap.add_argument("--upload", required=False, help="upload post", type=int, default=0)
ap.add_argument('--no-interaction', required=False, help="do not interact with posts and accounts", dest='no-interact', default=False, action='store_true')
ap.add_argument('--no-pods', required=False, help="do not join pods", dest='no-pods', default=False, action='store_true')
args = vars(ap.parse_args())

if args['account'].endswith('/'): args['account'] = args['account'][0:-1]

"""
args = {}
args['account'] = 'testingaccount2020'
args['no-pods'] = False
args['no-interact'] = False
"""

sys.path.append('./{}'.format(args['account']))

# Login credentials
from credentials import insta_username, insta_password
# Account config
import config


# ---------------------------------------------------------------------------- #
#                               General Settings                               #
# ---------------------------------------------------------------------------- #

# get an InstaPy session and login
# set headless_browser=True to run InstaPy in the background
session = InstaPy(username=insta_username,
                    password=insta_password,
                    want_check_browser=False,
                    headless_browser=config.headless_browser,
                    geckodriver_path='./{}/geckodriver'.format(args['account']))

session.login()

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

session.set_simulation(enabled=True, percentage=90)

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
#                                   Start Run                                  #
# ---------------------------------------------------------------------------- #

try:
    # TODO: modify loop to reset UPLOADED_POST every day and be able to run the code 24/7
    UPLOADED_POSTS=0
    while True:
        # ---------------------------------------------------------------------------- #
        #                                 Upload posts                                 #
        # ---------------------------------------------------------------------------- #

        # While upload a post on every iteration until argument is passed
        if UPLOADED_POSTS < args['upload']:
            UPLOADED_POSTS += 1
            # Get post
            path = './{}/posts_source/'.format(args['account'])
            files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            files.sort()
            post = []
            delete = []
            text = ""
            base_name = files[0][0:files[0].index('UTC')+3]
            text_is_bad = False
            for file_name in files:
                if text_is_bad and not file_name.startswith(base_name):
                    post = []
                    delete = []
                    text = ""
                    base_name = file_name[0:file_name.index('UTC')+3]
                    text_is_bad = False
                if file_name.startswith(base_name):
                    delete.append(path + file_name)
                    if file_name.endswith('.txt') and "location" not in file_name:
                        text = open(path + file_name, "r").read().strip()
                        if "@" in text:
                            session.logger.info(
                                "check post {} text, possibly has a tag \n posting next one".format(base_name)
                            )
                            text_is_bad = True
                    elif file_name.endswith('.jpg') or file_name.endswith('.mp4'):
                        post.append(file_name)
                elif not text_is_bad:
                    break

            #Upload!
            upload_single_image(post[0], text, args['account'], session)

            # Remove files related to the uploaded pic
            for file_name in  delete:
                os.remove(file_name)

        # ---------------------------------------------------------------------------- #
        #                                   Join Pods                                  #
        # ---------------------------------------------------------------------------- #

        if not args['no-pods']:
            # Topics allowed are {'general', 'fashion', 'food', 'travel', 'sports', 'entertainment'}.
            # TODO: move to config files
            session.join_pods(topic='fashion', engagement_mode='normal')
            session.join_pods(topic='travel', engagement_mode='normal')


        # ---------------------------------------------------------------------------- #
        #                              Perform Activities                              #
        # ---------------------------------------------------------------------------- #

        if not args['no-interact']:
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
            session.like_by_tags(   random.sample(config.like_tag_list, 
                                        random.randint( config.like_by_tags_amount_of_tags,
                                                        config.like_by_tags_amount_of_tags*2    )), 
                                    amount=random.randint(  config.like_by_tags_amount, 
                                                            config.like_by_tags_amount*2    ),
                                    skip_top_posts=False, 
                                    interact=True )


            # Unfollow some users who dont follow back after 3-5 days
            session.unfollow_users( amount=20, instapy_followed_enabled=True, 
                                    instapy_followed_param="nonfollowers", style="RANDOM", 
                                    unfollow_after=random.randint(72, 120)*60*60, sleep_delay=random.randint(403,501))
    
        
except KeyboardInterrupt:
    pass
except ConnectionRefusedError:
    print("User: {} was blocked by instagram".format(insta_username))
finally:
    session.end()

    
    
