from time import sleep

from instapy.util import web_address_navigator, get_current_url
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webelement import WebElement


def check_if_in_correct_page(
        self,
        desired_link: str
):
    current_url = get_current_url(self.browser)

    if current_url is None or desired_link is None:
        return False

    # remove slashes at the end to compare efficiently
    if current_url.endswith("/"):
        current_url = current_url[:-1]

    if desired_link.endswith("/"):
        desired_link = desired_link[:-1]

    return current_url == desired_link


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
        self.logger.warning("Failed to get a page element")


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
        self.logger.warning("Failed to go to get a page element")


def nf_type_on_explore(
        self,
        text: str
):
    # clicking explore
    explore = self.browser.find_element_by_xpath(
        "/html/body/div[1]/section/nav[2]/div/div/div[2]/div/div/div[2]"
    )
    explore.click()
    sleep(1)
    # typing text
    search_bar = self.browser.find_element_by_xpath(
        "/html/body/div[1]/section/nav[1]/div/header/div/h1/div/div/div/div[1]/label/input"
    )
    search_bar.click()
    search_bar.send_keys(text)


def nf_scroll_into_view(
        self,
        element: WebElement
):
    """Scrolls until desired element is in the center of the screen or as close as it can get"""
    desired_y = (element.size['height'] / 2) + element.location['y']
    window_h = self.browser.execute_script('return window.innerHeight')
    window_y = self.browser.execute_script('return window.pageYOffset')
    current_y = (window_h / 2) + window_y
    scroll_y_by = desired_y - current_y
    # TODO: add random offset and smooth scrolling to appear more natural
    self.browser.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)


def nf_click_center_of_element(
        self,
        element: WebElement,
        desired_link: str
):
    """Moves pointer to center of element and then clicks"""
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
    try:
        sleep(1)
        if not check_if_in_correct_page(self, desired_link):
            self.browser.execute_script("arguments[0].click();", element)
        sleep(1)
        if not check_if_in_correct_page(self, desired_link):
            self.logger.warning("Failed to press element, navigating to desired link")
            web_address_navigator(self.browser, desired_link)
    except StaleElementReferenceException:
        pass


def nf_find_and_press_back(
        self,
        link: str,
        try_n: int = 1
):
    """Finds and press back button"""
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
    else:
        nf_scroll_into_view(self, back)
        nf_click_center_of_element(self, back, link)
        sleep(1)
        bad_loading = self.browser.find_elements_by_xpath(
            '/html/body/div[1]/section[@class="_9eogI E3X2T"]/span[@class="BHkOG PID-B"]'
        )
        if bad_loading and try_n <= 3:
            try_n += 1
            nf_find_and_press_back(self, link, try_n)
    if not check_if_in_correct_page(self, link):
        self.logger.error("Failed to go back, navigating there")
        # TODO: retry to get there naturally
        web_address_navigator(self.browser, link)


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
        nf_click_center_of_element(self, username_button, user_link)
    except NoSuchElementException:
        self.logger.warning("Failed to get user page button, navigating there")
        web_address_navigator(self.browser, user_link)


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
        self.logger.error("Failed to get {} page button, navigating there".format(which))
        web_address_navigator(self.browser, follow_link)
