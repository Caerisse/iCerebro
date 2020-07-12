import csv
import os
import re
import time
from datetime import datetime
import random
from typing import List, Tuple

from instapy.comment_util import verify_commenting, comment_image
from instapy.util import get_current_url, get_relationship_counts, truncate_float, getUserData, \
    default_profile_pic_instagram
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from sqlalchemy.exc import SQLAlchemyError

from iCerebro.db_utils import db_get_or_create_user, db_get_or_create_post, db_store_comments
from iCerebro.navigation import nf_scroll_into_view, nf_go_from_post_to_profile, nf_find_and_press_back


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
                        image_link,
                        caption,
                        user,
                        image_description
                    )
                    self.db.session.add(post)
                    db_posts.append(post)
                self.db.session.commit()
                if db_posts:
                    self.logger.info("About to store comments")
                    db_store_comments(self, db_posts, post_link)
            except SQLAlchemyError:
                self.db.session.rollback()
            finally:
                self.db.session.commit()

        elapsed_time = time.perf_counter() - t
        self.logger.info("check post elapsed time: {:.0f} seconds".format(elapsed_time))


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
