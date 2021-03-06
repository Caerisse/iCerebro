from datetime import datetime
import random
import re
from re import findall
from time import perf_counter, sleep
from typing import Tuple
from typing import List

import iCerebro.constants_x_paths as XP
import iCerebro.constants_js_scripts as JS
from iCerebro.util_loggers import LogDecorator
from iCerebro.navigation import nf_scroll_into_view, nf_click_center_of_element, nf_find_and_press_back, \
    check_if_in_correct_page, nf_go_from_post_to_profile, explicit_wait, SoftBlockedException, check_for_error
from iCerebro.util import Interactions, nf_get_all_posts_on_element, nf_validate_user_call, check_character_set, \
    get_user_data, format_number, extract_text_from_element, get_like_count, sleep_while_blocked
from iCerebro.util_db import store_post, store_comments, add_user_to_blacklist, is_follow_restricted, deform_emojis
from iCerebro.util_follow import follow_user

from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException


@LogDecorator()
def like_loop(
        self,
        what: str,
        base_link: str,
        amount: int,
        users_validated: False
) -> Interactions:
    try_again = 0
    sc_rolled = 0
    scroll_nap = 1.5
    already_interacted_links = []
    interactions = Interactions()
    likes = 0
    try:
        while likes in range(0, amount):
            if self.aborting or (self.until_time and datetime.now() > self.until_time):
                break
            
            if self.jumps.check_likes():
                self.logger.warning(
                    "Like quotient reached its peak, leaving Like By {} activity".format(what)
                )
                self.quotient_breach = True
                # reset jump counter after a breach report
                self.jumps.likes = 0
                break

            if sc_rolled > 100:
                try_again += 1
                if try_again > 2:
                    self.logger.info(
                        "'{}' possibly has less images than "
                        "desired ({}), found: {}".format(
                            what,
                            amount,
                            len(already_interacted_links)
                        )
                    )
                    break
                delay_random = random.randint(400, 600)
                self.logger.info(
                    "Scrolled too much. Sleeping {} minutes and {} seconds".format(
                        int(delay_random/60),
                        delay_random % 60
                    )
                )
                sleep(delay_random)
                sc_rolled = 0

            main_elem = self.browser.find_element_by_tag_name("main")
            posts = nf_get_all_posts_on_element(main_elem)

            # Interact with links
            for post in posts:
                link = post.get_attribute("href")
                if link not in already_interacted_links:
                    sleep(1)
                    nf_scroll_into_view(self, post)
                    sleep(1)
                    nf_click_center_of_element(self, post, link)
                    msg, post_interactions = interact_with_post(
                        self,
                        link,
                        users_validated
                    )
                    interactions += post_interactions
                    if post_interactions.liked_img > 0:
                        likes += 1
                        self.logger.info("[{}] - Like [{}/{}]".format(
                            what, likes, amount))
                    if msg == "block on likes":
                        raise SoftBlockedException(msg)
                    else:
                        sleep(1)
                    nf_find_and_press_back(self, base_link)
                    already_interacted_links.append(link)
                    break
            else:
                # For loop ended means all posts in screen has been interacted with
                # will scroll the screen a bit and reload
                for i in range(3):
                    self.browser.execute_script(JS.SCROLL_SCREEN)
                    self.quota_supervisor.add_server_call()
                    sc_rolled += 1
                    sleep(scroll_nap)
    except SoftBlockedException:
        sleep_while_blocked(self)
    except Exception as err:
        self.logger.error("Unexpected Exception: {}".format(err))
    finally:
        return interactions


@LogDecorator()
def interact_with_post(
        self,
        link: str,
        user_validated: bool = False,
) -> Tuple[str, Interactions]:  # msg, post_interactions
    interactions = Interactions()
    try:
        self.logger.debug("Checking post")
        if verify_liked_image(self):
            interactions.already_liked += 1
            return "already liked", interactions
        else:
            inappropriate, user_name, is_video, image_links, reason, scope = check_post(self, link)
        if not inappropriate:
            sleep(1)
            if user_validated:
                valid = True
                details = "User already validated"
            else:
                self.logger.debug("Validating user")
                valid, details = nf_validate_user_call(self, user_name, self.quota_supervisor.LIKE, link)
                self.logger.info("'{}' is{} a valid user{}".format(
                    user_name,
                    "" if valid else " not",
                    "" if valid else ": {}".format(details)
                ))

            if not valid:
                interactions.not_valid_users += 1
                return "Not valid user", interactions

            # try to like
            self.logger.debug("Liking post")
            sleep(1)
            like_state, msg = like_image(self, user_name)

            if like_state is True:
                interactions.liked_img += 1
                # reset jump counter after a successful like
                self.jumps.likes = 0

                checked_img = True
                temp_comments = []

                commenting = random.randint(0, 100) <= self.settings.comment_percentage
                following = random.randint(0, 100) <= self.settings.follow_percentage
                interact = random.randint(0, 100) <= self.settings.user_interact_percentage

                if self.settings.use_image_analysis and commenting:
                    try:
                        checked_img, temp_comments, image_analysis_tags = self.ImgAn.image_analysis(
                            image_links, logger=self.logger
                        )
                    except Exception as err:
                        self.logger.error(
                            "Image analysis error: {}".format(err)
                        )

                # comment
                if (
                        self.settings.do_comment
                        and checked_img
                        and commenting
                        and user_name not in self.settings.dont_include
                ):
                    comments = self.settings.comments
                    comments.append(self.settings.video_comments if is_video else self.settings.photo_comments)
                    # TODO: util_comment
                    # success = process_comments(self, user_name, comments, temp_comments)
                    # if success:
                    #     interactions.commented += 1
                else:
                    if self.settings.do_comment:
                        self.logger.info("Not commented")
                    sleep(1)

                # follow or interact only of user not previously validated to avoid recursion
                if not user_validated:
                    # follow
                    if (
                            self.settings.do_follow
                            and checked_img
                            and following
                            and user_name not in self.settings.dont_include
                            and not is_follow_restricted(self, user_name)
                    ):
                        self.logger.debug("Following user")
                        follow_state, msg = follow_user(self, "post", user_name, None)
                        if follow_state is True:
                            interactions.followed += 1
                        elif msg == "already followed":
                            interactions.already_followed += 1
                        sleep(1)

                    # interact
                    if self.settings.do_like and interact:
                        self.logger.info("Interacting with user '{}'".format(user_name))
                        user_link = "https://www.instagram.com/{}/".format(user_name)
                        if not check_if_in_correct_page(self, user_link):
                            nf_go_from_post_to_profile(self, user_name)
                        interactions += like_loop(
                            self,
                            "Interact with user '{}'".format(user_name),
                            user_link,
                            self.settings.user_interact_amount,
                            True
                        )

            elif msg == "already liked":
                interactions.already_liked += 1
                return msg, interactions

            elif msg == "block on likes":
                return msg, interactions

            elif msg == "jumped":
                # will break the loop after certain consecutive jumps
                self.jumps.likes += 1

            return "success", interactions

        else:
            self.logger.info(
                "Image not liked: {}\n{}".format(reason, scope)
            )
            interactions.inap_img += 1
            return "inap_img", interactions

    except NoSuchElementException as err:
        self.logger.error("Invalid Page: {}".format(err))
        return "Invalid Page", interactions
    except Exception as err:
        self.logger.error("Unexpected Exception: {}".format(err))
        return "Unexpected Exception", interactions


@LogDecorator()
def get_media_edge_comment_string(media):
    options = ["edge_media_to_comment", "edge_media_preview_comment"]
    for option in options:
        try:
            media[option]
        except KeyError:
            continue
        return option


@LogDecorator()
def check_post(
        self,
        post_link: str
) -> Tuple[bool, str, bool, List[str], str, str]:
    """Checks if post can be liked according to declared settings

    Also stores post data in database if appropriate

    :returns: inappropriate, username, is_video, image_links, reason, scope
    """
    t = perf_counter()
    username_text = ""
    caption = ""
    image_descriptions = []
    image_links = []
    likes_count = None
    try:
        username = self.browser.find_element_by_xpath(XP.POST_USERNAME)
        username_text = username.text
        if "\nVerified" in username_text:
            username_text = username_text.replace("\nVerified", "")

        # follow_button = self.browser.find_element_by_xpath(POST_FOLLOW_BUTTON)
        # following = follow_button.text == "Following"

        locations = self.browser.find_elements_by_xpath(XP.POST_LOCATION)
        location_text = locations[0].text if locations != [] else None
        # location_link = locations[0].get_attribute('href') if locations != [] else None

        images = self.browser.find_elements_by_xpath(XP.POST_IMAGES)
        """
        video_previews = self.browser.find_elements_by_xpath(XP.POST_VIDEO_PREVIEWS)
        videos = self.browser.find_elements_by_xpath(XP.POST_VIDEOS)
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

        caption = self.browser.find_elements_by_xpath(XP.POST_CAPTION)
        caption = caption[0].text if caption else ""
        caption = caption if caption is not None else ""
        caption, emoji_less_caption = deform_emojis(caption)

        for image in images:
            image_description = image.get_attribute('alt')
            if image_description is not None and 'Image may contain:' in image_description:
                image_description = image_description[image_description.index(
                    'Image may contain:') + 19:]
            else:
                image_description = None

            image_descriptions.append(image_description)
            image_links.append(image.get_attribute('src'))
        
        log = ""
        log += "Post from: {}\n".format(username_text)
        log += "Link: {}\n".format(post_link)
        log += "Caption: {}\n".format(caption)
        for image_description in image_descriptions:
            if image_description:
                log += "Description: {}\n".format(image_description)
        if location_text:
            log += "Location: {}".format(location_text)
        self.logger.info(log)
                

        # Check if likes_count is between minimum and maximum values defined by user
        if self.settings.delimit_liking:
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
            elif self.settings.max_likes and likes_count > self.settings.max_likes:
                return (
                    True,
                    username_text,
                    is_video,
                    image_links,
                    "Delimited by liking",
                    "maximum limit: {}, post has: {}".format(self.settings.max_likes, likes_count)
                )
            elif self.settings.min_likes and likes_count < self.settings.min_likes:
                return (
                    True,
                    username_text,
                    is_video,
                    image_links,
                    "Delimited by liking",
                    "minimum limit: {}, post has: {}".format(self.settings.min_likes, likes_count)
                )

        # Check if mandatory character set, before adding the location to the text
        if self.settings.mandatory_language:
            if not check_character_set(self, caption):
                return (
                    True,
                    username_text,
                    is_video,
                    image_links,
                    "Mandatory language not fulfilled",
                    "Not mandatory language character found",
                )

        # Append location to image_text so we can search through both in one go
        if location_text:
            caption = caption + "\n" + location_text

        if self.settings.mandatory_words:
            if not any((word in caption for word in self.settings.mandatory_words)):
                return (
                    True,
                    username_text,
                    is_video,
                    image_links,
                    "Mandatory words not fulfilled",
                    "Not mandatory likes",
                )

        image_text_lower = [x.lower() for x in caption]
        ignore_if_contains_lower = [x.lower() for x in self.settings.ignore_if_contains]
        if any((word in image_text_lower for word in ignore_if_contains_lower)):
            return (
                False,
                username_text,
                is_video,
                image_links,
                "Contains word in ignore_if_contains list",
                "Ignore if contains")

        dont_like_regex = []

        for dont_likes in self.settings.dont_like:
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
                    (((quash.group(0)).split("#")[1]).split(" ")[0]).split("\n")[0].encode("utf-8")
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
                reason = 'Inappropriate: contains "{}"'.format(
                    quashed if iffy == quashed else '" in "'.join([str(iffy), str(quashed)])
                )
                return True, username_text, is_video, image_links, reason, "Undesired word"

        return False, username_text, is_video, image_links, "None", "Success"
    finally:
        try:
            post_date = self.browser.find_element_by_xpath(XP.POST_DATE).get_attribute('datetime')
            post_date = datetime.fromisoformat(post_date[:-1])
        except NoSuchElementException:
            post_date = datetime.now()
        self.logger.debug("Storing Post")
        post = store_post(post_link, username_text, post_date, image_links,
                          caption, likes_count, image_descriptions)
        self.logger.debug("Storing Comments")
        # store_comments(self, post)
        elapsed_time = perf_counter() - t
        self.logger.info("Check post elapsed time: {:.0f} seconds".format(elapsed_time))


@LogDecorator()
def like_image(self, username, trying_again=False):
    """Likes the browser opened image"""
    # check action availability
    if self.quota_supervisor.jump_like():
        return False, "jumped"

    # find first for like element
    like_elem = self.browser.find_elements_by_xpath(XP.LIKE)

    if len(like_elem) == 1:
        sleep(1)
        nf_scroll_into_view(self, like_elem[0])
        sleep(1)
        nf_click_center_of_element(self, like_elem[0])
        # check now we have unlike instead of like
        liked_elem = self.browser.find_elements_by_xpath(XP.UNLIKE)

        if len(liked_elem) == 1:
            self.logger.info("Post Liked")
            add_user_to_blacklist(self, username, self.quota_supervisor.LIKE)
            self.quota_supervisor.add_like()
            # after every 10 liked image do checking on the block
            if self.interactions.liked_img % 10 == 0 and not verify_liked_image(self):
                return False, "block on likes"

            return True, "success"

        elif not trying_again:
            # if like not seceded wait for 2 min
            self.logger.info("Couldn't like post, may be soft-blocked, bot will sleep for 2 minutes and try again")
            sleep(120)
            like_image(self, username, True)
        else:
            return False, "block on likes"

    else:
        liked_elem = self.browser.find_elements_by_xpath(XP.UNLIKE)
        if len(liked_elem) == 1:
            self.logger.info("Image was already liked")
            return False, "already liked"

    self.logger.info("Invalid Like Element")
    return False, "invalid element"


@LogDecorator()
def verify_liked_image(self):
    """Check for a ban on likes using the last liked image"""
    self.browser.refresh()
    like_elem = self.browser.find_elements_by_xpath(XP.UNLIKE)

    if len(like_elem) == 1:
        return True
    else:
        return False


@LogDecorator()
def get_tags(self):
    """Gets all the tags of the given description in the url"""
    try:
        self.browser.execute_script(JS.ADDITIONAL_DATA)
    except WebDriverException:
        self.browser.execute_script(JS.SHARED_DATA)

    graphql = self.browser.execute_script(JS.RETURN_DATA)

    if graphql:
        image_text = self.browser.execute_script(JS.CAPTION_1)

    else:
        image_text = self.browser.execute_script(JS.CAPTION_2)

    tags = findall(r"#\w*", image_text)

    return tags


@LogDecorator()
def like_comment(self, original_comment_text):
    """ Like the given comment """
    try:
        comments_block = self.browser.find_elements_by_xpath(XP.COMMENTS_BLOCK)
        for comment_line in comments_block:
            comment_elem = comment_line.find_elements_by_tag_name("span")[0]
            comment = extract_text_from_element(comment_elem)

            if comment and (comment == original_comment_text):
                # find "Like" span (a direct child of Like button)
                span_like_elements = comment_line.find_elements_by_xpath(XP.SPAN_LIKE_ELEMENTS)
                if not span_like_elements:
                    # this is most likely a liked comment
                    return True, "success"

                # like the given comment
                span_like = span_like_elements[0]
                comment_like_button = span_like.find_element_by_xpath(XP.COMMENT_LIKE_BUTTON)
                nf_click_center_of_element(self, comment_like_button)

                # verify if like succeeded by waiting until the like button
                # element goes stale..
                button_change = explicit_wait(self, "SO", [comment_like_button], 7, False)

                if button_change:
                    self.logger.info("Liked comment")
                    sleep(random.uniform(1, 2))
                    return True, "success"

                else:
                    self.logger.info("Failed to Like comment")
                    sleep(random.uniform(0, 1))
                    return False, "failure"

    except (NoSuchElementException, StaleElementReferenceException) as exc:
        self.logger.error(
            "Error occurred while liking a comment.\n\t{}\n\n".format(
                str(exc)
            )
        )
        return False, "error"

    return None, "unknown"
