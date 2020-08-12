""" Module that handles the like features """
import random
import re
from re import findall
from time import sleep, perf_counter
from typing import List, Tuple

from selenium.webdriver.remote.webelement import WebElement

from iCerebro import ICerebro
import iCerebro.constants as C
import iCerebro.constants_css_selectors as CS
import iCerebro.constants_js_scripts as JS
import iCerebro.constants_x_paths as XP
from iCerebro.navigation import nf_go_to_tag_page, check_if_in_correct_page, nf_go_from_post_to_profile, \
    nf_go_to_user_page, nf_scroll_into_view, nf_click_center_of_element, nf_find_and_press_back
from iCerebro.quota_supervisor import quota_supervisor
from iCerebro.util import format_number, check_character_set
from iCerebro.util import add_user_to_blacklist
from iCerebro.util import is_private_profile
from iCerebro.util import is_page_available
from iCerebro.util import update_activity
from iCerebro.util import get_action_delay
from iCerebro.util import explicit_wait
from iCerebro.util import extract_text_from_element

from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException

from iCerebro.util import Interactions
from iCerebro.util_comment import process_comments
from iCerebro.util_follow import nf_validate_user_call, follow_restriction, follow_user


def like_by_tags(
        self: ICerebro,
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
            possible_posts = self.browser.execute_script(
                "return window._sharedData.entry_data."
                "TagPage[0].graphql.hashtag.edge_hashtag_to_media.count"
            )
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
            "desired amount: {}  |  top posts [{}] |  possible posts: "
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
        self: ICerebro,
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
            validation, details = nf_validate_user_call(self, username)
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
        self: ICerebro,
        amount
):
    if self.aborting:
        return self

    self.logger.info("Like by Feed - started")
    interactions = like_loop(self, "Feed", "https://www.instagram.com/", amount, True)
    self.logger.info("Like by Feed - ended")
    self.logger.info(interactions.__str__)
    self.interactions += interactions


def like_loop(
        self: ICerebro,
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
    try:
        while interactions.liked_img in range(0, amount):
            if self.jumps["consequent"]["likes"] >= self.jumps["limit"]["likes"]:
                self.logger.warning(
                    "Like quotient reached its peak, leaving Like By {} activity".format(what)
                )
                self.quotient_breach = True
                # reset jump counter after a breach report
                self.jumps["consequent"]["likes"] = 0
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
                self.logger.info("Scrolled too much. Sleeping 10 minutes")
                sleep(600)
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
                        amount,
                        users_validated
                    )
                    interactions += post_interactions
                    sleep(1)
                    nf_find_and_press_back(self, base_link)
                    already_interacted_links.append(link)
                    if msg == "block on likes":
                        # TODO deal with block on likes
                        pass

                    break
            else:
                # For loop ended means all posts in screen has been interacted with
                # will scroll the screen a bit and reload
                for i in range(3):
                    self.browser.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);"
                    )
                    update_activity(self.browser, state=None)
                    sc_rolled += 1
                    sleep(scroll_nap)

    except Exception:
        raise
    finally:
        return interactions


def interact_with_post(
        self: ICerebro,
        link: str,
        amount: int,
        user_validated: bool = False,
) -> Tuple[str, Interactions]:  # msg, post_interactions
    interactions = Interactions()
    try:
        self.logger.debug("Checking post")
        inappropriate, user_name, is_video, image_links, reason, scope = check_post(self, link)
        if not inappropriate:
            self.logger.debug("Validating user")
            sleep(1)
            if user_validated:
                valid = True
                details = "User already validated"
            else:
                valid, details = nf_validate_user_call(self, user_name, link)

            self.logger.info("{}Valid User, details: {}".format("" if valid else "Not ", details))

            if not valid:
                interactions.not_valid_users += 1
                return "Not valid user", interactions

            # try to like
            self.logger.debug("Liking post")
            sleep(1)
            like_state, msg = like_image(self, "user_name")

            if like_state is True:
                interactions.liked_img += 1
                self.logger.info("Like [{}/{}]".format(interactions.liked_img, amount))
                self.logger.info(link)
                # reset jump counter after a successful like
                self.jumps["consequent"]["likes"] = 0

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
                        and user_name not in self.settings.dont_include
                        and checked_img
                        and commenting
                ):
                    comments = self.settings.comments
                    comments.append(self.settings.video_comments if is_video else self.settings.photo_comments)
                    success = process_comments(self, user_name, comments, temp_comments)
                    if success:
                        interactions.commented += 1
                else:
                    self.logger.info("Not commented")
                    sleep(1)

                # follow
                if (
                        self.settings.do_follow
                        and user_name not in self.settings.dont_include
                        and checked_img
                        and following
                        and not follow_restriction(self, user_name)
                ):

                    self.logger.debug("Following user")
                    sleep(1)
                    follow_state, msg = follow_user(self, "post", user_name, None)
                    if follow_state is True:
                        interactions.followed += 1
                        self.logger.info("Followed user")
                    elif msg == "already followed":
                        interactions.already_followed += 1
                else:
                    self.logger.info("Not followed")
                    sleep(1)

                # interact (only of user not previously validated to impede recursion)
                if interact and not user_validated:
                    self.logger.info("Interacting with user '{}'".format(user_name))
                    # disable re-validating user in like_by_users
                    like_by_users(self, [user_name], None, True)

            elif msg == "already liked":
                interactions.already_liked += 1
                return msg, interactions

            elif msg == "block on likes":
                return msg, interactions

            elif msg == "jumped":
                # will break the loop after certain consecutive jumps
                self.jumps["consequent"]["likes"] += 1

            return "success", interactions

        else:
            self.logger.info(
                "Image not liked: {}\n{}".format(reason.encode("utf-8"), scope.encode("utf-8"))
            )
            interactions.inap_img += 1
            return "inap_img", interactions

    except NoSuchElementException as err:
        self.logger.error("Invalid Page: {}".format(err))
        return "Invalid Page", interactions


def get_media_edge_comment_string(media):
    options = ["edge_media_to_comment", "edge_media_preview_comment"]
    for option in options:
        try:
            media[option]
        except KeyError:
            continue
        return option


def check_post(
        self: ICerebro,
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

        caption = self.browser.find_element_by_xpath(XP.POST_CAPTION).text
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
                    "Not mandatory " "language",
                )

        # Append location to image_text so we can search through both in one go
        if location_text:
            self.logger.info("Location: {}".format(location_text.encode("utf-8")))
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
        # TODO: modify to use django database
        # if True:  # self.settings.store_in_database:
        #     try:
        #         user = db_get_or_create_user(self, username_text)
        #         already_saved_posts = self.db.session.query(Post).filter(Post.user == user).all()
        #         if post_link in [post.link for post in already_saved_posts]:
        #             raise SQLAlchemyError
        #         self.db.session.add(user)
        #         self.db.session.commit()
        #         db_posts = []
        #         for image_link, image_description in zip(image_links, image_descriptions):
        #             try:
        #                 post_date = self.browser.find_element_by_xpath(
        #                     '/html/body/div[1]/section/main/div/div/article//a[@class="c-Yi7"]/time'
        #                 ).get_attribute('datetime')
        #                 post_date = datetime.fromisoformat(post_date[:-1])
        #             except NoSuchElementException:
        #                 post_date = datetime.now()
        #             post = db_get_or_create_post(
        #                 self,
        #                 post_date,
        #                 post_link,
        #                 image_link,
        #                 caption,
        #                 likes_count,
        #                 user,
        #                 image_description
        #             )
        #             self.db.session.add(post)
        #             db_posts.append(post)
        #         self.db.session.commit()
        #         if db_posts:
        #             self.logger.info("About to store comments")
        #             db_store_comments(self, db_posts, post_link)
        #         self.db.session.expunge(user)
        #         for post in db_posts:
        #             self.db.session.expunge(post)
        #     except SQLAlchemyError:
        #         self.db.session.rollback()
        #     finally:
        #         self.db.session.commit()

        elapsed_time = perf_counter() - t
        self.logger.info("check post elapsed time: {:.0f} seconds".format(elapsed_time))


def get_like_count(
        self,
) -> int:
    try:
        likes_count = self.browser.execute_script(
            JS.LIKERS_COUNT_1
        )
        return likes_count
    except WebDriverException:
        try:
            self.browser.execute_script("location.reload()")
            update_activity(self.browser, state=None)

            likes_count = self.browser.execute_script(

            )
            return likes_count

        except WebDriverException:
            try:
                likes_count = self.browser.find_element_by_css_selector(CS.LIKES_COUNT).text
                if likes_count:
                    return format_number(likes_count)
                else:
                    self.logger.info("Failed to check likes' count  ~empty string\n")
                    return -1

            except NoSuchElementException:
                self.logger.info("Failed to check likes' count\n")
                return -1


def nf_get_all_posts_on_element(
        element: WebElement
) -> List[WebElement]:
    return element.find_elements_by_xpath(XP.POSTS_ON_ELEMENT)


def nf_get_all_users_on_element(
        self
) -> List[WebElement]:
    # return element.find_elements_by_xpath('//li/div/div[1]/div[2]/div[1]/a')
    return self.browser.find_elements_by_xpath(XP.USERS_ON_ELEMENT)


def like_image(self: ICerebro, username):
    """Likes the browser opened image"""
    # check action availability
    if quota_supervisor(C.LIKE) == C.JUMP:
        return False, "jumped"

    # find first for like element
    like_elem = self.browser.find_elements_by_xpath(XP.LIKE)

    if len(like_elem) == 1:
        sleep(1)
        nf_click_center_of_element(self, like_elem[0])
        # check now we have unlike instead of like
        liked_elem = self.browser.find_elements_by_xpath(XP.UNLIKE)

        if len(liked_elem) == 1:
            self.logger.info("Post Liked")
            update_activity(self, action=C.LIKE, state=None)
            # TODO:check blacklist idea
            # if blacklist["enabled"] is True:
            #     action = "liked"
            #     add_user_to_blacklist(
            #         username, blacklist["campaign"], action, logger, logfolder
            #     )

            # get the post-like delay time to sleep
            naply = get_action_delay(self, C.LIKE)
            sleep(naply)

            # after every 10 liked image do checking on the block
            if self.interactions.liked_img % 10 == 0 and not verify_liked_image(self):
                return False, "block on likes"

            return True, "success"

        else:
            # if like not seceded wait for 2 min
            self.logger.info("Couldn't like post, may be soft-blocked, bot will sleep for 2 minutes")
            sleep(120)

    else:
        liked_elem = self.browser.find_elements_by_xpath(XP.UNLIKE)
        if len(liked_elem) == 1:
            self.logger.info("Image was already liked")
            return False, "already liked"

    self.logger.info("Invalid Like Element")
    return False, "invalid element"


def verify_liked_image(self: ICerebro):
    """Check for a ban on likes using the last liked image"""
    self.browser.refresh()
    like_elem = self.browser.find_elements_by_xpath(XP.UNLIKE)

    if len(like_elem) == 1:
        return True
    else:
        self.logger.warning(
            "Bot has a block on likes!"
        )
        return False


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


def like_comment(self: ICerebro, original_comment_text):
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
                str(exc).encode("utf-8")
            )
        )
        return False, "error"

    return None, "unknown"
