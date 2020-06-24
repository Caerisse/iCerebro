
import os
import random
import re
from re import findall
import csv
import time

from instapy import InstaPy
from instapy.constants import MEDIA_PHOTO, MEDIA_CAROUSEL, MEDIA_ALL_TYPES
from instapy.util import click_element, click_visibly, update_activity, format_number
from instapy.util import web_address_navigator, get_relationship_counts, getUserData
from instapy.util import truncate_float, default_profile_pic_instagram, get_current_url
from instapy.comment_util import verify_commenting, comment_image
from instapy.like_util import like_image, verify_liking
from instapy.xpath import read_xpath
from instapy.unfollow_util import follow_restriction, follow_user
from instapy.time_util import sleep

from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException

from selenium.webdriver.common.action_chains import ActionChains

from image_analisis import ImageAnalisis


class MyInstaPy(InstaPy):

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.use_image_analisis = False
        self.ImgAn = None

    def set_use_image_analisis(
        self,
        use_image_analisis: bool,
        classification_model_name: str = 'resnext101_32x8d',
        detection_model_name: str = 'fasterrcnn_resnet50_fpn',
    ):
        self.use_image_analisis = use_image_analisis
        if use_image_analisis:
            self.ImgAn = ImageAnalisis(
                classification_model_name, detection_model_name)
        else:
            self.ImgAn = None

    def nf_like_by_tags(
        self,
        tags: list = None,
        amount: int = 50,
        skip_top_posts: bool = True,
        use_smart_hashtags: bool = False,
        use_smart_location_hashtags: bool = False,
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

            self.nf_go_to_tag_page(tag)

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
                    posts = self.nf_get_all_posts_on_element(main_elem)

                    # Interact with links instead of just storing them
                    for post in posts:
                        link = post.get_attribute("href")
                        if link not in already_interacted_links:

                            self.logger.info("about to scroll to post")
                            sleep(1)
                            self.nf_scroll_into_view(post)
                            self.logger.info("about to click to post")
                            sleep(1)
                            self.nf_click_center_of_element(post)

                            success, msg, state = self.nf_interact_with_post( 
                                                            link, 
                                                            amount,
                                                            state,
                                                        )

                            self.logger.info("Returned from liking, should still be in post page")
                            sleep(5)
                            self.nf_find_and_press_back("https://www.instagram.com/explore/tags/{}/".format(tag))

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
                        user_validated=False,
    ):
                try:
                    self.logger.info("about to check post")
                    sleep(1)
                    inappropriate, user_name, is_video, image_links, reason, scope = self.nf_check_post(link)
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
                            validation = True
                            details = "User already validated"
                        else:
                            validation, details = self.nf_validate_user_call(user_name, link)

                        self.logger.info("Validation succes? {}, details: {}".format(validation, details))

                        if validation is not True:
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

                            if self.use_image_analisis and (following or commenting):
                                try:
                                    (
                                        checked_img,
                                        temp_comments,
                                        image_analisis_tags,
                                    ) = self.ImgAn.image_analisis(image_links, logger=self.logger)
                                    # TODO: image_analisis
                                except Exception as err:
                                    self.logger.error(
                                        "Image analisis error: {}".format(err)
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

                                success = self.process_comments(user_name, comments, temp_comments)

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
                                sleep(5)

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
                                sleep(5)


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

                                # disable revalidating user in like_by_users
                                self.nf_like_by_users(
                                    [user_name],
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

    def nf_go_to_tag_page(self, tag):
        try:
            sleep(1)
            # clicking explore
            explore = self.browser.find_element_by_xpath(
                "/html/body/div[1]/section/nav[2]/div/div/div[2]/div/div/div[2]"
            )
            explore.click()
            sleep(1)
            # tiping tag
            search_bar = self.browser.find_element_by_xpath(
                "/html/body/div[1]/section/nav[1]/div/header/div/h1/div/div/div/div[1]/label/input"
            )
            search_bar.click()
            search_bar.send_keys("#" + tag)
            sleep(2)
            # click tag
            tag_option = self.browser.find_element_by_xpath(
                '//a[@href="/explore/tags/{}/"]'.format(tag)
            )
            #self.browser.execute_script("arguments[0].click();", tag_option)
            self.nf_click_center_of_element(tag_option)
            sleep(1)
        except NoSuchElementException:
            self.logger.warning("Failed to get a page element")

        tag_link = "https://www.instagram.com/explore/tags/{}/".format(tag)
        if not self.check_if_in_correct_page(tag_link):
            self.logger.error("Failed to go to tag page, navigating there")
            #TODO: retry to get there naturally
            web_address_navigator(self.browser, tag_link)

    def nf_go_to_user_page(self, username):
        try:
            sleep(1)
            # clicking explore
            explore = self.browser.find_element_by_xpath(
                "/html/body/div[1]/section/nav[2]/div/div/div[2]/div/div/div[2]"
            )
            explore.click()

            sleep(1)
            # tiping tag
            search_bar = self.browser.find_element_by_xpath(
                "/html/body/div[1]/section/nav[1]/div/header/div/h1/div/div/div/div[1]/label/input"
            )
            search_bar.click()
            search_bar.send_keys(username)

            sleep(2)
            # click tag
            user_option = self.browser.find_element_by_xpath(
                '//a[@href="/{}/"]'.format(username)
            )

            self.nf_click_center_of_element(user_option)

            sleep(1)
        except NoSuchElementException:
            self.logger.warning("Failed to go to get a page element")

        user_link = "https://www.instagram.com/{}/".format(username)
        if not self.check_if_in_correct_page(user_link):
            self.logger.error("Failed to go to user page, navigating there")
            #TODO: retry to get there naturally
            web_address_navigator(self.browser, user_link)

    def nf_scroll_into_view(self, element):
        desired_y = (element.size['height'] / 2) + element.location['y']
        window_h = self.browser.execute_script('return window.innerHeight')
        window_y = self.browser.execute_script('return window.pageYOffset')
        current_y = (window_h / 2) + window_y
        scroll_y_by = desired_y - current_y
        #TODO: add random offset and smooth scrolling to appear more natural
        sleep(1)
        self.browser.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)
        sleep(1)

    def nf_click_center_of_element(self, element):
        sleep(1)
        (
            ActionChains(self.browser)
            .move_to_element(element)
            .move_by_offset(
                element.size['width']//2,
                element.size['height']//2, 
            )
            .click()
            .perform()
        )
        sleep(1)

    def nf_get_all_posts_on_element(self, element):
        return element.find_elements_by_xpath('//a[starts-with(@href, "/p/")]')

    def nf_check_post(self, post_link):
        # Check URL of the webpage, if it already is post's page, then do not
        # navigate to it again, should never do anything
        #web_address_navigator(self.browser, post_link)
        try: 
            t = time.process_time()
    
            username = self.browser.find_element_by_xpath(
                '/html/body/div[1]/section/main/div/div/article/header//div[@class="e1e1d"]'
            )
    
            username_text = username.text
    
            follow_button = self.browser.find_element_by_xpath(
                '/html/body/div[1]/section/main/div/div/article/header/div[2]/div[1]/div[2]/button'
            )
    
            following = follow_button.text == "Following"
    
            locations = self.browser.find_elements_by_xpath(
                '/html/body/div[1]/section/main/div/div/article/header//a[contains(@href,"locations")]'
            )
    
            location_text = locations[0].text if locations != [] else None
            location_link = locations[0].get_attribute('href') if locations != [] else None
    
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
            """
            
            """
            if (len(images) + len(videos)) == 1:
                # single image or video
            elif len(images) == 2:
                # carrousel
            """
    
            is_video = len(images)==0
    
            image_descriptions = []
            image_links = []
            for image in images:
                image_description = image.get_attribute('alt')
                if image_description is not None and 'Image may contain:' in image_description:
                    image_description = image_description[image_description.index('Image may contain:') + 19 :]
                else:
                    image_description = None
                image_descriptions.append(image_description)
                image_links.append(image.get_attribute('src'))
    
    
            more_button = self.browser.find_elements_by_xpath("//button[text()='more']")
            if more_button != []:
                self.nf_scroll_into_view(more_button[0])
                more_button[0].click()
     
            caption = self.browser.find_element_by_xpath(
                "/html/body/div[1]/section/main/div/div/article//div[2]/div[1]//div/span/span"
            ).text
    
            comments_button = self.browser.find_elements_by_xpath(
                '//article//div[2]/div[1]//a[contains(@href,"comments")]'
            )
    
            self.logger.info("Image from: {}".format(username_text.encode("utf-8")))
            self.logger.info("Link: {}".format(post_link.encode("utf-8")))
            self.logger.info("Caption: {}".format(caption.encode("utf-8")))
            for image_description in image_descriptions:
                if image_description:
                    self.logger.info("Description: {}".format(image_description.encode("utf-8")))
            
    
            # Check if mandatory character set, before adding the location to the text
            caption = "" if caption is None else caption
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
                if not any((word in image_text for word in self.mandatory_words)):
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
                return False, username_text, is_video, image_links, "None", "Pass"
    
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
                    inapp_unit = 'Inappropriate! ~ contains "{}"'.format(
                        quashed if iffy == quashed else '" in "'.join([str(iffy), str(quashed)])
                    )
                    return True, username_text, is_video, image_links, inapp_unit, "Undesired word"
    
            return False, username_text, is_video, image_links, "None", "Success"
        finally:
            elapsed_time = time.process_time() - t
            self.logger.info("check post elapsed time: {:.0f} seconds".format(elapsed_time))

    def nf_validate_user_call(self, username, post_link):

        if username == self.username:
            inap_msg = "---> Username '{}' is yours!\t~skipping user\n".format(self.username)
            return False, inap_msg

        if username in self.ignore_users:
            inap_msg = (
                "---> '{}' is in the `ignore_users` list\t~skipping "
                "user\n".format(username)
            )
            return False, inap_msg

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

            self.nf_go_from_post_to_profile(username)

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
                            inap_msg = (
                                "'{}' is not a {} with the relationship ratio of {}  "
                                "~skipping user\n".format(
                                    username,
                                    "potential user"
                                    if not reverse_relationship
                                    else "massive follower",
                                    truncate_float(relationship_ratio, 2),
                                )
                            )
                            return False, inap_msg

                    elif self.delimit_by_numbers:
                        if followers_count:
                            if max_followers:
                                if followers_count > max_followers:
                                    inap_msg = (
                                        "User '{}'s followers count exceeds maximum "
                                        "limit  ~skipping user\n".format(username)
                                    )
                                    return False, inap_msg

                            if min_followers:
                                if followers_count < min_followers:
                                    inap_msg = (
                                        "User '{}'s followers count is less than "
                                        "minimum limit  ~skipping user\n".format(username)
                                    )
                                    return False, inap_msg

                        if following_count:
                            if max_following:
                                if following_count > max_following:
                                    inap_msg = (
                                        "User '{}'s following count exceeds maximum "
                                        "limit  ~skipping user\n".format(username)
                                    )
                                    return False, inap_msg

                            if min_following:
                                if following_count < min_following:
                                    inap_msg = (
                                        "User '{}'s following count is less than "
                                        "minimum limit  ~skipping user\n".format(username)
                                    )
                                    return False, inap_msg

                        if potency_ratio:
                            if relationship_ratio and relationship_ratio < potency_ratio:
                                inap_msg = (
                                    "'{}' is not a {} with the relationship ratio of "
                                    "{}  ~skipping user\n".format(
                                        username,
                                        "potential user"
                                        if not reverse_relationship
                                        else "massive " "follower",
                                        truncate_float(relationship_ratio, 2),
                                    )
                                )
                                return False, inap_msg

            if min_posts or max_posts:
                # if you are interested in relationship number of posts boundaries
                try:
                    number_of_posts = getUserData(
                        "graphql.user.edge_owner_to_timeline_media.count", self.browser
                    )
                except WebDriverException:
                    self.logger.error("~cannot get number of posts for username")
                    inap_msg = "---> Sorry, couldn't check for number of posts of " "username\n"
                    return False, inap_msg
                if max_posts:
                    if number_of_posts > max_posts:
                        inap_msg = (
                            "Number of posts ({}) of '{}' exceeds the maximum limit "
                            "given {}\n".format(number_of_posts, username, max_posts)
                        )
                        return False, inap_msg
                if min_posts:
                    if number_of_posts < min_posts:
                        inap_msg = (
                            "Number of posts ({}) of '{}' is less than the minimum "
                            "limit given {}\n".format(number_of_posts, username, min_posts)
                        )
                        return False, inap_msg

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
                        "---> Skiping non business because skip_non_business set to True",
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
        except:
            raise
            return False, "Unknown error"
        finally:
            self.nf_find_and_press_back(post_link)

    def nf_find_and_press_back(self, link):
        possibles = [
            '/html/body/div[1]/section/nav[1]/div/header//a[@class=" Iazdo"]',
            '/html/body/div[1]/section/nav[1]/div/header//a[@class="Iazdo"]',
            #'/html/body/div[1]/section/nav[1]/div/header/div/div[1]/a',
            #'/html/body/div[1]/section/nav[1]/div/header/div/div[1]/a/span/svg',
            '/html/body/div[1]/section/nav[1]/div/header//a//*[name()="svg"][@class="_8-yf5 "]',
            '/html/body/div[1]/section/nav[1]/div/header//a//*[name()="svg"][@class="_8-yf5"]',
            '/html/body/div[1]/section/nav[1]/div/header//a//*[name()="svg"][@aria-label="Back"]',
            '/html/body/div[1]/section/nav[1]/div/header//a/span/*[name()="svg"][@class="_8-yf5 "]',
            '/html/body/div[1]/section/nav[1]/div/header//a/span/*[name()="svg"][@class="_8-yf5"]',
            '/html/body/div[1]/section/nav[1]/div/header//a/span/*[name()="svg"][@aria-label="Back"]',
        ]
        success = False
        for back_path in possibles:
            if not success:
                try:
                    back = self.browser.find_element_by_xpath(back_path)
                    self.nf_scroll_into_view(back)
                    #self.nf_click_center_of_element(back)
                    self.browser.execute_script("arguments[0].click();", back)
                    success = True
                    break
                except:
                    success = False
                    #self.logger.warning("Failed to get back button with xpath:\n{}".format(back_path))

        if not success:
            self.logger.warning("Failed to get back button with all xpaths")
        else:
            self.logger.info("Pressed back button with xpath:\n     {}".format(back_path))
        
        if not self.check_if_in_correct_page(link):
            self.logger.error("Failed to go back, navigating there")
            #TODO: retry to get there naturally
            web_address_navigator(self.browser, link)

        sleep(2)

    def nf_go_from_post_to_profile(self, username):
        try:
            sleep(1)

            self.logger.info("about to go to user page") 

            sleep(1)

            username_button = self.browser.find_element_by_xpath(
                '/html/body/div[1]/section/main/div/div/article/header//div[@class="e1e1d"]'
            )

            self.nf_scroll_into_view(username_button)
            
            self.nf_click_center_of_element(username_button)
            self.logger.info("clicked username button")
            sleep(3)
        except NoSuchElementException:
            self.logger.warning("Failed to get user page button")
        except:
            raise
        
        user_link = "https://www.instagram.com/{}/".format(username)
        if not self.check_if_in_correct_page(user_link):
            self.logger.error("Failed to go to user page, navigating there")
            #TODO: retry to get there naturally
            web_address_navigator(self.browser, user_link)

    def process_comments(
        self,
        username,
        comments,
        image_analisis_comments
    ):
        if self.delimit_commenting:
            self.commenting_approved, disapproval_reason = verify_commenting(
                                                            self.browser,
                                                            self.max_comments,
                                                            self.min_comments,
                                                            self.comments_mandatory_words,
                                                            self.logger,
                                                        )
        if not self.commenting_approved:
            logger.info(disapproval_reason)
            return False
        
        if not self.commenting_approved:
            self.logger.info(disapproval_reason)
            return False

        if len(image_analisis_comments) > 0:
            comments = image_analisis_comments

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

    def nf_like_by_users(
        self,
        usernames: list,
        users_validated= False,
    ):
        """Likes some amounts of images for each usernames"""
        if self.aborting:
            return self

        standalone = (
            True if "like_by_users" not in self.internal_usage.keys() else False
        )

        amount = self.user_interact_amount
        randomize = self.user_interact_random
        media = self.user_interact_media

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
                self.nf_go_from_post_to_profile(username)
            else:
                self.nf_go_to_user_page(username)

            following = random.randint(0, 100) <= self.follow_percentage

            if not users_validated:
                validation, details = self.nf_validate_user_call(username)
                if not validation:
                    self.logger.info(
                        "--> Not a valid user: {}".format(details)
                    )
                    not_valid_users += 1
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
                                    tag, amount, len(already_interacted_links))
                            )
                            break
                        self.logger.info(
                            "Scrolled too much! ~ sleeping 10 minutes")
                        sleep(600)
                        sc_rolled = 0

                    main_elem = self.browser.find_element_by_tag_name("main")
                    #feed = main_elem.find_elements_by_xpath('//div[@class=" _2z6nI"]')
                    posts = self.nf_get_all_posts_on_element(main_elem)

                    # Interact with links instead of just storing them
                    for post in posts:
                        link = post.get_attribute("href")
                        if link not in already_interacted_links:

                            self.logger.info("about to scroll to post")
                            sleep(1)
                            self.nf_scroll_into_view(post)
                            self.logger.info("about to click to post")
                            sleep(1)
                            self.nf_click_center_of_element(post)

                            success, msg, state = self.nf_interact_with_post(
                                link,
                                amount,
                                state,
                                users_validated,
                            )

                            self.logger.info(
                                "Returned from liking, should still be in post page")
                            sleep(5)
                            self.nf_find_and_press_back(
                                "https://www.instagram.com/{}/".format(username))

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

    def check_if_in_correct_page(self, desired_link):
        current_url = get_current_url(self.browser)

        if current_url is None or desired_link is None:
            return False

        # remove slashes at the end to compare efficiently
        if current_url.endswith("/"):
            current_url = current_url[:-1]

        if desired_link.endswith("/"):
            desired_link = desired_link[:-1]

        return current_url == desired_link









