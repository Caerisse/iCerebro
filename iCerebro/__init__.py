import logging
from time import sleep, time
from typing import List

from pyvirtualdisplay import Display
from selenium.common.exceptions import ElementClickInterceptedException
from sqlalchemy import func

from app_main.models import BotSettings
from iCerebro.database import IgDb, User
from iCerebro.db_utils import scrap_for_user_relationships, store_all_posts_of_user
from iCerebro.image_analisis import ImageAnalysis
from iCerebro.natural_flow import like_by_tags, follow_user_follow, like_by_users, unfollow_users, like_by_feed
from iCerebro.upload import upload_single_image


class ICerebro:

    def __init__(
            self,
            settings: BotSettings
    ):
        self.start_time = time()
        self.settings = settings

        self.username = self.settings.instauser.username
        self.password = self.settings.password

        self.followed_by = 0
        self.following_num = 0

        self.display = Display(visible=0, size=(800, 600))
        self.display.start()

        # use this variable to terminate the nested loops after quotient
        # reaches
        self.quotient_breach = False
        # hold the consecutive jumps and set max of it used with QS to break
        # loops
        self.jumps = {
            "consequent": {"likes": 0, "comments": 0, "follows": 0, "unfollows": 0},
            "limit": {"likes": 7, "comments": 3, "follows": 5, "unfollows": 4},
        }

        self.check_letters = {}

        self.aborting = False

        self.logger = logging.getLogger('db')
        self.extra={'bot_username': self.username}

        if self.settings.use_image_analysis:
            self.ImgAn = ImageAnalysis(
                self.settings.classification_model_name, self.settings.detection_model_name)
        else:
            self.ImgAn = None

        self.browser, err_msg = set_selenium_local_session(self)
        if len(err_msg) > 0:
            raise Exception(err_msg)

    def login(self):
        pass

    def nf_like_by_tags(
            self,
            tags: List[str] = None,
            amount: int = 50,
            skip_top_posts: bool = True,
            use_smart_hashtags: bool = False,
            use_smart_location_hashtags: bool = False,
    ):
        like_by_tags(self, tags, amount, skip_top_posts, use_smart_hashtags, use_smart_location_hashtags)

    def nf_like_by_users(
        self,
        usernames: List[str],
        amount: int = None,
        users_validated: bool = False
    ):
        like_by_users(self, usernames, amount, users_validated)

    def nf_like_by_feed(
            self,
            amount: int = None,
    ):
        like_by_feed(self, amount)

    def nf_follow_user_follow(
            self,
            follow: str,
            usernames: List[str],
            amount: int = 10,
            randomize: bool = False
    ):
        follow_user_follow(self, follow, usernames, amount, randomize)

    def nf_upload_single_image(self, image_name: str, text: str, insta_username: str):
        upload_single_image(self, image_name, text, insta_username)

    def nf_unfollow_users(
            self,
            amount: int = 10,
            custom_list_enabled: bool = False,
            custom_list: list = [],
            custom_list_param: str = "all",
            instapy_followed_enabled: bool = False,
            instapy_followed_param: str = "all",
            nonFollowers: bool = False,
            allFollowing: bool = False,
            style: str = "FIFO",
            unfollow_after: int = None,
            delay_followbackers: int = 0,  # 864000 = 10 days, 0 = don't delay
            sleep_delay: int = 600,
    ):
        unfollow_users(
                self,
                amount,
                custom_list_enabled,
                custom_list,
                custom_list_param,
                instapy_followed_enabled,
                instapy_followed_param,
                nonFollowers,
                allFollowing,
                style,
                unfollow_after,
                delay_followbackers,
                sleep_delay,
        )

    def complete_user_relationships_of_users_already_in_db(self):
        for user in self.db.session.query(User).yield_per(100).enable_eagerloads(False).order_by(func.random()):
            scrap_for_user_relationships(self, user.username)
            sleep(30)

    def complete_posts_of_users_already_in_db(self):
        for user in self.db.session.query(User).yield_per(100).enable_eagerloads(False).order_by(func.random()):
            try:
                store_all_posts_of_user(self, user.username)
            except ElementClickInterceptedException:
                pass
            sleep(30)
