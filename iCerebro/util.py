import signal
import unicodedata
from contextlib import contextmanager
from time import sleep, time, perf_counter
import random
import re
from typing import List, Tuple

from platform import system
from subprocess import call
from selenium.webdriver.remote.webelement import WebElement

from selenium.common.exceptions import NoSuchElementException, JavascriptException, StaleElementReferenceException
from selenium.common.exceptions import WebDriverException

import iCerebro.constants_x_paths as XP
import iCerebro.constants_js_scripts as JS
import iCerebro.constants_css_selectors as CS
from iCerebro.util_loggers import LogDecorator
from iCerebro.navigation import nf_click_center_of_element, get_current_url, explicit_wait, \
    nf_go_from_post_to_profile, nf_find_and_press_back, go_to_bot_user_page, nf_go_to_user_page, nf_scroll_into_view, \
    check_if_in_correct_page, check_for_error, SoftBlockedException
from iCerebro.util_db import store_user, is_in_blacklist

default_profile_pic_instagram = [
    "https://instagram.flas1-2.fna.fbcdn.net/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
    "https://scontent-yyz1-1.cdninstagram.com/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
    "https://instagram.faep12-1.fna.fbcdn.net/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
    "https://instagram.fbts2-1.fna.fbcdn.net/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
    "https://scontent-mia3-1.cdninstagram.com/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
]
next_screenshot = 1


class Interactions:
    def __init__(
            self,
            liked_img=0,
            already_liked=0,
            liked_comments=0,
            commented=0,
            replied_to_comments=0,
            followed=0,
            already_followed=0,
            unfollowed=0,
            inap_img=0,
            not_valid_users=0,
            video_played=0,
            already_Visited=0,
            stories_watched=0,
            reels_watched=0
    ):
        self.liked_img = liked_img
        self.already_liked = already_liked
        self.liked_comments = liked_comments
        self.commented = commented
        self.replied_to_comments = replied_to_comments
        self.followed = followed
        self.already_followed = already_followed
        self.unfollowed = unfollowed
        self.inap_img = inap_img
        self.not_valid_users = not_valid_users
        self.video_played = video_played
        self.already_Visited = already_Visited
        self.stories_watched = stories_watched
        self.reels_watched = reels_watched

    def __add__(self, other):
        return (
            Interactions(
                self.liked_img + other.liked_img,
                self.already_liked + other.already_liked,
                self.liked_comments + other.liked_comments,
                self.commented + other.commented,
                self.replied_to_comments + other.replied_to_comments,
                self.followed + other.followed,
                self.already_followed + other.already_followed,
                self.unfollowed + other.unfollowed,
                self.inap_img + other.inap_img,
                self.not_valid_users + other.not_valid_users,
                self.video_played + other.video_played,
                self.already_Visited + other.already_Visited,
                self.stories_watched + other.stories_watched,
                self.reels_watched + other.reels_watched
            )
        )

    def __str__(self):
        string = "Interactions: "
        string += "\nLiked Images: {}".format(self.liked_img) if self.liked_img != 0 else ""
        string += "\nAlready Liked Images: {}".format(self.already_liked) if self.already_liked != 0 else ""
        string += "\nComments Liked: {}".format(self.liked_comments) if self.liked_comments != 0 else ""
        string += "\nComments Made: {}".format(self.commented) if self.commented != 0 else ""
        string += "\nComments Replied: {}".format(self.replied_to_comments) if self.replied_to_comments != 0 else ""
        string += "\nFollowed: {}".format(self.followed) if self.followed != 0 else ""
        string += "\nAlready Followed: {}".format(self.already_followed) if self.already_followed != 0 else ""
        string += "\nUnfollowed: {}".format(self.unfollowed) if self.unfollowed != 0 else ""
        string += "\nInappropriate Images: {}".format(self.inap_img) if self.inap_img != 0 else ""
        string += "\nNot valid Users: {}".format(self.not_valid_users) if self.not_valid_users != 0 else ""
        string += "\nVideos Played: {}".format(self.video_played) if self.video_played != 0 else ""
        string += "\nAlready Visited: {}".format(self.already_Visited) if self.already_Visited != 0 else ""
        string += "\nStories Watched: {}".format(self.stories_watched) if self.stories_watched != 0 else ""
        string += "\nReels Watched: {}".format(self.reels_watched) if self.reels_watched != 0 else ""
        string = string if string != "Interactions: " else "No interactions recorded"
        return string


class Jumps:
    def __init__(self):
        self.likes = 0
        self.comments = 0
        self.follows = 0
        self.unfollows = 0

    def check_likes(self):
        return self.likes >= 7

    def check_comments(self):
        return self.comments >= 3

    def check_follows(self):
        return self.likes >= 5

    def check_unfollows(self):
        return self.likes >= 4


def sleep_while_blocked(self):
    while True:
        delay_random = random.randint(300, 600)
        self.logger.info(
            "Bot is soft blocked will sleep for {} minutes and {} seconds and check if it can continue".format(
                int(delay_random/60),
                delay_random % 60
            )
        )
        sleep(delay_random)
        try:
            self.browser.execute_script(JS.RELOAD)
            self.quota_supervisor.add_server_call()
            check_for_error(self)
            break
        except SoftBlockedException:
            pass


def nf_get_all_posts_on_element(
        element: WebElement
) -> List[WebElement]:
    return element.find_elements_by_xpath(XP.POSTS_ON_ELEMENT)


@LogDecorator()
def nf_get_all_users_on_element(
        self
) -> List[WebElement]:
    # return element.find_elements_by_xpath('//li/div/div[1]/div[2]/div[1]/a')
    return self.browser.find_elements_by_xpath(XP.USERS_ON_ELEMENT)


@LogDecorator()
def nf_validate_user_call(
        self,
        username: str,
        action: str,
        post_link: str = None,
) -> Tuple[bool, str]:
    """Checks if user can be liked according to declared settings

   Also stores user data in database if appropriate

   :returns: valid, reason
   """
    t = perf_counter()
    followers_count = None
    following_count = None
    number_of_posts = None
    if username == self.username:
        return False, "Can not follow self"

    if username in self.settings.ignore_users:
        return False, "'{}' is in the 'ignore_users' list".format(username)

    if is_in_blacklist(self, username, action):
        return False, "'{}' is in the 'blacklist' for current campaign and action".format(username)

    if not any(
            [self.settings.potency_ratio,
             self.settings.delimit_by_numbers,
             self.settings.max_followers,
             self.settings.max_following,
             self.settings.min_followers,
             self.settings.min_following,
             self.settings.min_posts,
             self.settings.max_posts,
             self.settings.skip_private,
             self.settings.skip_private_percentage,
             self.settings.skip_no_profile_pic,
             self.settings.skip_no_profile_pic_percentage,
             self.settings.skip_business,
             self.settings.skip_non_business,
             self.settings.skip_business_percentage,
             self.settings.skip_business_categories,
             self.settings.skip_bio_keyword]
    ):
        # Nothing to check, skip going to user page and then back for nothing
        return True, "Valid user"

    try:
        if post_link:
            nf_go_from_post_to_profile(self, username)
        # Checks the potential of target user by relationship status in order
        # to delimit actions within the desired boundary
        if (
                self.settings.potency_ratio
                or self.settings.delimit_by_numbers
                and (self.settings.max_followers or self.settings.max_following or
                     self.settings.min_followers or self.settings.min_following)
        ):

            relationship_ratio = None
            reverse_relationship = False

            # get followers & following counts
            followers_count, following_count = get_relationship_counts(self, username)

            potency_ratio = self.settings.potency_ratio if self.settings.potency_ratio else None
            if self.settings.potency_ratio:
                if self.settings.potency_ratio >= 0:
                    potency_ratio = self.settings.potency_ratio
                else:
                    potency_ratio = -self.settings.potency_ratio
                    reverse_relationship = True

            # division by zero is bad
            followers_count = 1 if followers_count == 0 else followers_count
            following_count = 1 if following_count == 0 else following_count

            if followers_count and following_count:
                relationship_ratio = (
                    float(followers_count) / float(following_count)
                    if not reverse_relationship
                    else float(following_count) / float(followers_count)
                )

            self.logger.info(
                "User: '{}'  |> followers: {}  |> following: {}  |> relationship "
                "ratio: {}".format(
                    username,
                    followers_count if followers_count else "unknown",
                    following_count if following_count else "unknown",
                    "{:.2f}".format(relationship_ratio) if relationship_ratio else "unknown",
                )
            )

            if followers_count or following_count:
                if potency_ratio and relationship_ratio and relationship_ratio < potency_ratio:
                    return False, "Potency ratio not satisfied"

                if self.settings.delimit_by_numbers:
                    if followers_count:
                        if self.settings.max_followers:
                            if followers_count > self.settings.max_followers:
                                return False, "'{}'s followers count exceeds " \
                                              "maximum limit".format(username)

                        if self.settings.min_followers:
                            if followers_count < self.settings.min_followers:
                                return False, "'{}'s followers count is less than " \
                                              "minimum limit".format(username)

                    if following_count:
                        if self.settings.max_following:
                            if following_count > self.settings.max_following:
                                return False, "'{}'s following count exceeds " \
                                              "maximum limit".format(username)

                        if self.settings.min_following:
                            if following_count < self.settings.min_following:
                                return False, "'{}'s following count is less than " \
                                              "minimum limit".format(username)

        if self.settings.min_posts or self.settings.max_posts:
            # if you are interested in relationship number of posts boundaries
            try:
                number_of_posts = get_number_of_posts(self)
                if number_of_posts is None:
                    raise NoSuchElementException
            except NoSuchElementException or WebDriverException:
                self.logger.error("Couldn't get number of posts")
                return False, "Couldn't get number of posts"

            if self.settings.max_posts:
                if number_of_posts > self.settings.max_posts:
                    reason = (
                        "Number of posts ({}) of '{}' exceeds the maximum limit "
                        "given {}".format(number_of_posts, username, self.settings.max_posts)
                    )
                    return False, reason
            if self.settings.min_posts:
                if number_of_posts < self.settings.min_posts:
                    reason = (
                        "Number of posts ({}) of '{}' is less than the minimum "
                        "limit given {}".format(number_of_posts, username, self.settings.min_posts)
                    )
                    return False, reason

        # Skip users
        # skip private
        if self.settings.skip_private:
            try:
                self.browser.find_element_by_xpath(XP.IS_PRIVATE_PROFILE)
                is_private = True
            except NoSuchElementException:
                is_private = False
            if is_private and (random.randint(0, 100) <= self.settings.skip_private_percentage):
                return False, "{} is private account, skipping".format(username)

        # skip no profile pic
        if self.settings.skip_no_profile_pic:
            try:
                profile_pic = get_user_data(self, JS.PROFILE_PIC)
            except WebDriverException:
                self.logger.error("Couldn't get profile picture")
                return False, "Couldn't get profile picture"
            if (
                    (profile_pic in default_profile_pic_instagram
                     or str(profile_pic).find("11906329_960233084022564_1448528159_a.jpg") > 0)
                    and (random.randint(0, 100) <= self.settings.skip_no_profile_pic_percentage)
            ):
                return False, "{} has default instagram profile picture".format(username)

        # skip business
        if self.settings.skip_business or self.settings.skip_non_business:
            # if is business account skip under conditions
            try:
                is_business_account = get_user_data(self, JS.BUSINESS_ACCOUNT)
            except WebDriverException:
                self.logger.error("Couldn't get if user is a business account")
                return False, "Couldn't get if user is a business account",

            if self.settings.skip_non_business and not is_business_account:
                return False, "{} isn't a business account, skipping".format(username)

            if is_business_account:
                try:
                    category = get_user_data(self, JS.BUSINESS_CATEGORY)
                except WebDriverException:
                    self.logger.error("Couldn't get business category")
                    return False, "Couldn't get business category"

                if category not in self.settings.dont_skip_business_categories:
                    if category in self.settings.skip_business_categories:
                        return (
                            False,
                            "'{}' is a business account in the undesired category of '{}'".format(
                                username, category)
                        )
                    elif random.randint(0, 100) <= self.settings.skip_business_percentage:
                        return False, "'{}' is business account, skipping".format(username)

        if len(self.settings.skip_bio_keyword) != 0:
            # if contain stop words then skip
            try:
                profile_bio = get_user_data(self, JS.BIOGRAPHY)
            except WebDriverException:
                self.logger.error("Couldn't get get user bio")
                return False, "Couldn't get get user bio"
            for bio_keyword in self.settings.skip_bio_keyword:
                if bio_keyword.lower() in profile_bio.lower():
                    return (
                        False,
                        "'{}' has a bio keyword '{}', skipping".format(
                            username, bio_keyword
                        ),
                    )

        # if everything is ok
        return True, "Valid user"

    except NoSuchElementException:
        return False, "Unable to locate element"
    finally:
        self.logger.debug("Storing User")
        store_user(username, followers_count, following_count, number_of_posts)
        if post_link:
            nf_find_and_press_back(self, post_link)
        elapsed_time = perf_counter() - t
        self.logger.info("Validate user elapsed time: {:.0f} seconds".format(elapsed_time))


@LogDecorator()
def is_private_profile(
        self,
        following=True
):
    try:
        is_private = get_user_data(self, JS.IS_PRIVATE)
    except WebDriverException:
        return None
    # double check with xpath that should work only when we not following a user
    if is_private and not following:
        self.logger.info("Is private account you're not following.")
        body_elem = self.browser.find_element_by_tag_name("body")
        is_private = body_elem.find_element_by_xpath(XP.IS_PRIVATE)
    return is_private


@LogDecorator()
def get_number_of_posts(self):
    """Get the number of posts from the profile screen"""
    num_of_posts = None
    try:
        num_of_posts = get_user_data(self, JS.NUMBER_OF_POST)
    except WebDriverException:
        try:
            num_of_posts_txt = self.browser.find_element_by_xpath(XP.NUM_OF_POSTS_TXT).text
        except NoSuchElementException:
            try:
                num_of_posts_txt = self.browser.find_element_by_xpath(XP.NUM_OF_POSTS_TXT_NO_SUCH_ELEMENT).text
            except NoSuchElementException:
                num_of_posts_txt = None
        if num_of_posts_txt:
            num_of_posts_txt = num_of_posts_txt.replace(" ", "")
            num_of_posts_txt = num_of_posts_txt.replace(",", "")
            num_of_posts = int(num_of_posts_txt)

    return num_of_posts


@LogDecorator()
def get_user_data(
        self,
        query: str,
        base_query_1: str = JS.BASE_QUERY_1,
        base_query_2: str = JS.BASE_QUERY_2,
):
    first_query = True
    try:
        try:
            data = self.browser.execute_script(base_query_1 + query)
        except WebDriverException:
            first_query = False
            self.browser.execute_script(JS.RELOAD)
            self.quota_supervisor.add_server_call()
            data = self.browser.execute_script(base_query_2 + query)
        return data
    except JavascriptException:
        check_for_error(self)
        self.logger.debug(
            "JavascriptException in get_user_data, current url: {} trying query {}".format(
                get_current_url(self), (base_query_1 if first_query else base_query_2) + query
            )
        )
        raise WebDriverException


# TODO: rewrite so it uses less graphql
@LogDecorator()
def get_active_users(
        self,
        username: str,
        posts_amount: int,
        boundary: int = None
):
    """Returns a list with usernames who liked the latest n posts"""
    start_time = time()
    user_link = "https://www.instagram.com/{}/".format(username)
    if not check_if_in_correct_page(self, user_link):
        if username == self.username:
            go_to_bot_user_page(self)
        else:
            nf_go_to_user_page(self, username)

    total_posts = get_number_of_posts(self)

    if total_posts and posts_amount > total_posts:
        posts_amount = total_posts

    message = (
        "without boundary (all users)" if boundary is None
        else "using only the visible usernames from posts without scrolling" if boundary == 0
        else "with a maximum of {} per post".format(boundary)
    )
    # posts argument is the number of posts to collect usernames
    self.logger.info(
        "Getting active users who liked the latest {} posts {}".format(posts_amount, message)
    )
    active_users = []
    already_checked_links = []
    sc_rolled = 0
    count = 0
    while count <= posts_amount:
        if sc_rolled > 90:
            delay_random = random.randint(400, 600)
            self.logger.info(
                "Scrolled too much. Sleeping {} minutes and {} seconds".format(
                    int(delay_random / 60),
                    delay_random % 60
                )
            )
            sc_rolled = 0
        main_elem = self.browser.find_element_by_tag_name("main")
        posts = nf_get_all_posts_on_element(main_elem)
        for post in posts:
            link = post.get_attribute("href")
            if link not in already_checked_links:
                sleep(1)
                nf_scroll_into_view(self, post)
                sleep(1)
                nf_click_center_of_element(self, post, link)
                success, active_users_for_post = get_likers(self, link, boundary)
                if success:
                    count += 1
                    self.logger.info(
                        "Post {} - Likers recorded: {}".format(
                            count, len(active_users_for_post)
                        )
                    )
                    for user in active_users_for_post:
                        active_users.append(user)
                sleep(1)
                close_dialog_box(self)
                self.browser.back()
                # nf_find_and_press_back(self, user_link)
                already_checked_links.append(link)
                break
        else:
            # For loop ended means all posts in screen has been interacted with
            # will scroll the screen a bit and reload
            for i in range(3):
                self.browser.execute_script(JS.SCROLL_SCREEN)
                self.quota_supervisor.add_server_call()
                sc_rolled += 1
                sleep(3)
    time_taken = time() - start_time
    # delete duplicated users
    active_users = list(set(active_users))
    self.logger.info(
        "Gathered a total of {} unique active followers from the latest {} "
        "posts in {} minutes and {} seconds".format(
            len(active_users),
            count,
            int(time_taken / 60),
            time_taken % 60
        )
    )
    return active_users


@LogDecorator()
def get_like_count(
        self,
) -> int:
    try:
        likes_count = self.browser.find_element_by_xpath(XP.LIKERS_COUNT).text
    except NoSuchElementException:
        likes_count = None
    if likes_count:
        return format_number(likes_count)
    else:
        try:
            return get_user_data(self, JS.LIKERS_COUNT, base_query_2=JS.ENTRY_DATA)
        except WebDriverException:
            try:
                likes_count = self.browser.find_element_by_css_selector(CS.LIKES_COUNT).text
                if likes_count:
                    return format_number(likes_count)
                else:
                    self.logger.info("Failed to check likes count, empty string")
                    return 0
            except NoSuchElementException:
                self.logger.info("Failed to check likes count")
                return 0


@LogDecorator()
def get_likers(
        self,
        link: str,
        boundary: int = None
) -> Tuple[bool, list]:
    likers_count = get_like_count(self)
    try:
        likes_button = self.browser.find_elements_by_xpath(XP.LIKES_BUTTON)
        if likes_button:
            if likes_button[1] is not None:
                likes_button = likes_button[1]
            else:
                likes_button = likes_button[0]
            # TODO: check if link should change
            nf_click_center_of_element(self, likes_button)
            sleep(3)
        else:
            return False, []
    except (IndexError, NoSuchElementException):
        return False, []

    # get a reference to the 'Likes' dialog box
    dialog = self.browser.find_element_by_xpath(XP.LIKES_DIALOG_BODY_XPATH)
    scroll_it = True
    try_again = 0
    user_list = []
    sc_rolled = 0
    too_many_requests = 0

    if likers_count != -1:
        amount = (
            likers_count
            if boundary is None
            else None
            if boundary == 0
            else (boundary if boundary < likers_count else likers_count)
        )
    else:
        amount = None
    tmp_scroll_height = 0
    user_list_len = -1
    while scroll_it is not False and boundary != 0:
        scroll_height = self.browser.execute_script(JS.GET_SCROLL_HEIGHT)
        # check if it should keep scrolling down or exit
        if (
                scroll_height >= tmp_scroll_height
                and len(user_list) > user_list_len
        ):
            tmp_scroll_height = scroll_height
            user_list_len = len(user_list)
            scroll_it = True
        else:
            scroll_it = False

        if scroll_it is True:
            scroll_it = self.browser.execute_script(JS.SCROLL_1000)
            self.quota_supervisor.add_server_call()

        if sc_rolled > 90 or too_many_requests > 1:
            delay_random = random.randint(400, 600)
            self.logger.info(
                "Too many requests sent. Sleeping {} minutes and {} seconds".format(
                    int(delay_random / 60),
                    delay_random % 60
                )
            )
            sc_rolled = 0
            too_many_requests = (
                0 if too_many_requests >= 1 else too_many_requests
            )
        else:
            sleep(1.2)  # old value 5.6
            sc_rolled += 1

        try:
            user_list = get_users_from_dialog(user_list, dialog)
        except NoSuchElementException:
            self.logger.error("Error while searching for active users")
            return False, []

        if boundary is not None:
            if len(user_list) >= boundary:
                break

        if (
                scroll_it is False
                and likers_count
                and likers_count - 1 > len(user_list)
        ):

            if (
                    boundary is not None and likers_count - 1 > boundary
            ) or boundary is None:

                if try_again <= 1:  # can increase the amount of tries
                    try_again += 1
                    too_many_requests += 1
                    scroll_it = True
                    nap_it = 4 if try_again == 0 else 7
                    sleep(nap_it)

    try:
        user_list = get_users_from_dialog(user_list, dialog)
        return True, user_list
    except NoSuchElementException:
        self.logger.error("Error while searching for active users")
        return False, []


@LogDecorator()
def get_users_from_dialog(old_data: list, dialog: WebElement):
    """
    Prepared to work specially with the dynamic data load in the 'Likes'
    dialog box
    """
    user_blocks = dialog.find_elements_by_tag_name("a")
    loaded_users = [
        extract_text_from_element(u)
        for u in user_blocks
        if extract_text_from_element(u)
    ]
    new_data = old_data + loaded_users
    new_data = remove_duplicates(new_data, True, None)

    return new_data


@LogDecorator()
def close_dialog_box(self):
    """ Click on the close button spec. in the 'Likes' dialog box """
    try:
        close = self.browser.find_element_by_xpath(XP.LIKES_DIALOG_CLOSE_XPATH)
        nf_click_center_of_element(self, close, get_current_url(self.browser))
    except NoSuchElementException:
        pass


@LogDecorator()
def extract_text_from_element(elem: WebElement):
    """ As an element is valid and contains text, extract it and return """
    if elem and hasattr(elem, "text") and elem.text:
        text = elem.text
    else:
        text = None
    return text


@LogDecorator()
def remove_duplicates(container, keep_order, logger):
    """ Remove duplicates from all kinds of data types easily """
    # add support for data types as needed in future
    # currently only 'list' data type is supported
    if isinstance(container, list):
        if keep_order is True:
            result = sorted(set(container), key=container.index)
        else:
            result = set(container)
    else:
        logger.warning(
            "The given data type- '{}' is not supported "
            "in `remove_duplicates` function, yet!".format(type(container))
        )
        result = container
    return result


def format_number(number):
    """
    Format number. Remove the unused comma. Replace the concatenation with
    relevant zeros. Remove the dot.

    :param number: str

    :return: int
    """
    formatted_num = number.replace(",", "")
    formatted_num = re.sub(
        r"(k)$", "00" if "." in formatted_num else "000", formatted_num
    )
    formatted_num = re.sub(
        r"(m)$", "00000" if "." in formatted_num else "000000", formatted_num
    )
    formatted_num = formatted_num.replace(".", "")
    return int(formatted_num)


@LogDecorator()
def get_relationship_counts(self, username):
    """ Gets the followers & following counts of a given user """

    user_link = "https://www.instagram.com/{}/".format(username)

    if not check_if_in_correct_page(self, user_link):
        self.logger.debug("Not in correct page, shouldn't happen if calling from validate_user_call")
        if username == self.username:
            go_to_bot_user_page(self)
        else:
            nf_go_to_user_page(self, username)

    try:
        followers_count = get_user_data(self, JS.FOLLOWERS_COUNT)
        self.quota_supervisor.add_server_call()
    except WebDriverException:
        try:
            followers_count = format_number(self.browser.find_element_by_xpath(XP.FOLLOWERS_COUNT).text)
        except (NoSuchElementException, StaleElementReferenceException):
            try:
                self.browser.execute_script(JS.RELOAD)
                self.quota_supervisor.add_server_call()
                followers_count = get_user_data(self, JS.FOLLOWERS_COUNT)
            except WebDriverException:
                try:
                    top_count_elements = self.browser.find_elements_by_xpath(XP.TOP_COUNT_ELEMENTS)
                    if top_count_elements:
                        followers_count = format_number(top_count_elements[1].text)
                    else:
                        self.logger.info(
                            "Failed to get followers count of '{}'".format(username)
                        )
                        followers_count = None
                except (NoSuchElementException, StaleElementReferenceException):
                    self.logger.error(
                        "Error occurred while getting followers count "
                        "of '{}'".format(username)
                    )
                    followers_count = None

    try:
        following_count = get_user_data(self, JS.FOLLOWING_COUNT)
    except WebDriverException:
        try:
            following_count = format_number(
                self.browser.find_element_by_xpath(XP.FOLLOWING_COUNT).text
            )
        except (NoSuchElementException, StaleElementReferenceException):
            try:
                self.browser.execute_script(JS.RELOAD)
                self.quota_supervisor.add_server_call()
                following_count = get_user_data(self, JS.FOLLOWING_COUNT)
            except WebDriverException:
                try:
                    top_count_elements = self.browser.find_elements_by_xpath(XP.TOP_COUNT_ELEMENTS)
                    if top_count_elements:
                        following_count = format_number(top_count_elements[2].text)
                    else:
                        self.logger.info(
                            "Failed to get following count of '{}'".format(username)
                        )
                        following_count = None
                except (NoSuchElementException, StaleElementReferenceException):
                    self.logger.error(
                        "Error occurred while getting following count "
                        "of '{}'".format(username)
                    )
                    following_count = None
    # TODO: update in database
    return followers_count, following_count


@LogDecorator()
def emergency_exit(self):
    """ Raise emergency if the is no connection to server OR if user is not
    logged in """
    server_address = "instagram.com"
    connection_state = ping_server(server_address, self.logger)
    if connection_state is False:
        return True, "not connected"

    # check if the user is logged in
    auth_method = "activity counts"
    login_state = check_authorization(self, auth_method)
    if login_state is False:
        return True, "not logged in"

    return False, "no emergency"


@LogDecorator()
def ping_server(host, logger):
    """
    Return True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if
    the host name is valid.
    """
    logger.info("Pinging '{}' to check the connectivity...".format(str(host)))

    # ping command count option as function of OS
    param = "-n" if system().lower() == "windows" else "-c"
    # building the command. Ex: "ping -c 1 google.com"
    command = " ".join(["ping", param, "1", str(host)])
    need_sh = False if system().lower() == "windows" else True

    # pinging
    ping_attempts = 2
    connectivity = None

    while connectivity is not True and ping_attempts > 0:
        connectivity = call(command, shell=need_sh) == 0

        if connectivity is False:
            logger.warning(
                "Pinging the server again!\t~total attempts left: {}".format(
                    ping_attempts
                )
            )
            ping_attempts -= 1
            sleep(5)

    if connectivity is False:
        logger.critical("There is no connection to the '{}' server!".format(host))
        return False

    return True


@LogDecorator()
def is_page_available(self):
    """ Check if the page is available and valid """
    expected_keywords = ["Page Not Found", "Content Unavailable"]
    page_title = get_page_title(self)
    if any(keyword in page_title for keyword in expected_keywords):
        self.browser.execute_script(JS.RELOAD)
        self.quota_supervisor.add_server_call()
        page_title = get_page_title(self)
        if any(keyword in page_title for keyword in expected_keywords):
            if "Page Not Found" in page_title:
                self.logger.warning(
                    "The page isn't available, the link may be broken, or the page may have been removed"
                )
            elif "Content Unavailable" in page_title:
                self.logger.warning(
                    "The page isn't available, the bot may have blocked"
                )
            return False
    return True


@LogDecorator()
def get_page_title(self):
    """ Get the title of the web page """
    # wait for the current page fully load to get the correct page's title
    explicit_wait(self, "PFL", [], 10)
    try:
        page_title = self.browser.title
    except WebDriverException:
        try:
            page_title = self.browser.execute_script(JS.GET_TITLE_1)
        except WebDriverException:
            try:
                page_title = self.browser.execute_script(JS.GET_TITLE_2)
            except WebDriverException:
                self.logger.info("Unable to find the title of the page")
                return None
    return page_title


def is_mandatory_character(self, uchr):
    if self.aborting:
        return self
    try:
        return self.check_letters[uchr]
    except KeyError:
        return self.check_letters.setdefault(
            uchr,
            any(
                mandatory_char in unicodedata.name(uchr)
                for mandatory_char in self.settings.mandatory_character
            ),
        )


@LogDecorator()
def check_character_set(self, unistr):
    if self.aborting:
        return self
    if not self.settings.mandatory_character:
        return True
    self.check_letters = {}
    return all(
        is_mandatory_character(self, uchr) for uchr in unistr if uchr.isalpha()
    )


@LogDecorator()
def check_authorization(self, method, notify=True):
    """ Check if user is NOW logged in """
    if notify is True:
        self.logger.info("Checking if '{}' is logged in".format(self.username))

    # different methods can be added in future
    if method == "activity counts":
        user_link = "https://www.instagram.com/{}/".format(self.username)
        if not check_if_in_correct_page(self, user_link):
            go_to_bot_user_page(self)
        check_for_error(self)
        # if user is not logged in, `activity_counts` will be `None`- JS `null`
        try:
            activity_counts = self.browser.execute_script(JS.ACTIVITY_COUNT)
        except WebDriverException:
            try:
                self.browser.execute_script(JS.RELOAD)
                self.quota_supervisor.add_server_call()
                activity_counts = self.browser.execute_script(JS.ACTIVITY_COUNT)
            except WebDriverException:
                activity_counts = None
        # if user is not logged in, `activity_counts_new` will be `None`- JS
        # `null`
        try:
            activity_counts_new = self.browser.execute_script(JS.VIEWER)
        except WebDriverException:
            try:
                self.browser.execute_script(JS.RELOAD)
                activity_counts_new = self.browser.execute_script(JS.VIEWER)
            except WebDriverException:
                activity_counts_new = None

        if activity_counts is None and activity_counts_new is None:
            if notify is True:
                self.logger.critical("'{}' is not logged in".format(self.username))
            return False
    return True


# TODO: check all bellow here (remove if unused, rewrite if used)

@contextmanager
def interruption_handler(
    threaded=False,
    SIG_type=signal.SIGINT,
    handler=signal.SIG_IGN,
    notify=None,
    logger=None,
):
    """ Handles external interrupt, usually initiated by the user like
    KeyboardInterrupt with CTRL+C """
    if notify is not None and logger is not None:
        logger.warning(notify)

    if not threaded:
        original_handler = signal.signal(SIG_type, handler)
    try:
        yield
    finally:
        if not threaded:
            signal.signal(SIG_type, original_handler)
#
#

#
#
# def get_username_by_js_query(browser, track, logger):
#     """ Get the username of a user from the loaded profile page """
#     if track == "profile":
#         query = "return window._sharedData.entry_data. \
#                     ProfilePage[0].graphql.user.username"
#
#     elif track == "post":
#         query = "return window._sharedData.entry_data. \
#                     PostPage[0].graphql.shortcode_media.owner.username"
#
#     try:
#         username = browser.execute_script(query)
#
#     except WebDriverException:
#         try:
#             browser.execute_script("location.reload()")
#             update_activity(browser, state=None)
#
#             username = browser.execute_script(query)
#
#         except WebDriverException:
#             current_url = get_current_url(browser)
#             logger.info(
#                 "Failed to get the username from '{}' page".format(
#                     current_url or "user" if track == "profile" else "post"
#                 )
#             )
#             username = None
#
#     # in future add XPATH ways of getting username
#
#     return username
#
#
# def find_user_id(browser, track, username, logger):
#     """  Find the user ID from the loaded page """
#     if track in ["dialog", "profile"]:
#         query = "return window.__additionalData[Object.keys(window.__additionalData)[0]].data.graphql.user.id"
#
#     elif track == "post":
#         query = (
#             "return window._sharedData.entry_data.PostPage["
#             "0].graphql.shortcode_media.owner.id"
#         )
#         meta_XP = read_xpath(find_user_id.__name__, "meta_XP")
#
#     failure_message = "Failed to get the user ID of '{}' from {} page!".format(
#         username, track
#     )
#
#     try:
#         user_id = browser.execute_script(query)
#
#     except WebDriverException:
#         try:
#             browser.execute_script("location.reload()")
#             update_activity(browser, state=None)
#
#             user_id = browser.execute_script(
#                 "return window._sharedData."
#                 "entry_data.ProfilePage[0]."
#                 "graphql.user.id"
#             )
#
#         except WebDriverException:
#             if track == "post":
#                 try:
#                     user_id = browser.find_element_by_xpath(meta_XP).get_attribute(
#                         "content"
#                     )
#                     if user_id:
#                         user_id = format_number(user_id)
#
#                     else:
#                         logger.error("{}\t~empty string".format(failure_message))
#                         user_id = None
#
#                 except NoSuchElementException:
#                     logger.error(failure_message)
#                     user_id = None
#
#             else:
#                 logger.error(failure_message)
#                 user_id = None
#
#     return user_id
#
#
# @contextmanager
# def new_tab(browser):
#     """ USE once a host tab must remain untouched and yet needs extra data-
#     get from guest tab """
#     try:
#         # add a guest tab
#         browser.execute_script("window.open()")
#         sleep(1)
#         # switch to the guest tab
#         browser.switch_to.window(browser.window_handles[1])
#         sleep(2)
#         yield
#
#     finally:
#         # close the guest tab
#         browser.execute_script("window.close()")
#         sleep(1)
#         # return to the host tab
#         browser.switch_to.window(browser.window_handles[0])
#         sleep(2)
#
#
# def get_username_from_id(browser, user_id, logger):
#     """ Convert user ID to username """
#     # method using graphql 'Account media' endpoint
#     logger.info("Trying to find the username from the given user ID by loading a post")
#
#     query_hash = "42323d64886122307be10013ad2dcc44"  # earlier-
#     # "472f257a40c653c64c666ce877d59d2b"
#     graphql_query_URL = (
#         "https://www.instagram.com/graphql/query/?query_hash" "={}".format(query_hash)
#     )
#     variables = {"id": str(user_id), "first": 1}
#     post_url = "{}&variables={}".format(graphql_query_URL, str(json.dumps(variables)))
#
#     web_address_navigator(browser, post_url)
#     try:
#         pre = browser.find_element_by_tag_name("pre").text
#     except NoSuchElementException:
#         logger.info("Encountered an error to find `pre` in page, skipping username.")
#         return None
#     user_data = json.loads(pre)["data"]["user"]
#
#     if user_data:
#         user_data = user_data["edge_owner_to_timeline_media"]
#
#         if user_data["edges"]:
#             post_code = user_data["edges"][0]["node"]["shortcode"]
#             post_page = "https://www.instagram.com/p/{}".format(post_code)
#
#             web_address_navigator(browser, post_page)
#             username = get_username_by_js_query(browser, "post", logger)
#             if username:
#                 return username
#
#         else:
#             if user_data["count"] == 0:
#                 logger.info("Profile with ID {}: no pics found".format(user_id))
#
#             else:
#                 logger.info(
#                     "Can't load pics of a private profile to find username ("
#                     "ID: {})".format(user_id)
#                 )
#
#     else:
#         logger.info(
#             "No profile found, the user may have blocked you (ID: {})".format(user_id)
#         )
#         return None
#
#     """  method using private API
#     #logger.info("Trying to find the username from the given user ID by a
#     quick API call")
#
#     #req = requests.get(u"https://i.instagram.com/api/v1/users/{}/info/"
#     #                   .format(user_id))
#     #if req:
#     #    data = json.loads(req.text)
#     #    if data["user"]:
#     #        username = data["user"]["username"]
#     #        return username
#     """
#
#     """ Having a BUG (random log-outs) with the method below, use it only in
#     the external sessions
#     # method using graphql 'Follow' endpoint
#     logger.info("Trying to find the username from the given user ID "
#                 "by using the GraphQL Follow endpoint")
#
#     user_link_by_id = ("https://www.instagram.com/web/friendships/{}/follow/"
#                        .format(user_id))
#
#     web_address_navigator(browser, user_link_by_id)
#     username = get_username(browser, "profile", logger)
#     """
#
#     return None
#
#
#
#
#
# def get_time_until_next_month():
#     """ Get total seconds remaining until the next month """
#     now = datetime.datetime.now()
#     next_month = now.month + 1 if now.month < 12 else 1
#     year = now.year if now.month < 12 else now.year + 1
#     date_of_next_month = datetime.datetime(year, next_month, 1)
#
#     remaining_seconds = (date_of_next_month - now).total_seconds()
#
#     return remaining_seconds
#
#

#
#
# def has_any_letters(text):
#     """ Check if the text has any letters in it """
#     # result = re.search("[A-Za-z]", text)   # works only with english letters
#     result = any(
#         c.isalpha() for c in text
#     )  # works with any letters - english or non-english
#
#     return result
#
#
# def is_follow_me(browser, person=None):
#     # navigate to profile page if not already in it
#     if person:
#         user_link = "https://www.instagram.com/{}/".format(person)
#         web_address_navigator(browser, user_link)
#
#     return get_user_data("graphql.user.follows_viewer", browser)
#
#
# def progress_tracker(current_value, highest_value, initial_time, logger):
#     """ Provide a progress tracker to keep value updated until finishes """
#     if current_value is None or highest_value is None or highest_value == 0:
#         return
#
#     try:
#         real_time = time()
#         progress_percent = int((current_value / highest_value) * 100)
#
#         elapsed_time = real_time - initial_time
#         elapsed = (
#             "{:.0f} seconds".format(elapsed_time/1000)
#             if elapsed_time/1000 < 60
#             else "{:.1f} minutes".format(elapsed_time/1000/60)
#         )
#
#         eta_time = abs(
#             (elapsed_time * 100) / (progress_percent if progress_percent != 0 else 1)
#             - elapsed_time
#         )
#         eta = (
#             "{:.0f} seconds".format(eta_time/1000)
#             if eta_time/1000 < 60
#             else "{:.1f} minutes".format(eta_time/1000/60)
#         )
#
#         tracker_line = "-----------------------------------"
#         filled_index = int(progress_percent / 2.77)
#         progress_container = (
#             "[" + tracker_line[:filled_index] + "+" + tracker_line[filled_index:] + "]"
#         )
#         progress_container = (
#             progress_container[: filled_index + 1].replace("-", "=")
#             + progress_container[filled_index + 1 :]
#         )
#
#         total_message = (
#             "\r  {}/{} {}  {}%    "
#             "|> Elapsed: {}    "
#             "|> ETA: {}      ".format(
#                 current_value,
#                 highest_value,
#                 progress_container,
#                 progress_percent,
#                 elapsed,
#                 eta,
#             )
#         )
#
#         sys.stdout.write(total_message)
#         sys.stdout.flush()
#
#     except Exception as exc:
#         logger.info(
#             "Error occurred with Progress Tracker:\n{}".format(str(exc).encode("utf-8"))
#         )
#
#
# def get_cord_location(browser, location):
#     base_url = "https://www.instagram.com/explore/locations/"
#     query_url = "{}{}{}".format(base_url, location, "?__a=1")
#     browser.get(query_url)
#     json_text = browser.find_element_by_xpath(
#         read_xpath(get_cord_location.__name__, "json_text")
#     ).text
#     data = json.loads(json_text)
#
#     lat = data["graphql"]["location"]["lat"]
#     lon = data["graphql"]["location"]["lng"]
#
#     return lat, lon
#
#
# def get_bounding_box(
#     latitude_in_degrees, longitude_in_degrees, half_side_in_miles, logger
# ):
#     if half_side_in_miles == 0:
#         logger.error("Check your Radius its lower then 0")
#         return {}
#     if latitude_in_degrees < -90.0 or latitude_in_degrees > 90.0:
#         logger.error("Check your latitude should be between -90/90")
#         return {}
#     if longitude_in_degrees < -180.0 or longitude_in_degrees > 180.0:
#         logger.error("Check your longtitude should be between -180/180")
#         return {}
#     half_side_in_km = half_side_in_miles * 1.609344
#     lat = radians(latitude_in_degrees)
#     lon = radians(longitude_in_degrees)
#
#     radius = 6371
#     # Radius of the parallel at given latitude
#     parallel_radius = radius * cos(lat)
#
#     lat_min = lat - half_side_in_km / radius
#     lat_max = lat + half_side_in_km / radius
#     lon_min = lon - half_side_in_km / parallel_radius
#     lon_max = lon + half_side_in_km / parallel_radius
#
#     lat_min = rad2deg(lat_min)
#     lon_min = rad2deg(lon_min)
#     lat_max = rad2deg(lat_max)
#     lon_max = rad2deg(lon_max)
#
#     bbox = {
#         "lat_min": lat_min,
#         "lat_max": lat_max,
#         "lon_min": lon_min,
#         "lon_max": lon_max,
#     }
#
#     return bbox
#
#
# def take_rotative_screenshot(browser, logfolder):
#     """
#         Make a sequence of screenshots, based on hour:min:secs
#     """
#     global next_screenshot
#
#     if next_screenshot == 1:
#         browser.save_screenshot("{}screenshot_1.png".format(logfolder))
#     elif next_screenshot == 2:
#         browser.save_screenshot("{}screenshot_2.png".format(logfolder))
#     else:
#         browser.save_screenshot("{}screenshot_3.png".format(logfolder))
#         next_screenshot = 0
#         # sum +1 next
#
#     # update next
#     next_screenshot += 1
#
#
# def get_query_hash(browser, logger):
#     """ Load Instagram JS file and find query hash code """
#     link = "https://www.instagram.com/static/bundles/es6/Consumer.js/1f67555edbd3.js"
#     web_address_navigator(browser, link)
#     page_source = browser.page_source
#     # locate pattern value from JS file
#     # sequence of 32 words and/or numbers just before ,n=" value
#     hash = re.findall('[a-z0-9]{32}(?=",n=")', page_source)
#     if hash:
#         return hash[0]
#     else:
#         logger.warn("Query Hash not found")
#
