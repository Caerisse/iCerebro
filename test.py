# Imports
from natural_flow import MyInstaPy
import random
import argparse
import os
import sys

args = {}
args['account'] = 'testingaccount2020'

sys.path.append('./{}'.format(args['account']))

# Login credentials
from credentials import insta_username, insta_password
# Account config
import config

session = MyInstaPy(username=insta_username,
                    password=insta_password,
                    want_check_browser=False,
                    headless_browser=config.headless_browser,
                    geckodriver_path='./{}/geckodriver'.format(args['account']))

session.login()

session.nf_like_by_tags(random.sample(config.like_tag_list, random.randint(5, 10)), 
                        amount=random.randint(10, 20),
                        skip_top_posts=False, 
                        interact=True )

