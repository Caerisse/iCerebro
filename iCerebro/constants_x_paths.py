# bypass_suspicious_login
BYPASS_WITH_SMS_OPTION = "//label[contains(text(),'Phone:')]"
BYPASS_WITH_EMAIL_OPTION = "//label[contains(text(),'Email:')]"
SEND_SECURITY_CODE_BUTTON = "//button[text()='Send Security Code']"
SECURITY_CODE_FIELD = "//input[@id='security_code']"
SUBMIT_SECURITY_CODE_BUTTON = "//button[text()='Submit']"
WRONG_LOGIN = "//p[text()='Please check the code we sent you and try again.']"
# dismiss_this_was_me
THIS_WAS_ME_BUTTON = "//button[@name='choice'][text()='This Was Me']"
# class_selectors"] = "{
LIKES_DIALOG_BODY_XPATH = "//main"
LIKES_DIALOG_CLOSE_XPATH = "//div/button/span"
# confirm_unfollow
BUTTON_XP = "//button[text()='Unfollow']"
# dialog_username_extractor
PERSON = "../../*"
# dismiss_get_app_offer
OFFER_ELEM = "//*[contains(text(), 'Get App')]"
DISMISS_ELEM = "//*[contains(text(), 'Not Now')]"
# dismiss_notification_offer
OFFER_ELEM_LOC = "//div/h2[text()='Turn on Notifications']"
DISMISS_ELEM_LOC = "//button[text()='Not Now']"
# extract_information
CLOSE_OVERLAY = "//div/div[@role='dialog']"
ONE_PIC_ELEM = "//section/main/article/div[1]/div/div[10]/div[3]/a/div"
LIKE_ELEMENT = "//a[@role='button']/span[text()='Like']/.."
# extract_post_info
COMMENT_LIST = "//div/ul",
COMMENTS = "//li[@role='menuitem']",
LOAD_MORE_COMMENTS_ELEMENT = "//div/ul/li/div/button"
LOAD_MORE_COMMENTS_ELEMENT_ALT = "//div/ul/li[1]/button"
# find_user_id
META_XP = "//meta[@property='instapp:owner_user_id']"
# get_active_users
PROFILE_POSTS = "(//div[contains(@class, '_9AhH0')])[{}]"
LIKERS_COUNT = "//section/div/div/a/span"
LIKES_BUTTON = "//div[@class='Nm9Fw']/a"
NEXT_BUTTON = "//a[text()='Next']"
TOP_COUNT_ELEMENTS = "//span[contains(@class,'g47SY')]"
# get_buttons_from_dialog
FOLLOW_BUTTON = "//button[text()='Follow']"
UNFOLLOW_BUTTON = "//button[text()='Following']"
# get_comment_input
COMMENT_INPUT = "//form/textarea"
PLACEHOLDER = '//textarea[@Placeholder="Add a comment…"]'
# get_comments_on_post
COMMENTER_ELEM = "//h3/a"
COMMENTS_BLOCK = "//div/div/h3/../../../.."
LIKE_BUTTON_FULL_XPATH = "//div/span/button/span[@aria-label='Like']"
UNLIKE_BUTTON_FULL_XPATH = "//div/span/button/span[@aria-label='Unlike']"
# get_cord_location
JSON_TEXT = "//body"
# get_following_status
FOLLOW_BUTTON_XP = "//button[text()='Following' or \
                                  text()='Requested' or \
                                  text()='Follow' or \
                                  text()='Follow Back' or \
                                  text()='Unblock']"
FOLLOW_SPAN_XP_FOLLOWING = "//button/div/span[contains(@aria-label, 'Following')]"
# get_follow_requests
LIST_OF_USERS = "//section/div"
VIEW_MORE_BUTTON = "//button[text()='View More']"
# get_given_user_followers
FOLLOWERS_LINK = "//ul/li[2]/a/span"
# get_given_user_following
ALL_FOLLOWING = "//a[contains(@href,'following')]/span"
FOLLOWING_LINK = '//a[@href="/{}/following/"]'
# get_photo_urls_from_profile
PHOTOS_A_ELEMS = "//div/a"
# get_links_for_location or tag
TOP_ELEMENTS = "//main/article/div[1]"
MAIN_ELEM = "//main/article/div[2]"
POSSIBLE_POST = "//span[contains(@class, 'g47SY')]"
# get_links_from_feed
GET_LINKS = "//article/div[2]/div[2]/a"
# get_number_of_posts
NUM_OF_POSTS_TXT = "//section/main/div/ul/li[1]/span/span"
NUM_OF_POSTS_TXT_NO_SUCH_ELEMENT = "//section/div[3]/div/header/section/ul/li[1]/span/span"
# get_relationship_counts
FOLLOWING_COUNT = "//a[contains(@href,'following') and not(contains(@href,'mutual'))]/span"
FOLLOWERS_COUNT = "//a[contains(@href,'followers') and not(contains(@href,'mutual'))]/span"
# get_source_link"
IMAGE = '//img[@class="FFVAD"]'
IMAGE_ALT = '//img[@class="_8jZFn"]'
VIDEO = '//video[@class="tWeCl"]'
# get_users_through_dialog
FIND_DIALOG_BOX = "//body/div[4]/div/div[2]"
# is_private_profile
IS_PRIVATE = '//h2[@class="_kcrwx"]'
IS_PRIVATE_PROFILE = "//*[contains(text(), 'This Account is Private')]"
# like_comment
SPAN_LIKE_ELEMENTS = "//span[@aria-label='Like']"
COMMENT_LIKE_BUTTON = ".."
# like_image
LIKE = "//section/span/button[*[local-name()='svg']/@aria-label='Like']"
UNLIKE = "//section/span/button[*[local-name()='svg']/@aria-label='Unlike']"
# like_from_image
MAIN_ARTICLE = "//main//article//div//div[1]//div[1]//a[1]"
# login_user
INPUT_PASSWORD = "//input[@name='password']"
INPUT_USERNAME_XP = "//input[@name='username']"
LOGIN_ELEM = "//button[text()='Log In']"
LOGIN_ELEM_NO_SUCH_EXCEPTION = "//a[text()='Log in']"
NAV = "//nav"
WEBSITE_STATUS = "//span[@id='status']"
RESPONSE_TIME = "//span[@id='response']"
RESPONSE_CODE = "//span[@id='code']"
ACCOUNT_DISABLED = "//p[contains(text(),'Your account has been disabled')]"
ADD_PHONE_NUMBER = "//h2[text()='Add Your Phone Number']"
SUSPICIOUS_LOGIN_ATTEMPT = "//p[text()='Suspicious Login Attempt']"
ERROR_ALERT = "//p[@id='slfErrorAlert']"
# open_comment_section
COMMENT_ELEM = "//button[*[local-name()='svg']/@aria-label='Comment']"
# unfollow
UNFOLLOW_FOLLOWING_LINK = "//ul/li[3]/a/span"
UNFOLLOW_FIND_DIALOG_BOX = "//section/main/div[2]"
# watch_story_for_tag
EXPLORE_STORIES_TAG = "//section/main/header/div[1]/div"
# watch_story_for_user
EXPLORE_STORIES_USER = "//section/main/div/header/div/div"
# watch_story
NEXT_FIRST = "/html/body/span/section/div/div/section/div[2]/button"
NEXT_STORY = "/html/body/span/section/div/div/section/div[2]/button[2]"
# likers_from_photo
LIKED_COUNTER_BUTTON = "//div/article/div[2]/section[2]/div/div/a"
SECOND_COUNTER_BUTTON = "//div/article/div[2]/section[2]/div/div/button"
# utils
POSTS_ON_ELEMENT = '//a[starts-with(@href, "/p/") and not(contains(@href,"liked_by"))]'
USERS_ON_ELEMENT = '//a[@class="FPmhX notranslate  _0imsa "]'
# check_post
POST_USERNAME = '/html/body/div[1]/section/main/div/div/article/header//div[@class="e1e1d"]'
POST_FOLLOW_BUTTON = '/html/body/div[1]/section/main/div/div/article/header/div[2]/div[1]/div[2]/button'
POST_LOCATION = '/html/body/div[1]/section/main/div/div/article/header//a[contains(@href,"locations")]'
POST_IMAGES = '/html/body/div[1]/section/main/div/div/article//img[@class="FFVAD"]'
POST_VIDEO_PREVIEWS = '/html/body/div[1]/section/main/div/div/article//img[@class="_8jZFn"]'
POST_VIDEOS = '/html/body/div[1]/section/main/div/div/article//video[@class="tWeCl"]'
POST_CAPTION = "/html/body/div[1]/section/main/div/div/article//div/div/span/span"
POST_DATE = '/html/body/div[1]/section/main/div/div/article//a[@class="c-Yi7"]/time'