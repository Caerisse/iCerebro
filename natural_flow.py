

import random

from instapy import InstaPy
from instapy.constants import MEDIA_PHOTO, MEDIA_CAROUSEL, MEDIA_ALL_TYPES
from instapy.util import click_element, click_visibly, update_activity, format_number, web_address_navigator
from instapy.comment_util import get_comments_on_post
from instapy.like_util import check_link, like_image
from instapy.xpath import read_xpath
from instapy.time_util import sleep

from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException


from selenium.webdriver.common.action_chains import ActionChains


class MyInstaPy(InstaPy):

    def nf_like_by_tags(
        self,
        tags: list = None,
        amount: int = 50,
        skip_top_posts: bool = True,
        use_smart_hashtags: bool = False,
        use_smart_location_hashtags: bool = False,
        interact: bool = False,
        media: str = None,
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


        if media is None:
            # all known media types
            media = MEDIA_ALL_TYPES
        elif media == MEDIA_PHOTO:
            # include posts with multiple images in it
            media = [MEDIA_PHOTO, MEDIA_CAROUSEL]
        else:
            # make it an array to use it in the following part
            media = [media]

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

            self.nf_go_to_tag_page(self.browser, tag)

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
                while state['liked_img'] in range(0, amount-1):
                    if sc_rolled > 100:
                        try_again += 1
                        if try_again > 2: # you can try again as much as you want by changing this number
                            self.logger.info(
                                    "'{}' tag POSSIBLY has less images than "
                                    "desired:{} found:{}...".format(tag, amount, len(already_interacted_links))
                                )
                            break
                        self.logger.info("Scrolled too much! ~ sleeping 10 minutes")
                        sleep(600)
                        sc_rolled = 0

                    # Failsafe in case we dont end in the tag page, if we are there nothing is done
                    #web_address_navigator(self.browser, "https://www.instagram.com/explore/tags/{}/".format(tag))

                    main_elem = self.browser.find_element_by_tag_name("main")
                    posts = self.nf_get_all_posts_on_element(self.browser, main_elem)

                    # Interact with links instead of just storing them
                    for post in posts:
                        link = post.get_attribute("href")
                        if link not in already_interacted_links:

                            self.logger.info("about to scroll to post")
                            sleep(2)
                            self.nf_scroll_into_view(self.browser, post)
                            self.logger.info("about to click to post")
                            sleep(1)
                            self.nf_click_center_of_element(self.browser, post)
                            #self.browser.execute_script("arguments[0].click();", post)
                            
                            self.logger.info("about to like post")
                            sleep(3)
                            success, msg, state = self.nf_interact_with_post( 
                                                            link, 
                                                            amount,
                                                            state,
                                                            interact,
                                                        )

                            self.logger.info("Returned from liking, should still be in post page")
                            sleep(1)
                            back = self.browser.find_element_by_xpath(
                                        '/html/body/div[1]/section/nav[1]/div/header/div/div[1]/a'
                            )
                            #self.nf_click_center_of_element(self.browser, back)
                            self.browser.execute_script("arguments[0].click();", back)
                            self.logger.info("Clicked back button")

                            if success:
                                already_interacted_links.append(link)
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


    def nf_interact_with_post(   
                        self,
                        link, 
                        amount,
                        state,
                        interact,
                    ):
                try:
                        """
                    inappropriate, user_name, is_video, reason, scope = check_link(
                        self.browser,
                        link,
                        self.dont_like,
                        self.mandatory_words,
                        self.mandatory_language,
                        self.is_mandatory_character,
                        self.mandatory_character,
                        self.check_character_set,
                        self.ignore_if_contains,
                        self.logger,
                    )

                    if not inappropriate and self.delimit_liking:
                        self.liking_approved = verify_liking(
                            self.browser, self.max_likes, self.min_likes, self.logger
                        )

                    if not inappropriate and self.liking_approved:
                        # validate user
                        validation, details = self.validate_user_call(user_name)
                        if validation is not True:
                            self.logger.info(details)
                            not_valid_users += 1
                            return True, "not_valid_users"
                        else:
                            web_address_navigator(self.browser, link)
                        """
                        # try to like
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

                            """
                            commenting = random.randint(0, 100) <= self.comment_percentage
                            following = random.randint(0, 100) <= self.follow_percentage

                            if self.use_clarifai and (following or commenting):
                                try:
                                    (
                                        checked_img,
                                        temp_comments,
                                        clarifai_tags,
                                    ) = self.query_clarifai()

                                except Exception as err:
                                    self.logger.error(
                                        "Image check error: {}".format(err)
                                    )

                            # comments
                            if (
                                self.do_comment
                                and user_name not in self.dont_include
                                and checked_img
                                and commenting
                            ):
                                comments = self.comments + (self.video_comments if is_video else self.photo_comments)
                                success = process_comments(comments, temp_comments, self.delimit_commenting,
                                                           self.max_comments,
                                                           self.min_comments, self.comments_mandatory_words,
                                                           self.username, self.blacklist,
                                                           self.browser, self.logger, self.logfolder)

                                if success:
                                    commented += 1
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
                                    followed += 1
                            else:
                                self.logger.info("--> Not following")
                                sleep(1)

                            # interactions (if any)
                            if interact:
                                self.logger.info(
                                    "--> User gonna be interacted: '{}'".format(
                                        user_name
                                    )
                                )

                                # disable revalidating user in like_by_users
                                with self.feature_in_feature("like_by_users", False):
                                    self.like_by_users(
                                        user_name,
                                        self.user_interact_amount,
                                        self.user_interact_random,
                                        self.user_interact_media,
                                    )
                            """
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
                        """
                    else:
                        self.logger.info(
                            "--> Image not liked: {}".format(reason.encode("utf-8"))
                        )
                        inap_img += 1
                        return True, "inap_img"
                        """
                    

                except NoSuchElementException as err:
                    self.logger.error("Invalid Page: {}".format(err))
                    return False, "Invalid Page", state


    def nf_go_to_tag_page(self, browser, tag):
        sleep(1)
        # clicking explore
        explore = browser.find_element_by_xpath(
                "/html/body/div[1]/section/nav[2]/div/div/div[2]/div/div/div[2]"
        )
        explore.click()
        sleep(1)
        # tiping tag
        search_bar = browser.find_element_by_xpath(
                "/html/body/div[1]/section/nav[1]/div/header/div/h1/div/div/div/div[1]/label/input"
        )
        search_bar.click()
        search_bar.send_keys("#" + tag)
        sleep(2)
        # click tag
        tag_option = browser.find_element_by_xpath(
                '//a[@href="/explore/tags/{}/"]'.format(tag)
        )
        #browser.execute_script("arguments[0].click();", tag_option)
        self.nf_click_center_of_element(browser, tag_option)
        sleep(1)


    def nf_scroll_into_view(self, browser, element):
        desired_y = (element.size['height'] / 2) + element.location['y']
        window_h = browser.execute_script('return window.innerHeight')
        window_y = browser.execute_script('return window.pageYOffset')
        current_y = (window_h / 2) + window_y
        scroll_y_by = desired_y - current_y
        #TODO: add random offset and smooth scrolling to appear more natural
        sleep(1)
        browser.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)
        sleep(1)

    def nf_click_center_of_element(self, browser, element):
        sleep(1)
        (
            ActionChains(browser)
            .move_to_element(element)
            .move_by_offset(
                element.size['height']/2, 
                element.size['width']/2
            )
            .click()
            .perform()
        )
        sleep(1)

    def nf_get_all_posts_on_element(self, browser, element):
        return element.find_elements_by_xpath('//a[starts-with(@href, "/p/")]')












