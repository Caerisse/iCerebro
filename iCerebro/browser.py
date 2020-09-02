from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as Firefox_Options
from selenium.webdriver import Remote
from webdriverdownloader import GeckoDriverDownloader

import os
import zipfile
import shutil
from os.path import sep
from time import sleep

from iCerebro.util import interruption_handler
from iCerebro.util_loggers import LogDecorator


@LogDecorator()
def use_assets():
    # TODO: change as appropriate to server
    return os.getcwd()


@LogDecorator()
def get_geckodriver():
    # prefer using geckodriver from path
    gecko_path = os.environ.get('GECKODRIVER_PATH')
    if gecko_path:
        return gecko_path
    if os.path.isfile('./geckodriver'):
        return './geckodriver'
    gecko_path = shutil.which("geckodriver") or shutil.which("geckodriver.exe")
    if gecko_path:
        return gecko_path

    asset_path = use_assets()
    gdd = GeckoDriverDownloader(asset_path, asset_path)
    # skips download if already downloaded
    bin_path, sym_path = gdd.download_and_install()
    return sym_path


@LogDecorator()
def create_firefox_extension():
    ext_path = os.path.abspath(os.path.dirname(__file__) + sep + "firefox_extension")
    # safe into assets folder
    zip_file = use_assets() + sep + "extension.xpi"

    files = ["manifest.json", "content.js", "arrive.js"]
    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED, False) as zipf:
        for file in files:
            zipf.write(ext_path + sep + file, file)

    return zip_file


@LogDecorator()
def set_selenium_local_session(
    self
):
    """Starts local session for a selenium server."""

    # set Firefox Agent to mobile agent
    user_agent = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 12_1 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) FxiOS/18.1 Mobile/16B92 Safari/605.1.15"
    )

    firefox_options = Firefox_Options()

    # TODO: remove comment before commiting to server
    firefox_options.add_argument("--headless")
    firefox_options.add_argument("--disable-gpu")
    firefox_options.add_argument("--no-sandbox")

    firefox_profile = webdriver.FirefoxProfile()

    # set English language
    firefox_profile.set_preference("intl.accept_languages", "en-US")
    firefox_profile.set_preference("general.useragent.override", user_agent)

    if self.settings.disable_image_load:
        # permissions.default.image = 2: Disable images load,
        # this setting can improve pageload & save bandwidth
        # TODO: remove comment before commiting to server
        # pass
        firefox_profile.set_preference("permissions.default.image", 2)

    # TODO: check how this could work with django
    # if self.settings.proxy_address and self.settings.proxy_port:
    #     firefox_profile.set_preference("network.proxy.type", 1)
    #     firefox_profile.set_preference("network.proxy.http", proxy_address)
    #     firefox_profile.set_preference("network.proxy.http_port", int(proxy_port))
    #     firefox_profile.set_preference("network.proxy.ssl", proxy_address)
    #     firefox_profile.set_preference("network.proxy.ssl_port", int(proxy_port))

    # mute audio while watching stories
    firefox_profile.set_preference("media.volume_scale", "0.0")

    driver_path = get_geckodriver()
    firefox_bin = os.environ.get('FIREFOX_BIN')
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
def proxy_authentication(browser, logger, proxy_username, proxy_password):
    """ Authenticate proxy using popup alert window """

    # FIXME: https://github.com/SeleniumHQ/selenium/issues/7239
    # this feauture is not working anymore due to the Selenium bug report above
    logger.warn(
        "Proxy Authentication is not working anymore due to the Selenium bug "
        "report: https://github.com/SeleniumHQ/selenium/issues/7239"
    )

    try:
        # sleep(1) is enough, sleep(2) is to make sure we
        # give time to the popup windows
        sleep(2)
        alert_popup = browser.switch_to_alert()
        alert_popup.send_keys(
            "{username}{tab}{password}{tab}".format(
                username=proxy_username, tab=Keys.TAB, password=proxy_password
            )
        )
        alert_popup.accept()
    except Exception:
        logger.warn("Unable to proxy authenticate")


@LogDecorator()
def close_browser(browser, threaded_session, logger):
    with interruption_handler(threaded=threaded_session):
        # delete cookies
        try:
            browser.delete_all_cookies()
        except Exception as exc:
            if isinstance(exc, WebDriverException):
                logger.exception(
                    "Error occurred while deleting cookies "
                    "from web browser!\n\t{}".format(str(exc).encode("utf-8"))
                )

        # close web browser
        try:
            browser.quit()
        except Exception as exc:
            if isinstance(exc, WebDriverException):
                logger.exception(
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

