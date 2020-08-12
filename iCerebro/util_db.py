from datetime import datetime
from time import sleep
from typing import List

from instapy.like_util import get_links_for_username
from instapy.relationship_tools import get_followers, get_following
from instapy.util import web_address_navigator, deform_emojis, get_relationship_counts, getUserData, update_activity, \
    format_number
from progressbar import progressbar
from selenium.common.exceptions import WebDriverException, NoSuchElementException, InvalidSelectorException

from iCerebro.database import Post, Comment, User
from iCerebro.navigation import nf_scroll_into_view, nf_click_center_of_element, \
    nf_find_and_press_back
from sqlalchemy.exc import SQLAlchemyError


def db_store_comments(
        self,
        posts: List[Post],
        post_link: str,
):
    """Stores all comments of open post then goes back to post page"""
    comments_button = self.browser.find_elements_by_xpath(
            '//article//div[2]/div[1]//a[contains(@href,"comments")]'
    )
    if comments_button:
        try:
            self.logger.info("Loading comments...")
            comments_link = post_link + 'comments/'
            nf_scroll_into_view(self, comments_button[0])
            nf_click_center_of_element(self, comments_button[0], comments_link)
            sleep(1)
            for _ in range(9):
                try:
                    more_comments = self.browser.find_element_by_xpath(
                        '//span[@aria-label="Load more comments"]'
                    )
                except NoSuchElementException:
                    break
                nf_scroll_into_view(self, more_comments)
                self.browser.execute_script("arguments[0].click();", more_comments)

            comments = self.browser.find_elements_by_xpath(
                '/html/body/div[1]/section/main/div/ul/ul[@class="Mr508"]'
            )
            self.logger.info("Saving comments")
            for comment in progressbar(comments):
                inner_container = comment.find_element_by_xpath(
                    './/div[@class="C4VMK"]'
                )
                username = inner_container.find_element_by_xpath('.//h3/div/a').text
                text, _ = deform_emojis(inner_container.find_element_by_xpath('.//span').text)
                post_date = inner_container.find_element_by_xpath(
                    './/time').get_attribute('datetime')
                post_date = datetime.fromisoformat(post_date[:-1])

                user = db_get_or_create_user(self, username)
                self.db.session.add(user)
                self.db.session.commit()

                for post in posts:
                    comment = Comment(
                        date_posted=post_date,
                        text=text,
                        user=user,
                        post=post,
                    )
                    self.db.session.add(comment)
                    self.db.session.commit()
                    self.db.session.expunge(comment)
        except SQLAlchemyError:
            self.db.session.rollback()
            raise
        finally:
            self.db.session.commit()
            nf_find_and_press_back(self, post_link)


def db_get_or_create_user(
        self,
        username: str
) -> User:
    users = self.db.session.query(User).filter(User.username == username).all()
    if not users:
        user = User(
            date_checked=datetime.now(),
            username=username,
        )
    else:
        user = users[0]
    return user


def db_get_or_create_post(
        self,
        post_date: datetime,
        post_link: str,
        src_link: str,
        caption: str,
        likes: int,
        user: str,
        ig_desciption: str = None,
        objects_detected: str = None,
        classified_as: str = None,
) -> Post:
    caption, _ = deform_emojis(caption)
    if ig_desciption:
        ig_desciption, _ = deform_emojis(ig_desciption)
    posts = self.db.session.query(Post).filter(Post.src == src_link).all()
    if not posts:
        post = Post(
            date_posted=post_date,
            link=post_link,
            src=src_link,
            caption=caption,
            likes=likes,
            user=user,
            ig_desciption=ig_desciption,
            objects_detected=objects_detected,
            classified_as=classified_as,
        )
    else:
        post = posts[0]
    return post


def scrap_for_user_relationships(self, starting_username: str):
    user_link = "https://www.instagram.com/{}/".format(starting_username)
    web_address_navigator(self.browser, user_link)
    followers_count, following_count = get_relationship_counts(self.browser, starting_username, self.logger)
    try:
        posts_count = getUserData(
            "graphql.user.edge_owner_to_timeline_media.count", self.browser
        )
    except WebDriverException:
        posts_count = 0

    starting_user = None
    try:
        starting_user = db_get_or_create_user(self, starting_username)
        self.db.session.add(starting_user)
        starting_user.date_checked = datetime.now()
        if starting_user.followers_count != followers_count:
            starting_user.followers_count = followers_count
        if starting_user.following_count != following_count:
            starting_user.following_count = following_count
        if starting_user.posts_count != posts_count and posts_count != 0:
            starting_user.posts_count = posts_count
        self.db.session.commit()
    except SQLAlchemyError:
        self.db.session.rollback()
    already_saved_followers = [follower.username for follower in starting_user.followers]
    already_saved_following = [following.username for following in starting_user.following]
    saved_followers_count = len(already_saved_followers)
    saved_following_count = len(already_saved_following)
    if starting_user and saved_followers_count != followers_count:
        followers = get_followers(
            self.browser,
            starting_username,
            "full",
            self.relationship_data,
            True,
            False,
            self.logger,
            self.logfolder
        )
        already_saved_followers_set = set(already_saved_followers)
        followers_set = set(followers)
        followers = list(followers_set - already_saved_followers_set)
        followers_no_more = list(already_saved_followers_set - followers_set)
        if saved_followers_count - len(followers_no_more) > 0:
            self.logger.info("{} of {}'s followers already in the database".format(
                saved_followers_count, starting_username))
        try:
            self.logger.info("Saving followers of {}".format(starting_username))
            for username in progressbar(followers):
                user = db_get_or_create_user(self, username)
                starting_user.followers.append(user)
                self.db.session.add(user)
                self.db.session.commit()
                self.db.session.expunge(user)
            if len(followers_no_more) != 0:
                self.logger.info("Saving un-followers of {}".format(starting_username))
                for username in progressbar(followers_no_more):
                    user = db_get_or_create_user(self, username)
                    starting_user.followers.remove(user)
                    self.db.session.add(user)
                    self.db.session.commit()
                    self.db.session.expunge(user)
        except SQLAlchemyError:
            self.db.session.rollback()

    if starting_user and saved_following_count != following_count:
        following = get_following(
            self.browser,
            starting_username,
            "full",
            self.relationship_data,
            True,
            False,
            self.logger,
            self.logfolder
        )
        already_saved_following_set = set(already_saved_followers)
        following_set = set(following)
        following = list(following_set - already_saved_following_set)
        following_no_more = list(already_saved_following_set - following_set)
        if saved_following_count - len(following_no_more) > 0:
            self.logger.info("{} of {}'s followings already in the database".format(
                saved_following_count, starting_username))
        try:
            self.logger.info("Saving following of {}".format(starting_username))
            for username in progressbar(following):
                user = db_get_or_create_user(self, username)
                starting_user.following.append(user)
                self.db.session.add(user)
                self.db.session.commit()
                self.db.session.expunge(user)
            if len(following_no_more) != 0:
                self.logger.info("Saving un-following of {}".format(starting_username))
                for username in progressbar(following_no_more):
                    user = db_get_or_create_user(self, username)
                    starting_user.following.remove(user)
                    self.db.session.add(user)
                    self.db.session.commit()
                    self.db.session.expunge(user)
        except SQLAlchemyError:
            self.db.session.rollback()


def store_all_posts_of_user(self, username: str):
    user_link = "https://www.instagram.com/{}/".format(username)
    web_address_navigator(self.browser, user_link)
    try:
        posts_count = getUserData(
            "graphql.user.edge_owner_to_timeline_media.count", self.browser
        )
    except WebDriverException:
        posts_count = 0

    user = None
    try:
        user = db_get_or_create_user(self, username)
        self.db.session.add(user)
        if user.posts_count != posts_count and posts_count != 0:
            user.posts_count = posts_count
        self.db.session.commit()
    except SQLAlchemyError:
        self.db.session.rollback()

    if user and len(user.posts) != posts_count:
        try:
            post_links = get_links_for_username(
                self.browser,
                self.username,
                username,
                100,
                self.logger,
                self.logfolder
            )
        except InvalidSelectorException:
            # Private account, get_links_for_username already prints it on log
            return
        except Exception:
            self.logger.error("Failed to get post links of {}".format(username))
            return
        already_saved_posts = self.db.session.query(Post).filter(Post.user == user).all()
        if len(already_saved_posts) != 0:
            self.logger.info("{} of {}'s posts already in the database".format(len(already_saved_posts), username))
        post_links = list(set(post_links) - set([post.link for post in already_saved_posts]))
        already_saved_post_srcs = [post.src for post in already_saved_posts]
        for i, post_link in enumerate(post_links):
            self.logger.info("Saving post {}/{} of {}".format(i+1, len(post_links), username))
            web_address_navigator(self.browser, post_link)
            try:
                username_button = self.browser.find_element_by_xpath(
                    '/html/body/div[1]/section/main/div/div/article/header//div[@class="e1e1d"]'
                )
                username_text = username_button.text
                images = self.browser.find_elements_by_xpath(
                    '/html/body/div[1]/section/main/div/div/article//img[@class="FFVAD"]'
                )
                more_button = self.browser.find_elements_by_xpath("//button[text()='more']")
                if more_button:
                    nf_scroll_into_view(self, more_button[0])
                    more_button[0].click()
                try:
                    caption = self.browser.find_element_by_xpath(
                        "/html/body/div[1]/section/main/div/div/article//div/div/span/span"
                    ).text
                except NoSuchElementException:
                    caption = None
                caption = "" if caption is None else caption
                likes_count = get_like_count(self)
                image_descriptions = []
                image_links = []
                for image in images:
                    image_description = image.get_attribute('alt')
                    if image_description is not None and 'Image may contain:' in image_description:
                        image_description = image_description[image_description.index(
                            'Image may contain:') + 19:]
                    else:
                        image_description = None
                    image_descriptions.append(image_description)
                    image_links.append(image.get_attribute('src'))

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
                        post_link,
                        image_link,
                        caption,
                        likes_count,
                        user,
                        image_description
                    )
                    self.db.session.add(post)
                    # forgot to save post link on database so this is an extra check to not store
                    # comments again if post was already saved
                    # TODO: delete
                    if image_link not in already_saved_post_srcs:
                        db_posts.append(post)
                self.db.session.commit()
                if db_posts:
                    db_store_comments(self, db_posts, post_link)
                    for post in db_posts:
                        self.db.session.expunge(post)
            except SQLAlchemyError:
                self.db.session.rollback()
            finally:
                self.db.session.commit()


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
