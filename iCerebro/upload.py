import time
import pyautogui


def upload_single_image(self, image_name: str, text: str, insta_username: str):
    time.sleep(1.5)

    self.browser.find_element_by_xpath("//div[@role='menuitem']").click()

    time.sleep(1.5)
    # pyautogui.hotkey("winleft", "pgup")nt
    time.sleep(1.5)
    pyautogui.moveTo(100, 80)
    pyautogui.click()
    inputs = ['Development', ['enter'], 'InstaPy', ['enter'],
              'bots', ['enter'], insta_username, ['enter'],
              'posts_source', ['enter'], image_name, ['enter']]
    for input_ in inputs:
        time.sleep(1)
        pyautogui.typewrite(input_, interval=1)

    time.sleep(4)
    self.browser.find_element_by_xpath("//*[@id='react-root']/section/div[1]/header/div/div[2]/button").click()
    time.sleep(1)
    self.browser.find_element_by_xpath("//*[@id='react-root']/section/div[2]/section[1]/div[1]/textarea").send_keys(
        text)
    time.sleep(1)
    self.browser.find_element_by_xpath("//*[@id='react-root']/section/div[1]/header/div/div[2]/button").click()
    time.sleep(10)
