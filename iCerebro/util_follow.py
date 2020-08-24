import random
from time import sleep
from typing import Union
from typing import Tuple

from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotVisibleException

import iCerebro.constants_x_paths as XP
import iCerebro.constants_js_scripts as JS
from iCerebro.util_loggers import LogDecorator
from iCerebro.navigation import nf_go_to_user_page, nf_scroll_into_view, explicit_wait
from iCerebro.navigation import check_if_in_correct_page
from iCerebro.navigation import nf_click_center_of_element
from iCerebro.util import is_page_available
from iCerebro.util import emergency_exit
from iCerebro.util_db import add_user_to_blacklist
from iCerebro.util_db import add_follow_times


@LogDecorator()
def unfollow_loop(
        self,
        unfollow_list: list,
        amount: int
):
    """ Unfollow the given amount of users"""
    unfollowed = 0
    try:
        skip_set = set(
            self.settings.dont_include
        ).union(
            set(self.settings.white_list)
        ).union(
            set(self.active_users)
        )
        sleep_counter = 0
        sleep_after = random.randint(8, 12)
        for person in unfollow_list:
            if unfollowed >= amount:
                break

            if self.jumps.check_unfollows():
                self.logger.warning(
                    "Unfollow quotient reached its peak, leaving Unfollow Users activity")
                self.jumps.unfollows = 0
                break

            if sleep_counter >= sleep_after:
                delay_random = random.randint(400, 600)
                self.logger.info(
                    "Unfollowed {} users, sleeping {} minutes and {} seconds".format(
                        sleep_counter,
                        int(delay_random/60),
                        delay_random % 60
                        )
                )
                sleep(delay_random)
                sleep_counter = 0
                sleep_after = random.randint(8, 12)
                pass

            if person not in skip_set:
                self.logger.info(
                    "Unfollow [{}/{}]: now unfollowing '{}'...".format(
                        unfollowed + 1, amount, person.encode("utf-8"))
                )
                nf_go_to_user_page(self, person)
                if is_page_available(self):
                    try:
                        unfollow_state, msg = unfollow(
                            self,
                            "profile",
                            person,
                            None,
                        )
                    except BaseException as e:
                        self.logger.error("Unfollow loop error:  {}\n".format(str(e)))
                        continue

                    if unfollow_state is True:
                        unfollowed += 1
                        sleep_counter += 1
                        # reset jump counter after a successful unfollow
                        self.jumps.unfollows = 0

                    elif msg == "jumped":
                        # will break the loop after certain consecutive jumps
                        self.jumps.unfollows += 1

                    elif msg in ["temporary block", "not connected", "not logged in"]:
                        # break the loop in extreme conditions to prevent
                        # misbehaviour
                        self.logger.warning(
                            "There is a serious issue: '{}'!\t~leaving "
                            "Unfollow Users activity".format(msg)
                        )
                        break
    except BaseException as e:
        self.logger.error("Unfollow loop error:  {}\n".format(str(e)))

    return unfollowed


@LogDecorator()
def unfollow(
        self,
        track: str,
        person: str,
        button: Union[WebElement, None]
):
    """ Unfollow a user either from the profile or post page or dialog box """
    # list of available tracks to unfollow in: ["profile", "post" "dialog]
    # check action availability
    if self.quota_supervisor.jump_unfollow():
        return False, "jumped"

    if track in ["profile", "post"]:
        # Method of unfollowing from a user's profile page or post page
        if track == "profile":
            user_link = "https://www.instagram.com/{}/".format(person)
            if not check_if_in_correct_page(self, user_link):
                nf_go_to_user_page(self, person)

        for _ in range(3):
            following_status, follow_button = get_following_status(self, track, person)
            if following_status in ["Following", "Requested"]:
                nf_click_center_of_element(self, follow_button)
                sleep(3)
                confirm_unfollow(self.browser)
                sleep(1)
                following_status, follow_button = get_following_status(self, track, person)
                if following_status in ["Follow", "Follow Back"]:
                    break
            elif following_status in ["Follow", "Follow Back"]:
                self.logger.info(
                    "Already unfollowed '{}' or is a private user that "
                    "rejected your request".format(person)
                )
                return False, "already unfollowed"
            elif following_status == "Unblock":
                self.logger.warning("Couldn't unfollow '{}', is blocked".format(person))
                return False, "blocked"
            elif following_status == "UNAVAILABLE":
                self.logger.warning("Couldn't unfollow '{}', is unavailable".format(person))
                return False, "unavailable"
            elif following_status is None:
                sirens_wailing, emergency_state = emergency_exit(self)
                if sirens_wailing is True:
                    return False, emergency_state
            else:
                self.logger.warning(
                    "Couldn't unfollow '{}', unexpected failure".format(person)
                )
                return False, "unexpected failure"
    elif track == "dialog" and button is not None:
        # Method of unfollowing from a dialog box
        nf_click_center_of_element(self, button)
        sleep(4)
        confirm_unfollow(self)

    self.logger.info("Unfollowed '{}'".format(person))
    self.quota_supervisor.add_unfollow()
    return True, "success"


@LogDecorator()
def get_following_status(
        self,
        track: str,
        person: str
) -> Tuple[str, Union[WebElement, None]]:  # following_status, follow_button
    """ Verify if you are following the user in the loaded page """
    if person == self.username:
        return "OWNER", None

    if track == "profile":
        user_link = "https://www.instagram.com/{}/".format(person)
        if not check_if_in_correct_page(self, user_link):
            nf_go_to_user_page(self, person)

    # check if the page is available
    valid_page = is_page_available(self)
    if not valid_page:
        self.logger.error(
            "Couldn't access the profile page of '{}', might have changed the"
            " username".format(person)
        )
        return "UNAVAILABLE", None
    # wait until the follow button is located and visible, then get it
    try:
        self.browser.find_element_by_xpath(XP.FOLLOW_BUTTON_XP)
    except NoSuchElementException:
        try:
            follow_button = self.browser.find_element_by_xpath(XP.FOLLOW_SPAN_XP_FOLLOWING)
            return "Following", follow_button
        except:
            return "UNAVAILABLE", None

    follow_button = explicit_wait(self, "VOEL", [XP.FOLLOW_BUTTON_XP, "XPath"], 7, False)

    if not follow_button:
        self.browser.execute_script(JS.RELOAD)
        self.quota_supervisor.add_server_call()
        follow_button = explicit_wait(self, "VOEL", [XP.FOLLOW_BUTTON_XP, "XPath"], 7, False)
        if not follow_button:
            # cannot find the any of the expected buttons
            self.logger.error(
                "Unable to detect the following status of '{}'".format(person.encode("utf-8"))
            )
            return "UNAVAILABLE", None

    # get follow status
    following_status = follow_button.text
    return following_status, follow_button


@LogDecorator()
def confirm_unfollow(self):
    """ Deal with the confirmation dialog boxes during an unfollow """
    attempt = 0
    while attempt < 3:
        try:
            attempt += 1
            unfollow_button = self.browser.find_element_by_xpath(XP.BUTTON_XP)
            if unfollow_button.is_displayed():
                nf_click_center_of_element(self, unfollow_button)
                sleep(2)
                break
        except (ElementNotVisibleException, NoSuchElementException) as exc:
            # prob confirm dialog didn't pop up
            if isinstance(exc, ElementNotVisibleException):
                break
            elif isinstance(exc, NoSuchElementException):
                sleep(1)


@LogDecorator()
def follow_user(
        self,
        track: str,
        user_name: str,
        button: Union[WebElement, None] = None
) -> Tuple[bool, str]:  # follow_state, msg
    """ Follow a user either from the profile page or post page or dialog
    box """
    # list of available tracks to follow in: ["profile", "post" "dialog"]

    # check action availability
    if self.quota_supervisor.jump_follow():
        return False, "jumped"

    if track in ["profile", "post"]:
        if track == "profile":
            # check URL of the webpage, if it already is user's profile
            # page, then do not navigate to it again
            user_link = "https://www.instagram.com/{}/".format(user_name)
            if not check_if_in_correct_page(self, user_link):
                nf_go_to_user_page(self, user_name)

        # find out CURRENT following status
        for _ in range(3):
            following_status, follow_button = get_following_status(self, track, user_name)
            if following_status in ["Follow", "Follow Back"]:
                nf_scroll_into_view(self, follow_button)
                nf_click_center_of_element(self, follow_button)
                sleep(3)
                following_status, follow_button = get_following_status(self, track, user_name)
                if following_status in ["Following", "Requested"]:
                    break
            elif following_status == "Following":
                self.logger.info("Already following '{}'".format(user_name))
                return False, "already followed"
            elif following_status == "Requested":
                self.logger.info("Already requested '{}' to follow".format(user_name))
                return False, "already requested"
            elif following_status == "Unblock":
                self.logger.info("User '{}' is blocked".format(user_name))
                return False, "user is blocked"
            elif following_status == "UNAVAILABLE":
                self.logger.info("User '{}' is inaccessible".format(user_name))
                return False, "user is inaccessible"
            elif following_status is None:
                sirens_wailing, emergency_state = emergency_exit(self)
                if sirens_wailing is True:
                    return False, emergency_state
            else:
                self.logger.warning(
                    "Couldn't unfollow '{}', unexpected failure".format(user_name)
                )
                return False, "unexpected failure"
    elif track == "dialog":
        nf_click_center_of_element(self, button)

    # general tasks after a successful follow
    self.logger.info("Followed '{}".format(user_name.encode("utf-8")))
    add_follow_times(self, user_name)
    add_user_to_blacklist(self, user_name, self.quota_supervisor.FOLLOW)
    self.quota_supervisor.add_follow()
    return True, "success"


@LogDecorator()
def get_followers(
        self,
        username: str
) -> list:  # list of followers of given username
    # TODO
    return []












#
#
# def scroll_to_bottom_of_followers_list(browser):
#     browser.execute_script("window.scrollTo(0, document.body.scrollHeight)")
#     return
#
#
# def get_users_through_dialog_with_graphql(
#     browser,
#     login,
#     user_name,
#     amount,
#     users_count,
#     randomize,
#     dont_include,
#     blacklist,
#     follow_times,
#     simulation,
#     channel,
#     jumps,
#     logger,
#     logfolder,
# ):
#
#     # TODO: simulation implmentation
#
#     real_amount = amount
#     if randomize and amount >= 3:
#         # expanding the population for better sampling distribution
#         amount = amount * 1.9
#     try:
#         user_id = browser.execute_script(
#             "return window.__additionalData[Object.keys(window.__additionalData)[0]].data.graphql.user.id"
#         )
#     except WebDriverException:
#         user_id = browser.execute_script(
#             "return window._sharedData." "entry_data.ProfilePage[0]." "graphql.user.id"
#         )
#
#     query_hash = get_query_hash(browser, logger)
#     # check if hash is present
#     if query_hash is None:
#         logger.info("Unable to locate GraphQL query hash")
#
#     graphql_query_URL = "view-source:https://www.instagram.com/graphql/query/?query_hash={}".format(
#         query_hash
#     )
#     variables = {
#         "id": str(user_id),
#         "include_reel": "true",
#         "fetch_mutual": "true",
#         "first": 50,
#     }
#     url = "{}&variables={}".format(graphql_query_URL, str(json.dumps(variables)))
#
#     web_address_navigator(browser, url)
#
#     pre = browser.find_element_by_tag_name("pre")
#     # set JSON object
#     data = json.loads(pre.text)
#     # get all followers of current page
#     followers_page = data["data"]["user"]["edge_followed_by"]["edges"]
#     followers_list = []
#
#     # iterate over page size and add users to the list
#     for follower in followers_page:
#         # get follower name
#         followers_list.append(follower["node"]["username"])
#
#     has_next_page = data["data"]["user"]["edge_followed_by"]["page_info"][
#         "has_next_page"
#     ]
#
#     while has_next_page and len(followers_list) <= amount:
#         # server call interval
#         sleep(random.randint(2, 6))
#
#         # get next page reference
#         end_cursor = data["data"]["user"]["edge_followed_by"]["page_info"]["end_cursor"]
#
#         # url variables
#         variables = {
#             "id": str(user_id),
#             "include_reel": "true",
#             "fetch_mutual": "true",
#             "first": 50,
#             "after": end_cursor,
#         }
#         url = "{}&variables={}".format(graphql_query_URL, str(json.dumps(variables)))
#         browser.get("view-source:{}".format(url))
#         pre = browser.find_element_by_tag_name("pre")
#         # response to JSON object
#         data = json.loads(pre.text)
#
#         # get all followers of current page
#         followers_page = data["data"]["user"]["edge_followed_by"]["edges"]
#         # iterate over page size and add users to the list
#         for follower in followers_page:
#             # get follower name
#             followers_list.append(follower["node"]["username"])
#
#         # check if there is next page
#         has_next_page = data["data"]["user"]["edge_followed_by"]["page_info"][
#             "has_next_page"
#         ]
#
#         # simulation
#         # TODO: this needs to be rewrited
#         # if (
#         #     simulation["enabled"] is True
#         #     and simulation["percentage"] >= random.randint(1, 100)
#         #     and (
#         #         simulator_counter > random.randint(5, 17)
#         #         or abort is True
#         #         or total_list >= amount
#         #         or sc_rolled == random.randint(3, 5)
#         #     )
#         #     and len(buttons) > 0
#         # ):
#
#         #     quick_amount = 1 if not total_list >= amount else random.randint(1, 4)
#
#         #     for i in range(0, quick_amount):
#         #         quick_index = random.randint(0, len(buttons) - 1)
#         #         quick_button = buttons[quick_index]
#         #         quick_username = dialog_username_extractor(quick_button)
#
#         #         if quick_username and quick_username[0] not in simulated_list:
#         #             if not pts_printed:
#         #                 if total_list >= amount:
#         #                     pts_printed = True
#
#         #             logger.info("Simulated follow : {}".format(len(simulated_list) + 1))
#
#         #             quick_follow = follow_through_dialog(
#         #                 browser,
#         #                 login,
#         #                 quick_username,
#         #                 quick_button,
#         #                 quick_amount,
#         #                 dont_include,
#         #                 blacklist,
#         #                 follow_times,
#         #                 jumps,
#         #                 logger,
#         #                 logfolder,
#         #             )
#         #             if (quick_amount == 1 or i != (quick_amount - 1)) and (
#         #                 not pts_printed or not abort
#         #             ):
#         #                 simulated_list.extend(quick_follow)
#
#         #     simulator_counter = 0
#
#     # shuffle it if randomize is enable
#     if randomize:
#         random.shuffle(followers_list)
#
#     # get real amount
#     followers_list = random.sample(followers_list, real_amount)
#     print(followers_list)
#     return followers_list, []
#
#
# def dialog_username_extractor(buttons):
#     """ Extract username of a follow button from a dialog box """
#
#     if not isinstance(buttons, list):
#         buttons = [buttons]
#
#     person_list = []
#     for person in buttons:
#         if person and hasattr(person, "text") and person.text:
#             try:
#                 xpath = read_xpath(dialog_username_extractor.__name__, "person")
#                 element_by_xpath = person.find_element_by_xpath(xpath)
#                 elements_by_tag_name = element_by_xpath.find_elements_by_tag_name("a")[
#                     0
#                 ].text
#
#                 if elements_by_tag_name == "":
#                     elements_by_tag_name = element_by_xpath.find_elements_by_tag_name(
#                         "a"
#                     )[1].text
#
#                 person_list.append(elements_by_tag_name)
#             except IndexError:
#                 print("how many?")
#                 pass  # Element list is too short to have a [1] element
#
#     return person_list
#
#
# def follow_through_dialog(
#     browser,
#     login,
#     person_list,
#     buttons,
#     amount,
#     dont_include,
#     blacklist,
#     follow_times,
#     jumps,
#     logger,
#     logfolder,
# ):
#     """ Will follow username directly inside a dialog box """
#     if not isinstance(person_list, list):
#         person_list = [person_list]
#
#     if not isinstance(buttons, list):
#         buttons = [buttons]
#
#     person_followed = []
#     followNum = 0
#
#     try:
#         for person, button in zip(person_list, buttons):
#             if followNum >= amount:
#                 logger.info("--> Total follow number reached: {}".format(followNum))
#                 break
#
#             elif jumps["consequent"]["follows"] >= jumps["limit"]["follows"]:
#                 logger.warning(
#                     "--> Follow quotient reached its peak!\t~leaving "
#                     "Follow-Through-Dialog activity\n"
#                 )
#                 break
#
#             if person not in dont_include and not follow_restriction(
#                 "read", person, follow_times, logger
#             ):
#                 follow_state, msg = follow_user(
#                     browser,
#                     "dialog",
#                     login,
#                     person,
#                     button,
#                     blacklist,
#                     logger,
#                     logfolder,
#                 )
#                 if follow_state is True:
#                     # register this session's followed user for further
#                     # interaction
#                     person_followed.append(person)
#                     followNum += 1
#                     # reset jump counter after a successful follow
#                     jumps["consequent"]["follows"] = 0
#
#                 elif msg == "jumped":
#                     # will break the loop after certain consecutive jumps
#                     jumps["consequent"]["follows"] += 1
#
#             else:
#                 logger.info("Not followed '{}'  ~inappropriate user".format(person))
#
#     except BaseException as e:
#         logger.error(
#             "Error occurred while following through dialog box:\n{}".format(str(e))
#         )
#
#     return person_followed
#
#
# def get_given_user_followers(
#     browser,
#     login,
#     user_name,
#     amount,
#     dont_include,
#     randomize,
#     blacklist,
#     follow_times,
#     simulation,
#     jumps,
#     logger,
#     logfolder,
# ):
#     """
#     For the given username, follow their followers.
#
#     :param browser: webdriver instance
#     :param login:
#     :param user_name: given username of account to follow
#     :param amount: the number of followers to follow
#     :param dont_include: ignore these usernames
#     :param randomize: randomly select from users' followers
#     :param blacklist:
#     :param follow_times:
#     :param logger: the logger instance
#     :param logfolder: the logger folder
#     :return: list of user's followers also followed
#     """
#     user_name = user_name.strip().lower()
#
#     user_link = "https://www.instagram.com/{}/".format(user_name)
#     web_address_navigator(browser, user_link)
#
#     if not is_page_available(browser, logger):
#         return [], []
#
#     # check how many people are following this user.
#     allfollowers, _ = get_relationship_counts(browser, user_name, logger)
#
#     # skip early for no followers
#     if not allfollowers:
#         logger.info("'{}' has no followers".format(user_name))
#         return [], []
#
#     elif allfollowers < amount:
#         logger.warning(
#             "'{}' has less followers- {}, than the given amount of {}".format(
#                 user_name, allfollowers, amount
#             )
#         )
#
#     # locate element to user's followers
#     try:
#         followers_link = browser.find_element_by_xpath(
#             read_xpath(get_given_user_followers.__name__, "followers_link")
#         )
#         click_element(browser, followers_link)
#         # update server calls
#         update_activity(browser, state=None)
#
#     except NoSuchElementException:
#         logger.error("Could not find followers' link for {}".format(user_name))
#         return [], []
#
#     except BaseException as e:
#         logger.error("`followers_link` error {}".format(str(e)))
#         return [], []
#
#     channel = "Follow"
#     person_list, simulated_list = get_users_through_dialog_with_graphql(
#         browser,
#         login,
#         user_name,
#         amount,
#         allfollowers,
#         randomize,
#         dont_include,
#         blacklist,
#         follow_times,
#         simulation,
#         channel,
#         jumps,
#         logger,
#         logfolder,
#     )
#
#     return person_list, simulated_list
#
#
# def get_given_user_following(
#     browser,
#     login,
#     user_name,
#     amount,
#     dont_include,
#     randomize,
#     blacklist,
#     follow_times,
#     simulation,
#     jumps,
#     logger,
#     logfolder,
# ):
#     user_name = user_name.strip().lower()
#
#     user_link = "https://www.instagram.com/{}/".format(user_name)
#     web_address_navigator(browser, user_link)
#
#     if not is_page_available(browser, logger):
#         return [], []
#
#     #  check how many poeple are following this user.
#     #  throw RuntimeWarning if we are 0 people following this user
#     try:
#         # allfollowing = format_number(
#         #    browser.find_element_by_xpath(read_xpath(get_given_user_following.__name__,"all_following")).text)
#         allfollowing = format_number(
#             browser.find_element_by_xpath(
#                 read_xpath(get_given_user_following.__name__, "all_following")
#             ).text
#         )
#
#     except NoSuchElementException:
#         try:
#             allfollowing = browser.execute_script(
#                 "return window.__additionalData[Object.keys(window.__additionalData)[0]].data."
#                 "graphql.user.edge_follow.count"
#             )
#
#         except WebDriverException:
#             try:
#                 browser.execute_script("location.reload()")
#                 update_activity(browser, state=None)
#
#                 allfollowing = browser.execute_script(
#                     "return window._sharedData."
#                     "entry_data.ProfilePage[0]."
#                     "graphql.user.edge_follow.count"
#                 )
#
#             except WebDriverException:
#                 try:
#                     topCount_elements = browser.find_elements_by_xpath(
#                         read_xpath(
#                             get_given_user_following.__name__, "topCount_elements"
#                         )
#                     )
#
#                     if topCount_elements:
#                         allfollowing = format_number(topCount_elements[2].text)
#                     else:
#                         logger.info(
#                             "Failed to get following count of '{}'  ~empty "
#                             "list".format(user_name)
#                         )
#                         allfollowing = None
#
#                 except (NoSuchElementException, IndexError):
#                     logger.error(
#                         "\nError occured during getting the following count "
#                         "of '{}'\n".format(user_name)
#                     )
#                     return [], []
#
#     # skip early for no followers
#     if not allfollowing:
#         logger.info("'{}' has no any following".format(user_name))
#         return [], []
#
#     elif allfollowing < amount:
#         logger.warning(
#             "'{}' has less following- {} than the desired amount of {}".format(
#                 user_name, allfollowing, amount
#             )
#         )
#
#     try:
#         following_link = browser.find_elements_by_xpath(
#             read_xpath(get_given_user_following.__name__, "following_link").format(
#                 user_name
#             )
#         )
#         click_element(browser, following_link[0])
#         # update server calls
#         update_activity(browser, state=None)
#
#     except NoSuchElementException:
#         logger.error("Could not find following's link for {}".format(user_name))
#         return [], []
#
#     except BaseException as e:
#         logger.error("`following_link` error {}".format(str(e)))
#         return [], []
#
#     channel = "Follow"
#     person_list, simulated_list = get_users_through_dialog_with_graphql(
#         browser,
#         login,
#         user_name,
#         amount,
#         allfollowing,
#         randomize,
#         dont_include,
#         blacklist,
#         follow_times,
#         simulation,
#         channel,
#         jumps,
#         logger,
#         logfolder,
#     )
#
#     return person_list, simulated_list
#
#
# def dump_follow_restriction(profile_name, logger, logfolder):
#     """ Dump follow restriction data to a local human-readable JSON """
#
#     try:
#         # get a DB and start a connection
#         db, id = get_database()
#         conn = sqlite3.connect(db)
#
#         with conn:
#             conn.row_factory = sqlite3.Row
#             cur = conn.cursor()
#
#             cur.execute(
#                 "SELECT * FROM followRestriction WHERE profile_id=:var", {"var": id}
#             )
#             data = cur.fetchall()
#
#         if data:
#             # get the existing data
#             filename = "{}followRestriction.json".format(logfolder)
#             if os.path.isfile(filename):
#                 with open(filename) as followResFile:
#                     current_data = json.load(followResFile)
#             else:
#                 current_data = {}
#
#             # pack the new data
#             follow_data = {user_data[1]: user_data[2] for user_data in data or []}
#             current_data[profile_name] = follow_data
#
#             # dump the fresh follow data to a local human readable JSON
#             with open(filename, "w") as followResFile:
#                 json.dump(current_data, followResFile)
#
#     except Exception as exc:
#         logger.error(
#             "Pow! Error occurred while dumping follow restriction data to a "
#             "local JSON:\n\t{}".format(str(exc).encode("utf-8"))
#         )
#
#     finally:
#         if conn:
#             # close the open connection
#             conn.close()
#
#
# def follow_restriction(operation, username, limit, logger):
#     """ Keep track of the followed users and help avoid excessive follow of
#     the same user """
#
#     try:
#         # get a DB and start a connection
#         db, profile_id = get_database()
#         conn = sqlite3.connect(db)
#
#         with conn:
#             conn.row_factory = sqlite3.Row
#             cur = conn.cursor()
#
#             cur.execute(
#                 "SELECT * FROM followRestriction WHERE profile_id=:id_var "
#                 "AND username=:name_var",
#                 {"id_var": profile_id, "name_var": username},
#             )
#             data = cur.fetchone()
#             follow_data = dict(data) if data else None
#
#             if operation == "write":
#                 if follow_data is None:
#                     # write a new record
#                     cur.execute(
#                         "INSERT INTO followRestriction (profile_id, "
#                         "username, times) VALUES (?, ?, ?)",
#                         (profile_id, username, 1),
#                     )
#                 else:
#                     # update the existing record
#                     follow_data["times"] += 1
#                     sql = (
#                         "UPDATE followRestriction set times = ? WHERE "
#                         "profile_id=? AND username = ?"
#                     )
#                     cur.execute(sql, (follow_data["times"], profile_id, username))
#
#                 # commit the latest changes
#                 conn.commit()
#
#             elif operation == "read":
#                 if follow_data is None:
#                     return False
#
#                 elif follow_data["times"] < limit:
#                     return False
#
#                 else:
#                     exceed_msg = "" if follow_data["times"] == limit else "more than "
#                     logger.info(
#                         "---> {} has already been followed {}{} times".format(
#                             username, exceed_msg, str(limit)
#                         )
#                     )
#                     return True
#
#     except Exception as exc:
#         logger.error(
#             "Dap! Error occurred with follow Restriction:\n\t{}".format(
#                 str(exc).encode("utf-8")
#             )
#         )
#
#     finally:
#         if conn:
#             # close the open connection
#             conn.close()
#
#
# def get_buttons_from_dialog(dialog, channel):
#     """ Gets buttons from the `Followers` or `Following` dialog boxes"""
#
#     if channel == "Follow":
#         # get follow buttons. This approach will find the follow buttons and
#         # ignore the Unfollow/Requested buttons.
#         buttons = dialog.find_elements_by_xpath(
#             read_xpath(get_buttons_from_dialog.__name__, "follow_button")
#         )
#
#     elif channel == "Unfollow":
#         buttons = dialog.find_elements_by_xpath(
#             read_xpath(get_buttons_from_dialog.__name__, "unfollow_button")
#         )
#
#     return buttons
#
#
# def get_user_id(browser, track, username, logger):
#     """ Get user's ID either from a profile page or post page """
#     user_id = "unknown"
#
#     if track != "dialog":  # currently do not get the user ID for follows
#         # from 'dialog'
#         user_id = find_user_id(browser, track, username, logger)
#
#     return user_id
#
#
# def verify_username_by_id(browser, username, person, person_id, logger, logfolder):
#     """ Check if the given user has changed username after the time of
#     followed """
#     # try to find the user by ID
#     if person_id is None:
#         person_id = load_user_id(username, person, logger, logfolder)
#
#     if person_id and person_id not in [None, "unknown", "undefined"]:
#         # get the [new] username of the user from the stored user ID
#         person_new = get_username_from_id(browser, person_id, logger)
#         if person_new:
#             if person_new != person:
#                 logger.info(
#                     "User '{}' has changed username and now is called '{}' :S".format(
#                         person, person_new
#                     )
#                 )
#             return person_new
#
#         else:
#             logger.info("The user with the ID of '{}' is unreachable".format(person))
#
#     else:
#         logger.info("The user ID of '{}' doesn't exist in local records".format(person))
#
#     return None
#
#
# def verify_action(
#     browser, action, track, username, person, person_id, logger, logfolder
# ):
#     """ Verify if the action has succeeded """
#     # currently supported actions are follow & unfollow
#
#     retry_count = 0
#
#     if action in ["follow", "unfollow"]:
#
#         # assuming button_change testing is relevant to those actions only
#         button_change = False
#
#         if action == "follow":
#             post_action_text_correct = ["Following", "Requested"]
#             post_action_text_fail = ["Follow", "Follow Back", "Unblock"]
#
#         elif action == "unfollow":
#             post_action_text_correct = ["Follow", "Follow Back", "Unblock"]
#             post_action_text_fail = ["Following", "Requested"]
#
#         while True:
#
#             # count retries at beginning
#             retry_count += 1
#
#             # find out CURRENT follow status (this is safe as the follow button is before others)
#             following_status, follow_button = get_following_status(
#                 browser, track, username, person, person_id, logger, logfolder
#             )
#             if following_status in post_action_text_correct:
#                 button_change = True
#             elif following_status in post_action_text_fail:
#                 button_change = False
#             else:
#                 logger.error(
#                     "Hey! Last {} is not verified out of an unexpected "
#                     "failure!".format(action)
#                 )
#                 return False, "unexpected"
#
#             if button_change:
#                 break
#             else:
#                 if retry_count == 1:
#                     reload_webpage(browser)
#                     sleep(4)
#
#                 elif retry_count == 2:
#                     # handle it!
#                     # try to do the action one more time!
#                     click_visibly(browser, follow_button)
#
#                     if action == "unfollow":
#                         confirm_unfollow(browser)
#
#                     sleep(4)
#                 elif retry_count == 3:
#                     logger.warning(
#                         "Last {0} is not verified."
#                         "\t~'{1}' might be temporarily blocked "
#                         "from {0}ing\n".format(action, username)
#                     )
#                     sleep(210)
#                     return False, "temporary block"
#
#         logger.info("Last {} is verified after reloading the page!".format(action))
#
#     return True, "success"
#
#
# def post_unfollow_actions(browser, person, logger):
#     pass
#
#
# def get_follow_requests(browser, amount, sleep_delay, logger, logfolder):
#     """ Get follow requests from instagram access tool list """
#
#     user_link = (
#         "https://www.instagram.com/accounts/access_tool" "/current_follow_requests"
#     )
#     web_address_navigator(browser, user_link)
#
#     list_of_users = []
#     view_more_button_exist = True
#     view_more_clicks = 0
#
#     while (
#         len(list_of_users) < amount
#         and view_more_clicks < 750
#         and view_more_button_exist
#     ):
#         sleep(4)
#         list_of_users = browser.find_elements_by_xpath(
#             read_xpath(get_follow_requests.__name__, "list_of_users")
#         )
#
#         if len(list_of_users) == 0:
#             logger.info("There are not outgoing follow requests")
#             break
#
#         try:
#             view_more_button = browser.find_element_by_xpath(
#                 read_xpath(get_follow_requests.__name__, "view_more_button")
#             )
#         except NoSuchElementException:
#             view_more_button_exist = False
#
#         if view_more_button_exist:
#             logger.info(
#                 "Found '{}' outgoing follow requests, Going to ask for more...".format(
#                     len(list_of_users)
#                 )
#             )
#             click_element(browser, view_more_button)
#             view_more_clicks += 1
#
#     users_to_unfollow = []
#
#     for user in list_of_users:
#         users_to_unfollow.append(user.text)
#         if len(users_to_unfollow) == amount:
#             break
#
#     logger.info(
#         "Found '{}' outgoing follow requests '{}'".format(
#             len(users_to_unfollow), users_to_unfollow
#         )
#     )
#
#     return users_to_unfollow
#
#
# def set_followback_in_pool(username, person, person_id, logtime, logger, logfolder):
#     # first we delete the user from pool
#     delete_line_from_file(
#         "{0}{1}_followedPool.csv".format(logfolder, username), person, logger
#     )
#
#     # return the username with new timestamp
#     log_followed_pool(username, person, logger, logfolder, logtime, person_id)
#
#
# def refresh_follow_time_in_pool(
#     username, person, person_id, extra_secs, logger, logfolder
# ):
#     # set the new time to now plus extra delay
#     logtime = (datetime.now() + timedelta(seconds=extra_secs)).strftime(
#         "%Y-%m-%d %H:%M"
#     )
#
#     # first we delete the user from pool
#     delete_line_from_file(
#         "{0}{1}_followedPool.csv".format(logfolder, username), person, logger
#     )
#
#     # return the username with new timestamp
#     log_followed_pool(username, person, logger, logfolder, logtime, person_id)
