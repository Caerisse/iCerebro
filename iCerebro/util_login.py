import socket
import json
from time import sleep

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import MoveTargetOutOfBoundsException

import iCerebro.constants_x_paths as XP
import iCerebro.constants_js_scripts as JS
from iCerebro.navigation import web_address_navigator, explicit_wait, SoftBlockedException, nf_go_to_home
from iCerebro.navigation import nf_click_center_of_element
from iCerebro.util import check_authorization, sleep_while_blocked
from iCerebro.util_db import get_cookies, save_cookies
from iCerebro.util_loggers import LogDecorator


@LogDecorator()
def bypass_suspicious_login(
        self
) -> bool:  # success
    """ Bypass suspicious login attempt verification. """

    # close sign up Instagram modal if available
    dismiss_get_app_offer(self)
    dismiss_notification_offer(self)
    dismiss_this_was_me(self)

    option = None
    try:
        if self.settings.bypass_security_challenge_using == "SMS":
            option = self.browser.find_element_by_xpath(XP.BYPASS_WITH_SMS_OPTION)
        elif self.settings.bypass_security_challenge_using == "EMAIL":
            option = self.browser.find_element_by_xpath(XP.BYPASS_WITH_EMAIL_OPTION)
    except NoSuchElementException:
        self.logger.warn(
            "Unable to choose ({}) option to bypass the challenge".format(
                self.settings.bypass_security_challenge_using
            )
        )
        return False

    nf_click_center_of_element(self, option)
    # next button click will miss the DOM reference for this element, so ->
    option_text = option.text

    # click on security code
    send_security_code_button = self.browser.find_element_by_xpath(XP.SEND_SECURITY_CODE_BUTTON)
    nf_click_center_of_element(self, send_security_code_button)

    # update server calls
    self.quota_supervisor.add_server_call()

    print("Instagram detected an unusual login attempt")
    print('Check Instagram App for "Suspicious Login attempt" prompt')
    print("A security code was sent to your {}".format(option_text))

    # TODO: integrate with django somehow
    security_code = input("Type the security code here: ")

    security_code_field = self.browser.find_element_by_xpath(XP.SECURITY_CODE_FIELD)

    (
        ActionChains(self.browser)
        .move_to_element(security_code_field)
        .click()
        .send_keys(security_code)
        .perform()
    )

    # update server calls for both 'click' and 'send_keys' actions
    for _ in range(2):
        self.quota_supervisor.add_server_call()

    submit_security_code_button = self.browser.find_element_by_xpath(XP.SUBMIT_SECURITY_CODE_BUTTON)
    nf_click_center_of_element(self, submit_security_code_button)

    try:
        sleep(3)
        # locate wrong security code message
        wrong_login = self.browser.find_element_by_xpath(XP.WRONG_LOGIN)

        if wrong_login is not None:
            self.logger.info(
                "Wrong security code, please check the code Instagram sent you and try again."
            )
        return False
    except NoSuchElementException:
        # correct security code
        pass
    return True


@LogDecorator()
def check_browser(self) -> bool:  # success
    # check connection status
    try:
        self.logger.info("Connection Checklist [1/3] (Internet Connection Status)")
        self.browser.get("view-source:https://ip4.seeip.org/geoip")
        pre = self.browser.find_element_by_tag_name("pre").text
        current_ip_info = json.loads(pre)
        if (
            self.settings.use_proxy
            and socket.gethostbyname(self.settings.proxy_address) != current_ip_info["ip"]
        ):
            self.logger.warn("Proxy is set, but it's not working properly")
            self.logger.warn(
                'Expected Proxy IP is "{}", and the current IP is "{}"'.format(
                    self.settings.proxy_address, current_ip_info["ip"]
                )
            )
            self.logger.warn("Try again or disable the Proxy Address on your setup")
            self.logger.warn("Aborting connection")
            return False
        else:
            self.logger.info("Internet Connection Status: ok")
            self.logger.info(
                'Current IP is "{}" and it\'s from "{}/{}"'.format(
                    current_ip_info["ip"],
                    current_ip_info["country"],
                    current_ip_info["country_code"],
                )
            )
    except Exception:
        self.logger.warn("Internet Connection Status: error")
        return False

    # check Instagram.com status
    try:
        self.logger.info("Connection Checklist [2/3] (Instagram Server Status)")
        self.browser.get("https://isitdownorjust.me/instagram-com/")
        sleep(2)
        # collect isitdownorjust.me website information
        website_status = self.browser.find_element_by_xpath(XP.WEBSITE_STATUS)
        response_time = self.browser.find_element_by_xpath(XP.RESPONSE_TIME)
        response_code = self.browser.find_element_by_xpath(XP.RESPONSE_CODE)

        self.logger.info("Instagram WebSite Status: {} ".format(website_status.text))
        self.logger.info("Instagram Response Time: {} ".format(response_time.text))
        self.logger.info("Instagram Response Code: {}".format(response_code.text))
        self.logger.info("Instagram Server Status: ok")
    except Exception:
        self.logger.warn("Instagram Server Status: error")
        return False

    # check if hide-selenium extension is running
    self.logger.info("Connection Checklist [3/3] (Hide Selenium Extension)")
    webdriver = self.browser.execute_script("return window.navigator.webdriver")
    self.logger.info("window.navigator.webdriver response: {}".format(webdriver))
    if webdriver:
        self.logger.warn("Hide Selenium Extension: error")
    else:
        self.logger.info("Hide Selenium Extension: ok")
    # everything is ok, then continue(True)
    return True


@LogDecorator()
def login_user(
    self
) -> bool:  # success
    """Logins the user with the given username and password"""

    # Hotfix - this check crashes more often than not -- plus in not necessary, I can verify my own connection
    if self.settings.want_check_browser:
        if not check_browser(self):
            return False

    ig_homepage = "https://www.instagram.com"
    web_address_navigator(self, ig_homepage)
    cookie_loaded = False

    # try to load cookie from username
    try:
        for cookie in get_cookies(self):
            self.browser.add_cookie(cookie)
            cookie_loaded = True
    except WebDriverException:
        self.logger.warning("Error loading cookie into browser")

    if cookie_loaded:
        # force refresh after cookie load or check_authorization() will FAIL
        self.browser.execute_script(JS.RELOAD)
        self.quota_supervisor.add_server_call()
        # cookie has been loaded, so the user should be logged in
        dismiss_popups(self)
        try:
            login_state = check_authorization(self, "activity counts", False)
        except SoftBlockedException:
            sleep_while_blocked(self)
            login_state = check_authorization(self, "activity counts", False)
        if login_state is True:
            return True
        else:
            self.logger.warning("There is a issue with the saved cookie, will create a new one")

    # Check if the first div is 'Create an Account' or 'Log In'
    try:
        login_elem = self.browser.find_element_by_xpath(XP.LOGIN_ELEM)
    except NoSuchElementException:
        self.logger.info("Login A/B test detected! Trying another string...")
        try:
            login_elem = self.browser.find_element_by_xpath(XP.LOGIN_ELEM_NO_SUCH_EXCEPTION)
        except NoSuchElementException:
            return False

    if login_elem is not None:
        try:
            self.browser.execute_script("arguments[0].click();", login_elem)
        except MoveTargetOutOfBoundsException:
            login_elem.click()
            self.quota_supervisor.add_server_call()

    # Enter username and password and logs the user in
    # Sometimes the element name isn't 'Username' and 'Password'
    # (valid for placeholder too)

    # wait until it navigates to the login page
    # Instagram changed this, no longer needed
    # login_page_title = "Login"
    # explicit_wait(self, "TC", login_page_title)

    # wait until the 'username' input element is located and visible
    explicit_wait(self, "VOEL", [XP.INPUT_USERNAME_XP, "XPath"])

    input_username = self.browser.find_element_by_xpath(XP.INPUT_USERNAME_XP)

    (
        ActionChains(self.browser)
        .move_to_element(input_username)
        .click()
        .send_keys(self.username)
        .perform()
    )

    # update server calls for both 'click' and 'send_keys' actions
    for _ in range(2):
        self.quota_supervisor.add_server_call()

    #  password
    input_password = self.browser.find_elements_by_xpath(XP.INPUT_PASSWORD)

    (
        ActionChains(self.browser)
        .move_to_element(input_password[0])
        .click()
        .send_keys(self.settings.password)
        .perform()
    )

    sleep(1)

    (
        ActionChains(self.browser)
        .move_to_element(input_password[0])
        .click()
        .send_keys(Keys.ENTER)
        .perform()
    )

    # update server calls for both 'click' and 'send_keys' actions
    for _ in range(4):
        self.quota_supervisor.add_server_call()

    sleep(1)
    dismiss_popups(self)

    # check for login error messages and display it in the logs
    if "instagram.com/challenge" in self.browser.current_url:
        # check if account is disabled by Instagram,
        # or there is an active challenge to solve
        try:
            account_disabled = self.browser.find_element_by_xpath(XP.ACCOUNT_DISABLED)
            self.logger.warn(account_disabled.text)
            return False
        except NoSuchElementException:
            pass

        # in case the user doesnt have a phone number linked to the Instagram account
        try:
            self.browser.find_element_by_xpath(XP.ADD_PHONE_NUMBER)
            self.logger.warn(
                "Instagram initiated a challenge before allow your account to login. "
                "At the moment there isn't a phone number linked to your Instagram "
                "account. Please, add a phone number to your account, and try again."
            )
            return False
        except NoSuchElementException:
            pass

        # try to initiate security code challenge
        try:
            self.browser.find_element_by_xpath(XP.SUSPICIOUS_LOGIN_ATTEMPT)
            self.logger.info("Trying to solve suspicious attempt login")
            bypass_suspicious_login(self)
        except NoSuchElementException:
            pass

    # check for wrong username or password message, and show it to the user
    try:
        error_alert = self.browser.find_element_by_xpath(XP.ERROR_ALERT)
        self.logger.warn(error_alert.text)
        return False
    except NoSuchElementException:
        pass

    if "instagram.com/accounts/onetap" in self.browser.current_url:
        self.browser.get("https://instagram.com")

    # wait until page fully load
    explicit_wait(self, "PFL", [], 5)

    # Check if user is logged-in (If there's two 'nav' elements)
    nav = self.browser.find_elements_by_xpath(XP.NAV)
    if len(nav) == 2:
        # create cookie for username
        save_cookies(self, self.browser.get_cookies())
        return True
    else:
        return False


@LogDecorator()
def dismiss_popups(self):
    dismiss_save_login_offer(self)
    dismiss_home_screen_offer(self)
    self.browser.execute_script(JS.RELOAD)
    self.quota_supervisor.add_server_call()
    dismiss_get_app_offer(self)
    self.browser.execute_script(JS.RELOAD)
    self.quota_supervisor.add_server_call()
    dismiss_notification_offer(self)
    dismiss_use_app_offer(self)


def dismiss_get_app_offer(self):
    """ Dismiss 'Get the Instagram App' page after a fresh login """
    # wait a bit and see if the 'Get App' offer rises up
    offer_loaded = explicit_wait(self, "VOEL", [XP.OFFER_ELEM, "XPath"], 5, False)
    if offer_loaded:
        dismiss_elem = self.browser.find_element_by_xpath(XP.DISMISS_ELEM)
        nf_click_center_of_element(self, dismiss_elem, skip_action_chain=True)


def dismiss_notification_offer(self):
    """ Dismiss 'Turn on Notifications' offer on session start """
    # wait a bit and see if the 'Turn on Notifications' offer rises up
    offer_loaded = explicit_wait(self, "VOEL", [XP.OFFER_ELEM_LOC, "XPath"], 4, False)
    if offer_loaded:
        dismiss_elem = self.browser.find_element_by_xpath(XP.DISMISS_ELEM_LOC)
        nf_click_center_of_element(self, dismiss_elem, skip_action_chain=True)


def dismiss_home_screen_offer(self):
    """ Dismiss 'Add Instagram to your Home screen' offer on session start """
    # wait a bit and see if the 'Add Instagram to your Home screen' offer rises up
    offer_loaded = explicit_wait(self, "VOEL", [XP.OFFER_ELEM_HOME, "XPath"], 4, False)
    if offer_loaded:
        dismiss_elem = self.browser.find_element_by_xpath(XP.DISMISS_ELEM_HOME)
        nf_click_center_of_element(self, dismiss_elem, skip_action_chain=True)


def dismiss_use_app_offer(self):
    """ Dismiss 'Use the App' offer on session start """
    # wait a bit and see if the 'Use the App' offer rises up
    offer_loaded = explicit_wait(self, "VOEL", [XP.OFFER_ELEM_USE, "XPath"], 4, False)
    if offer_loaded:
        dismiss_elem = self.browser.find_element_by_xpath(XP.DISMISS_ELEM_USE)
        nf_click_center_of_element(self, dismiss_elem, skip_action_chain=True)


def dismiss_save_login_offer(self):
    """ Dismiss 'Use the App' offer on session start """
    # wait a bit and see if the 'Use the App' offer rises up
    offer_loaded = explicit_wait(self, "VOEL", [XP.OFFER_ELEM_LOGIN, "XPath"], 4, False)
    if offer_loaded:
        dismiss_elem = self.browser.find_element_by_xpath(XP.DISMISS_ELEM_LOGIN)
        nf_click_center_of_element(self, dismiss_elem, skip_action_chain=True)


def dismiss_this_was_me(self):
    try:
        # click on "This was me" button if challenge page was called
        this_was_me_button = self.browser.find_element_by_xpath(XP.THIS_WAS_ME_BUTTON)
        nf_click_center_of_element(self, this_was_me_button, skip_action_chain=True)
    except NoSuchElementException:
        # no verification needed
        pass
