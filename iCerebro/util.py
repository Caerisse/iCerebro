import unicodedata
from time import sleep, time
import datetime
from math import radians
from math import degrees as rad2deg
from math import cos
import random
import re
from typing import List

import regex
import signal
import os
import sys
from platform import system
from subprocess import call
import csv
import json
from contextlib import contextmanager
import emoji
from emoji.unicode_codes import UNICODE_EMOJI
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException

import iCerebro.constants_x_paths as XP
from iCerebro import ICerebro
from iCerebro.instapy.event import Event
from iCerebro.navigation import nf_click_center_of_element, web_address_navigator, get_current_url

default_profile_pic_instagram = [
    "https://instagram.flas1-2.fna.fbcdn.net/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
    "https://scontent-yyz1-1.cdninstagram.com/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
    "https://instagram.faep12-1.fna.fbcdn.net/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
    "https://instagram.fbts2-1.fna.fbcdn.net/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
    "https://scontent-mia3-1.cdninstagram.com/vp"
    "/a8539c22ed9fec8e1c43b538b1ebfd1d/5C5A1A7A/t51.2885-19"
    "/11906329_960233084022564_1448528159_a.jpg",
]
next_screenshot = 1


class Interactions:
    def __init__(
            self,
            liked_img=0,
            already_liked=0,
            liked_comments=0,
            commented=0,
            replied_to_comments=0,
            followed=0,
            already_followed=0,
            unfollowed=0,
            inap_img=0,
            not_valid_users=0,
            video_played=0,
            already_Visited=0,
            stories_watched=0,
            reels_watched=0,
    ):
        self.liked_img = liked_img
        self.already_liked = already_liked
        self.liked_comments = liked_comments
        self.commented = commented
        self.replied_to_comments = replied_to_comments
        self.followed = followed
        self.already_followed = already_followed
        self.unfollowed = unfollowed
        self.inap_img = inap_img
        self.not_valid_users = not_valid_users
        self.video_played = video_played
        self.already_Visited = already_Visited
        self.stories_watched = stories_watched
        self.reels_watched = reels_watched

    def __add__(self, other):
        return (
            Interactions(
                self.liked_img + other.liked_img,
                self.already_liked + other.already_liked,
                self.liked_comments + other.liked_comments,
                self.commented + other.commented,
                self.replied_to_comments + other.replied_to_comments,
                self.followed + other.followed,
                self.already_followed + other.already_followed,
                self.unfollowed + other.unfollowed,
                self.inap_img + other.inap_img,
                self.not_valid_users + other.not_valid_users,
                self.video_played + other.video_played,
                self.already_Visited + other.already_Visited,
                self.stories_watched + other.stories_watched,
                self.reels_watched + other.reels_watched
            )
        )

    def __str__(self):
        string = "Interactions: "
        string += "\nLiked Images: {}".format(self.liked_img) if self.liked_img != 0 else ""
        string += "\nAlready Liked Images: {}".format(self.already_liked) if self.already_liked != 0 else ""
        string += "\nComments Liked: {}".format(self.liked_comments) if self.liked_comments != 0 else ""
        string += "\nComments Made: {}".format(self.commented) if self.commented != 0 else ""
        string += "\nComments Replied: {}".format(self.replied_to_comments) if self.replied_to_comments != 0 else ""
        string += "\nFollowed: {}".format(self.followed) if self.followed != 0 else ""
        string += "\nAlready Followed: {}".format(self.already_followed) if self.already_followed != 0 else ""
        string += "\nUnfollowed: {}".format(self.unfollowed) if self.unfollowed != 0 else ""
        string += "\nInappropriate Images: {}".format(self.inap_img) if self.inap_img != 0 else ""
        string += "\nNot valid Users: {}".format(self.not_valid_users) if self.not_valid_users != 0 else ""
        string += "\nVideos Played: {}".format(self.video_played) if self.video_played != 0 else ""
        string += "\nAlready Visited: {}".format(self.already_Visited) if self.already_Visited != 0 else ""
        string += "\nStories Watched: {}".format(self.stories_watched) if self.stories_watched != 0 else ""
        string += "\nReels Watched: {}".format(self.reels_watched) if self.reels_watched != 0 else ""
        return string


def is_private_profile(browser, logger, following=True):
    is_private = None
    try:
        is_private = browser.execute_script(
            "return window.__additionalData[Object.keys(window.__additionalData)[0]]."
            "data.graphql.user.is_private"
        )

    except WebDriverException:
        try:
            browser.execute_script("location.reload()")
            update_activity(browser, state=None)

            is_private = browser.execute_script(
                "return window._sharedData.entry_data."
                "ProfilePage[0].graphql.user.is_private"
            )

        except WebDriverException:
            return None

    # double check with xpath that should work only when we not following a
    # user
    if is_private and not following:
        logger.info("Is private account you're not following.")
        body_elem = browser.find_element_by_tag_name("body")
        is_private = body_elem.find_element_by_xpath(
            read_xpath(is_private_profile.__name__, "is_private")
        )

    return is_private


def getUserData(
    query,
    browser,
    basequery="return window.__additionalData[Object.keys(window.__additionalData)[0]].data.",
):
    try:
        data = browser.execute_script(basequery + query)
        return data
    except WebDriverException:
        browser.execute_script("location.reload()")
        update_activity(browser, state=None)

        data = browser.execute_script(
            "return window._sharedData." "entry_data.ProfilePage[0]." + query
        )
        return data


# TODO: rewrite
def update_activity(
    self, action="server_calls", state=None
):
    """
        1. Record every Instagram server call (page load, content load, likes,
        comments, follows, unfollow)
        2. Take rotative screenshots
        3. update connection state and record to .json file
    """
    pass
    # # check action availability
    # quota_supervisor("server_calls")
    #
    # # take screen shot
    # if browser and logfolder and logger:
    #     take_rotative_screenshot(browser, logfolder)
    #
    # # update state to JSON file
    # if state and logfolder and logger:
    #     try:
    #         path = "{}state.json".format(logfolder)
    #         data = {}
    #         # check if file exists and has content
    #         if os.path.isfile(path) and os.path.getsize(path) > 0:
    #             # load JSON file
    #             with open(path, "r") as json_file:
    #                 data = json.load(json_file)
    #
    #         # update connection state
    #         connection_data = {}
    #         connection_data["connection"] = state
    #         data["state"] = connection_data
    #
    #         # write to JSON file
    #         with open(path, "w") as json_file:
    #             json.dump(data, json_file, indent=4)
    #     except Exception:
    #         logger.warn("Unable to update JSON state file")
    #
    # # in case is just a state update and there is no server call
    # if action is None:
    #     return
    #
    # # get a DB, start a connection and sum a server call
    # db, id = get_database()
    # conn = sqlite3.connect(db)
    #
    # with conn:
    #     conn.row_factory = sqlite3.Row
    #     cur = conn.cursor()
    #     # collect today data
    #     cur.execute(
    #         "SELECT * FROM recordActivity WHERE profile_id=:var AND "
    #         "STRFTIME('%Y-%m-%d %H', created) == STRFTIME('%Y-%m-%d "
    #         "%H', 'now', 'localtime')",
    #         {"var": id},
    #     )
    #     data = cur.fetchone()
    #
    #     if data is None:
    #         # create a new record for the new day
    #         cur.execute(
    #             "INSERT INTO recordActivity VALUES "
    #             "(?, 0, 0, 0, 0, 1, STRFTIME('%Y-%m-%d %H:%M:%S', "
    #             "'now', 'localtime'))",
    #             (id,),
    #         )
    #
    #     else:
    #         # sqlite3.Row' object does not support item assignment -> so,
    #         # convert it into a new dict
    #         data = dict(data)
    #
    #         # update
    #         data[action] += 1
    #         quota_supervisor(action, update=True)
    #
    #         if action != "server_calls":
    #             # always update server calls
    #             data["server_calls"] += 1
    #             quota_supervisor("server_calls", update=True)
    #
    #         sql = (
    #             "UPDATE recordActivity set likes = ?, comments = ?, "
    #             "follows = ?, unfollows = ?, server_calls = ?, "
    #             "created = STRFTIME('%Y-%m-%d %H:%M:%S', 'now', "
    #             "'localtime') "
    #             "WHERE  profile_id=? AND STRFTIME('%Y-%m-%d %H', created) "
    #             "== "
    #             "STRFTIME('%Y-%m-%d %H', 'now', 'localtime')"
    #         )
    #
    #         cur.execute(
    #             sql,
    #             (
    #                 data["likes"],
    #                 data["comments"],
    #                 data["follows"],
    #                 data["unfollows"],
    #                 data["server_calls"],
    #                 id,
    #             ),
    #         )
    #
    #     # commit the latest changes
    #     conn.commit()


# TODO: rewrite to use django db
def add_user_to_blacklist(username, campaign, action, logger, logfolder):
    file_exists = os.path.isfile("{}blacklist.csv".format(logfolder))
    fieldnames = ["date", "username", "campaign", "action"]
    today = datetime.date.today().strftime("%m/%d/%y")

    try:
        with open("{}blacklist.csv".format(logfolder), "a+") as blacklist:
            writer = csv.DictWriter(blacklist, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(
                {
                    "date": today,
                    "username": username,
                    "campaign": campaign,
                    "action": action,
                }
            )
    except Exception as err:
        logger.error("blacklist dictWrite error {}".format(err))

    logger.info(
        "--> {} added to blacklist for {} campaign (action: {})".format(
            username, campaign, action
        )
    )


# TODO: rewrite
def get_active_users(browser, username, posts, boundary, logger):
    """Returns a list with usernames who liked the latest n posts"""

    user_link = "https://www.instagram.com/{}/".format(username)

    # check URL of the webpage, if it already is user's profile page,
    # then do not navigate to it again
    web_address_navigator(browser, user_link)

    try:
        total_posts = browser.execute_script(
            "return window._sharedData.entry_data."
            "ProfilePage[0].graphql.user.edge_owner_to_timeline_media.count"
        )
    except WebDriverException:
        try:
            topCount_elements = browser.find_elements_by_xpath(
                read_xpath(get_active_users.__name__, "topCount_elements")
            )

            if topCount_elements:  # prevent an empty string scenario
                total_posts = format_number(topCount_elements[0].text)
            else:
                logger.info(
                    "Failed to get posts count on your profile!  ~empty " "string"
                )
                total_posts = None
        except NoSuchElementException:
            logger.info("Failed to get posts count on your profile!")
            total_posts = None

    # if posts > total user posts, assume total posts
    posts = (
        posts if total_posts is None else total_posts if posts > total_posts else posts
    )

    active_users = []
    sc_rolled = 0
    start_time = time()
    too_many_requests = 0  # helps to prevent misbehaviours when requests
    # list of active users repeatedly within less than 10 min of breaks

    message = (
        "~collecting the entire usernames from posts without a boundary!\n"
        if boundary is None
        else "~collecting only the visible usernames from posts without scrolling "
        "at the boundary of zero..\n"
        if boundary == 0
        else "~collecting the usernames from posts with the boundary of {}"
        "\n".format(boundary)
    )
    # posts argument is the number of posts to collect usernames
    logger.info(
        "Getting active users who liked the latest {} posts:\n  {}".format(
            posts, message
        )
    )

    count = 1
    checked_posts = 0
    while count <= posts:
        # load next post
        try:
            latest_post = browser.find_element_by_xpath(
                read_xpath(get_active_users.__name__, "profile_posts").format(count)
            )
            # avoid no posts
            if latest_post:
                nf_click_center_of_element(browser, latest_post)
        except (NoSuchElementException, WebDriverException):
            logger.warning("Failed to click on the latest post to grab active likers!")
            return []
        try:
            checked_posts += 1
            sleep(2)

            try:
                likers_count = browser.find_element_by_xpath(
                    read_xpath(get_active_users.__name__, "likers_count")
                ).text
                if likers_count:  # prevent an empty string scenarios
                    likers_count = format_number(likers_count)
                    # liked by 'username' AND 165 others (166 in total)
                    likers_count += 1
                else:
                    logger.info(
                        "Failed to get likers count on your post {}  "
                        "~empty string".format(count)
                    )
                    likers_count = None
            except NoSuchElementException:
                logger.info("Failed to get likers count on your post {}".format(count))
                likers_count = None
            try:
                likes_button = browser.find_elements_by_xpath(
                    read_xpath(get_active_users.__name__, "likes_button")
                )

                if likes_button != []:
                    if likes_button[1] is not None:
                        likes_button = likes_button[1]
                    else:
                        likes_button = likes_button[0]
                    nf_click_center_of_element(browser, likes_button)
                    sleep(3)
                else:
                    raise NoSuchElementException

            except (IndexError, NoSuchElementException):
                # Video have no likes button / no posts in page
                logger.info("video found, try next post until we run out of posts")

                # edge case of account having only videos,  or last post is a video.
                if checked_posts >= total_posts:
                    break
                # if not reached posts(parameter) value, continue (but load next post)
                browser.back()
                # go to next post
                count += 1
                continue

            # get a reference to the 'Likes' dialog box
            dialog = browser.find_element_by_xpath(
                read_xpath("class_selectors", "likes_dialog_body_xpath")
            )

            scroll_it = True
            try_again = 0
            start_time = time.time()
            user_list = []

            if likers_count:
                amount = (
                    likers_count
                    if boundary is None
                    else None
                    if boundary == 0
                    else (boundary if boundary < likers_count else likers_count)
                )
            else:
                amount = None
            tmp_scroll_height = 0
            user_list_len = -1
            while scroll_it is not False and boundary != 0:
                scroll_height = browser.execute_script(
                    """
                    let main = document.getElementsByTagName('main')
                    return main[0].scrollHeight
                    """
                )
                # check if it should keep scrolling down or exit
                if (
                    scroll_height >= tmp_scroll_height
                    and len(user_list) > user_list_len
                ):
                    tmp_scroll_height = scroll_height
                    user_list_len = len(user_list)
                    scroll_it = True
                else:
                    scroll_it = False

                if scroll_it is True:
                    scroll_it = browser.execute_script("window.scrollBy(0, 1000)")
                    update_activity(browser, state=None)

                if sc_rolled > 91 or too_many_requests > 1:  # old value 100
                    print("\n")
                    logger.info("Too Many Requests sent! ~will sleep some :>\n")
                    sleep(600)
                    sc_rolled = 0
                    too_many_requests = (
                        0 if too_many_requests >= 1 else too_many_requests
                    )

                else:
                    sleep(1.2)  # old value 5.6
                    sc_rolled += 1

                user_list = get_users_from_dialog(user_list, dialog)

                # write & update records at Progress Tracker
                if amount:
                    progress_tracker(len(user_list), amount, start_time, None)

                if boundary is not None:
                    if len(user_list) >= boundary:
                        break

                if (
                    scroll_it is False
                    and likers_count
                    and likers_count - 1 > len(user_list)
                ):

                    if (
                        boundary is not None and likers_count - 1 > boundary
                    ) or boundary is None:

                        if try_again <= 1:  # can increase the amount of tries
                            logger.info(
                                "Failed to get the desired amount of "
                                "usernames but trying again.."
                                "\t|> post:{}  |> attempt: {}\n".format(
                                    posts, try_again + 1
                                )
                            )
                            try_again += 1
                            too_many_requests += 1
                            scroll_it = True
                            nap_it = 4 if try_again == 0 else 7
                            sleep(nap_it)

            user_list = get_users_from_dialog(user_list, dialog)

            logger.info(
                "Post {}  |  Likers: found {}, catched {}\n\n".format(
                    count, likers_count, len(user_list)
                )
            )
        except NoSuchElementException as exc:
            logger.error(
                "Ku-ku! There is an error searching active users"
                "~\t{}\n\n".format(str(exc).encode("utf-8"))
            )

        for user in user_list:
            active_users.append(user)

        sleep(1)

        # if not reached posts(parameter) value, continue
        if count != posts + 1:
            try:
                # click close button
                close_dialog_box(browser)
                browser.back()
            except Exception:
                logger.error("Unable to go to next profile post")
        count += 1

    real_time = time.time()
    diff_in_minutes = int((real_time - start_time) / 60)
    diff_in_seconds = int((real_time - start_time) % 60)

    # delete duplicated users
    active_users = list(set(active_users))

    logger.info(
        "Gathered total of {} unique active followers from the latest {} "
        "posts in {} minutes and {} seconds".format(
            len(active_users), posts, diff_in_minutes, diff_in_seconds
        )
    )

    return active_users


def get_users_from_dialog(old_data, dialog):
    """
    Prepared to work specially with the dynamic data load in the 'Likes'
    dialog box
    """

    user_blocks = dialog.find_elements_by_tag_name("a")
    loaded_users = [
        extract_text_from_element(u)
        for u in user_blocks
        if extract_text_from_element(u)
    ]
    new_data = old_data + loaded_users
    new_data = remove_duplicates(new_data, True, None)

    return new_data


def extract_text_from_element(elem):
    """ As an element is valid and contains text, extract it and return """
    if elem and hasattr(elem, "text") and elem.text:
        text = elem.text
    else:
        text = None
    return text


def remove_duplicates(container, keep_order, logger):
    """ Remove duplicates from all kinds of data types easily """
    # add support for data types as needed in future
    # currently only 'list' data type is supported
    if isinstance(container, list):
        if keep_order is True:
            result = sorted(set(container), key=container.index)
        else:
            result = set(container)
    else:
        logger.warning(
            "The given data type- '{}' is not supported "
            "in `remove_duplicates` function, yet!".format(type(container))
        )
        result = container
    return result


def format_number(number):
    """
    Format number. Remove the unused comma. Replace the concatenation with
    relevant zeros. Remove the dot.

    :param number: str

    :return: int
    """
    formatted_num = number.replace(",", "")
    formatted_num = re.sub(
        r"(k)$", "00" if "." in formatted_num else "000", formatted_num
    )
    formatted_num = re.sub(
        r"(m)$", "00000" if "." in formatted_num else "000000", formatted_num
    )
    formatted_num = formatted_num.replace(".", "")
    return int(formatted_num)


def get_number_of_posts(browser):
    """Get the number of posts from the profile screen"""
    try:
        num_of_posts = getUserData(
            "graphql.user.edge_owner_to_timeline_media.count", browser
        )
    except WebDriverException:
        try:
            num_of_posts_txt = browser.find_element_by_xpath(
                read_xpath(get_number_of_posts.__name__, "num_of_posts_txt")
            ).text

        except NoSuchElementException:
            num_of_posts_txt = browser.find_element_by_xpath(
                read_xpath(
                    get_number_of_posts.__name__, "num_of_posts_txt_no_such_element"
                )
            ).text

        num_of_posts_txt = num_of_posts_txt.replace(" ", "")
        num_of_posts_txt = num_of_posts_txt.replace(",", "")
        num_of_posts = int(num_of_posts_txt)

    return num_of_posts


def get_relationship_counts(browser, username, logger):
    """ Gets the followers & following counts of a given user """

    user_link = "https://www.instagram.com/{}/".format(username)

    # check URL of the webpage, if it already is user's profile page,
    # then do not navigate to it again
    web_address_navigator(browser, user_link)

    try:
        followers_count = browser.execute_script(
            "return window._sharedData.entry_data."
            "ProfilePage[0].graphql.user.edge_followed_by.count"
        )

    except WebDriverException:
        try:
            followers_count = format_number(
                browser.find_element_by_xpath(
                    str(read_xpath(get_relationship_counts.__name__, "followers_count"))
                ).text
            )
        except NoSuchElementException:
            try:
                browser.execute_script("location.reload()")
                update_activity(browser, state=None)

                followers_count = browser.execute_script(
                    "return window._sharedData.entry_data."
                    "ProfilePage[0].graphql.user.edge_followed_by.count"
                )

            except WebDriverException:
                try:
                    topCount_elements = browser.find_elements_by_xpath(
                        read_xpath(
                            get_relationship_counts.__name__, "topCount_elements"
                        )
                    )

                    if topCount_elements:
                        followers_count = format_number(topCount_elements[1].text)

                    else:
                        logger.info(
                            "Failed to get followers count of '{}'  ~empty "
                            "list".format(username.encode("utf-8"))
                        )
                        followers_count = None

                except NoSuchElementException:
                    logger.error(
                        "Error occurred during getting the followers count "
                        "of '{}'\n".format(username.encode("utf-8"))
                    )
                    followers_count = None

    try:
        following_count = browser.execute_script(
            "return window._sharedData.entry_data."
            "ProfilePage[0].graphql.user.edge_follow.count"
        )

    except WebDriverException:
        try:
            following_count = format_number(
                browser.find_element_by_xpath(
                    str(read_xpath(get_relationship_counts.__name__, "following_count"))
                ).text
            )

        except NoSuchElementException:
            try:
                browser.execute_script("location.reload()")
                update_activity(browser, state=None)

                following_count = browser.execute_script(
                    "return window._sharedData.entry_data."
                    "ProfilePage[0].graphql.user.edge_follow.count"
                )

            except WebDriverException:
                try:
                    topCount_elements = browser.find_elements_by_xpath(
                        read_xpath(
                            get_relationship_counts.__name__, "topCount_elements"
                        )
                    )

                    if topCount_elements:
                        following_count = format_number(topCount_elements[2].text)

                    else:
                        logger.info(
                            "Failed to get following count of '{}'  ~empty "
                            "list".format(username.encode("utf-8"))
                        )
                        following_count = None

                except (NoSuchElementException, IndexError):
                    logger.error(
                        "\nError occurred during getting the following count "
                        "of '{}'\n".format(username.encode("utf-8"))
                    )
                    following_count = None

    Event().profile_data_updated(username, followers_count, following_count)
    return followers_count, following_count


@contextmanager
def interruption_handler(
    threaded=False,
    SIG_type=signal.SIGINT,
    handler=signal.SIG_IGN,
    notify=None,
    logger=None,
):
    """ Handles external interrupt, usually initiated by the user like
    KeyboardInterrupt with CTRL+C """
    if notify is not None and logger is not None:
        logger.warning(notify)

    if not threaded:
        original_handler = signal.signal(SIG_type, handler)

    try:
        yield

    finally:
        if not threaded:
            signal.signal(SIG_type, original_handler)


def ping_server(host, logger):
    """
    Return True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if
    the host name is valid.
    """
    logger.info("Pinging '{}' to check the connectivity...".format(str(host)))

    # ping command count option as function of OS
    param = "-n" if system().lower() == "windows" else "-c"
    # building the command. Ex: "ping -c 1 google.com"
    command = " ".join(["ping", param, "1", str(host)])
    need_sh = False if system().lower() == "windows" else True

    # pinging
    ping_attempts = 2
    connectivity = None

    while connectivity is not True and ping_attempts > 0:
        connectivity = call(command, shell=need_sh) == 0

        if connectivity is False:
            logger.warning(
                "Pinging the server again!\t~total attempts left: {}".format(
                    ping_attempts
                )
            )
            ping_attempts -= 1
            sleep(5)

    if connectivity is False:
        logger.critical("There is no connection to the '{}' server!".format(host))
        return False

    return True


def emergency_exit(browser, username, logger):
    """ Raise emergency if the is no connection to server OR if user is not
    logged in """
    server_address = "instagram.com"
    connection_state = ping_server(server_address, logger)
    if connection_state is False:
        return True, "not connected"

    # check if the user is logged in
    auth_method = "activity counts"
    login_state = check_authorization(browser, username, auth_method, logger)
    if login_state is False:
        return True, "not logged in"

    return False, "no emergency"


def check_authorization(browser, username, method, logger, notify=True):
    """ Check if user is NOW logged in """
    if notify is True:
        logger.info("Checking if '{}' is logged in...".format(username))

    # different methods can be added in future
    if method == "activity counts":

        # navigate to owner's profile page only if it is on an unusual page
        current_url = get_current_url(browser)
        if (
            not current_url
            or "https://www.instagram.com" not in current_url
            or "https://www.instagram.com/graphql/" in current_url
        ):
            profile_link = "https://www.instagram.com/{}/".format(username)
            web_address_navigator(browser, profile_link)

        # if user is not logged in, `activity_counts` will be `None`- JS `null`
        try:
            activity_counts = browser.execute_script(
                "return window._sharedData.activity_counts"
            )

        except WebDriverException:
            try:
                browser.execute_script("location.reload()")
                update_activity(browser, state=None)

                activity_counts = browser.execute_script(
                    "return window._sharedData.activity_counts"
                )

            except WebDriverException:
                activity_counts = None

        # if user is not logged in, `activity_counts_new` will be `None`- JS
        # `null`
        try:
            activity_counts_new = browser.execute_script(
                "return window._sharedData.config.viewer"
            )

        except WebDriverException:
            try:
                browser.execute_script("location.reload()")
                activity_counts_new = browser.execute_script(
                    "return window._sharedData.config.viewer"
                )

            except WebDriverException:
                activity_counts_new = None

        if activity_counts is None and activity_counts_new is None:
            if notify is True:
                logger.critical("--> '{}' is not logged in!\n".format(username))
            return False

    return True


def get_username_by_js_query(browser, track, logger):
    """ Get the username of a user from the loaded profile page """
    if track == "profile":
        query = "return window._sharedData.entry_data. \
                    ProfilePage[0].graphql.user.username"

    elif track == "post":
        query = "return window._sharedData.entry_data. \
                    PostPage[0].graphql.shortcode_media.owner.username"

    try:
        username = browser.execute_script(query)

    except WebDriverException:
        try:
            browser.execute_script("location.reload()")
            update_activity(browser, state=None)

            username = browser.execute_script(query)

        except WebDriverException:
            current_url = get_current_url(browser)
            logger.info(
                "Failed to get the username from '{}' page".format(
                    current_url or "user" if track == "profile" else "post"
                )
            )
            username = None

    # in future add XPATH ways of getting username

    return username


def find_user_id(browser, track, username, logger):
    """  Find the user ID from the loaded page """
    if track in ["dialog", "profile"]:
        query = "return window.__additionalData[Object.keys(window.__additionalData)[0]].data.graphql.user.id"

    elif track == "post":
        query = (
            "return window._sharedData.entry_data.PostPage["
            "0].graphql.shortcode_media.owner.id"
        )
        meta_XP = read_xpath(find_user_id.__name__, "meta_XP")

    failure_message = "Failed to get the user ID of '{}' from {} page!".format(
        username, track
    )

    try:
        user_id = browser.execute_script(query)

    except WebDriverException:
        try:
            browser.execute_script("location.reload()")
            update_activity(browser, state=None)

            user_id = browser.execute_script(
                "return window._sharedData."
                "entry_data.ProfilePage[0]."
                "graphql.user.id"
            )

        except WebDriverException:
            if track == "post":
                try:
                    user_id = browser.find_element_by_xpath(meta_XP).get_attribute(
                        "content"
                    )
                    if user_id:
                        user_id = format_number(user_id)

                    else:
                        logger.error("{}\t~empty string".format(failure_message))
                        user_id = None

                except NoSuchElementException:
                    logger.error(failure_message)
                    user_id = None

            else:
                logger.error(failure_message)
                user_id = None

    return user_id


@contextmanager
def new_tab(browser):
    """ USE once a host tab must remain untouched and yet needs extra data-
    get from guest tab """
    try:
        # add a guest tab
        browser.execute_script("window.open()")
        sleep(1)
        # switch to the guest tab
        browser.switch_to.window(browser.window_handles[1])
        sleep(2)
        yield

    finally:
        # close the guest tab
        browser.execute_script("window.close()")
        sleep(1)
        # return to the host tab
        browser.switch_to.window(browser.window_handles[0])
        sleep(2)


def explicit_wait(browser, track, ec_params, logger, timeout=35, notify=True):
    """
    Explicitly wait until expected condition validates

    :param browser: webdriver instance
    :param track: short name of the expected condition
    :param ec_params: expected condition specific parameters - [param1, param2]
    :param logger: the logger instance
    """
    # list of available tracks:
    # <https://seleniumhq.github.io/selenium/docs/api/py/webdriver_support/
    # selenium.webdriver.support.expected_conditions.html>

    if not isinstance(ec_params, list):
        ec_params = [ec_params]

    # find condition according to the tracks
    if track == "VOEL":
        elem_address, find_method = ec_params
        ec_name = "visibility of element located"

        find_by = (
            By.XPATH
            if find_method == "XPath"
            else By.CSS_SELECTOR
            if find_method == "CSS"
            else By.CLASS_NAME
        )
        locator = (find_by, elem_address)
        condition = ec.visibility_of_element_located(locator)

    elif track == "TC":
        expect_in_title = ec_params[0]
        ec_name = "title contains '{}' string".format(expect_in_title)

        condition = ec.title_contains(expect_in_title)

    elif track == "PFL":
        ec_name = "page fully loaded"
        condition = lambda browser: browser.execute_script(
            "return document.readyState"
        ) in ["complete" or "loaded"]

    elif track == "SO":
        ec_name = "staleness of"
        element = ec_params[0]

        condition = ec.staleness_of(element)

    # generic wait block
    try:
        wait = WebDriverWait(browser, timeout)
        result = wait.until(condition)

    except TimeoutException:
        if notify is True:
            logger.info(
                "Timed out with failure while explicitly waiting until {}!\n".format(
                    ec_name
                )
            )
        return False

    return result


def get_username_from_id(browser, user_id, logger):
    """ Convert user ID to username """
    # method using graphql 'Account media' endpoint
    logger.info("Trying to find the username from the given user ID by loading a post")

    query_hash = "42323d64886122307be10013ad2dcc44"  # earlier-
    # "472f257a40c653c64c666ce877d59d2b"
    graphql_query_URL = (
        "https://www.instagram.com/graphql/query/?query_hash" "={}".format(query_hash)
    )
    variables = {"id": str(user_id), "first": 1}
    post_url = "{}&variables={}".format(graphql_query_URL, str(json.dumps(variables)))

    web_address_navigator(browser, post_url)
    try:
        pre = browser.find_element_by_tag_name("pre").text
    except NoSuchElementException:
        logger.info("Encountered an error to find `pre` in page, skipping username.")
        return None
    user_data = json.loads(pre)["data"]["user"]

    if user_data:
        user_data = user_data["edge_owner_to_timeline_media"]

        if user_data["edges"]:
            post_code = user_data["edges"][0]["node"]["shortcode"]
            post_page = "https://www.instagram.com/p/{}".format(post_code)

            web_address_navigator(browser, post_page)
            username = get_username_by_js_query(browser, "post", logger)
            if username:
                return username

        else:
            if user_data["count"] == 0:
                logger.info("Profile with ID {}: no pics found".format(user_id))

            else:
                logger.info(
                    "Can't load pics of a private profile to find username ("
                    "ID: {})".format(user_id)
                )

    else:
        logger.info(
            "No profile found, the user may have blocked you (ID: {})".format(user_id)
        )
        return None

    """  method using private API
    #logger.info("Trying to find the username from the given user ID by a
    quick API call")

    #req = requests.get(u"https://i.instagram.com/api/v1/users/{}/info/"
    #                   .format(user_id))
    #if req:
    #    data = json.loads(req.text)
    #    if data["user"]:
    #        username = data["user"]["username"]
    #        return username
    """

    """ Having a BUG (random log-outs) with the method below, use it only in
    the external sessions
    # method using graphql 'Follow' endpoint
    logger.info("Trying to find the username from the given user ID "
                "by using the GraphQL Follow endpoint")

    user_link_by_id = ("https://www.instagram.com/web/friendships/{}/follow/"
                       .format(user_id))

    web_address_navigator(browser, user_link_by_id)
    username = get_username(browser, "profile", logger)
    """

    return None


def is_page_available(browser, logger):
    """ Check if the page is available and valid """
    expected_keywords = ["Page Not Found", "Content Unavailable"]
    page_title = get_page_title(browser, logger)

    if any(keyword in page_title for keyword in expected_keywords):
        reload_webpage(browser)
        page_title = get_page_title(browser, logger)

        if any(keyword in page_title for keyword in expected_keywords):
            if "Page Not Found" in page_title:
                logger.warning(
                    "The page isn't available!\t~the link may be broken, "
                    "or the page may have been removed..."
                )

            elif "Content Unavailable" in page_title:
                logger.warning(
                    "The page isn't available!\t~the user may have blocked " "you..."
                )

            return False

    return True


def reload_webpage(browser):
    """ Reload the current webpage """
    browser.execute_script("location.reload()")
    update_activity(browser, state=None)
    sleep(2)

    return True


def get_page_title(browser, logger):
    """ Get the title of the webpage """
    # wait for the current page fully load to get the correct page's title
    explicit_wait(browser, "PFL", [], logger, 10)

    try:
        page_title = browser.title

    except WebDriverException:
        try:
            page_title = browser.execute_script("return document.title")

        except WebDriverException:
            try:
                page_title = browser.execute_script(
                    "return document.getElementsByTagName('title')[0].text"
                )

            except WebDriverException:
                logger.info("Unable to find the title of the page :(")
                return None

    return page_title


def get_action_delay(self, action):
    """ Get the delay time to sleep after doing actions """
    delays = {
        "like": self.settings.action_delays_like,
        "comment": self.settings.action_delays_comment,
        "follow": self.settings.action_delays_follow,
        "unfollow": self.settings.action_delays_unfollow,
        "story": self.settings.action_delays_story
    }

    if not self.settings.action_delays_enabled or action not in delays:
        return 1

    if not self.settings.action_delays_randomize:
        return delays[action]

    return random.uniform(
        delays[action]*self.settings.action_delays_random_range_from,
        delays[action]*self.settings.action_delays_random_range_to)


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


def get_time_until_next_month():
    """ Get total seconds remaining until the next month """
    now = datetime.datetime.now()
    next_month = now.month + 1 if now.month < 12 else 1
    year = now.year if now.month < 12 else now.year + 1
    date_of_next_month = datetime.datetime(year, next_month, 1)

    remaining_seconds = (date_of_next_month - now).total_seconds()

    return remaining_seconds


def remove_extra_spaces(text):
    """ Find and remove redundant spaces more than 1 in text """
    new_text = re.sub(r" {2,}", " ", text)

    return new_text


def has_any_letters(text):
    """ Check if the text has any letters in it """
    # result = re.search("[A-Za-z]", text)   # works only with english letters
    result = any(
        c.isalpha() for c in text
    )  # works with any letters - english or non-english

    return result


def is_follow_me(browser, person=None):
    # navigate to profile page if not already in it
    if person:
        user_link = "https://www.instagram.com/{}/".format(person)
        web_address_navigator(browser, user_link)

    return getUserData("graphql.user.follows_viewer", browser)


def progress_tracker(current_value, highest_value, initial_time, logger):
    """ Provide a progress tracker to keep value updated until finishes """
    if current_value is None or highest_value is None or highest_value == 0:
        return

    try:
        real_time = time()
        progress_percent = int((current_value / highest_value) * 100)

        elapsed_time = real_time - initial_time
        elapsed = (
            "{:.0f} seconds".format(elapsed_time/1000)
            if elapsed_time/1000 < 60
            else "{:.1f} minutes".format(elapsed_time/1000/60)
        )

        eta_time = abs(
            (elapsed_time * 100) / (progress_percent if progress_percent != 0 else 1)
            - elapsed_time
        )
        eta = (
            "{:.0f} seconds".format(eta_time/1000)
            if eta_time/1000 < 60
            else "{:.1f} minutes".format(eta_time/1000/60)
        )

        tracker_line = "-----------------------------------"
        filled_index = int(progress_percent / 2.77)
        progress_container = (
            "[" + tracker_line[:filled_index] + "+" + tracker_line[filled_index:] + "]"
        )
        progress_container = (
            progress_container[: filled_index + 1].replace("-", "=")
            + progress_container[filled_index + 1 :]
        )

        total_message = (
            "\r  {}/{} {}  {}%    "
            "|> Elapsed: {}    "
            "|> ETA: {}      ".format(
                current_value,
                highest_value,
                progress_container,
                progress_percent,
                elapsed,
                eta,
            )
        )

        sys.stdout.write(total_message)
        sys.stdout.flush()

    except Exception as exc:
        logger.info(
            "Error occurred with Progress Tracker:\n{}".format(str(exc).encode("utf-8"))
        )


def close_dialog_box(self):
    """ Click on the close button spec. in the 'Likes' dialog box """
    try:
        close = self.browser.find_element_by_xpath(
            read_xpath("class_selectors", "likes_dialog_close_xpath")
        )
        nf_click_center_of_element(self, close, get_current_url(self.browser))
    except NoSuchElementException:
        pass


def get_cord_location(browser, location):
    base_url = "https://www.instagram.com/explore/locations/"
    query_url = "{}{}{}".format(base_url, location, "?__a=1")
    browser.get(query_url)
    json_text = browser.find_element_by_xpath(
        read_xpath(get_cord_location.__name__, "json_text")
    ).text
    data = json.loads(json_text)

    lat = data["graphql"]["location"]["lat"]
    lon = data["graphql"]["location"]["lng"]

    return lat, lon


def get_bounding_box(
    latitude_in_degrees, longitude_in_degrees, half_side_in_miles, logger
):
    if half_side_in_miles == 0:
        logger.error("Check your Radius its lower then 0")
        return {}
    if latitude_in_degrees < -90.0 or latitude_in_degrees > 90.0:
        logger.error("Check your latitude should be between -90/90")
        return {}
    if longitude_in_degrees < -180.0 or longitude_in_degrees > 180.0:
        logger.error("Check your longtitude should be between -180/180")
        return {}
    half_side_in_km = half_side_in_miles * 1.609344
    lat = radians(latitude_in_degrees)
    lon = radians(longitude_in_degrees)

    radius = 6371
    # Radius of the parallel at given latitude
    parallel_radius = radius * cos(lat)

    lat_min = lat - half_side_in_km / radius
    lat_max = lat + half_side_in_km / radius
    lon_min = lon - half_side_in_km / parallel_radius
    lon_max = lon + half_side_in_km / parallel_radius

    lat_min = rad2deg(lat_min)
    lon_min = rad2deg(lon_min)
    lat_max = rad2deg(lat_max)
    lon_max = rad2deg(lon_max)

    bbox = {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max,
    }

    return bbox


def take_rotative_screenshot(browser, logfolder):
    """
        Make a sequence of screenshots, based on hour:min:secs
    """
    global next_screenshot

    if next_screenshot == 1:
        browser.save_screenshot("{}screenshot_1.png".format(logfolder))
    elif next_screenshot == 2:
        browser.save_screenshot("{}screenshot_2.png".format(logfolder))
    else:
        browser.save_screenshot("{}screenshot_3.png".format(logfolder))
        next_screenshot = 0
        # sum +1 next

    # update next
    next_screenshot += 1


def get_query_hash(browser, logger):
    """ Load Instagram JS file and find query hash code """
    link = "https://www.instagram.com/static/bundles/es6/Consumer.js/1f67555edbd3.js"
    web_address_navigator(browser, link)
    page_source = browser.page_source
    # locate pattern value from JS file
    # sequence of 32 words and/or numbers just before ,n=" value
    hash = re.findall('[a-z0-9]{32}(?=",n=")', page_source)
    if hash:
        return hash[0]
    else:
        logger.warn("Query Hash not found")


def is_mandatory_character(self, uchr):
    if self.aborting:
        return self
    try:
        return self.check_letters[uchr]
    except KeyError:
        return self.check_letters.setdefault(
            uchr,
            any(
                mandatory_char in unicodedata.name(uchr)
                for mandatory_char in self.settings.mandatory_character
            ),
        )


def check_character_set(self, unistr):
    if self.aborting:
        return self
    if not self.settings.mandatory_character:
        return True
    self.check_letters = {}
    return all(
        is_mandatory_character(self, uchr) for uchr in unistr if uchr.isalpha()
    )
