# Imports
from instapy import InstaPy
from instapy import smart_run
import instaloader
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
from config import source, similar_accounts, friend_list, ignored_users, like_tag_list, photo_comments, dont_like

ignored_users.append(source)
if (os.path.exists("./{}/ignored_users.txt".format(args['account']))):
    with open("./{}/ignored_users.txt".format(args['account']), "r") as f:
        for line in f:
            ignored_users.append(line.strip())
else:
    L = instaloader.Instaloader()
    L.login(insta_username, insta_password)
    profile = instaloader.Profile.from_username(L.context, source)
    followers = set(profile.get_followers())
    with open("./{}/ignored_users.txt".format(args['account']), "w") as f:
        for follower in list(followers):
            f.write(str(follower.username) +"\n")
            ignored_users.append(str(follower.username))

# ---------------------------------------------------------------------------- #
#                                  InstaPy-cli                                 #
# ---------------------------------------------------------------------------- #

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
                      headless_browser=False)
    
    with smart_run(session):
    
    # ---------------------------------------------------------------------------- #
    #                               General Settings                               #
    # ---------------------------------------------------------------------------- #
    
        # quality of account to classify for being followed
        session.set_relationship_bounds(enabled=True,
                                        delimit_by_numbers=True,
                                        max_followers=50000,
                                        min_followers=40,
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
                                        peak_likes_hourly=30,
                                        peak_likes_daily=200,
                                        peak_comments_hourly=10,
                                        peak_comments_daily=100,
                                        peak_follows_hourly=20,
                                        peak_follows_daily=100,
                                        peak_unfollows_hourly=40,
                                        peak_unfollows_daily=400,
                                        peak_server_calls_hourly=300,
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
        session.set_simulation(enabled=False, percentage=0)
    
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
    
    
    # ---------------------------------------------------------------------------- #
    #                               Activity Settings                              #
    # ---------------------------------------------------------------------------- #
    
        session.set_comments(photo_comments, media = 'Photo')
        session.set_do_comment(     enabled = False,percentage = 0)
        session.set_do_like(        enabled = True, percentage = 80)
        session.set_do_follow(      enabled = True, percentage = 70, times = 2)
        session.set_do_story(       enabled = True, percentage = 50, simulate = False)
        session.set_user_interact(  percentage = 60, amount = 3, randomize = False,  media = 'Photo')
        
        
    # ---------------------------------------------------------------------------- #
    #                              Perform Activities                              #
    # ---------------------------------------------------------------------------- #
    
        # Remove outgoing unapproved follow requests from private accounts
        # session.remove_follow_requests(amount=200, sleep_delay=600)
        
        #Accept follow requests
        session.accept_follow_requests(amount=100, sleep_delay=1)
        # Follow some users of given account followers
        session.follow_user_followers(  random.sample(similar_accounts, 3), 
                                        amount=random.randint(5, 20), 
                                        randomize=True, 
                                        interact=True)
        # Like post of given tags and interact with users in the process (Follow some, and or like more post of same users)
        session.like_by_tags(   random.sample(like_tag_list, 10), 
                                amount=random.randint(10, 30),
                                skip_top_posts=False, 
                                interact=True )
        # Unfollow some users who dont follow back after 90 hours
        # session.unfollow_users( amount=60, instapy_followed_enabled=True, 
        #                        instapy_followed_param="nonfollowers", style="RANDOM", 
        #                        unfollow_after=90*60*60, sleep_delay=501    )
    
     
    
    