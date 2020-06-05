import argparse
import os
import sys
import glob
import instaloader

ap = argparse.ArgumentParser()
ap.add_argument("-a", "--account", required=True, help="folder with account data")
args = vars(ap.parse_args())

if args['account'].endswith('/'): args['account'] = args['account'][0:-1]
sys.path.append('./{}'.format(args['account']))

# Login credentials
from testingaccount2020.credentials import insta_username, insta_password
# Account config
from config import source

# Create session
IL = instaloader.Instaloader()
IL.login(insta_username, insta_password)

# Get profile
print("Getting profile, i tmay take a while")
profile = instaloader.Profile.from_username(IL.context, source)

#Get followers
print("Getting followers, it may take a while")
followers = set(profile.get_followers())

# Save to file for later loading
with open("./{}/ignored_users.txt".format(args['account']), "w") as f:
    for follower in list(followers):
        f.write(str(follower.username) +"\n")

# Get already saved posts if any
saved_posts = set([])
if os.path.exists("./{}/posts_source".format(args['account'])):
    saved_posts = set(filter(lambda s: isinstance(s, Post),
                           (load_structure_from_file(L.context, file)
                            for file in glob('./{}/posts_source/*.json.*'.format(args['account'])))))

# Get all online posts
print("Getting posts, it may take a while")
post_iterator = instaloader.Profile.from_username(IL.context, source).get_posts()
online_posts = set(post_iterator)

# Download new posts
print("Downloading posts: ")
os.chdir(args['account'])
for post in online_posts-saved_posts:
    try:
        IL.download_post(post, "posts_source")
    except instaloader.QueryReturnedNotFoundException:
        print("Post not found, skipping")