import random
from platform import python_version
from typing import List

from instapy.util import update_activity, format_number, highlight_print
from instapy.like_util import like_image
from instapy.xpath import read_xpath
from instapy.unfollow_util import follow_restriction, follow_user, set_automated_followed_pool
from instapy.time_util import sleep

from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException

from iCerebro.navigation import nf_go_to_tag_page, nf_scroll_into_view, nf_click_center_of_element, \
    nf_find_and_press_back, nf_go_from_post_to_profile, nf_go_to_user_page, nf_go_to_follow_page, \
    check_if_in_correct_page
from iCerebro.utils import nf_check_post, nf_get_all_posts_on_element, nf_validate_user_call, process_comments, \
    nf_get_all_users_on_element, unfollow


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
        tag_link =  "https://www.instagram.com/explore/tags/{}/".format(tag)
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

        like_loop(self, "TAG", tag_link, amount, state, False)

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
                    "--> Not a valid user: {}".format(details)
                )
                state["not_valid_users"] += 1
                continue

        like_loop(self, "USER", user_link, amount, state, users_validated)

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
            "follow_user_follow: follow must be one of %r." % valid)

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
                while len(users) == 0:
                    nf_find_and_press_back(self, user_link)
                    in_user_page = check_if_in_correct_page(self, user_link)
                    if not in_user_page:
                        nf_go_to_user_page(self, username)
                    nf_go_to_follow_page(self, follow, username)
                    users = nf_get_all_users_on_element(self)
                    if len(users) == 0:
                        self.logger.info("Soft block on see followers ~ sleeping 5 minutes")
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
                            self.logger.info("Followed [{}/{}]".format(state["followed"], actual_amount))
                            self.logger.info("--> Trying user {}".format(user_text.encode("utf-8")))
                            nf_scroll_into_view(self, user)
                            sleep(1)
                            nf_click_center_of_element(self, user, user_link2)
                            sleep(2)
                            valid = False
                            if (
                                    user_text not in self.dont_include
                                    and not follow_restriction(
                                        "read", user_text, self.follow_times, self.logger
                                    )
                                    and random.randint(0, 100) <= random_chance
                            ):
                                valid, details = nf_validate_user_call(self, user_text)
                                self.logger.info("Valid User: {}, details: {}".format(valid, details))
                            if valid:
                                follow_state, msg = follow_user(
                                    self.browser,
                                    "profile",
                                    self.username,
                                    user_text,
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
                                            user_text
                                        )
                                    )
                                    # disable re-validating user in like_by_users
                                    like_by_users(
                                        self,
                                        [user_text],
                                        None,
                                        True,
                                    )
                            else:
                                state["not_valid_users"] += 1
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
        inappropriate, user_name, is_video, image_links, reason, scope = nf_check_post(self, link)
        if not inappropriate:
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
                "--> Image not liked: {}\n{}".format(reason.encode("utf-8"), scope.encode("utf-8"))
            )
            state["inap_img"] += 1
            return True, "inap_img", state

    except NoSuchElementException as err:
        self.logger.error("Invalid Page: {}".format(err))
        return False, "Invalid Page", state


def unfollow_users(
        self,
        amount: int = 10,
        custom_list_enabled: bool = False,
        custom_list=None,
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
    """Unfollows (default) 10 users from your following list"""

    if custom_list is None:
        custom_list = []
    if self.aborting:
        return self

    message = "Starting to unfollow users.."
    highlight_print(self.username, message, "feature", "info", self.logger)

    if unfollow_after is not None:
        if not python_version().startswith(("2.7", "3")):
            self.logger.warning(
                "`unfollow_after` parameter is not"
                " available for Python versions below 2.7"
            )
            unfollow_after = None

    self.automatedFollowedPool = set_automated_followed_pool(
        self.username,
        unfollow_after,
        self.logger,
        self.logfolder,
        delay_followbackers,
    )

    try:
        unfollowed = unfollow(
            self,
            amount,
            (custom_list_enabled, custom_list, custom_list_param),
            (instapy_followed_enabled, instapy_followed_param),
            nonFollowers,
            allFollowing,
            style,
            sleep_delay,
            delay_followbackers,
        )
        self.logger.info("--> Total people unfollowed : {}\n".format(unfollowed))
        self.unfollowed += unfollowed

    except Exception as exc:
        if isinstance(exc, RuntimeWarning):
            self.logger.warning("Warning: {} , stopping unfollow_users".format(exc))
            return self

        else:
            self.logger.error("Sorry, an error occurred: {}".format(exc))
            self.aborting = True
            return self

    return self


def follow_by_list(
        self,
        follow_list,
        users_validated: bool = False,
):
    if self.aborting:
        return self

    state = {
        'followed': 0,
        'already_followed': 0,
        'not_valid_users': 0
    }

    for index, username in enumerate(follow_list):
        self.logger.info("User [{}/{}]".format(index + 1, len(follow_list)))
        if self.jumps["consequent"]["follows"] >= self.jumps["limit"]["follows"]:
            self.logger.warning(
                "--> Follow quotient reached its peak!\t~leaving follow_by_list"
            )
            # reset jump counter before breaking the loop
            self.jumps["consequent"]["follows"] = 0
            # turn on `quotient_breach` to break the internal iterators
            # of the caller
            self.quotient_breach = True
            break
        if follow_restriction(
                "read", username, self.follow_times, self.logger
        ):
            state["already_followed"] += 1
            self.logger.info("Account {} already followed {} times".format(username, self.follow_times))
            continue

        if not users_validated:
            validation, details = nf_validate_user_call(self, username)
            if not validation:
                self.logger.info(
                    "--> Not a valid user: {}".format(details)
                )
                state["not_valid_users"] += 1
                continue

        follow_state, msg = follow_user(
            self.browser,
            "profile",
            self.username,
            username,
            None,
            self.blacklist,
            self.logger,
            self.logfolder,
        )
        if follow_state is True:
            state['followed'] += 1
            self.logger.info("user followed")
        elif msg == "already followed":
            state["already_followed"] += 1

        elif msg == "jumped":
            # will break the loop after certain consecutive jumps
            self.jumps["consequent"]["follows"] += 1

        if self.do_like and random.randint(0, 100) <= self.user_interact_percentage:
            self.logger.info(
                "--> User gonna be interacted: '{}'".format(username)
            )
            # disable re-validating user in like_by_users
            like_by_users(
                self,
                [username],
                None,
                True,
            )

    self.logger.info("Followed: {}".format(state['followed']))
    self.logger.info("Already followed: {}".format(state['already_followed']))
    self.logger.info("Not Valid Users: {}".format(state['not_valid_users']))
    self.followed += state["followed"]
    self.already_followed += state["already_followed"]
    self.not_valid_users += state["not_valid_users"]


def like_by_feed(
        self,
        amount
):
    if self.aborting:
        return self

    state = {
        'liked_img': 0,
        'already_liked': 0,
        'inap_img': 0,
        'commented': 0,
        'followed': 0,
        'not_valid_users': 0,
    }
    self.logger.info("Liking by feed")
    like_loop(self, "FEED", "https://www.instagram.com/", amount, state, True)
    self.logger.info("Liked: {}".format(state['liked_img']))
    self.logger.info("Already Liked: {}".format(state['already_liked']))
    self.logger.info("Commented: {}".format(state['commented']))
    self.logger.info("Followed: {}".format(state['followed']))
    self.logger.info("Inappropriate: {}".format(state['inap_img']))
    self.liked_img += state['liked_img']
    self.already_liked += state['already_liked']
    self.commented += state['commented']
    self.followed += state['followed']
    self.inap_img += state['inap_img']


def like_loop(
        self,
        what: str,
        base_link: str,
        amount: int,
        state: dict,
        users_validated: False
):
    try_again = 0
    sc_rolled = 0
    scroll_nap = 1.5
    already_interacted_links = []
    try:
        while state['liked_img'] in range(0, amount):
            if self.jumps["consequent"]["likes"] >= self.jumps["limit"]["likes"]:
                self.logger.warning(
                    "--> Like quotient reached its peak!\t~leaving "
                    "Like-By-{} activity\n".format(what)
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
                        "desired:{}, found:{}...".format(
                            what,
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
                    sleep(1)
                    nf_scroll_into_view(self, post)
                    sleep(1)
                    nf_click_center_of_element(self, post, link)
                    success, msg, state = nf_interact_with_post(
                        self,
                        link,
                        amount,
                        state,
                        users_validated
                    )
                    sleep(1)
                    nf_find_and_press_back(self, base_link)
                    already_interacted_links.append(link)
                    if success:
                        # TODO add to quotient
                        pass
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
