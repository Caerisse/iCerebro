

# ---------------------------------------------------------------------------- #
#                              Session run config                              #
# ---------------------------------------------------------------------------- #

headless_browser = False

# set_quota_supervisor
peak_likes_hourly=200
peak_likes_daily=3000
peak_comments_hourly=30
peak_comments_daily=200
peak_follows_hourly=100
peak_follows_daily=3000
peak_unfollows_hourly=50
peak_unfollows_daily=200
peak_server_calls_hourly=500
peak_server_calls_daily=5000

# set_action_delays (seconds)
# action delay will be chosen at random each time from between these numbers and its double
like=5
comment=10
follow=10
unfollow=5
story=5

# set_relationship_bounds
max_followers=10000
min_followers=50
min_following=10
min_posts=10 

# set_skip_users
skip_private=True
private_percentage=80
skip_no_profile_pic=True
no_profile_pic_percentage=100
skip_business=True
skip_non_business=False
business_percentage=100
skip_business_categories=[]
dont_skip_business_categories=['Creators & Celebrities']

# activity settings
do_comment_percentage = 0
do_like_percentage = 80
do_follow_percentage = 70
do_follow_times = 2
do_story_percentage = 50
user_interact_percentage = 60
# Sill chiise a nomber within this and 3 times it
user_interact_amount = 1

accept_follow_requests_amount = 100
accept_follow_requests_sleep_delay = 5

# Will actually use a random number between these and its double
follow_user_followers_amount_of_accounts = 1
follow_user_followers_amount = 5
like_by_tags_amount_of_tags = 2
like_by_tags_amount = 10

# Posts sources
# https://www.instagram.com/the.sunshine.yogi/
source = 'the.sunshine.yogi'

# variables
similar_accounts = [
    'yoga', 'yoga_girl', 'merins_yoga_wanderlust', 'almudena_yogalife', 'aloyoga',
    'simya_evi', 'entrepreneur', 'marieforleo', 'carol_enrico', 'faceintimate', 
    'mssannamaria', 'figsfit'
]
friend_list = []
ignored_users = []

# tag sources:
# https://displaypurposes.com/
# http://best-hashtags.com/
like_tag_list = [
    #YOGA
    "yoga", "meditation", "fitness", "yogainspiration", "yogalife", "love", "yogapractice", 
    "yogaeverydamnday", "yogi", "yogateacher", "namaste", "pilates", "yogalove", "yogaeveryday", 
    "mindfulness", "gym", "workout", "yogagirl", "wellness", "yogaeverywhere", "health", "yogini", 
    "motivation", "yogachallenge", "yogapose", "asana", "fitnessmotivation", "healthylifestyle", "hathayoga",
    "nature", "yogajourney", "o", "peace", "yogaposes", "balance", "selfcare", "healing", "selflove", 
    "instayoga", "reiki", "lifestyle", "sport", "igyoga", "flexibility", "healthy", "yogacommunity", 
    "training", "life", "relax", "yogisofinstagram", "instagood", "yogapants", "vegan", "spirituality", 
    "vinyasa", "yogadaily",
    #FITNESS
    "fitness", "gym", "workout", "fit", "fitnessmotivation", "motivation", "bodybuilding", "training", 
    "health", "fitfam", "lifestyle", "sport", "love", "healthy", "crossfit", "healthylifestyle", 
    "gymlife", "instagood", "personaltrainer", "exercise", "muscle", "weightloss", "gymmotivation", 
    "fitnessmodel", "fitnessgirl", "yoga", "fitspo", "instafit", "wellness",
    "follow", "strong", "nutrition", "like", "life", "fashion", "goals", "running", "instagram", 
    "strength", "fitnessjourney", "fitlife", "fitnessaddict", "model", "healthyfood", "diet", 
    "happy", "photography", "abs", "food", "inspiration", "photooftheday", "bhfyp", "fitnesslife", 
    "gains", "sports", "boxing", "body", "dieta",
    #WELLNESS
    "wellness", "health", "fitness", "healthylifestyle", "selfcare", "healthy", "yoga", "motivation", 
    "love", "beauty", "lifestyle", "nutrition", "wellbeing", "healthyliving", "mentalhealth", "workout", 
    "mindfulness", "gym", "healing", "meditation", "relax", "skincare", "selflove", "weightloss", "fit", 
    "spa", "fitnessmotivation", "massage", "organic",
    "healthyfood", "vegan", "exercise", "cbd", "life", "instagood", "essentialoils", "bodybuilding", 
    "fitfam", "personaltrainer", "inspiration", "training", "holistic", "healthandwellness", "nature", 
    "holistichealth", "covid", "happiness", "plantbased", "detox", "happy", "community", "sport", "benessere", 
    "diet", "anxiety", "healthylife", "energy", "goals",
    #ENTREPRENEURSHIP
    "entrepreneurship", "entrepreneur", "business", "entrepreneurlife", "success", "motivation", 
    "startup", "entrepreneurs", "businessowner", "marketing", "inspiration", "smallbusiness", 
    "hustle", "money", "mindset", "leadership", "entrepreneurmindset", "digitalmarketing", "goals", 
    "lifestyle", "motivationalquotes", "entrepreneurlifestyle", "love", "businesswoman", "branding", 
    "businessman", "startups", "networking", "startuplife",
    "wealth", "realestate", "socialmediamarketing", "instagood", "innovation", "millionaire", 
    "fashion", "millionairemindset", "quotes", "socialmedia", "successquotes", "investing", 
    "entrepreneurquotes", "investment", "instagram", "successful", "womeninbusiness", "life", 
    "businesstips", "finance", "businesscoach", "onlinebusiness", "successmindset", "bitcoin", 
    "networkmarketing", "like", "investor", "work", "workfromhome", "motivational",
]
photo_comments = [
        u'What an amazing shot! :heart_eyes: What do '
        u'you think of my recent shot?',

        u'What an amazing shot! :heart_eyes: I think '
        u'you might also like mine. :wink:',

        u'Wonderful!! :heart_eyes: Would be awesome if '
        u'you would checkout my photos as well!',

        u'Wonderful!! :heart_eyes: I would be honored '
        u'if you would checkout my images and tell me '
        u'what you think. :wink:',

        u'This is awesome!! :heart_eyes: Any feedback '
        u'for my photos? :wink:',

        u'This is awesome!! :heart_eyes:  maybe you '
        u'like my photos, too? :wink:',

        u'I really like the way you captured this. I '
        u'bet you like my photos, too :wink:',

        u'I really like the way you captured this. If '
        u'you have time, check out my photos, too. I '
        u'bet you will like them. :wink:',

        u'Great capture!! :smiley: Any feedback for my '
        u'recent shot? :wink:',

        u'Great capture!! :smiley: :thumbsup: What do '
        u'you think of my recent photo?'
        ]


dont_like = ['dick', 'squirt',
         'kids', 'children', 'child', 'nazi', 'jew', 'judaism', 'muslim', 'islam', 
         'bangladesh', 'hijab', 'niqab', 'farright', 'rightwing', 'conservative', 'death', 
         'racist', 'pussy', 'porn', 'hentai']
