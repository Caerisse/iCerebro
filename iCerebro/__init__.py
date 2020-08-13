import logging
import random
from datetime import datetime, timedelta
from time import sleep, time
from typing import List, Union

from pyvirtualdisplay import Display
from selenium.common.exceptions import WebDriverException, NoSuchElementException

from app_main.models import BotSettings, BotFollowed
import iCerebro.constants_x_paths as XP
import iCerebro.constants_js_scripts as JS
from iCerebro.browser import set_selenium_local_session
from iCerebro.image_analisis import ImageAnalysis
from iCerebro.navigation import nf_go_to_tag_page, check_if_in_correct_page, nf_go_from_post_to_profile, \
    nf_go_to_user_page, go_to_feed, nf_go_to_follow_page, nf_find_and_press_back, nf_scroll_into_view, \
    nf_click_center_of_element, go_to_bot_user_page
from iCerebro.quota_supervisor import QuotaSupervisor
from iCerebro.upload import upload_single_image
from iCerebro.util import Interactions, get_active_users, format_number, nf_validate_user_call, \
    nf_get_all_users_on_element

from iCerebro.util import Jumps
from iCerebro.util_db import is_follow_restricted
from iCerebro.util_follow import follow_user, get_followers, unfollow_loop
from iCerebro.util_like import like_loop
from iCerebro.util_login import login_user


class ICerebro:

    def __init__(
            self,
            settings: BotSettings
    ):
        self.start_time = time()
        self.settings = settings
        self.instauser = self.settings.instauser
        self.username = self.settings.instauser.username

        self.followed_by = 0
        self.following_num = 0
        self.active_users = []

        self.display = Display(visible=0, size=(800, 600))
        self.display.start()

        self.browser, err_msg = set_selenium_local_session(self)
        if len(err_msg) > 0:
            raise Exception(err_msg)

        self.interactions = Interactions()

        self.quota_supervisor = QuotaSupervisor(self)
        # use this variable to terminate the nested loops after quotient is reached
        self.quotient_breach = False
        # hold the consecutive jumps and set max of it used with QS to break loops
        self.jumps = Jumps()

        self.check_letters = {}

        self.aborting = False

        self.logger = logging.getLogger('db')
        self.extra = {'bot_username': self.username}

        if self.settings.use_image_analysis:
            self.ImgAn = ImageAnalysis()
            #    self.settings.classification_model_name, self.settings.detection_model_name)
        else:
            self.ImgAn = None

    def login(self):
        """Used to login the user with username and password"""
        self.browser.implicitly_wait(5)

        if not login_user(self):
            self.logger.critical("Unable to login to Instagram, aborting")
            self.aborting = True
            return self

        # back the page_delay to default, or the value set by the user
        self.browser.implicitly_wait(15)
        self.logger.info("Logged in successfully")
        # try to save account progress
        # try:
        #     save_account_progress(self)
        # except Exception as e:
        #     self.logger.warning(
        #         "Unable to save account progress, skipping data update " + str(e)
        #     )

        return self

    def like_by_tags(
            self,
            tags: List[str] = None,
            amount: int = 50,
            skip_top_posts: bool = True
    ):
        """Likes (default) 50 images per given tag"""
        if self.aborting:
            return self

        # deletes white spaces in tags
        tags = [tag.strip() for tag in tags]
        tags = tags or []
        self.quotient_breach = False

        for index, tag in enumerate(tags):
            if self.quotient_breach:
                break

            self.logger.info(
                "Like by Tag [{}/{}]: {} - started".format(index + 1, len(tags), tag.encode("utf-8"))
            )

            tag = tag[1:] if tag[:1] == "#" else tag
            tag_link = "https://www.instagram.com/explore/tags/{}/".format(tag)
            nf_go_to_tag_page(self, tag)

            # get amount of post with this hashtag
            try:
                possible_posts = self.browser.execute_script(JS.POSSIBLE_POSTS)
            except WebDriverException:
                try:
                    possible_posts = self.browser.find_element_by_xpath(XP.POSSIBLE_POST).text
                    if possible_posts:
                        possible_posts = format_number(possible_posts)
                    else:
                        # raise exception cause it generates the same log I would otherwise put here
                        raise NoSuchElementException
                except NoSuchElementException:
                    self.logger.info(
                        "Failed to get the amount of possible posts in {} tag".format(tag)
                    )
                    possible_posts = None

            self.logger.info(
                "Desired amount: {}  |  top posts [{}] |  possible posts: "
                "{}".format(
                    amount,
                    "enabled" if not skip_top_posts else "disabled",
                    possible_posts,
                )
            )

            if possible_posts is not None:
                amount = possible_posts if amount > possible_posts else amount
            # sometimes pages do not have the correct amount of posts as it is
            # written there, it may be cos of some posts is deleted but still keeps
            # counted for the tag

            sleep(1)

            interactions = like_loop(self, "Tag", tag_link, amount, False)
            self.logger.info(
                "Like by Tag [{}/{}]: {} - ended".format(index + 1, len(tags), tag.encode("utf-8"))
            )
            self.logger.info(interactions.__str__)
            self.interactions += interactions

        return self

    def like_by_users(
            self,
            usernames: List[str],
            amount: int = None,
            users_validated: bool = False
    ):
        """Likes some amounts of images for each usernames"""
        if self.aborting:
            return self

        amount = amount or self.settings.user_interact_amount
        usernames = usernames or []
        self.quotient_breach = False

        for index, username in enumerate(usernames):
            if self.quotient_breach:
                break
            interactions = Interactions()
            self.logger.info(
                "Like by User [{}/{}]: {} - started".format(
                    index + 1, len(usernames), username.encode("utf-8")
                )
            )
            user_link = "https://www.instagram.com/{}/".format(username)
            if not check_if_in_correct_page(self, user_link):
                if len(usernames) == 1 and users_validated:
                    nf_go_from_post_to_profile(self, username)
                else:
                    nf_go_to_user_page(self, username)

            if not users_validated:
                validation, details = nf_validate_user_call(self, username, self.quota_supervisor.LIKE)
                if not validation:
                    self.logger.info(
                        "{} isn't a valid user: {}".format(username.encode("utf-8"), details)
                    )
                    interactions.not_valid_users += 1
                    continue

            interactions += like_loop(self, "User", user_link, amount, users_validated)

            self.logger.info(
                "Like by User [{}/{}]: {} - ended".format(
                    index + 1, len(usernames), username.encode("utf-8")
                )
            )
            self.logger.info(interactions.__str__)
            self.interactions += interactions

        return self

    def like_by_feed(
            self,
            amount
    ):
        if self.aborting:
            return self

        self.logger.info("Like by Feed - started")
        go_to_feed(self)
        interactions = like_loop(self, "Feed", "https://www.instagram.com/", amount, True)
        self.logger.info("Like by Feed - ended")
        self.logger.info(interactions.__str__)
        self.interactions += interactions
        return self

    def like_by_location(
            self,
            locations: List[str],
            amount: int = 50,
            skip_top_posts: bool = True
    ):
        # TODO
        return self

    def follow_user_follow(
            self,
            follow: str,
            usernames: List[str],
            amount: int = 10,
            randomize: bool = False
    ):
        if self.aborting:
            return self

        valid = {"followers", "followings"}
        if follow not in valid:
            raise ValueError(
                "follow_user_follow: follow must be one of %r." % valid)

        self.logger.info("Starting to follow users {}".format(follow))

        for index, username in enumerate(usernames):
            interactions = Interactions()
            self.logger.info("Follow User {} [{}/{}] - started".format(follow, index + 1, len(usernames)))
            self.logger.info("--> {}".format(username.encode("utf-8")))

            nf_go_to_user_page(self, username)
            sleep(1)

            user_link = "https://www.instagram.com/{}".format(username)
            follow_link = "https://www.instagram.com/{}/{}".format(username, follow)

            # TODO: get follow count
            follow_count = 10
            actual_amount = amount
            if follow_count < amount:
                actual_amount = follow_count

            self.logger.info("About to go to {} page".format(follow))
            nf_go_to_follow_page(self, follow, username)
            sleep(2)

            sc_rolled = 0
            scroll_nap = 1.5
            already_interacted_links = []
            random_chance = 50 if randomize else 100
            try:
                while interactions.followed in range(0, actual_amount):
                    if self.jumps.check_follows():
                        self.logger.warning(
                            "Follow quotient reached its peak, leaving Follow User {} activity".format(
                                follow
                            )
                        )
                        # reset jump counter before breaking the loop
                        self.jumps.follows = 0
                        self.quotient_breach = True
                        break

                    if sc_rolled > 100:
                        delay_random = random.randint(400, 600)
                        self.logger.info(
                            "Scrolled too much, sleeping {} minutes and {} seconds".format(
                                int(delay_random/60),
                                delay_random % 60
                            )
                        )
                        sleep(delay_random)
                        sc_rolled = 0

                    users = nf_get_all_users_on_element(self)
                    while len(users) == 0:
                        nf_find_and_press_back(self, user_link)
                        in_user_page = check_if_in_correct_page(self, user_link)
                        if not in_user_page:
                            nf_go_to_user_page(self, username)
                        nf_go_to_follow_page(self, follow, username)
                        users = nf_get_all_users_on_element(self)
                        if len(users) == 0:
                            delay_random = random.randint(200, 300)
                            self.logger.info(
                                "Soft block on see followers, "
                                "sleeping {} minutes and {} seconds".format(
                                    int(delay_random/60),
                                    delay_random % 60
                                )
                            )
                            sleep(300)
                    self.logger.info("Grabbed {} usernames".format(len(users)))

                    # Interact with links instead of just storing them
                    for user in users[1:]:
                        link = user.get_attribute("href")
                        if link not in already_interacted_links:
                            msg = ""
                            try:
                                user_text = user.text
                                user_link2 = "https://www.instagram.com/{}".format(user_text)
                                self.logger.info("Followed [{}/{}]".format(
                                    interactions.followed,
                                    actual_amount
                                )
                                )
                                self.logger.info("Trying user {}".format(user_text.encode("utf-8")))
                                nf_scroll_into_view(self, user)
                                sleep(1)
                                nf_click_center_of_element(self, user, user_link2)
                                sleep(2)
                                valid = False
                                if (
                                        user_text not in self.settings.dont_include
                                        and not is_follow_restricted(self, user_text)
                                        and random.randint(0, 100) <= random_chance
                                ):
                                    valid, details = nf_validate_user_call(self, user_text, self.quota_supervisor.FOLLOW)
                                    self.logger.info("Valid User: {}, details: {}".format(valid, details))
                                if valid:
                                    follow_state, msg = follow_user(self, "profile", user_text)
                                    if follow_state is True:
                                        interactions.followed += 1
                                        self.logger.info("Followed '{}'".format(user_text))
                                    else:
                                        self.logger.info("Not following")
                                        sleep(1)
                                    if random.randint(0, 100) <= self.settings.user_interact_percentage:
                                        self.logger.info(
                                            "Going to interact with user '{}'".format(
                                                user_text
                                            )
                                        )
                                        # disable re-validating user in like_by_users
                                        self.like_by_users(
                                            [user_text],
                                            None,
                                            True,
                                        )
                                else:
                                    interactions.not_valid_users += 1
                            except Exception as e:
                                self.logger.error(e)
                            finally:
                                sleep(5)
                                nf_find_and_press_back(self, follow_link)
                                in_follow_page = check_if_in_correct_page(self, follow_link)
                                if not in_follow_page:
                                    in_user_page = check_if_in_correct_page(self, user_link)
                                    if not in_user_page:
                                        nf_go_to_user_page(self, username)
                                    nf_go_to_follow_page(self, follow, username)

                                already_interacted_links.append(link)
                                if msg == "block on follow":
                                    pass  # TODO: deal with block on follow
                                break
                    else:
                        # For loop ended means all users in screen has been interacted with
                        scrolled_to_bottom = self.browser.execute_script(JS.SCROLLED_TO_BOTTOM)
                        if scrolled_to_bottom and randomize and random_chance < 100:
                            random_chance += 25
                            self.browser.execute_script(JS.SCROLL_TO_TOP)
                            self.quota_supervisor.add_server_call()
                            sc_rolled += 1
                            sleep(scroll_nap)
                        elif scrolled_to_bottom:
                            # already followed all possibles users
                            break
                        # will scroll the screen a bit and reload
                        for i in range(3):
                            self.browser.execute_script(JS.SCROLL_SCREEN)
                            self.quota_supervisor.add_server_call()
                            sc_rolled += 1
                            sleep(scroll_nap)

            except Exception:
                raise

            sleep(3)
            self.logger.info(
                "Follow User {} [{}/{}] - ended".format(follow, index + 1, len(usernames))
            )
            self.logger.info(interactions.__str__)
            self.interactions += interactions

        return self

    def follow_by_list(
            self,
            follow_list: list,
            users_validated: bool = False,
    ):
        if self.aborting:
            return self

        interactions = Interactions()

        for index, username in enumerate(follow_list):
            self.logger.info("Follow User [{}/{}] - started".format(index + 1, len(follow_list)))
            if self.jumps.check_follows():
                self.logger.warning(
                    "--> Follow quotient reached its peak!\t~leaving follow_by_list"
                )
                self.jumps.follows = 0
                self.quotient_breach = True
                break
            if is_follow_restricted(self, username):
                interactions.already_followed += 1
                self.logger.info(
                    "Account {} already followed {} times".format(
                        username,
                        self.settings.follow_times
                    )
                )
                continue

            if not users_validated:
                validation, details = nf_validate_user_call(self, username, self.quota_supervisor.FOLLOW)
                if not validation:
                    self.logger.info(
                        "--> Not a valid user: {}".format(details)
                    )
                    interactions.not_valid_users += 1
                    continue

            follow_state, msg = follow_user(self, "profile", username)
            if follow_state is True:
                interactions.followed += 1
                self.logger.info("user followed")
            elif msg == "already followed":
                interactions.already_followed += 1

            elif msg == "jumped":
                # will break the loop after certain consecutive jumps
                self.jumps.follows += 1

            if self.settings.do_like and random.randint(0, 100) <= self.settings.user_interact_percentage:
                self.logger.info(
                    "Going to interact with user '{}'".format(username)
                )
                # disable re-validating user in like_by_users
                self.like_by_users(
                    [username],
                    None,
                    True,
                )

            self.logger.info(
                "Follow User [{}/{}] - ended".format(index + 1, len(follow_list))
            )

        self.logger.info(interactions.__str__)
        self.interactions += interactions
        return self

    def follow_by_tag(
            self,
            tags: List[str],
            amount: int = 10,
            skip_top_posts: bool = True,
    ):
        # TODO
        return self

    def follow_by_locations(
            self,
            locations: List[str],
            amount: int = 10,
            skip_top_posts: bool = True,
    ):
        # TODO
        return self

    def unfollow_users(
            self,
            amount: int = 10,
            unfollow_list: Union[list, str] = "all",
            track: str = "all",
            unfollow_after_hours: int = None,
            dont_unfollow_active_users: bool = False,
            posts_to_check: int = None,
            boundary_to_check: int = None
    ):
        """Unfollows (default) 10 users from your following list"""
        if self.aborting:
            return self

        valid_lists = {"all", "iCerebro_followed"}
        if not isinstance(unfollow_list, list) or unfollow_list not in valid_lists:
            raise ValueError("unfollow_users: use_list must be a list or one of %r." % valid_lists)
        valid_tracks = {"all", "nonfollowers"}
        if track not in valid_tracks:
            raise ValueError("unfollow_users: custom_list_param must be one of %r." % valid_tracks)

        self.logger.info("Unfollow Users - started")
        go_to_bot_user_page(self)

        if dont_unfollow_active_users and posts_to_check and posts_to_check > 0:
            self.active_users = get_active_users(
                self, self.username, posts_to_check, boundary_to_check
            )

        following_query = self.instauser.following
        following_list = [following.username for following in following_query]
        following_set = set(following_list)
        if track == "nonfollowers":
            self.logger.info("Unfollowing only users who do not follow back")
            followers_list = get_followers(self, self.username)
            following_set = following_set-set(followers_list)

        if unfollow_list == "all":
            unfollow_list = list(following_set)
        elif unfollow_list == "iCerebro_followed":
            self.logger.info("Unfollowing from the users followed by iCerebro")
            if unfollow_after_hours:
                before_date = datetime.now() - timedelta(hours=unfollow_after_hours)
                bot_followed_query = BotFollowed.objects.filter(bot=self.username, date_lte=before_date)
            else:
                bot_followed_query = BotFollowed.objects.filter(bot=self.username)
            unfollow_list = [bot_followed.followed.username for bot_followed in bot_followed_query]
            unfollow_list = list(following_set.intersection(set(unfollow_list)))
        else:
            self.logger.info("Unfollowing from the list of pre-defined usernames")
            unfollow_list = list(following_set.intersection(set(unfollow_list)))

        available = len(unfollow_list)
        if amount > available:
            self.logger.info(
                "There are less users to unfollow than you have requested: "
                "{}/{}, using available amount".format(available, amount)
            )
            amount = available

        random.shuffle(unfollow_list)

        try:
            unfollowed = unfollow_loop(self, unfollow_list, amount)
            self.logger.info("Total people unfollowed: {}".format(unfollowed))
            self.interactions.unfollowed += unfollowed

        except Exception as exc:
            if isinstance(exc, RuntimeWarning):
                self.logger.warning("Warning: {} , stopping unfollow_users".format(exc))
                return self
            else:
                self.logger.error("An error occurred: {}".format(exc))
                self.aborting = True
                return self

        return self

    def upload_single_image(self, image_name: str, text: str, insta_username: str):
        upload_single_image(self, image_name, text, insta_username)

    # TODO: make complaint with django ORM
    # def complete_user_relationships_of_users_already_in_db(self):
    #     for user in self.db.session.query(User).yield_per(100).enable_eagerloads(False).order_by(func.random()):
    #         scrap_for_user_relationships(self, user.username)
    #         sleep(30)
    #
    # def complete_posts_of_users_already_in_db(self):
    #     for user in self.db.session.query(User).yield_per(100).enable_eagerloads(False).order_by(func.random()):
    #         try:
    #             store_all_posts_of_user(self, user.username)
    #         except ElementClickInterceptedException:
    #             pass
    #         sleep(30)
