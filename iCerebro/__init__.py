import random
import threading
from datetime import datetime, timedelta
from time import sleep
from typing import List, Union

from django.core.exceptions import ObjectDoesNotExist
from selenium.common.exceptions import WebDriverException, NoSuchElementException

from app_main.models import BotSettings, BotFollowed, BotRunSettings, ProxyAddress
import iCerebro.constants_x_paths as XP
import iCerebro.constants_js_scripts as JS
from iCerebro.navigation import nf_go_to_tag_page, check_if_in_correct_page, nf_go_from_post_to_profile, \
    nf_go_to_user_page, nf_go_to_home, nf_go_to_follow_page, nf_find_and_press_back, nf_scroll_into_view, \
    nf_click_center_of_element, go_to_bot_user_page
from iCerebro.quota_supervisor import QuotaSupervisor
from iCerebro.upload import upload_single_image
from iCerebro.util import Interactions, get_active_users, format_number, nf_validate_user_call, \
    nf_get_all_users_on_element, get_relationship_counts

from iCerebro.util import Jumps
from iCerebro.util_db import is_follow_restricted
from iCerebro.util_follow import follow_user, get_follow, unfollow_loop
from iCerebro.util_like import like_loop
from iCerebro.util_login import login_user
from iCerebro.util_loggers import IceLogger
from iCerebro.run import run


class ICerebro:
    def __init__(
            self,
            settings: BotSettings,
            run_settings: BotRunSettings
    ):
        """
        iCerebro class, contains all the actions the bot can perform

        :param settings:
        :param run_settings:
        """
        self.thread = None
        self.update_thread = None
        self.settings = settings
        self.run_settings = run_settings
        self.instauser = self.settings.instauser
        self.username = self.settings.instauser.username

        # if the user is running the proxy desktop or android app get the port number where it is working
        try:
            self.proxy = ProxyAddress.objects.get(user=self.settings.icerebrouser)
        except ObjectDoesNotExist:
            self.proxy = None

        # custom logger
        self.logger = IceLogger(username=self.username)

        # self info, maybe not needed here, active users is only used by unfollow_users, the other may not be used
        self.followed_by = 0
        self.following_num = 0
        self.active_users = []

        # pyvirtualdisplay may be moved to local variable in run
        self.display = None
        # selenium driver browser instance
        self.browser = None

        # hold the total interactions the bot performed this run
        self.interactions = Interactions()
        # manage amounts of calls of each action
        self.quota_supervisor = QuotaSupervisor(self)
        # use this variable to terminate the nested loops after quotient is reached
        self.quotient_breach = False
        # hold the consecutive jumps and set max of it used with quota supervisor to break loops
        self.jumps = Jumps()

        # helper for checking mandatory languages
        self.check_letters = {}

        # set to true to break most loops and end the run
        self.aborting = False

        # if self.settings.use_image_analysis:
        #     self.ImgAn = ImageAnalysis()
        #        self.settings.classification_model_name, self.settings.detection_model_name)
        # else:
        self.ImgAn = None
        
        self.until_time = None

    def start(self):
        """
        starts 2 threads, one tu run actions based on settings and one to keep updating the settings
        """
        self.logger.info("iCerebro Started")
        self.settings.abort = False
        self.settings.running = True
        self.settings.save()
        
        self.thread = threading.Thread(target=run, args=(self,))
        self.thread.daemon = True
        self.thread.start()
        
        self.update_thread = threading.Thread(target=self.update_settings, args=())
        self.update_thread.daemon = True
        self.update_thread.start()
        
    def update_settings(self):
        """
        updates the settings so changes are applied without needing to restart the bot or it can be stopped
        """
        while not self.aborting:
            # TODO: Think whats a good amount of time between refresh
            sleep(60)
            self.settings.refresh_from_db()
            if self.settings.abort:
                self.logger.info("iCerebro will stop soon")
                self.aborting = True

    def login(self):
        """
        logins the user into instagram - ? and saves account progress?
        """
        self.browser.implicitly_wait(5)

        if not login_user(self):
            self.logger.critical("Unable to login to Instagram, aborting")
            self.aborting = True
            return self

        self.browser.implicitly_wait(15)
        self.logger.info("Logged in successfully")

        # TODO: decide if this is useful or not
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
            amount: int = 20,
            skip_top_posts: bool = True
    ):
        """
        Likes 'amount' (default 20) images per given tag, after liking it may comment, follow or interact with the
        post/account according to bot settings

        :param tags: list of tags to enter
        :param amount: amount of post to like in each tag
        :param skip_top_posts: if the bot should ignore the first 9 post of the tag feed
        """
        if self.aborting:
            return self

        tags = tags or []
        self.quotient_breach = False

        # for each tag in the list
        for index, tag in enumerate(tags):
            # if aborting or quota was breached or its past time according to settings break the loop
            if self.aborting or self.quotient_breach or (self.until_time and datetime.now() > self.until_time):
                break

            # clean tag
            tag = tag.strip()
            tag = tag[1:] if tag[:1] == "#" else tag
            tag_link = "https://www.instagram.com/explore/tags/{}/".format(tag)

            self.logger.info(
                "Like by Tag [{}/{}]: {} - started".format(index + 1, len(tags), tag)
            )

            # navigate to tag page
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

            # change amount if it is more than hte posts the tag has
            if possible_posts is not None:
                amount = possible_posts if amount > possible_posts else amount

            sleep(1)

            # like images
            interactions = like_loop(
                self,
                "Tag [{}/{}]: {}".format(index + 1, len(tags), tag),
                tag_link,
                amount,
                False)
            self.logger.info(
                "Like by Tag [{}/{}]: {} - ended".format(index + 1, len(tags), tag)
            )
            self.logger.info(str(interactions))
            self.interactions += interactions

        return self

    def like_by_users(
            self,
            usernames: List[str],
            amount: int = None,
            users_validated: bool = False
    ):
        """
        Likes 'amount' (default bot settings 'user_interact_amount') images per given user,
        before it starts liking it may follow the user and after each like it may comment the post,
        according to bot settings

        :param usernames: list of usernames to like posts of
        :param amount: amount of post to like in each user feed
        :param users_validated: if users are already considered valid to like them
        """
        if self.aborting:
            return self

        amount = amount or self.settings.user_interact_amount
        usernames = usernames or []
        self.quotient_breach = False

        # for each username
        for index, username in enumerate(usernames):
            # if aborting or quota was breached or its past time according to settings break the loop
            if self.aborting or self.quotient_breach or (self.until_time and datetime.now() > self.until_time):
                break

            # clean username
            username = username.strip()
            user_link = "https://www.instagram.com/{}/".format(username)
            interactions = Interactions()

            self.logger.info(
                "Like by User [{}/{}]: {} - started".format(
                    index + 1, len(usernames), username
                )
            )

            # navigate to user feed
            if not check_if_in_correct_page(self, user_link):
                nf_go_to_user_page(self, username)
                sleep(1)

            # validate user according to settings
            if not users_validated:
                valid, details = nf_validate_user_call(self, username, self.quota_supervisor.LIKE)
                self.logger.info("'{}' is{} a valid user{}".format(
                    username,
                    "" if valid else " not",
                    "" if valid else ": {}".format(details)
                ))
                if not valid:
                    interactions.not_valid_users += 1
                    continue

            # follow user according to settings
            if (
                    self.settings.do_follow
                    and username not in self.settings.dont_include
                    and random.randint(0, 100) <= self.settings.follow_percentage
                    and not is_follow_restricted(self, username)
            ):
                self.logger.debug("Following user")
                follow_state, msg = follow_user(self, "profile", username, None)
                if follow_state is True:
                    interactions.followed += 1
                elif msg == "already followed":
                    interactions.already_followed += 1
                sleep(1)

            # like images
            interactions += like_loop(
                self,
                "User [{}/{}]: {}".format(index + 1, len(usernames), username),
                user_link,
                amount,
                True
            )

            self.logger.info(
                "Like by User [{}/{}]: {} - ended".format(
                    index + 1, len(usernames), username
                )
            )
            self.logger.info(str(interactions))
            self.interactions += interactions

        return self

    def like_by_feed(
            self,
            amount: int = 10
    ):
        """
        Likes 'amount' (default 10) images of the instagram feed, after each like it may comment the post,
        according to bot settings

        :param amount: amount of post to like in feed
        """
        if self.aborting:
            return self

        self.logger.info("Like by Feed - started")
        nf_go_to_home(self)
        interactions = like_loop(self, "Feed", "https://www.instagram.com/", amount, True)
        self.logger.info("Like by Feed - ended")
        self.logger.info(str(interactions))
        self.interactions += interactions
        return self

    def like_by_location(
            self,
            locations: List[str],
            amount: int = 20,
            skip_top_posts: bool = True
    ):
        """
        Likes 'amount' (default 20) images per given location, after liking it may comment, follow or interact with the
        post/account according to bot settings
        Not implemented yet

        :param locations: list of locations to enter
        :param amount: amount of post to like in each tag
        :param skip_top_posts: if the bot should ignore the first 9 post of the location feed
        """
        # TODO
        return self

    def follow_user_follow(
            self,
            relation: str,
            usernames: List[str],
            amount: int = 10,
            randomize: bool = False,
            random_chance: int = 50
    ):
        """
        Follows 'amount' users of 'relation' ("following" or "followers") list of each user in usernames

        :param relation: what list to use, "following" or "followers"
        :param usernames: list of usernames to follow relations of
        :param amount: amount of users to follow for each user in 'usernames'
        :param randomize: if the bot will include a random factor to choose who to follow or
        follow the first 'amount' of usernames on the list
        :param random_chance: chance a user will be followed if using 'randomize'
        """
        if self.aborting:
            return self

        valid = {"followers", "following"}
        if relation not in valid:
            self.logger.info('{} is not a valid relation, using "followers"'.format(relation))
            relation = "followers"

        self.logger.info("Starting to follow users {}".format(relation))

        # for each username
        for index, username in enumerate(usernames):
            # if aborting or quota was breached or its past time according to settings break the loop
            if self.aborting or self.quotient_breach or (self.until_time and datetime.now() > self.until_time):
                break
            
            interactions = Interactions()

            self.logger.info(
                "Follow User {} [{}/{}]: {} - started".format(
                    relation, index + 1, len(usernames), username
                )
            )

            user_link = "https://www.instagram.com/{}".format(username)
            follow_link = "https://www.instagram.com/{}/{}".format(username, relation)

            # navigate to user page
            if not check_if_in_correct_page(self, user_link):
                nf_go_to_user_page(self, username)
                sleep(1)

            # get followers & following counts and change amount if less than desired
            followers_count, following_count = get_relationship_counts(self, username)
            follow_count = following_count if relation == "following" else followers_count
            follow_count = follow_count if follow_count else 0
            actual_amount = amount
            if follow_count < amount:
                actual_amount = follow_count

            # go to relation page
            nf_go_to_follow_page(self, relation, username)
            sleep(2)

            # follow users
            sc_rolled = 0
            scroll_nap = 1.5
            already_interacted_links = []
            while interactions.followed in range(actual_amount):
                # if aborting or quota was breached or its past time according to settings break the loop
                if self.aborting or (self.until_time and datetime.now() > self.until_time):
                    break

                # if quotient was breached break the loop
                if self.jumps.check_follows():
                    self.logger.warning(
                        "Follow quotient reached its peak, leaving Follow User {} activity".format(
                            relation
                        )
                    )
                    # reset jump counter before breaking the loop
                    self.jumps.follows = 0
                    self.quotient_breach = True
                    break

                # if scrolled too much sleep for 5-10 minutes
                if sc_rolled > 100:
                    delay_random = random.randint(300, 600)
                    self.logger.info(
                        "Scrolled too much, sleeping {} minutes and {} seconds".format(
                            int(delay_random/60),
                            delay_random % 60
                        )
                    )
                    sleep(delay_random)
                    sc_rolled = 0

                # get loaded usernames
                users = nf_get_all_users_on_element(self)
                # if no users were grabbed try to go back and load the relation page again
                while len(users) == 0:
                    nf_find_and_press_back(self, user_link)
                    in_user_page = check_if_in_correct_page(self, user_link)
                    if not in_user_page:
                        nf_go_to_user_page(self, username)
                    nf_go_to_follow_page(self, relation, username)
                    # get loaded usernames
                    users = nf_get_all_users_on_element(self)
                    # If after rechecking we are in the correct page there still no are users
                    # the bot is most surely soft blocked from seeing relations, that block doesnt last long usually.
                    # sleep for 5-10 minutes
                    if len(users) == 0:
                        delay_random = random.randint(300, 600)
                        self.logger.info(
                            "Soft block on see followers, "
                            "sleeping {} minutes and {} seconds".format(
                                int(delay_random/60),
                                delay_random % 60
                            )
                        )
                        sleep(delay_random)
                self.logger.debug("Grabbed {} usernames".format(len(users)))

                # first one in the list is un-clickable by bad design on browser instagram, its behind the top bar
                for user in users[1:]:
                    link = user.get_attribute("href")
                    # try to follow first not already interacted user
                    if link not in already_interacted_links:
                        msg = ""
                        try:
                            user_text = user.text
                            user_link2 = "https://www.instagram.com/{}".format(user_text)
                            self.logger.info(
                                "Followed [{}/{}]".format(
                                    interactions.followed,
                                    actual_amount
                                )
                            )
                            # Go to user page
                            self.logger.info("Trying user {}".format(user_text))
                            nf_scroll_into_view(self, user)
                            sleep(1)
                            nf_click_center_of_element(self, user, user_link2)
                            sleep(2)

                            # validate user
                            valid = False
                            if (
                                    user_text not in self.settings.dont_include
                                    and not is_follow_restricted(self, user_text)
                                    and random.randint(0, 100) <= random_chance
                            ):
                                valid, details = nf_validate_user_call(self, user_text, self.quota_supervisor.FOLLOW)
                                self.logger.info("Valid User: {}, details: {}".format(valid, details))
                            # follow user
                            if valid:
                                follow_state, msg = follow_user(self, "profile", user_text)
                                if follow_state is True:
                                    interactions.followed += 1
                                elif msg == "already followed":
                                    interactions.already_followed += 1
                                elif msg == "jumped":
                                    # will break the loop after certain consecutive jumps
                                    self.jumps.follows += 1
                                # interact with user
                                if (
                                        self.settings.do_like
                                        and random.randint(0, 100) <= self.settings.user_interact_percentage
                                ):
                                    self.logger.info("Interacting with user '{}'".format(user_text))
                                    if not check_if_in_correct_page(self, user_link2):
                                        nf_go_from_post_to_profile(self, user_text)
                                    interactions += like_loop(
                                        self,
                                        "Interact with user '{}'".format(user_text),
                                        user_link2,
                                        self.settings.user_interact_amount,
                                        True
                                    )
                            else:
                                interactions.not_valid_users += 1
                        except Exception as e:
                            self.logger.error(e)
                        finally:
                            # go back to relation page and start the loop again
                            sleep(1)
                            nf_find_and_press_back(self, follow_link)
                            in_follow_page = check_if_in_correct_page(self, follow_link)
                            if not in_follow_page:
                                in_user_page = check_if_in_correct_page(self, user_link)
                                if not in_user_page:
                                    nf_go_to_user_page(self, username)
                                nf_go_to_follow_page(self, relation, username)

                            already_interacted_links.append(link)
                            if msg == "block on follow":
                                # raise SoftBlockedException(msg)
                                pass  # TODO: deal with block on follow
                            break
                else:
                    # For loop ended means all users in screen has been interacted with
                    scrolled_to_bottom = self.browser.execute_script(JS.SCROLLED_TO_BOTTOM)
                    # even if we are at the bottom if we were using randomize some users were ignored
                    # so the bot can go back and look again with a higher random chance to foollow the users
                    if scrolled_to_bottom and randomize and random_chance < 100:
                        random_chance += 25
                        self.browser.execute_script(JS.SCROLL_TO_TOP)
                        self.quota_supervisor.add_server_call()
                        sc_rolled += 1
                        sleep(scroll_nap)
                    elif scrolled_to_bottom:
                        # already followed all possibles users
                        break
                    # if not at the bottom of the list
                    # will scroll the screen a bit and look again
                    for i in range(3):
                        self.browser.execute_script(JS.SCROLL_SCREEN)
                        self.quota_supervisor.add_server_call()
                        sc_rolled += 1
                        sleep(scroll_nap)

            sleep(3)
            self.logger.info(
                "Follow User {} [{}/{}] - ended".format(relation, index + 1, len(usernames))
            )
            self.logger.info(str(interactions))
            self.interactions += interactions

        return self

    def follow_by_list(
            self,
            follow_list: List[str],
            users_validated: bool = False
    ):
        """
        Follows users in 'follow_list'

        :param follow_list: list of usernames to follow
        :param users_validated: if users are already considered valid to follow them
        """
        if self.aborting:
            return self

        interactions = Interactions()

        # for each username
        for index, username in enumerate(follow_list):
            # if aborting or quota was breached or its past time according to settings break the loop
            if self.aborting or self.quotient_breach or (self.until_time and datetime.now() > self.until_time):
                break

            # if quotient was breached break the loop
            if self.jumps.check_follows():
                self.logger.warning(
                    "Follow quotient reached its peak, leaving Follow by List activity"
                )
                self.jumps.follows = 0
                self.quotient_breach = True
                break

            self.logger.info("Follow User [{}/{}] - started".format(index + 1, len(follow_list)))
            user_link = "https://www.instagram.com/{}".format(username)

            # skip to next in list if the user is follow restricted
            if is_follow_restricted(self, username):
                interactions.already_followed += 1
                self.logger.info(
                    "Account {} already followed {} times".format(
                        username,
                        self.settings.follow_times
                    )
                )
                continue

            # validate user if not considered valid
            if not users_validated:
                validation, details = nf_validate_user_call(self, username, self.quota_supervisor.FOLLOW)
                if not validation:
                    self.logger.info(
                        "--> Not a valid user: {}".format(details)
                    )
                    interactions.not_valid_users += 1
                    continue

            # follow user
            follow_state, msg = follow_user(self, "profile", username)
            if follow_state is True:
                interactions.followed += 1
                self.logger.debug("user followed")
            elif msg == "already followed":
                interactions.already_followed += 1
            elif msg == "jumped":
                # will break the loop after certain consecutive jumps
                self.jumps.follows += 1

            # interact with user
            if self.settings.do_like and random.randint(0, 100) <= self.settings.user_interact_percentage:
                self.logger.info("Interacting with user '{}'".format(username))
                if not check_if_in_correct_page(self, user_link):
                    nf_go_from_post_to_profile(self, username)
                interactions += like_loop(
                    self,
                    "Interact with user '{}'".format(username),
                    user_link,
                    self.settings.user_interact_amount,
                    True
                )

            self.logger.info(
                "Follow User [{}/{}] - ended".format(index + 1, len(follow_list))
            )

        self.logger.info(str(interactions))
        self.interactions += interactions
        return self

    def follow_by_tag(
            self,
            tags: List[str],
            amount: int = 10,
            skip_top_posts: bool = True
    ):
        # TODO
        return self

    def follow_by_locations(
            self,
            locations: List[str],
            amount: int = 10,
            skip_top_posts: bool = True
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
        """
        Unfollows 'amount' (default 10) users from the bot followings in the 'unfollow_list'
        and from those only the ones in the provided 'track'

        - If 'unfollow_list' is 'iCerebro_followed' the bot will only unfollow users that were followed
          at least 'unfollow_after_hours' before.

        - If 'dont_unfollow_active_users' is set to true then before starting unfollowing users the bot will check the
          last 'posts_to_check' posts it made for which users liked them withing the 'boundary_to_check'
          and wont unfollow those users

        :param amount: amount of users to unfollow
        :param unfollow_list: a List of usernames to unfollow, 'all' or 'iCerebro_followed',
            if 'all' the bot will unfollow randomly from all the users the  bot follows
            if 'iCerebro_followed' it will unfollow only users the bot previously followed by itself
        :param track: 'all' or 'non-followers' unfollow any user or just the ones that dont follow the bot back
        :param unfollow_after_hours: how many hours ago the bot needs to have followed the account for it to be
            considered for unfollowing
        :param dont_unfollow_active_users: if the bot should check which users are active (like your post) and
            dont unfollow them
        :param posts_to_check: how many post to check if dont_unfollow_active_users is True
        :param boundary_to_check: how many users gather from the checked posts checked if dont_unfollow_active_users
            is True, [None: all likers, 0: likers loaded after pressing to see likers [no scrolling],
            n (> 0): stop scrolling if gathered at least  n usernames]
        """
        if self.aborting:
            return self

        # check parameters are valid
        valid_lists = {"all", "iCerebro_followed"}
        if not isinstance(unfollow_list, list) and unfollow_list not in valid_lists:
            self.logger.warning(
                "unfollow_users: 'unfollow_list' must be a list or one of {}. Got: '{}'. Using 'all'".format(
                    valid_lists, unfollow_list
                )
            )
            unfollow_list = "all"
        valid_tracks = {"all", "nonfollowers"}
        if track not in valid_tracks:
            self.logger.warning(
                "unfollow_users: 'track' must be one of {}. Got {}. Using 'all'".format(
                    valid_tracks, track
                )
            )
            track = "all"
        if boundary_to_check and boundary_to_check < 0:
            self.logger.warning(
                "unfollow_users: 'boundary_to_check' must be None or an integer greater or equal to 0. "
                "Got {}. Using '0'".format(boundary_to_check)
            )
            boundary_to_check = None

        self.logger.info("Unfollow Users - started")
        go_to_bot_user_page(self)

        # Get active users
        if dont_unfollow_active_users and posts_to_check and posts_to_check > 0:
            self.active_users = get_active_users(
                self, self.username, posts_to_check, boundary_to_check
            )

        # Get set of users the bot is following
        following_set = get_follow(self, self.username, 'following')

        # Remove the ones who follow back
        if track == "nonfollowers":
            self.logger.info("Unfollowing only users who do not follow back")
            followers_set = get_follow(self, self.username, 'followers')
            following_set = following_set-followers_set

        # if the unfollow list is 'all' the actual unfollow list is following_set
        if unfollow_list == "all":
            unfollow_list = list(following_set)
        # if it is 'iCerebro_followed' query the database for users the bot followed and keep the
        # intersection with following_set
        elif unfollow_list == "iCerebro_followed":
            self.logger.info("Unfollowing from the users followed by iCerebro")
            # query with unfollow_after_hours if requested
            if unfollow_after_hours:
                before_date = datetime.now() - timedelta(hours=unfollow_after_hours)
                bot_followed_query = BotFollowed.objects.filter(bot=self.instauser, date__lte=before_date)
            else:
                bot_followed_query = BotFollowed.objects.filter(bot=self.instauser)
            unfollow_list = [bot_followed.followed.username for bot_followed in bot_followed_query]
            unfollow_list = list(following_set.intersection(set(unfollow_list)))
        # if it is a list of usernames keep the intersection of that list with following_set
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

        # shuffle the list
        random.shuffle(unfollow_list)

        # unfollow users
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
