import os
import shutil
import zipfile
from os.path import sep
from time import sleep

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver import Remote


PORT = 54631

PROXY = "socks5://localhost:{}".format(PORT)
user_agent = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 13_7 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Mobile/15E148 Instagram 157.0.0.23.119 (iPhone12,5; iOS 13_7; "
    "en_US; en-US; scale=3.00; 1242x2688; 241452311) NW/1"
)

chrome_options = webdriver.ChromeOptions()

display = Display(visible=0, size=(375, 812))
display.start()


# chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--start-maximized")
# chrome_options.add_argument("--window-size=375,812")
# chrome_options.add_argument("--force-app-mode")


# set English language ?

# set user agent
chrome_options.add_argument("user-agent={}".format(user_agent))


# mute audio while watching stories ?
# disable image load ?


# Alternative to extension
# firefox_profile.set_preference('dom.webdriver.enabled', False)
# firefox_profile.set_preference('useAutomationExtension', False)
# firefox_profile.set_preference('general.platform.override', 'iPhone')
# firefox_profile.update_preferences()

driver_path = './chromedriver/Linux/chromedriver'
chrome_path = os.environ.get('CHROME_BIN')
if not chrome_path:
    chrome_path = shutil.which("google-chrome-stable") or shutil.which("google-chrome-stable.exe")
capabilities = webdriver.DesiredCapabilities.CHROME.copy()
capabilities['binary'] = chrome_path



# chrome_options.add_argument('--ignore-certificate-errors')
#
# # add acceptInsecureCerts
# capabilities['acceptInsecureCerts'] = True

# set proxy
# chrome_options.add_argument('--proxy-server={}'.format(PROXY))

chrome_options.add_argument('--load-extension=iCerebro/firefox_extension')


browser = webdriver.Chrome(
    executable_path=driver_path,
    options=chrome_options,
    desired_capabilities=capabilities,
)

browser.implicitly_wait(5)

try:
    link = "https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html"
    browser.get(link)
    browser.implicitly_wait(5)
    browser.save_screenshot('test_webdriver.png')
    link = "https://intoli.com/blog/making-chrome-headless-undetectable/chrome-headless-test.html"
    browser.get(link)
    browser.implicitly_wait(5)
    browser.save_screenshot('test_webdriver_2.png')
    link = "https://whatsmyip.net/"
    browser.get(link)
    browser.implicitly_wait(5)
    browser.save_screenshot('test_ip.png')
finally:
    try:
        browser.delete_all_cookies()
    except Exception as exc:
        pass
    try:
        browser.quit()
    except Exception as exc:
        pass
    try:
        display.stop()
    except Exception as exc:
        pass
