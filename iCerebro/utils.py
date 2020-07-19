import csv
import os
import re
import time
from datetime import datetime
import random
from math import ceil
from typing import List, Tuple

from instapy.comment_util import verify_commenting, comment_image
from instapy.event import Event
from instapy.quota_supervisor import quota_supervisor
from instapy.relationship_tools import get_nonfollowers, get_followers, get_following
from instapy.unfollow_util import set_followback_in_pool, get_following_status, confirm_unfollow, \
    verify_action, post_unfollow_cleanup
from instapy.util import get_relationship_counts, truncate_float, getUserData, \
    default_profile_pic_instagram, is_page_available, is_follow_me, get_epoch_time_diff, delete_line_from_file, \
    click_element, update_activity, get_action_delay, emergency_exit, format_number
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from sqlalchemy.exc import SQLAlchemyError

from iCerebro.database import Post
from iCerebro.db_utils import db_get_or_create_user, db_get_or_create_post, db_store_comments
from iCerebro.navigation import nf_scroll_into_view, nf_go_from_post_to_profile, nf_find_and_press_back, \
    nf_go_to_user_page, check_if_in_correct_page


def nf_check_post(
        self,
        post_link: str
) -> Tuple[bool, str, bool, List[str], str, str]:
    """Checks if post can be liked according to declared settings

    Also stores post data in database if appropriate

    :returns: inappropriate, username, is_video, image_links, reason, scope
    """
    t = time.perf_counter()
    username_text = ""
    caption = ""
    image_descriptions = []
    image_links = []
    likes_count = None
    try:
        username = self.browser.find_element_by_xpath(
            '/html/body/div[1]/section/main/div/div/article/header//div[@class="e1e1d"]'
        )
        username_text = username.text

        # follow_button = self.browser.find_element_by_xpath(
        #     '/html/body/div[1]/section/main/div/div/article/header/div[2]/div[1]/div[2]/button'
        # )
        # following = follow_button.text == "Following"

        locations = self.browser.find_elements_by_xpath(
            '/html/body/div[1]/section/main/div/div/article/header//a[contains(@href,"locations")]'
        )
        location_text = locations[0].text if locations != [] else None
        # location_link = locations[0].get_attribute('href') if locations != [] else None

        images = self.browser.find_elements_by_xpath(
            '/html/body/div[1]/section/main/div/div/article//img[@class="FFVAD"]'
        )
        """
        video_previews = self.browser.find_elements_by_xpath(
            '/html/body/div[1]/section/main/div/div/article//img[@class="_8jZFn"]'
        )
        videos = self.browser.find_elements_by_xpath(
            '/html/body/div[1]/section/main/div/div/article//video[@class="tWeCl"]'
        )
        if (len(images) + len(videos)) == 1:
            # single image or video
        elif len(images) == 2:
            # carousel
        """
        is_video = len(images) == 0

        more_button = self.browser.find_elements_by_xpath("//button[text()='more']")
        if more_button:
            nf_scroll_into_view(self, more_button[0])
            more_button[0].click()

        caption = self.browser.find_element_by_xpath(
            "/html/body/div[1]/section/main/div/div/article//div/div/span/span"
        ).text
        caption = "" if caption is None else caption

        for image in images:
            image_description = image.get_attribute('alt')
            if image_description is not None and 'Image may contain:' in image_description:
                image_description = image_description[image_description.index(
                    'Image may contain:') + 19:]
            else:
                image_description = None

            image_descriptions.append(image_description)
            image_links.append(image.get_attribute('src'))

        self.logger.info("Image from: {}".format(username_text.encode("utf-8")))
        self.logger.info("Link: {}".format(post_link.encode("utf-8")))
        self.logger.info("Caption: {}".format(caption.encode("utf-8")))
        for image_description in image_descriptions:
            if image_description:
                self.logger.info("Description: {}".format(image_description.encode("utf-8")))

        # Check if likes_count is between minimum and maximum values defined by user
        if self.delimit_liking:
            likes_count = get_like_count(self)
            if likes_count is None:
                return (
                    True,
                    username_text,
                    is_video,
                    image_links,
                    "Couldn't get like count",
                    ""
                )
            elif self.max_likes is not None and likes_count > self.max_likes:
                return (
                    True,
                    username_text,
                    is_video,
                    image_links,
                    "Delimited by liking",
                    "maximum limit: {}, post has: {}".format(self.max_likes, likes_count)
                )
            elif self.min_likes is not None and likes_count < self.min_likes:
                return (
                    True,
                    username_text,
                    is_video,
                    image_links,
                    "Delimited by liking",
                    "minimum limit: {}, post has: {}".format(self.min_likes, likes_count)
                )

        # Check if mandatory character set, before adding the location to the text
        if self.mandatory_language:
            if not self.check_character_set(caption):
                return (
                    True,
                    username_text,
                    is_video,
                    image_links,
                    "Mandatory language not fulfilled",
                    "Not mandatory " "language",
                )

        # Append location to image_text so we can search through both in one go
        if location_text:
            self.logger.info("Location: {}".format(location_text.encode("utf-8")))
            caption = caption + "\n" + location_text

        if self.mandatory_words:
            if not any((word in caption for word in self.mandatory_words)):
                return (
                    True,
                    username_text,
                    is_video,
                    image_links,
                    "Mandatory words not fulfilled",
                    "Not mandatory likes",
                )

        image_text_lower = [x.lower() for x in caption]
        ignore_if_contains_lower = [x.lower() for x in self.ignore_if_contains]
        if any((word in image_text_lower for word in ignore_if_contains_lower)):
            return (
                False,
                username_text,
                is_video,
                image_links,
                "Contains word in ignore_if_contains list",
                "Ignore if contains")

        dont_like_regex = []

        for dont_likes in self.dont_like:
            if dont_likes.startswith("#"):
                dont_like_regex.append(dont_likes + r"([^\d\w]|$)")
            elif dont_likes.startswith("["):
                dont_like_regex.append("#" + dont_likes[1:] + r"[\d\w]+([^\d\w]|$)")
            elif dont_likes.startswith("]"):
                dont_like_regex.append(r"#[\d\w]+" + dont_likes[1:] + r"([^\d\w]|$)")
            else:
                dont_like_regex.append(r"#[\d\w]*" + dont_likes + r"[\d\w]*([^\d\w]|$)")

        for dont_likes_regex in dont_like_regex:
            quash = re.search(dont_likes_regex, caption, re.IGNORECASE)
            if quash:
                quashed = (
                    (((quash.group(0)).split("#")[1]).split(" ")[0])
                    .split("\n")[0]
                    .encode("utf-8")
                )  # dismiss possible space and newlines
                iffy = (
                    (re.split(r"\W+", dont_likes_regex))[3]
                    if dont_likes_regex.endswith("*([^\\d\\w]|$)")
                    else (re.split(r"\W+", dont_likes_regex))[1]  # 'word' without format
                    if dont_likes_regex.endswith("+([^\\d\\w]|$)")
                    else (re.split(r"\W+", dont_likes_regex))[3]  # '[word'
                    if dont_likes_regex.startswith("#[\\d\\w]+")
                    else (re.split(r"\W+", dont_likes_regex))[1]  # ']word'
                )  # '#word'
                reason = 'Inappropriate! ~ contains "{}"'.format(
                    quashed if iffy == quashed else '" in "'.join([str(iffy), str(quashed)])
                )
                return True, username_text, is_video, image_links, reason, "Undesired word"

        return False, username_text, is_video, image_links, "None", "Success"
    finally:
        if self.store_in_database:
            try:
                user = db_get_or_create_user(self, username_text)
                already_saved_posts = self.db.session.query(Post).filter(Post.user == user).all()
                if post_link in [post.link for post in already_saved_posts]:
                    raise SQLAlchemyError
                self.db.session.add(user)
                self.db.session.commit()
                db_posts = []
                for image_link, image_description in zip(image_links, image_descriptions):
                    try:
                        post_date = self.browser.find_element_by_xpath(
                            '/html/body/div[1]/section/main/div/div/article//a[@class="c-Yi7"]/time'
                        ).get_attribute('datetime')
                        post_date = datetime.fromisoformat(post_date[:-1])
                    except NoSuchElementException:
                        post_date = datetime.now()
                    post = db_get_or_create_post(
                        self,
                        post_date,
                        post_link,
                        image_link,
                        caption,
                        likes_count,
                        user,
                        image_description
                    )
                    self.db.session.add(post)
                    db_posts.append(post)
                self.db.session.commit()
                if db_posts:
                    self.logger.info("About to store comments")
                    db_store_comments(self, db_posts, post_link)
                self.db.session.expunge(user)
                for post in db_posts:
                    self.db.session.expunge(post)
            except SQLAlchemyError:
                self.db.session.rollback()
            finally:
                self.db.session.commit()

        elapsed_time = time.perf_counter() - t
        self.logger.info("check post elapsed time: {:.0f} seconds".format(elapsed_time))


def get_like_count(
        self,
) -> int:
    try:
        likes_count = self.browser.execute_script(
            "return window.__additionalData[Object.keys(window.__additionalData)[0]].data"
            ".graphql.shortcode_media.edge_media_preview_like.count"
        )
        return likes_count
    except WebDriverException:
        try:
            self.browser.execute_script("location.reload()")
            update_activity(self.browser, state=None)

            likes_count = self.browser.execute_script(
                "return window._sharedData.entry_data."
                "PostPage[0].graphql.shortcode_media.edge_media_preview_like"
                ".count"
            )
            return likes_count

        except WebDriverException:
            try:
                likes_count = self.browser.find_element_by_css_selector(
                    "section._1w76c._nlmjy > div > a > span"
                ).text

                if likes_count:
                    return format_number(likes_count)
                else:
                    self.logger.info("Failed to check likes' count  ~empty string\n")
                    return -1

            except NoSuchElementException:
                self.logger.info("Failed to check likes' count\n")
                return -1


def nf_validate_user_call(
        self,
        username: str,
        post_link: str = None
) -> Tuple[bool, str]:
    """Checks if user can be liked according to declared settings

   Also stores post data in database if appropriate

   :returns: valid, reason
   """
    followers_count = None
    following_count = None
    number_of_posts = None
    if username == self.username:
        reason = "---> Username '{}' is yours!\t~skipping user\n".format(self.username)
        return False, reason

    if username in self.ignore_users:
        reason = (
            "---> '{}' is in the `ignore_users` list\t~skipping "
            "user\n".format(username)
        )
        return False, reason

    blacklist_file = "{}blacklist.csv".format(self.logfolder)
    blacklist_file_exists = os.path.isfile(blacklist_file)
    if blacklist_file_exists:
        with open("{}blacklist.csv".format(self.logfolder), "rt") as f:
            reader = csv.reader(f, delimiter=",")
            for row in reader:
                for field in row:
                    if field == username:
                        return (
                            False,
                            "---> {} is in blacklist  ~skipping "
                            "user\n".format(username),
                        )

    potency_ratio = self.potency_ratio
    delimit_by_numbers = self.delimit_by_numbers
    max_followers = self.max_followers
    max_following = self.max_following
    min_followers = self.min_followers
    min_following = self.min_following
    min_posts = self.min_posts
    max_posts = self.max_posts
    skip_private = self.skip_private
    skip_private_percentage = self.skip_private_percentage
    skip_no_profile_pic = self.skip_no_profile_pic
    skip_no_profile_pic_percentage = self.skip_no_profile_pic_percentage
    skip_business = self.skip_business
    skip_non_business = self.skip_non_business
    skip_business_percentage = self.skip_business_percentage
    skip_business_categories = self.skip_business_categories
    dont_skip_business_categories = self.dont_skip_business_categories
    skip_bio_keyword = self.skip_bio_keyword

    if not any([potency_ratio, delimit_by_numbers, max_followers, max_following,
                min_followers, min_following, min_posts, max_posts, skip_private,
                skip_private_percentage, skip_no_profile_pic, skip_no_profile_pic_percentage,
                skip_business, skip_non_business, skip_business_percentage,
                skip_business_categories, skip_bio_keyword
                ]
               ):
        # Nothing to check, skip going to user page and then back for nothing
        return True, "Valid user"

    try:
        if post_link:
            nf_go_from_post_to_profile(self, username)
        self.logger.info("about to start checking user page")
        # Checks the potential of target user by relationship status in order
        # to delimit actions within the desired boundary
        if (
                potency_ratio
                or delimit_by_numbers
                and (max_followers or max_following or min_followers or min_following)
        ):

            relationship_ratio = None
            reverse_relationship = False

            # get followers & following counts
            self.logger.info("About to get relationship counts")
            followers_count, following_count = get_relationship_counts(
                self.browser, username, self.logger
            )

            if potency_ratio and potency_ratio < 0:
                potency_ratio *= -1
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
                    truncate_float(relationship_ratio, 2)
                    if relationship_ratio
                    else "unknown",
                )
            )

            if followers_count or following_count:
                if potency_ratio and not delimit_by_numbers:
                    if relationship_ratio and relationship_ratio < potency_ratio:
                        reason = (
                            "'{}' is not a {} with the relationship ratio of {}  "
                            "~skipping user\n".format(
                                username,
                                "potential user"
                                if not reverse_relationship
                                else "massive follower",
                                truncate_float(relationship_ratio, 2),
                            )
                        )
                        return False, reason

                elif self.delimit_by_numbers:
                    if followers_count:
                        if max_followers:
                            if followers_count > max_followers:
                                reason = (
                                    "User '{}'s followers count exceeds maximum "
                                    "limit  ~skipping user\n".format(username)
                                )
                                return False, reason

                        if min_followers:
                            if followers_count < min_followers:
                                reason = (
                                    "User '{}'s followers count is less than "
                                    "minimum limit  ~skipping user\n".format(username)
                                )
                                return False, reason

                    if following_count:
                        if max_following:
                            if following_count > max_following:
                                reason = (
                                    "User '{}'s following count exceeds maximum "
                                    "limit  ~skipping user\n".format(username)
                                )
                                return False, reason

                        if min_following:
                            if following_count < min_following:
                                reason = (
                                    "User '{}'s following count is less than "
                                    "minimum limit  ~skipping user\n".format(username)
                                )
                                return False, reason

                    if potency_ratio:
                        if relationship_ratio and relationship_ratio < potency_ratio:
                            reason = (
                                "'{}' is not a {} with the relationship ratio of "
                                "{}  ~skipping user\n".format(
                                    username,
                                    "potential user"
                                    if not reverse_relationship
                                    else "massive " "follower",
                                    truncate_float(relationship_ratio, 2),
                                )
                            )
                            return False, reason

        if min_posts or max_posts:
            # if you are interested in relationship number of posts boundaries
            try:
                number_of_posts = getUserData(
                    "graphql.user.edge_owner_to_timeline_media.count", self.browser
                )
            except WebDriverException:
                self.logger.error("~cannot get number of posts for username")
                reason = "---> Sorry, couldn't check for number of posts of " "username\n"
                return False, reason

            if max_posts:
                if number_of_posts > max_posts:
                    reason = (
                        "Number of posts ({}) of '{}' exceeds the maximum limit "
                        "given {}\n".format(number_of_posts, username, max_posts)
                    )
                    return False, reason
            if min_posts:
                if number_of_posts < min_posts:
                    reason = (
                        "Number of posts ({}) of '{}' is less than the minimum "
                        "limit given {}\n".format(number_of_posts, username, min_posts)
                    )
                    return False, reason

        # Skip users

        # skip private
        if skip_private:
            try:
                self.browser.find_element_by_xpath(
                    "//*[contains(text(), 'This Account is Private')]"
                )
                is_private = True
            except NoSuchElementException:
                is_private = False
            if is_private and (random.randint(0, 100) <= skip_private_percentage):
                return False, "{} is private account, by default skip\n".format(username)

        # skip no profile pic
        if skip_no_profile_pic:
            try:
                profile_pic = getUserData("graphql.user.profile_pic_url", self.browser)
            except WebDriverException:
                self.logger.error("~cannot get the post profile pic url")
                return False, "---> Sorry, couldn't get if user profile pic url\n"
            if (
                    profile_pic in default_profile_pic_instagram
                    or str(profile_pic).find("11906329_960233084022564_1448528159_a.jpg") > 0
            ) and (random.randint(0, 100) <= skip_no_profile_pic_percentage):
                return False, "{} has default instagram profile picture\n".format(username)

        # skip business
        if skip_business or skip_non_business:
            # if is business account skip under conditions
            try:
                is_business_account = getUserData(
                    "graphql.user.is_business_account", self.browser
                )
            except WebDriverException:
                self.logger.error("~cannot get if user has business account active")
                return (
                    False,
                    "---> Sorry, couldn't get if user has business " "account active\n",
                )

            if skip_non_business and not is_business_account:
                return (
                    False,
                    "---> Skipping non business because skip_non_business set to True",
                )

            if is_business_account:
                try:
                    category = getUserData("graphql.user.business_category_name", self.browser)
                except WebDriverException:
                    self.logger.error("~cannot get category name for user")
                    return False, "---> Sorry, couldn't get category name for " "user\n"

                if len(skip_business_categories) == 0:
                    # skip if not in dont_include
                    if category not in dont_skip_business_categories:
                        if len(dont_skip_business_categories) == 0 and (
                                random.randint(0, 100) <= skip_business_percentage
                        ):
                            return False, "'{}' has a business account\n".format(username)
                        else:
                            return (
                                False,
                                (
                                    "'{}' has a business account in the "
                                    "undesired category of '{}'\n".format(
                                        username, category
                                    )
                                ),
                            )
                else:
                    if category in skip_business_categories:
                        return (
                            False,
                            (
                                "'{}' has a business account in the "
                                "undesired category of '{}'\n".format(username, category)
                            ),
                        )

        if len(skip_bio_keyword) != 0:
            # if contain stop words then skip
            try:
                profile_bio = getUserData("graphql.user.biography", self.browser)
            except WebDriverException:
                self.logger.error("~cannot get user bio")
                return False, "---> Sorry, couldn't get get user bio " "account active\n"
            for bio_keyword in skip_bio_keyword:
                if bio_keyword.lower() in profile_bio.lower():
                    return (
                        False,
                        "{} has a bio keyword of {}, by default skip\n".format(
                            username, bio_keyword
                        ),
                    )

        # if everything is ok
        return True, "Valid user"

    except NoSuchElementException:
        return False, "Unable to locate element"
    finally:
        if self.store_in_database:
            try:
                user = db_get_or_create_user(self, username)
                self.db.session.add(user)
                user.date_checked = datetime.now()
                if followers_count:
                    user.followers_count = followers_count
                if following_count:
                    user.following_count = following_count
                if number_of_posts:
                    user.posts_count = number_of_posts
                self.db.session.expunge(user)
            except SQLAlchemyError:
                self.db.session.rollback()
            finally:
                self.db.session.commit()
        if post_link:
            nf_find_and_press_back(self, post_link)


def process_comments(
        self,
        username: str,
        comments: List[str],
        image_analysis_comments: List[str]
) -> bool:
    """Comments image if comments are enabled and in appropriate range according to settings

   :returns: if the image was commented
   """
    disapproval_reason = ""
    if self.delimit_commenting:
        self.commenting_approved, disapproval_reason = verify_commenting(
            self.browser,
            self.max_comments,
            self.min_comments,
            self.comments_mandatory_words,
            self.logger,
        )
    if not self.commenting_approved:
        self.logger.info(disapproval_reason)
        return False

    if not self.commenting_approved:
        self.logger.info(disapproval_reason)
        return False

    if len(image_analysis_comments) > 0:
        comments = image_analysis_comments

    # smart commenting
    if comments:
        comment_state, msg = comment_image(
            self.browser,
            username,
            comments,
            self.blacklist,
            self.logger,
            self.logfolder,
        )
        return comment_state

    return False


def nf_get_all_posts_on_element(
        element: WebElement
) -> List[WebElement]:
    return element.find_elements_by_xpath('//a[starts-with(@href, "/p/")]')


def nf_get_all_users_on_element(
        self
) -> List[WebElement]:
    # return element.find_elements_by_xpath('//li/div/div[1]/div[2]/div[1]/a')
    return self.browser.find_elements_by_xpath('//a[@class="FPmhX notranslate  _0imsa "]')


# noinspection PyPep8Naming
# noinspection PyUnboundLocalVariable
def unfollow(
        self,
        amount,
        customList,
        InstapyFollowed,
        nonFollowers,
        allFollowing,
        style,
        sleep_delay,
        delay_followbackers,
):
    """ Unfollow the given amount of users"""

    if (
            customList is not None
            and isinstance(customList, (tuple, list))
            and len(customList) == 3
            and customList[0] is True
            and isinstance(customList[1], (list, tuple, set))
            and len(customList[1]) > 0
            and customList[2] in ["all", "nonfollowers"]
    ):
        customList_data = customList[1]
        if not isinstance(customList_data, list):
            customList_data = list(customList_data)
        unfollow_track = customList[2]
        customList = True
    else:
        customList = False

    if (
            InstapyFollowed is not None
            and isinstance(InstapyFollowed, (tuple, list))
            and len(InstapyFollowed) == 2
            and InstapyFollowed[0] is True
            and InstapyFollowed[1] in ["all", "nonfollowers"]
    ):
        unfollow_track = InstapyFollowed[1]
        InstapyFollowed = True
    else:
        InstapyFollowed = False

    unfollowNum = 0

    # TODO: change to click self user icon
    nf_go_to_user_page(self, self.username)

    # check how many people we are following
    _, allfollowing = get_relationship_counts(self.browser, self.username, self.logger)

    if allfollowing is None:
        self.logger.warning(
            "Unable to find the count of users followed  ~leaving unfollow " "feature"
        )
        return 0
    elif allfollowing == 0:
        self.logger.warning("There are 0 people to unfollow  ~leaving unfollow feature")
        return 0

    if amount > allfollowing:
        self.logger.info(
            "There are less users to unfollow than you have requested:  "
            "{}/{}  ~using available amount\n".format(allfollowing, amount)
        )
        amount = allfollowing

    if (
            customList is True
            or InstapyFollowed is True
            or nonFollowers is True
            or allFollowing is True
    ):

        if nonFollowers is True:
            InstapyFollowed = False

        if customList is True:
            self.logger.info("Unfollowing from the list of pre-defined usernames\n")
            unfollow_list = customList_data

        elif InstapyFollowed is True:
            self.logger.info("Unfollowing the users followed by InstaPy\n")
            unfollow_list = list(self.automatedFollowedPool["eligible"].keys())

        elif nonFollowers is True:
            self.logger.info("Unfollowing the users who do not follow back\n")

            # Unfollow only the users who do not follow you back
            unfollow_list = get_nonfollowers(
                self.browser, self.username, self.relationship_data, False, True, self.logger, self.logfolder
            )

        # pick only the users in the right track- ["all" or "nonfollowers"]
        # for `customList` and
        #  `InstapyFollowed` unfollow methods
        if customList is True or InstapyFollowed is True:
            if unfollow_track == "nonfollowers":
                all_followers = get_followers(
                    self.browser,
                    self.username,
                    "full",
                    self.relationship_data,
                    False,
                    True,
                    self.logger,
                    self.logfolder,
                )
                loyal_users = [user for user in unfollow_list if user in all_followers]
                self.logger.info(
                    "Found {} loyal followers!  ~will not unfollow "
                    "them".format(len(loyal_users))
                )
                unfollow_list = [
                    user for user in unfollow_list if user not in loyal_users
                ]

            elif unfollow_track != "all":
                self.logger.info(
                    'Unfollow track is not specified! ~choose "all" or '
                    '"nonfollowers"'
                )
                return 0

        # re-generate unfollow list according to the `unfollow_after`
        # parameter for `customList` and
        #  `nonFollowers` unfollow methods
        if customList is True or nonFollowers is True:
            not_found = []
            non_eligible = []
            for person in unfollow_list:
                if person not in self.automatedFollowedPool["all"].keys():
                    not_found.append(person)
                elif (
                        person in self.automatedFollowedPool["all"].keys()
                        and person not in self.automatedFollowedPool["eligible"].keys()
                ):
                    non_eligible.append(person)

            unfollow_list = [user for user in unfollow_list if user not in non_eligible]
            self.logger.info(
                "Total {} users available to unfollow"
                "  ~not found in 'followedPool.csv': {}  |  didn't "
                "pass `unfollow_after`: {}\n".format(
                    len(unfollow_list), len(not_found), len(non_eligible)
                )
            )

        elif InstapyFollowed is True:
            non_eligible = [
                user
                for user in self.automatedFollowedPool["all"].keys()
                if user not in self.automatedFollowedPool["eligible"].keys()
            ]
            self.logger.info(
                "Total {} users available to unfollow  ~didn't pass "
                "`unfollow_after`: {}\n".format(len(unfollow_list), len(non_eligible))
            )
        elif allFollowing is True:
            self.logger.info("Unfollowing the users you are following")
            unfollow_list = get_following(
                self.browser,
                self.username,
                "full",
                self.relationship_data,
                False,
                True,
                self.logger,
                self.logfolder,
            )

        if len(unfollow_list) < 1:
            self.logger.info("There are no any users available to unfollow")
            return 0

        # choose the desired order of the elements
        if style == "LIFO":
            unfollow_list = list(reversed(unfollow_list))
        elif style == "RANDOM":
            random.shuffle(unfollow_list)

        if amount > len(unfollow_list):
            self.logger.info(
                "You have requested more amount: {} than {} of users "
                "available to unfollow"
                "~using available amount\n".format(amount, len(unfollow_list))
            )
            amount = len(unfollow_list)

        # unfollow loop
        try:
            sleep_counter = 0
            sleep_after = random.randint(8, 12)
            index = 0

            for person in unfollow_list:
                if unfollowNum >= amount:
                    self.logger.warning(
                        "--> Total unfollows reached it's amount given {}\n".format(
                            unfollowNum
                        )
                    )
                    break

                if self.jumps["consequent"]["unfollows"] >= self.jumps["limit"]["unfollows"]:
                    self.logger.warning(
                        "--> Unfollow quotient reached its peak!\t~leaving "
                        "Unfollow-Users activity\n"
                    )
                    break

                if sleep_counter >= sleep_after and sleep_delay not in [0, None]:
                    delay_random = random.randint(
                        ceil(sleep_delay * 0.85), ceil(sleep_delay * 1.14)
                    )
                    self.logger.info(
                        "Unfollowed {} new users  ~sleeping about {}\n".format(
                            sleep_counter,
                            "{} seconds".format(delay_random)
                            if delay_random < 60
                            else "{} minutes".format(
                                truncate_float(delay_random / 60, 2)
                            ),
                        )
                    )
                    time.sleep(delay_random)
                    sleep_counter = 0
                    sleep_after = random.randint(8, 12)
                    pass

                if person not in self.dont_include:
                    self.logger.info(
                        "Ongoing Unfollow [{}/{}]: now unfollowing '{}'...".format(
                            unfollowNum + 1, amount, person.encode("utf-8")
                        )
                    )

                    person_id = (
                        self.automatedFollowedPool["all"][person]["id"]
                        if person in self.automatedFollowedPool["all"].keys()
                        else False
                    )

                    # delay unfollowing of follow-backers
                    if delay_followbackers and unfollow_track != "nonfollowers":

                        followedback_status = self.automatedFollowedPool["all"][person][
                            "followedback"
                        ]
                        # if once before we set that flag to true
                        # now it is time to unfollow since
                        # time filter pass, user is now eligible to unfollow
                        if followedback_status is not True:
                            nf_go_to_user_page(self, person)
                            valid_page = is_page_available(self.browser, self.logger)

                            if valid_page and is_follow_me(self.browser, person):
                                # delay follow-backers with delay_follow_back.
                                time_stamp = (
                                    self.automatedFollowedPool["all"][person]["time_stamp"]
                                    if person in self.automatedFollowedPool["all"].keys()
                                    else False
                                )
                                if time_stamp not in [False, None]:
                                    try:
                                        time_diff = get_epoch_time_diff(
                                            time_stamp, self.logger
                                        )
                                        if time_diff is None:
                                            continue

                                        if (
                                                time_diff < delay_followbackers
                                        ):  # N days in seconds
                                            set_followback_in_pool(
                                                self.username,
                                                person,
                                                person_id,
                                                time_stamp,  # stay with original timestamp
                                                self.logger,
                                                self.logfolder,
                                            )
                                            # don't unfollow (for now) this follow backer !
                                            continue

                                    except ValueError:
                                        self.logger.error(
                                            "time_diff reading for user {} failed \n".format(
                                                person
                                            )
                                        )
                                        pass

                    try:
                        unfollow_state, msg = unfollow_user(
                            self,
                            "profile",
                            person,
                            person_id,
                            None,
                        )
                    except BaseException as e:
                        self.logger.error("Unfollow loop error:  {}\n".format(str(e)))

                    if unfollow_state is True:
                        unfollowNum += 1
                        sleep_counter += 1
                        # reset jump counter after a successful unfollow
                        self.jumps["consequent"]["unfollows"] = 0

                    elif msg == "jumped":
                        # will break the loop after certain consecutive jumps
                        self.jumps["consequent"]["unfollows"] += 1

                    elif msg in ["temporary block", "not connected", "not logged in"]:
                        # break the loop in extreme conditions to prevent
                        # misbehaviour
                        self.logger.warning(
                            "There is a serious issue: '{}'!\t~leaving "
                            "Unfollow-Users activity".format(msg)
                        )
                        break

                else:
                    # if the user in dont include (should not be) we shall
                    # remove him from the follow list
                    # if he is a white list user (set at init and not during
                    # run time)
                    if person in self.white_list:
                        delete_line_from_file(
                            "{0}{1}_followedPool.csv".format(self.logfolder, self.username),
                            person,
                            self.logger,
                        )
                        list_type = "whitelist"
                    else:
                        list_type = "dont_include"
                    self.logger.info(
                        "Not unfollowed '{}'!\t~user is in the list {}"
                        "\n".format(person, list_type)
                    )
                    index += 1
                    continue
        except BaseException as e:
            self.logger.error("Unfollow loop error:  {}\n".format(str(e)))
    else:
        self.logger.info(
            "Please select a proper unfollow method!  ~leaving unfollow " "activity\n"
        )

    return unfollowNum


def unfollow_user(
        self,
        track,
        person,
        person_id,
        button,
):
    """ Unfollow a user either from the profile or post page or dialog box """
    # list of available tracks to unfollow in: ["profile", "post" "dialog]
    # check action availability
    if quota_supervisor("unfollows") == "jump":
        return False, "jumped"

    if track in ["profile", "post"]:
        # Method of unfollowing from a user's profile page or post page
        if track == "profile":
            user_link = "https://www.instagram.com/{}/".format(person)
            if not check_if_in_correct_page(self, user_link):
                nf_go_to_user_page(self, person)

        # find out CURRENT follow status
        following_status, follow_button = get_following_status(
            self.browser, track, self.username, person, person_id, self.logger, self.logfolder
        )

        if following_status in ["Following", "Requested"]:
            click_element(self.browser, follow_button)
            time.sleep(3)
            confirm_unfollow(self.browser)
            unfollow_state, msg = verify_action(
                self.browser,
                "unfollow",
                track,
                self.username,
                person,
                person_id,
                self.logger,
                self.logfolder,
            )
            if unfollow_state is not True:
                return False, msg

        elif following_status in ["Follow", "Follow Back"]:
            self.logger.info(
                "--> Already unfollowed '{}'! or a private user that "
                "rejected your req".format(person)
            )
            post_unfollow_cleanup(
                ["successful", "uncertain"],
                self.username,
                person,
                self.relationship_data,
                person_id,
                self.logger,
                self.logfolder,
            )
            return False, "already unfollowed"

        elif following_status in ["Unblock", "UNAVAILABLE"]:
            if following_status == "Unblock":
                failure_msg = "user is in block"
            else:
                failure_msg = "user is inaccessible"

            self.logger.warning(
                "--> Couldn't unfollow '{}'!\t~{}".format(person, failure_msg)
            )
            post_unfollow_cleanup(
                "uncertain",
                self.username,
                person,
                self.relationship_data,
                person_id,
                self.logger,
                self.logfolder,
            )
            return False, following_status

        elif following_status is None:
            sirens_wailing, emergency_state = emergency_exit(self.browser, self.username, self.logger)
            if sirens_wailing is True:
                return False, emergency_state

            else:
                self.logger.warning(
                    "--> Couldn't unfollow '{}'!\t~unexpected failure".format(person)
                )
                return False, "unexpected failure"
    elif track == "dialog":
        # Method of unfollowing from a dialog box

        click_element(self.browser, button)
        time.sleep(4)
        confirm_unfollow(self.browser)

    # general tasks after a successful unfollow
    self.logger.info("--> Unfollowed '{}'!".format(person))
    Event().unfollowed(person)
    update_activity(
        self.browser, action="unfollows", state=None, logfolder=self.logfolder, logger=self.logger
    )
    post_unfollow_cleanup(
        "successful", self.username, person, self.relationship_data, person_id, self.logger, self.logfolder
    )

    # get the post-unfollow delay time to sleep
    naply = get_action_delay("unfollow")
    time.sleep(naply)

    return True, "success"
