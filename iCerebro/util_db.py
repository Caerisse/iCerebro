import re
from datetime import datetime
from time import sleep
from typing import List, Dict

from django.core.exceptions import ObjectDoesNotExist
import regex
import emoji
from emoji.unicode_codes import UNICODE_EMOJI
from selenium.common.exceptions import WebDriverException, NoSuchElementException, InvalidSelectorException

from app_main.models import InstaUser, BotBlacklist, BotFollowed, BotCookies, Post, Comment


def store_user(
        username: str,
        followers_count: int = None,
        following_count: int = None,
        posts_count: int = None):
    defaults = {}
    if followers_count:
        defaults['followers_count'] = followers_count
    if following_count:
        defaults['following_count'] = following_count
    if posts_count:
        defaults['posts_count'] = posts_count

    InstaUser.objects.update_or_create(
        username=username,
        defaults=defaults
    )


def store_post(
        post_link: str,
        username_text: str,
        post_date: datetime,
        image_links: List[str],
        caption: str,
        likes_count: int,
        image_descriptions: List[str],
        objects_detected: str = None,
        classified_as: str = None
) -> Post:
    user, _ = InstaUser.objects.get_or_create(username=username_text)
    post = None
    try:
        post, created = Post.objects.update_or_create(
            link=post_link,
            defaults={
                'instauser': user,
                'date_posted': post_date,
                'src': image_links,
                'caption': caption.encode("utf-8"),
                'likes': likes_count,
                'ig_desciption': image_descriptions,
                'objects_detected': objects_detected,
                'classified_as': classified_as
            }
        )
    except Exception as e:
        print(e)
    #post.save()
    return post


def store_comments(self, post):
    pass


def add_user_to_blacklist(self, username: str, action: str):
    if self.settings.blacklist_campaign is None or self.settings.blacklist_campaign.strip() == "":
        return
    user, _ = InstaUser.objects.get_or_create(username=username)
    _, created = BotBlacklist.objects.get_or_create(
        bot=self.instauser,
        instauser=user,
        campaign=self.settings.blacklist_campaign,
        action=action
    )
    if created:
        self.logger.info(
            "Added {} to blacklist for {} campaign and action {}".format(
                username, self.settings.blacklist_campaign, action
            )
        )
    else:
        self.logger.warn(
            "User {} was already in blacklist for {} campaign and action {}".format(
                username, self.settings.blacklist_campaign, action
            )
        )


def is_in_blacklist(self, username: str, action: str) -> bool:
    if self.settings.blacklist_campaign is None or self.settings.blacklist_campaign.strip() == "":
        return False
    user, _ = InstaUser.objects.get_or_create(username=username)
    try:
        _ = BotBlacklist.objects.get(
            bot=self.instauser,
            instauser=user,
            campaign=self.settings.blacklist_campaign,
            action=action
        )
        return True
    except ObjectDoesNotExist:
        return False


def add_follow_times(
        self,
        username: str
):
    bot_followed, created = BotFollowed.objects.get_or_create(bot=self.instauser, followed=username)
    bot_followed.times += 1
    bot_followed.save()


def is_follow_restricted(
        self,
        username: str
) -> bool:  # Followed username more than or equal than self.follow_times
    bot_followed, created = BotFollowed.objects.get_or_create(bot=self.instauser, followed=username)
    return bot_followed.times >= self.settings.follow_times


def get_cookies(self) -> List[Dict[str, str]]:
    cookies = []
    for cookie in BotCookies.objects.filter(bot=self.instauser):
        cookies.append(
            {
                "name": cookie.cookie_name,
                "value": cookie.cookie_value
            }
        )
    return cookies


def save_cookies(self, cookies: List[Dict[str, str]]):
    for cookie in cookies:
        BotCookies.objects.update_or_create(
            bot=self.instauser,
            cookie_name=cookie["name"],
            defaults={
                'cookie_value': cookie["value"]
            }
        )


def deform_emojis(text):
    """ Convert unicode emojis into their text form """
    new_text = ""
    emojiless_text = ""
    data = regex.findall(r"\X", text)
    emojis_in_text = []

    for word in data:
        if any(char in UNICODE_EMOJI for char in word):
            word_emoji = emoji.demojize(word).replace(":", "").replace("_", " ")
            if word_emoji not in emojis_in_text:  # do not add an emoji if
                # already exists in text
                emojiless_text += " "
                new_text += " ({}) ".format(word_emoji)
                emojis_in_text.append(word_emoji)
            else:
                emojiless_text += " "
                new_text += " "  # add a space [instead of an emoji to be
                # duplicated]

        else:
            new_text += word
            emojiless_text += word

    emojiless_text = remove_extra_spaces(emojiless_text)
    new_text = remove_extra_spaces(new_text)

    return new_text, emojiless_text


def remove_extra_spaces(text):
    """ Find and remove redundant spaces more than 1 in text """
    new_text = re.sub(r" {2,}", " ", text)
    return new_text


# def db_store_comments(
#         self,
#         posts: List[Post],
#         post_link: str,
# ):
#     """Stores all comments of open post then goes back to post page"""
#     comments_button = self.browser.find_elements_by_xpath(
#             '//article//div[2]/div[1]//a[contains(@href,"comments")]'
#     )
#     if comments_button:
#         try:
#             self.logger.info("Loading comments...")
#             comments_link = post_link + 'comments/'
#             nf_scroll_into_view(self, comments_button[0])
#             nf_click_center_of_element(self, comments_button[0], comments_link)
#             sleep(1)
#             for _ in range(9):
#                 try:
#                     more_comments = self.browser.find_element_by_xpath(
#                         '//span[@aria-label="Load more comments"]'
#                     )
#                 except NoSuchElementException:
#                     break
#                 nf_scroll_into_view(self, more_comments)
#                 self.browser.execute_script("arguments[0].click();", more_comments)
#
#             comments = self.browser.find_elements_by_xpath(
#                 '/html/body/div[1]/section/main/div/ul/ul[@class="Mr508"]'
#             )
#             self.logger.info("Saving comments")
#             for comment in progressbar(comments):
#                 inner_container = comment.find_element_by_xpath(
#                     './/div[@class="C4VMK"]'
#                 )
#                 username = inner_container.find_element_by_xpath('.//h3/div/a').text
#                 text, _ = deform_emojis(inner_container.find_element_by_xpath('.//span').text)
#                 post_date = inner_container.find_element_by_xpath(
#                     './/time').get_attribute('datetime')
#                 post_date = datetime.fromisoformat(post_date[:-1])
#
#                 user = db_get_or_create_user(self, username)
#                 self.db.session.add(user)
#                 self.db.session.commit()
#
#                 for post in posts:
#                     comment = Comment(
#                         date_posted=post_date,
#                         text=text,
#                         user=user,
#                         post=post,
#                     )
#                     self.db.session.add(comment)
#                     self.db.session.commit()
#                     self.db.session.expunge(comment)
#         except SQLAlchemyError:
#             self.db.session.rollback()
#             raise
#         finally:
#             self.db.session.commit()
#             nf_find_and_press_back(self, post_link)
#
#
# def scrap_for_user_relationships(self, starting_username: str):
#     user_link = "https://www.instagram.com/{}/".format(starting_username)
#     web_address_navigator(self.browser, user_link)
#     followers_count, following_count = get_relationship_counts(self.browser, starting_username, self.logger)
#     try:
#         posts_count = getUserData(
#             "graphql.user.edge_owner_to_timeline_media.count", self.browser
#         )
#     except WebDriverException:
#         posts_count = 0
#
#     starting_user = None
#     try:
#         starting_user = db_get_or_create_user(self, starting_username)
#         self.db.session.add(starting_user)
#         starting_user.date_checked = datetime.now()
#         if starting_user.followers_count != followers_count:
#             starting_user.followers_count = followers_count
#         if starting_user.following_count != following_count:
#             starting_user.following_count = following_count
#         if starting_user.posts_count != posts_count and posts_count != 0:
#             starting_user.posts_count = posts_count
#         self.db.session.commit()
#     except SQLAlchemyError:
#         self.db.session.rollback()
#     already_saved_followers = [follower.username for follower in starting_user.followers]
#     already_saved_following = [following.username for following in starting_user.following]
#     saved_followers_count = len(already_saved_followers)
#     saved_following_count = len(already_saved_following)
#     if starting_user and saved_followers_count != followers_count:
#         followers = get_followers(
#             self.browser,
#             starting_username,
#             "full",
#             self.relationship_data,
#             True,
#             False,
#             self.logger,
#             self.logfolder
#         )
#         already_saved_followers_set = set(already_saved_followers)
#         followers_set = set(followers)
#         followers = list(followers_set - already_saved_followers_set)
#         followers_no_more = list(already_saved_followers_set - followers_set)
#         if saved_followers_count - len(followers_no_more) > 0:
#             self.logger.info("{} of {}'s followers already in the database".format(
#                 saved_followers_count, starting_username))
#         try:
#             self.logger.info("Saving followers of {}".format(starting_username))
#             for username in progressbar(followers):
#                 user = db_get_or_create_user(self, username)
#                 starting_user.followers.append(user)
#                 self.db.session.add(user)
#                 self.db.session.commit()
#                 self.db.session.expunge(user)
#             if len(followers_no_more) != 0:
#                 self.logger.info("Saving un-followers of {}".format(starting_username))
#                 for username in progressbar(followers_no_more):
#                     user = db_get_or_create_user(self, username)
#                     starting_user.followers.remove(user)
#                     self.db.session.add(user)
#                     self.db.session.commit()
#                     self.db.session.expunge(user)
#         except SQLAlchemyError:
#             self.db.session.rollback()
#
#     if starting_user and saved_following_count != following_count:
#         following = get_following(
#             self.browser,
#             starting_username,
#             "full",
#             self.relationship_data,
#             True,
#             False,
#             self.logger,
#             self.logfolder
#         )
#         already_saved_following_set = set(already_saved_followers)
#         following_set = set(following)
#         following = list(following_set - already_saved_following_set)
#         following_no_more = list(already_saved_following_set - following_set)
#         if saved_following_count - len(following_no_more) > 0:
#             self.logger.info("{} of {}'s followings already in the database".format(
#                 saved_following_count, starting_username))
#         try:
#             self.logger.info("Saving following of {}".format(starting_username))
#             for username in progressbar(following):
#                 user = db_get_or_create_user(self, username)
#                 starting_user.following.append(user)
#                 self.db.session.add(user)
#                 self.db.session.commit()
#                 self.db.session.expunge(user)
#             if len(following_no_more) != 0:
#                 self.logger.info("Saving un-following of {}".format(starting_username))
#                 for username in progressbar(following_no_more):
#                     user = db_get_or_create_user(self, username)
#                     starting_user.following.remove(user)
#                     self.db.session.add(user)
#                     self.db.session.commit()
#                     self.db.session.expunge(user)
#         except SQLAlchemyError:
#             self.db.session.rollback()
#
#
# def store_all_posts_of_user(self, username: str):
#     user_link = "https://www.instagram.com/{}/".format(username)
#     web_address_navigator(self.browser, user_link)
#     try:
#         posts_count = getUserData(
#             "graphql.user.edge_owner_to_timeline_media.count", self.browser
#         )
#     except WebDriverException:
#         posts_count = 0
#
#     user = None
#     try:
#         user = db_get_or_create_user(self, username)
#         self.db.session.add(user)
#         if user.posts_count != posts_count and posts_count != 0:
#             user.posts_count = posts_count
#         self.db.session.commit()
#     except SQLAlchemyError:
#         self.db.session.rollback()
#
#     if user and len(user.posts) != posts_count:
#         try:
#             post_links = get_links_for_username(
#                 self.browser,
#                 self.username,
#                 username,
#                 100,
#                 self.logger,
#                 self.logfolder
#             )
#         except InvalidSelectorException:
#             # Private account, get_links_for_username already prints it on log
#             return
#         except Exception:
#             self.logger.error("Failed to get post links of {}".format(username))
#             return
#         already_saved_posts = self.db.session.query(Post).filter(Post.user == user).all()
#         if len(already_saved_posts) != 0:
#             self.logger.info("{} of {}'s posts already in the database".format(len(already_saved_posts), username))
#         post_links = list(set(post_links) - set([post.link for post in already_saved_posts]))
#         already_saved_post_srcs = [post.src for post in already_saved_posts]
#         for i, post_link in enumerate(post_links):
#             self.logger.info("Saving post {}/{} of {}".format(i+1, len(post_links), username))
#             web_address_navigator(self.browser, post_link)
#             try:
#                 username_button = self.browser.find_element_by_xpath(
#                     '/html/body/div[1]/section/main/div/div/article/header//div[@class="e1e1d"]'
#                 )
#                 username_text = username_button.text
#                 images = self.browser.find_elements_by_xpath(
#                     '/html/body/div[1]/section/main/div/div/article//img[@class="FFVAD"]'
#                 )
#                 more_button = self.browser.find_elements_by_xpath("//button[text()='more']")
#                 if more_button:
#                     nf_scroll_into_view(self, more_button[0])
#                     more_button[0].click()
#                 try:
#                     caption = self.browser.find_element_by_xpath(
#                         "/html/body/div[1]/section/main/div/div/article//div/div/span/span"
#                     ).text
#                 except NoSuchElementException:
#                     caption = None
#                 caption = "" if caption is None else caption
#                 likes_count = get_like_count(self)
#                 image_descriptions = []
#                 image_links = []
#                 for image in images:
#                     image_description = image.get_attribute('alt')
#                     if image_description is not None and 'Image may contain:' in image_description:
#                         image_description = image_description[image_description.index(
#                             'Image may contain:') + 19:]
#                     else:
#                         image_description = None
#                     image_descriptions.append(image_description)
#                     image_links.append(image.get_attribute('src'))
#
#                 user = db_get_or_create_user(self, username_text)
#                 self.db.session.add(user)
#                 self.db.session.commit()
#                 db_posts = []
#                 for image_link, image_description in zip(image_links, image_descriptions):
#                     try:
#                         post_date = self.browser.find_element_by_xpath(
#                             '/html/body/div[1]/section/main/div/div/article//a[@class="c-Yi7"]/time'
#                         ).get_attribute('datetime')
#                         post_date = datetime.fromisoformat(post_date[:-1])
#                     except NoSuchElementException:
#                         post_date = datetime.now()
#
#                     post = db_get_or_create_post(
#                         self,
#                         post_date,
#                         post_link,
#                         image_link,
#                         caption,
#                         likes_count,
#                         user,
#                         image_description
#                     )
#                     self.db.session.add(post)
#                     # forgot to save post link on database so this is an extra check to not store
#                     # comments again if post was already saved
#                     # TODO: delete
#                     if image_link not in already_saved_post_srcs:
#                         db_posts.append(post)
#                 self.db.session.commit()
#                 if db_posts:
#                     db_store_comments(self, db_posts, post_link)
#                     for post in db_posts:
#                         self.db.session.expunge(post)
#             except SQLAlchemyError:
#                 self.db.session.rollback()
#             finally:
#                 self.db.session.commit()
#