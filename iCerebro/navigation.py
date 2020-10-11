from time import sleep

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException, \
    TimeoutException, MoveTargetOutOfBoundsException, ElementClickInterceptedException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

import iCerebro.constants_x_paths as XP
import iCerebro.constants_js_scripts as JS
from iCerebro.util_loggers import LogDecorator


class SoftBlockedException(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return 'SoftBlockedException: {0} '.format(self.message)
        else:
            return 'SoftBlockedException'


@LogDecorator()
def check_for_error(self):
    try:
        self.browser.execute_script(JS.RELOAD)
        self.quota_supervisor.add_server_call()
        self.browser.find_element_by_xpath(XP.BLOCKED_ERROR)
    except NoSuchElementException:
        return False
    raise SoftBlockedException


@LogDecorator()
def get_current_url(self):
    """ Get URL of the loaded web page """
    try:
        current_url = self.browser.execute_script("return window.location.href")
        self.quota_supervisor.add_server_call()
    except WebDriverException:
        try:
            current_url = self.browser.current_url
        except WebDriverException:
            current_url = None
    return current_url


@LogDecorator()
def web_address_navigator(self, link):
    """Checks and compares current URL of web page and the URL to be
    navigated and if it is different, it does navigate"""
    if link is None:
        return
    current_url = get_current_url(self)
    total_timeouts = 0
    page_type = None  # file or directory

    # remove slashes at the end to compare efficiently
    if current_url is not None and current_url.endswith("/"):
        current_url = current_url[:-1]

    if link.endswith("/"):
        link = link[:-1]
        page_type = "dir"  # slash at the end is a directory

    new_navigation = current_url != link

    if current_url is None or new_navigation:
        check_for_error(self)
        link = link + "/" if page_type == "dir" else link
        while True:
            try:
                self.browser.get(link)
                self.quota_supervisor.add_server_call()
                sleep(2)
                break

            except TimeoutException as exc:
                if total_timeouts >= 7:
                    raise TimeoutException(
                        "Retried {} times to GET '{}' webpage "
                        "but failed out of a timeout!\n\t{}".format(
                            total_timeouts,
                            str(link).encode("utf-8"),
                            str(exc).encode("utf-8"),
                        )
                    )
                total_timeouts += 1
                sleep(2)


@LogDecorator()
def check_if_in_correct_page(
        self,
        desired_link: str
):
    current_url = get_current_url(self)

    if current_url is None:
        return False

    if desired_link is None:
        return True

    # remove slashes at the end to compare efficiently
    if current_url.endswith("/"):
        current_url = current_url[:-1]

    if desired_link.endswith("/"):
        desired_link = desired_link[:-1]

    return current_url == desired_link


@LogDecorator()
def nf_go_to_tag_page(
        self,
        tag: str
):
    """Navigates to the provided tag page by typing it on explore"""

    tag_link = "https://www.instagram.com/explore/tags/{}/".format(tag)
    try:
        nf_type_on_explore(self, "#" + tag)
        sleep(2)
        # click tag
        tag_option = self.browser.find_element_by_xpath(
            '//a[@href="/explore/tags/{}/"]'.format(tag)
        )
        nf_click_center_of_element(self, tag_option, tag_link)
    except NoSuchElementException:
        self.logger.debug("Failed to get a page element")
        check_for_error(self)


@LogDecorator()
def nf_go_to_user_page(
        self,
        username: str
):
    """Navigates to the provided user page by typing its name on explore"""
    user_link = "https://www.instagram.com/{}/".format(username)
    try:
        nf_type_on_explore(self, username)
        sleep(2)
        # click tag
        user_option = self.browser.find_element_by_xpath(
            '//a[@href="/{}/"]'.format(username)
        )
        nf_click_center_of_element(self, user_option, user_link)
    except NoSuchElementException:
        self.logger.debug("Failed to go to get a page element")
        check_for_error(self)


@LogDecorator()
def nf_type_on_explore(
        self,
        text: str
):
    # clicking explore
    explore = self.browser.find_element_by_xpath(
        "/html/body/div[1]/section/nav[2]/div/div/div[2]/div/div/div[2]"
    )
    explore.click()
    self.quota_supervisor.add_server_call()
    sleep(1)
    # typing text
    search_bar = self.browser.find_element_by_xpath(
        "/html/body/div[1]/section/nav[1]/div/header/div/h1/div/div/div/div[1]/label/input"
    )
    search_bar.click()
    self.quota_supervisor.add_server_call()
    search_bar.send_keys(text)
    self.quota_supervisor.add_server_call()


@LogDecorator()
def nf_scroll_into_view(
        self,
        element: WebElement,
        try_n: int = 1
):
    try:
        """Scrolls until desired element is in the center of the screen or as close as it can get"""
        desired_y = (element.size['height'] / 2) + element.location['y']
        window_h = self.browser.execute_script('return window.innerHeight')
        window_y = self.browser.execute_script('return window.pageYOffset')
        current_y = (window_h / 2) + window_y
        scroll_y_by = desired_y - current_y
        # TODO: add random offset and smooth scrolling to appear more natural
        self.browser.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)
        self.quota_supervisor.add_server_call()
    except StaleElementReferenceException:
        self.logger.debug("Stale Element")
        if try_n <= 3:
            self.browser.execute_script(JS.RELOAD)
            self.quota_supervisor.add_server_call()
            nf_scroll_into_view(self, element, try_n + 1)
        else:
            self.loger.debug("Failed to scroll to element")
            check_for_error(self)


@LogDecorator()
def nf_click_center_of_element(
        self,
        element: WebElement,
        desired_link: str = None,
        disable_navigation: bool = False,
        skip_action_chain: bool = False,
        try_n: int = 1
):
    """Moves pointer to center of element and then clicks"""
    if not skip_action_chain:
        try:
            (
                ActionChains(self.browser)
                .move_to_element(element)
                .move_by_offset(
                    element.size['width'] // 2,
                    element.size['height'] // 2,
                )
                .click()
                .perform()
            )
            self.quota_supervisor.add_server_call()
        except MoveTargetOutOfBoundsException:
            pass
        except StaleElementReferenceException:
            self.logger.debug("Stale Element")
            if try_n <= 3:
                self.browser.execute_script(JS.RELOAD)
                self.quota_supervisor.add_server_call()
                nf_click_center_of_element(self, element, desired_link, disable_navigation, skip_action_chain, try_n + 1)
    if desired_link or skip_action_chain:
        try:
            explicit_wait(self, "PFL", [], 7, False)
            if skip_action_chain or not check_if_in_correct_page(self, desired_link):
                try:
                    element.click()
                    self.quota_supervisor.add_server_call()
                    explicit_wait(self, "PFL", [], 7, False)
                except ElementClickInterceptedException:
                    pass
            if not check_if_in_correct_page(self, desired_link):
                self.browser.execute_script("arguments[0].click();", element)
                self.quota_supervisor.add_server_call()
                explicit_wait(self, "PFL", [], 7, False)
            if not check_if_in_correct_page(self, desired_link):
                self.logger.debug("Failed to press element{}".format(
                    ", navigating to desired link" if not disable_navigation else ""))
                if not disable_navigation:
                    web_address_navigator(self, desired_link)
        except StaleElementReferenceException:
            pass
    else:
        sleep(2)


@LogDecorator()
def nf_find_and_press_back(
        self,
        link: str,
        try_n: int = 1
):
    """Finds and press back button"""
    if check_if_in_correct_page(self, link):
        return
    possibles = [
        '/html/body/div[1]/section/nav[1]/div/header//a[@class=" Iazdo"]',
        '/html/body/div[1]/section/nav[1]/div/header//a[@class="Iazdo"]',
        '/html/body/div[1]/section/nav[1]/div/header//a//*[name()="svg"][@class="_8-yf5 "]',
        '/html/body/div[1]/section/nav[1]/div/header//a//*[name()="svg"][@class="_8-yf5"]',
        '/html/body/div[1]/section/nav[1]/div/header//a//*[name()="svg"][@aria-label="Back"]',
        '/html/body/div[1]/section/nav[1]/div/header//a/span/*[name()="svg"][@class="_8-yf5 "]',
        '/html/body/div[1]/section/nav[1]/div/header//a/span/*[name()="svg"][@class="_8-yf5"]',
        '/html/body/div[1]/section/nav[1]/div/header//a/span/*[name()="svg"][@aria-label="Back"]',
    ]
    success = False
    back = None
    for back_path in possibles:
        if not success:
            try:
                back = self.browser.find_element_by_xpath(back_path)
                success = True
                break
            except NoSuchElementException:
                success = False
    if not success:
        self.logger.warning("Failed to get back button with all xpaths")
        check_for_error(self)
    else:
        nf_scroll_into_view(self, back)
        nf_click_center_of_element(self, back, link, disable_navigation=True)
        bad_loading = self.browser.find_elements_by_xpath(
            '/html/body/div[1]/section[@class="_9eogI E3X2T"]/span[@class="BHkOG PID-B"]'
        )
        if bad_loading and try_n <= 3:
            try_n += 1
            nf_find_and_press_back(self, link, try_n)
    if not check_if_in_correct_page(self, link):
        self.logger.debug("Failed to go back, navigating there")
        web_address_navigator(self, link)


@LogDecorator()
def nf_go_from_post_to_profile(
        self,
        username: str
):
    user_link = "https://www.instagram.com/{}/".format(username)
    try:
        username_button = self.browser.find_element_by_xpath(
            '/html/body/div[1]/section/main/div/div/article/header//div[@class="e1e1d"]'
        )
        nf_scroll_into_view(self, username_button)
        nf_click_center_of_element(self, username_button, user_link, False, True)
    except NoSuchElementException:
        self.logger.debug("Failed to get user page button, navigating there")
        web_address_navigator(self, user_link)


@LogDecorator()
def nf_go_to_follow_page(self, which: str, username: str):
    follow_link = "https://www.instagram.com/{}/{}/".format(username, which)
    if check_if_in_correct_page(self, follow_link):
        return
    try:
        follow_which_button = self.browser.find_element_by_xpath(
            '//a[@href="/{}/{}/"]'.format(username, which)
        )
        nf_scroll_into_view(self, follow_which_button)
        nf_click_center_of_element(self, follow_which_button, follow_link)
    except NoSuchElementException:
        self.logger.debug("Failed to get {} page button, navigating there".format(which))
        web_address_navigator(self, follow_link)


@LogDecorator()
def nf_go_to_home(self):
    home_link = "https://www.instagram.com/"
    if check_if_in_correct_page(self, home_link):
        return
    try:
        home_button = self.browser.find_element_by_xpath('//a[@href="/"]')
        nf_click_center_of_element(self, home_button, home_link)
    except NoSuchElementException:
        self.logger.debug("Failed to get home button, navigating there")
        web_address_navigator(self, home_link)


@LogDecorator()
def go_to_bot_user_page(self):
    # TODO: click self user page button
    nf_go_to_user_page(self, self.username)


@LogDecorator()
def explicit_wait(self, track, ec_params, timeout=35, notify=True):
    """
    Explicitly wait until expected condition validates

    :param self: iCerebro instance
    :param track: short name of the expected condition
    :param ec_params: expected condition specific parameters - [param1, param2]
    :param timeout:
    :param notify:

    list of expected condition:
        <https://seleniumhq.github.io/selenium/docs/api/py/webdriver_support/selenium.webdriver.support.expected_conditions.html>
    """

    VOEL = "VOEL"
    TC = "TC"
    PFL = "PFL"
    SO = "SO"
    tracks = {VOEL, TC, PFL, SO}
    if track not in tracks:
        raise ValueError(
            "explicit_wait: track must be one of %r." % tracks)

    if not isinstance(ec_params, list):
        ec_params = [ec_params]

    # find condition according to the tracks
    if track == VOEL:
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
    elif track == TC:
        expect_in_title = ec_params[0]
        ec_name = "title contains '{}' string".format(expect_in_title)
        condition = ec.title_contains(expect_in_title)
    elif track == PFL:
        ec_name = "page fully loaded"
        condition = lambda browser: browser.execute_script(
            "return document.readyState"
        ) in ["complete" or "loaded"]
    elif track == SO:
        ec_name = "staleness of"
        element = ec_params[0]

        condition = ec.staleness_of(element)
    else:
        return False

    # generic wait block
    try:
        wait = WebDriverWait(self.browser, timeout)
        result = wait.until(condition)
    except TimeoutException:
        if notify is True:
            self.logger.info(
                "Timed out with failure while explicitly waiting until {}".format(ec_name)
            )
        return False
    return result
