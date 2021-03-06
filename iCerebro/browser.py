from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options as Firefox_Options
from selenium.webdriver import Remote

import os
import platform
import zipfile
import shutil
from os.path import sep
from time import sleep

from iCerebro.util import interruption_handler
from iCerebro.util_loggers import LogDecorator


@LogDecorator()
def get_geckodriver():
    # prefer using geckodriver from path
    gecko_path = os.environ.get('GECKODRIVER_PATH')
    if gecko_path:
        return gecko_path
    # if not in path try to find it with shutil
    gecko_path = shutil.which("geckodriver") or shutil.which("geckodriver.exe")
    if gecko_path:
        return gecko_path
    # if neither use local file according to OS
    system_name = platform.system()
    gecko_path = './geckodriver/{}/geckodriver{}'.format(system_name, '.exe' if system_name == 'Windows' else '')
    if os.path.isfile(gecko_path):
        return gecko_path

    # Disclaimer:
    #   All provided geckodriver are for 64 bits machines
    #   others can be dosloaded from here https://github.com/mozilla/geckodriver/releases
    #   From geckodriver github:
    #       Known problems
    #       macOS 10.15 (Catalina):
    #       Due to the requirement from Apple that all programs must be notarized, geckodriver will not work on Catalina
    #       if you manually download it through another notarized program, such as Firefox.
    #       Whilst we are working on a repackaging fix for this problem, you can find more details on how to work around
    #       this issue in the macOS notarization section of the documentation.
    #   https://firefox-source-docs.mozilla.org/testing/geckodriver/Notarization.html
    #   From that link:
    #       To bypass the notarization requirement on macOS if you have downloaded the geckodriver .tar.gz
    #       via a web browser, you can run the following command in a terminal:
    #           xattr -r -d com.apple.quarantine geckodriver
    #   For iCerebro if executing from the root of the project the command would be:
    #       xattr -r -d com.apple.quarantine geckodriver/Darwin/geckodriver


@LogDecorator()
def create_firefox_extension():
    ext_path = os.path.abspath(os.path.dirname(__file__) + sep + "firefox_extension")
    # safe into assets folder
    zip_file = ext_path + sep + "extension.xpi"

    files = ["manifest.json", "content.js", "arrive.js"]
    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED, False) as zipf:
        for file in files:
            zipf.write(ext_path + sep + file, file)

    return zip_file


@LogDecorator()
def set_selenium_local_session_firefox(
    self
):
    """Starts local session for a selenium server."""

    # set Firefox Agent to mobile agent
    user_agent = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 12_1 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) FxiOS/18.1 Mobile/16B92 Safari/605.1.15"
    )

    firefox_options = Firefox_Options()
    firefox_profile = webdriver.FirefoxProfile()

    if self.settings.disable_image_load:
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--disable-gpu")
        firefox_options.add_argument("--no-sandbox")
        # permissions.default.image = 2: Disable images load,
        # this setting can improve page load time & save bandwidth
        firefox_profile.set_preference("permissions.default.image", 2)

    # set English language
    firefox_profile.set_preference("intl.accept_languages", "en-US")
    firefox_profile.set_preference("general.useragent.override", user_agent)

    if self.proxy:
        self.logger.debug("Using android app proxy on port {}".format(self.proxy.port))
        firefox_profile.set_preference("network.proxy.type", 1)
        firefox_profile.set_preference("network.proxy.http", "localhost")
        firefox_profile.set_preference("network.proxy.http_port", self.proxy.port)
        firefox_profile.set_preference("network.proxy.ssl", "localhost")
        firefox_profile.set_preference("network.proxy.ssl_port", self.proxy.port)

        # TODO, test if connection is active in provided port, return None if not
    elif self.settings.use_proxy:
        if self.settings.proxy_address and self.settings.proxy_port:
            self.logger.debug('Using provided proxy: {}:{}'.format(self.settings.proxy_address, self.settings.proxy_port))
            firefox_profile.set_preference("network.proxy.type", 1)
            firefox_profile.set_preference("network.proxy.http", self.settings.proxy_address)
            firefox_profile.set_preference("network.proxy.http_port", int(self.settings.proxy_port))
            firefox_profile.set_preference("network.proxy.ssl", self.settings.proxy_address)
            firefox_profile.set_preference("network.proxy.ssl_port", int(self.settings.proxy_port))
        else:
            self.logger.error('Bot was asked to use a proxy address but settings are missing')
            return None
    else:
        self.logger.error('No proxy set, please run the iCerebro android app or provide a proxy address to use')
        # Commented for testing purpose (so it can be run without a proxy using the server ip)
        # return None
        self.logger.info('Running without proxy for testing purposes')

    # mute audio while watching stories
    firefox_profile.set_preference("media.volume_scale", "0.0")

    driver_path = get_geckodriver()
    firefox_path = os.environ.get('FIREFOX_BIN')
    if not firefox_path:
        firefox_path = shutil.which("firefox") or shutil.which("firefox.exe")
    firefox_bin = FirefoxBinary(firefox_path)
    browser = webdriver.Firefox(
        firefox_binary=firefox_bin,
        firefox_profile=firefox_profile,
        executable_path=driver_path,
        options=firefox_options,
    )

    # add extensions to hide selenium
    browser.install_addon(create_firefox_extension(), temporary=True)

    # authenticate with popup alert window
    # if self.settings.proxy_username and self.settings.proxy_password:
    #     proxy_authentication(self)

    browser.implicitly_wait(self.settings.page_delay)

    # set mobile viewport (iPhone X)
    browser.set_window_size(375, 812)

    self.logger.debug("Selenium session started")

    return browser


@LogDecorator()
def get_chromedriver():
    # prefer using geckodriver from path
    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
    if chromedriver_path:
        return chromedriver_path
    # if not in path try to find it with shutil
    chromedriver_path = shutil.which("chromedriver") or shutil.which("chromedriver.exe")
    if chromedriver_path:
        return chromedriver_path
    # if neither use local file according to OS
    system_name = platform.system()
    chromedriver_path = './chromedriver/{}/chromedriver{}'.format(system_name, '.exe' if system_name == 'Windows' else '')
    if os.path.isfile(chromedriver_path):
        return chromedriver_path


@LogDecorator()
def set_selenium_local_session_chrome(
        self
):
    """Starts local session for a selenium server."""

    # set Chrome Agent to mobile agent
    user_agent = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 13_7 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) CriOS/85.0.4183.109 Mobile/15E148 Safari/604.1"
    )

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("user-agent={}".format(user_agent))
    chrome_options.add_argument('--load-extension={}'.format(
        os.path.abspath(os.path.dirname(__file__) + sep + "firefox_extension"))
    )
    # chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-add-to-shelf")

    if self.settings.disable_image_load:
        # Cant load extensions in headless mode so cant hide we are using selenium
        # chrome_options.add_argument("--headless")
        # So instead we need to use pyvirtualdisplay
        self.display = Display(visible=0, size=(375, 812))
        self.display.start()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_prefs = {
            "profile.default_content_settings": {"images": 2},
            "profile.managed_default_content_settings": {"images": 2}
        }
        chrome_options.experimental_options["prefs"] = chrome_prefs

    if self.proxy:
        self.logger.debug("Using android app proxy on port {}".format(self.proxy.port))
        chrome_options.add_argument('--proxy-server=socks5://localhost:{}'.format(self.proxy.port))
        # TODO, test if connection is active in provided port, return None if not
    elif self.settings.use_proxy:
        if self.settings.proxy_address and self.settings.proxy_port:
            self.logger.debug('Using provided proxy: {}:{}'.format(self.settings.proxy_address, self.settings.proxy_port))
            chrome_options.add_argument('--proxy-server={}:{}'.format(self.settings.proxy_address, self.proxy.port))
        else:
            self.logger.error('Bot was asked to use a proxy address but settings are missing')
            return None
    else:
        self.logger.error('No proxy set, please run the iCerebro android app or provide a proxy address to use')
        # Commented for testing purpose (so it can be run without a proxy using the server ip)
        # return None
        self.logger.info('Running without proxy for testing purposes')

    driver_path = get_chromedriver()
    chrome_path = os.environ.get('CHROME_BIN')
    if not chrome_path:
        chrome_path = shutil.which("google-chrome-stable") or shutil.which("google-chrome-stable.exe")
    chrome_options.binary_location = chrome_path
    browser = webdriver.Chrome(
        executable_path=driver_path,
        options=chrome_options,
        # desired_capabilities=capabilities,
    )
    # set mobile viewport (iPhone X)
    browser.set_window_size(375, 812)

    browser.implicitly_wait(self.settings.page_delay)

    self.logger.debug("Selenium session started")

    return browser


@LogDecorator()
def proxy_authentication(self):
    """ Authenticate proxy using popup alert window """

    # FIXME: https://github.com/SeleniumHQ/selenium/issues/7239
    # this feauture is not working anymore due to the Selenium bug report above
    # self.logger.debug(
    #     "Proxy Authentication is not working anymore due to the Selenium bug "
    #     "report: https://github.com/SeleniumHQ/selenium/issues/7239"
    # )

    try:
        # sleep(1) is enough, sleep(2) is to make sure we
        # give time to the popup windows
        sleep(2)
        alert_popup = self.browser.switch_to_alert()
        alert_popup.send_keys(
            "{username}{tab}{password}{tab}".format(
                username=self.settings.proxy_username, tab=Keys.TAB, password=self.settings.proxy_password
            )
        )
        alert_popup.accept()
    except Exception:
        self.logger.error("Unable to authenticate proxy")


@LogDecorator()
def close_browser(browser, threaded_session, logger):
    with interruption_handler(threaded=threaded_session):
        # delete cookies
        try:
            browser.delete_all_cookies()
        except Exception as exc:
            if isinstance(exc, WebDriverException):
                logger.error(
                    "Error occurred while deleting cookies "
                    "from web browser!\n\t{}".format(str(exc).encode("utf-8"))
                )

        # close web browser
        try:
            browser.quit()
        except Exception as exc:
            if isinstance(exc, WebDriverException):
                logger.error(
                    "Error occurred while "
                    "closing web browser!\n\t{}".format(str(exc).encode("utf-8"))
                )


@LogDecorator()
def retry(max_retry_count=3, start_page=None):
    """
        Decorator which refreshes the page and tries to execute the function again.
        Use it like that: @retry() => the '()' are important because its a decorator
        with params.
    """

    def real_decorator(org_func):
        def wrapper(*args, **kwargs):
            browser = None
            _start_page = start_page

            # try to find instance of a browser in the arguments
            # all webdriver classes (chrome, firefox, ...) inherit from Remote class
            for arg in args:
                if not isinstance(arg, Remote):
                    continue

                browser = arg
                break

            else:
                for _, value in kwargs.items():
                    if not isinstance(value, Remote):
                        continue

                    browser = value
                    break

            if not browser:
                print("not able to find browser in parameters!")
                return org_func(*args, **kwargs)

            if max_retry_count == 0:
                print("max retry count is set to 0, this function is useless right now")
                return org_func(*args, **kwargs)

            # get current page if none is given
            if not start_page:
                _start_page = browser.current_url

            rv = None
            retry_count = 0
            while True:
                try:
                    rv = org_func(*args, **kwargs)
                    break
                except Exception as e:
                    # TODO: maybe handle only certain exceptions here
                    retry_count += 1

                    # if above max retries => throw original exception
                    if retry_count > max_retry_count:
                        raise e

                    rv = None

                    # refresh page
                    browser.get(_start_page)

            return rv

        return wrapper

    return real_decorator

