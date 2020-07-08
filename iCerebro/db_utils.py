from datetime import datetime
from time import sleep
from typing import List
from instapy.util import web_address_navigator, deform_emojis
from iCerebro.database import Post, Comment, User
from iCerebro.navigation import nf_scroll_into_view, nf_click_center_of_element, \
    nf_find_and_press_back, check_if_in_correct_page
from sqlalchemy.exc import SQLAlchemyError


def db_store_comments(
        self,
        posts: List[Post],
        post_link: str
):
    """Stores all comments of open post then goes back to post page"""
    try:
        comments_button = self.browser.find_elements_by_xpath(
            '//article//div[2]/div[1]//a[contains(@href,"comments")]'
        )
        if comments_button:
            nf_scroll_into_view(self, comments_button[0])
            nf_click_center_of_element(self, comments_button[0])
            sleep(2)
            comments_link = post_link + 'comments/'
            if not check_if_in_correct_page(self, comments_link):
                self.logger.error("Failed to go to comments page, navigating there")
                # TODO: retry to get there naturally
                web_address_navigator(self.browser, comments_link)
            more_comments = self.browser.find_elements_by_xpath(
                '//span[@aria-label="Load more comments"]'
            )
            counter = 1
            while more_comments and counter <= 10:
                self.logger.info("Loading comments ({}/10)...".format(counter))
                nf_scroll_into_view(self, more_comments[0])
                self.browser.execute_script(
                    "arguments[0].click();", more_comments[0])
                more_comments = self.browser.find_elements_by_xpath(
                    '//span[@aria-label="Load more comments"]'
                )
                counter += 1

            comments = self.browser.find_elements_by_xpath(
                '/html/body/div[1]/section/main/div/ul/ul[@class="Mr508"]'
            )
            for comment in comments:
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
        else:
            self.logger.error("No comments found")
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
        src_link: str,
        caption: str,
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
            src=src_link,
            caption=caption,
            user=user,
            ig_desciption=ig_desciption,
            objects_detected=objects_detected,
            classified_as=classified_as,
        )
    else:
        post = posts[0]
    return post
