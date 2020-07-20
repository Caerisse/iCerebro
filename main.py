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

try:
    while True:
        pass
except KeyboardInterrupt:
    pass
except ConnectionRefusedError:
    print("User: {} was blocked by instagram".format(insta_username))
finally:
    session.end()
