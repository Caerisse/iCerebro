import random
from typing import List

from instapy.util import update_activity, format_number
from instapy.like_util import like_image, verify_liking
from instapy.xpath import read_xpath
from instapy.unfollow_util import follow_restriction, follow_user
from instapy.time_util import sleep

from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException

from iCerebro.navigation import nf_go_to_tag_page, nf_scroll_into_view, nf_click_center_of_element, \
    nf_find_and_press_back, nf_go_from_post_to_profile, nf_go_to_user_page, nf_go_to_follow_page, \
    check_if_in_correct_page
from iCerebro.utils import nf_check_post, nf_get_all_posts_on_element, nf_validate_user_call, process_comments, \
    nf_get_all_users_on_element


def like_by_tags(
        self,
        tags: List[str] = None,
        amount: int = 50,
        skip_top_posts: bool = True,
        use_smart_hashtags: bool = False,
        use_smart_location_hashtags: bool = False,
):
    """Likes (default) 50 images per given tag"""
    if self.aborting:
        return self

    # if smart hashtag is enabled
    if use_smart_hashtags is True and self.smart_hashtags != []:
        self.logger.info("Using smart hashtags")
        tags = self.smart_hashtags
    elif use_smart_location_hashtags is True and self.smart_location_hashtags != []:
        self.logger.info("Using smart location hashtags")
        tags = self.smart_location_hashtags

    # deletes white spaces in tags
    tags = [tag.strip() for tag in tags]
    tags = tags or []
    self.quotient_breach = False

    for index, tag in enumerate(tags):
        if self.quotient_breach:
            break

        state = {
            'liked_img': 0,
            'already_liked': 0,
            'inap_img': 0,
            'commented': 0,
            'followed': 0,
            'not_valid_users': 0,
        }

        self.logger.info("Tag [{}/{}]".format(index + 1, len(tags)))
        self.logger.info("--> {}".format(tag.encode("utf-8")))

        tag = tag[1:] if tag[:1] == "#" else tag

        nf_go_to_tag_page(self, tag)

        # get amount of post with this hashtag
        try:
            possible_posts = self.browser.execute_script(
                "return window._sharedData.entry_data."
                "TagPage[0].graphql.hashtag.edge_hashtag_to_media.count"
            )
        except WebDriverException:
            try:
                possible_posts = self.browser.find_element_by_xpath(
                    read_xpath("get_links_for_tag", "possible_post")
                ).text
                if possible_posts:
                    possible_posts = format_number(possible_posts)
                else:
                    self.logger.info(
                        "Failed to get the amount of possible posts in '{}' tag  "
                        "~empty string".format(tag)
                    )
                    possible_posts = None

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

        try_again = 0
        sc_rolled = 0
        scroll_nap = 1.5
        already_interacted_links = []
        try:
            while state['liked_img'] in range(0, amount):
                if sc_rolled > 100:
                    try_again += 1
                    if try_again > 2:
                        self.logger.info(
                            "'{}' tag POSSIBLY has less images than "
                            "desired:{} found:{}...".format(
                                tag,
                                amount,
                                len(already_interacted_links)
                            )
                        )
                        break
                    self.logger.info("Scrolled too much! ~ sleeping 10 minutes")
                    sleep(600)
                    sc_rolled = 0

                main_elem = self.browser.find_element_by_tag_name("main")
                posts = nf_get_all_posts_on_element(main_elem)

                # Interact with links instead of just storing them
                for post in posts:
                    link = post.get_attribute("href")
                    if link not in already_interacted_links:

                        self.logger.info("about to scroll to post")
                        sleep(1)
                        nf_scroll_into_view(self, post)
                        self.logger.info("about to click to post")
                        sleep(1)
                        nf_click_center_of_element(self, post)

                        success, msg, state = nf_interact_with_post(
                            self,
                            link,
                            amount,
                            state,
                        )

                        self.logger.info("Returned from liking, should still be in post page")
                        sleep(2)
                        nf_find_and_press_back(self, "https://www.instagram.com/explore/tags/{}/".format(tag))

                        already_interacted_links.append(link)

                        if success:
                            break
                        if msg == "block on likes":
                            # TODO deal with block on likes
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

        sleep(2)

        self.logger.info("Tag [{}/{}]".format(index + 1, len(tags)))
        self.logger.info("--> {} ended".format(tag.encode("utf-8")))
        self.logger.info("Liked: {}".format(state['liked_img']))
        self.logger.info("Already Liked: {}".format(state['already_liked']))
        self.logger.info("Commented: {}".format(state['commented']))
        self.logger.info("Followed: {}".format(state['followed']))
        self.logger.info("Inappropriate: {}".format(state['inap_img']))
        self.logger.info("Not valid users: {}\n".format(state['not_valid_users']))

        self.liked_img += state['liked_img']
        self.already_liked += state['already_liked']
        self.commented += state['commented']
        self.followed += state['followed']
        self.inap_img += state['inap_img']
        self.not_valid_users += state['not_valid_users']

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

    amount = amount or self.user_interact_amount
    usernames = usernames or []
    self.quotient_breach = False

    for index, username in enumerate(usernames):
        if self.quotient_breach:
            break

        state = {
            'liked_img': 0,
            'already_liked': 0,
            'inap_img': 0,
            'commented': 0,
            'followed': 0,
            'not_valid_users': 0,
        }

        self.logger.info(
            "Username [{}/{}]".format(index + 1, len(usernames))
        )
        self.logger.info("--> {}".format(username.encode("utf-8")))

        if len(usernames) == 1 and users_validated:
            nf_go_from_post_to_profile(self, username)
        else:
            nf_go_to_user_page(self, username)

        if not users_validated:
            validation, details = nf_validate_user_call(self, username)
            if not validation:
                self.logger.info(
                    "--> Not a valid user: {}".format(details)
                )
                state["not_valid_users"] += 1
                continue

        try_again = 0
        sc_rolled = 0
        scroll_nap = 1.5
        already_interacted_links = []
        try:
            while state['liked_img'] in range(0, amount):

                if self.jumps["consequent"]["likes"] >= self.jumps["limit"]["likes"]:
                    self.logger.warning(
                        "--> Like quotient reached its peak!\t~leaving "
                        "Like-By-Users activity\n"
                    )
                    self.quotient_breach = True
                    # reset jump counter after a breach report
                    self.jumps["consequent"]["likes"] = 0
                    break

                if sc_rolled > 100:
                    try_again += 1
                    if try_again > 2:  # you can try again as much as you want by changing this number
                        self.logger.info(
                            "'{}' user POSSIBLY has less valid images than "
                            "desired:{} found:{}...".format(
                                username, amount, len(already_interacted_links))
                        )
                        break
                    self.logger.info(
                        "Scrolled too much! ~ sleeping 10 minutes")
                    sleep(600)
                    sc_rolled = 0

                main_elem = self.browser.find_element_by_tag_name("main")
                # feed = main_elem.find_elements_by_xpath('//div[@class=" _2z6nI"]')
                posts = nf_get_all_posts_on_element(main_elem)

                # Interact with links instead of just storing them
                for post in posts:
                    link = post.get_attribute("href")
                    if link not in already_interacted_links:
                        self.logger.info("about to scroll to post")
                        sleep(1)
                        nf_scroll_into_view(self, post)
                        self.logger.info("about to click to post")
                        sleep(1)
                        nf_click_center_of_element(self, post)

                        success, msg, state = nf_interact_with_post(
                            self,
                            link,
                            amount,
                            state,
                            users_validated,
                        )

                        self.logger.info(
                            "Returned from liking, should still be in post page")
                        sleep(5)
                        nf_find_and_press_back(
                            self,
                            "https://www.instagram.com/{}/".format(username)
                        )

                        already_interacted_links.append(link)

                        if success:
                            break
                        if msg == "block on likes":
                            # TODO deal with block on likes
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

        sleep(4)

        self.logger.info("Username [{}/{}]".format(index + 1, len(usernames)))
        self.logger.info("--> {} ended".format(username.encode("utf-8")))
        self.logger.info("Liked: {}".format(state['liked_img']))
        self.logger.info("Already Liked: {}".format(state['already_liked']))
        self.logger.info("Commented: {}".format(state['commented']))
        self.logger.info("Followed: {}".format(state['followed']))
        self.logger.info("Inappropriate: {}".format(state['inap_img']))
        self.logger.info("Not valid users: {}\n".format(state['not_valid_users']))

        self.liked_img += state['liked_img']
        self.already_liked += state['already_liked']
        self.commented += state['commented']
        self.followed += state['followed']
        self.inap_img += state['inap_img']
        self.not_valid_users += state['not_valid_users']

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
            "nf_follow_user_follow: follow must be one of %r." % valid)

    self.logger.info("Starting to follow user {}".format(follow))

    for index, username in enumerate(usernames):
        state = {
            'liked_img': 0,
            'already_liked': 0,
            'inap_img': 0,
            'commented': 0,
            'followed': 0,
            'not_valid_users': 0,
        }

        self.logger.info("User [{}/{}]".format(index + 1, len(usernames)))
        self.logger.info("--> {}".format(username.encode("utf-8")))

        nf_go_to_user_page(self, username)
        sleep(1)

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
        random_chance = 50
        try:
            while state['followed'] in range(0, actual_amount):
                if self.quotient_breach:
                    self.logger.warning(
                        "--> Follow quotient reached its peak!"
                        "\t~leaving Follow-User-Follow_ activity\n"
                    )
                    break

                if sc_rolled > 100:
                    self.logger.info("Scrolled too much! ~ sleeping 10 minutes")
                    sleep(600)
                    sc_rolled = 0

                users = nf_get_all_users_on_element(self)

                # Interact with links instead of just storing them
                for user in users:
                    link = user.get_attribute("href")
                    if link not in already_interacted_links:
                        msg = ""
                        try:
                            self.logger.info("about to scroll to user")
                            sleep(1)
                            nf_scroll_into_view(self, user)
                            self.logger.info("about to click to user")
                            sleep(1)
                            nf_click_center_of_element(self, user)
                            sleep(2)
                            valid = False
                            if (
                                    user.text not in self.dont_include
                                    and not follow_restriction(
                                        "read", user.text, self.follow_times, self.logger
                                    and random.randint(0, 100) <= random_chance
                                    )
                            ):
                                valid, details = nf_validate_user_call(self, user.text)
                                self.logger.info("Valid User: {}, details: {}".format(valid, details))
                            if valid:
                                self.logger.info("about to follow user")
                                follow_state, msg = follow_user(
                                    self.browser,
                                    "profile",
                                    self.username,
                                    user.text,
                                    None,
                                    self.blacklist,
                                    self.logger,
                                    self.logfolder,
                                )
                                if follow_state is True:
                                    state['followed'] += 1
                                    self.logger.info("user followed")
                                else:
                                    self.logger.info("--> Not following")
                                    sleep(1)
                                if random.randint(0, 100) <= self.user_interact_percentage:
                                    self.logger.info(
                                        "--> User gonna be interacted: '{}'".format(
                                            user.text
                                        )
                                    )
                                # disable re-validating user in like_by_users
                                like_by_users(
                                    self,
                                    [user.text],
                                    None,
                                    True,
                                )
                            else:
                                state["not_valid_users"] += 1

                        finally:
                            sleep(5)
                            user_link = "https://www.instagram.com/{}".format(username)
                            follow_link = "https://www.instagram.com/{}/{}".format(username, follow)
                            nf_find_and_press_back(self, follow_link)
                            sleep(3)
                            if check_if_in_correct_page(self, user_link):
                                nf_go_to_follow_page(self, follow, username)
                            already_interacted_links.append(link)
                            if msg == "block on follow":
                                pass  # TODO deal with block on follow
                            break
                else:
                    # For loop ended means all users in screen has been interacted with
                    scrolled_to_bottom = self.browser.execute_script(
                        "return window.scrollMaxY == window.scrollY"
                    )
                    if scrolled_to_bottom and randomize and random_chance < 100:
                        random_chance += 25
                        self.browser.execute_script(
                            "window.scrollTo(0, 0);"
                        )
                        update_activity(self.browser, state=None)
                        sc_rolled += 1
                        sleep(scroll_nap)
                    elif scrolled_to_bottom:
                        # already followed all possibles users
                        break
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

        sleep(4)

        self.logger.info("User [{}/{}]".format(index + 1, len(usernames)))
        self.logger.info("Liked: {}".format(state['liked_img']))
        self.logger.info("Already Liked: {}".format(state['already_liked']))
        self.logger.info("Commented: {}".format(state['commented']))
        self.logger.info("Followed: {}".format(state['followed']))
        self.logger.info("Inappropriate: {}".format(state['inap_img']))
        self.logger.info("Not valid users: {}\n".format(state['not_valid_users']))

        self.liked_img += state['liked_img']
        self.already_liked += state['already_liked']
        self.commented += state['commented']
        self.followed += state['followed']
        self.inap_img += state['inap_img']
        self.not_valid_users += state['not_valid_users']

    return self


def nf_interact_with_post(
        self,
        link: str,
        amount: int,
        state: dict,
        user_validated: bool = False,
):
    try:
        self.logger.info("about to check post")
        sleep(1)
        inappropriate, user_name, is_video, image_links, reason, scope = nf_check_post(self, link)
        self.logger.info("about to verify post")
        sleep(1)
        if not inappropriate and self.delimit_liking:
            self.liking_approved = verify_liking(
                self.browser, self.max_likes, self.min_likes, self.logger
            )

        if not inappropriate and self.liking_approved:
            # validate user
            self.logger.info("about to validate user")
            sleep(1)
            if user_validated:
                valid = True
                details = "User already validated"
            else:
                valid, details = nf_validate_user_call(self, user_name, link)

            self.logger.info("Valid User: {}, details: {}".format(valid, details))

            if not valid:
                state["not_valid_users"] += 1
                return True, "not_valid_users", state

            # try to like
            self.logger.info("about to like post")
            sleep(1)
            like_state, msg = like_image(
                self.browser,
                "user_name",
                self.blacklist,
                self.logger,
                self.logfolder,
                state['liked_img'],
            )

            if like_state is True:
                state['liked_img'] += 1
                self.logger.info("Like# [{}/{}]".format(state['liked_img'], amount))
                self.logger.info(link)
                # reset jump counter after a successful like
                self.jumps["consequent"]["likes"] = 0

                checked_img = True
                temp_comments = []

                commenting = random.randint(0, 100) <= self.comment_percentage
                following = random.randint(0, 100) <= self.follow_percentage
                interact = random.randint(0, 100) <= self.user_interact_percentage

                if self.use_image_analysis and (following or commenting):
                    try:
                        (
                            checked_img,
                            temp_comments,
                            image_analysis_tags,
                        ) = self.ImgAn.image_analysis(image_links, logger=self.logger)
                        # TODO: image_analysis
                    except Exception as err:
                        self.logger.error(
                            "Image analysis error: {}".format(err)
                        )

                # comments
                if (
                        self.do_comment
                        and user_name not in self.dont_include
                        and checked_img
                        and commenting
                ):
                    comments = (self.comments +
                                (self.video_comments if is_video else self.photo_comments))

                    success = process_comments(self, user_name, comments, temp_comments)

                    if success:
                        state['commented'] += 1
                else:
                    self.logger.info("--> Not commented")
                    sleep(1)

                # following
                if (
                        self.do_follow
                        and user_name not in self.dont_include
                        and checked_img
                        and following
                        and not follow_restriction(
                            "read", user_name, self.follow_times, self.logger
                        )
                ):

                    self.logger.info("about to follow user")
                    sleep(1)
                    follow_state, msg = follow_user(
                        self.browser,
                        "post",
                        self.username,
                        user_name,
                        None,
                        self.blacklist,
                        self.logger,
                        self.logfolder,
                    )
                    if follow_state is True:
                        state['followed'] += 1
                        self.logger.info("user followed")
                    else:
                        self.logger.info("--> Not following")
                        sleep(1)

                # interactions (only of user not previously validated to impede recursion)
                if interact and not user_validated:
                    self.logger.info(
                        "--> User gonna be interacted: '{}'".format(
                            user_name
                        )
                    )

                    # disable re-validating user in like_by_users
                    like_by_users(
                        self,
                        [user_name],
                        None,
                        True,
                    )

            elif msg == "already liked":
                state['already_liked'] += 1
                return True, msg, state

            elif msg == "block on likes":
                return False, msg, state

            elif msg == "jumped":
                # will break the loop after certain consecutive
                # jumps
                self.jumps["consequent"]["likes"] += 1

            return True, "success", state

        else:
            self.logger.info(
                "--> Image not liked: {}".format(reason.encode("utf-8"))
            )
            state["inap_img"] += 1
            return True, "inap_img", state

    except NoSuchElementException as err:
        self.logger.error("Invalid Page: {}".format(err))
        return False, "Invalid Page", state
