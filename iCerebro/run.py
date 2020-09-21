import random
from datetime import datetime, timedelta
from time import sleep, perf_counter
from iCerebro.browser import set_selenium_local_session, close_browser
from iCerebro.util import interruption_handler
from iCerebro.util_loggers import LogDecorator
from iCerebro.navigation import web_address_navigator


@LogDecorator()
def run(self):
    start_time = perf_counter()
    try:
        # self.display = Display(visible=0, size=(800, 600))
        # self.display.start()
        self.browser = set_selenium_local_session(self)
        # web_address_navigator(self, 'http://www.google.com')
        # search = self.browser.find_element_by_xpath(self, '/html/body/div/div[2]/form/div[2]/div[1]/div[1]/div/div[2]/input')
        # sleep(60)
        self.login()
        # self.like_by_tags(random.sample(self.settings.hashtags, 3), 5)
        # self.like_by_feed(10)
        run_loop(self)
    finally:
        close_browser(self.browser, True, self.logger)
        if self.display:
            with interruption_handler(threaded=True):
                self.display.stop()
        elapsed_time = perf_counter() - start_time
        self.logger.info("iCerebro stopped after {} hours and {} minutes".format(
            int(elapsed_time/3600),
            int((elapsed_time % 3600)/60),
        ))
        self.logger.info("{}{}".format("Total " if self.interactions else "", self.interactions))
        self.settings.abort = False
        self.settings.running = False
        self.settings.save()


@LogDecorator()
def run_loop(self):
    while not self.aborting:
        self.run_settings.refresh_from_db()
        settings = self.run_settings.__dict__
        now = datetime.now()
        hour = now.hour
        action_name = settings["do_from_{0:02d}".format(hour)]
        for i in range(1, 24):
            h = (hour + i) % 24
            if settings["do_from_{0:02d}".format(h)] != action_name:
                break
        else:
            # if the loop didn't break set i = 24 and the bot will start the function each day at the same hour
            i = 24

        minutes_till_next = 60 * i - now.minute + random.randint(1, 10)
        self.until_time = now + timedelta(minutes=minutes_till_next)

        if action_name == 'None':
            pass
        elif action_name == 'like_by_tags':
            self.like_by_tags(
                random.sample(self.settings.hashtags, len(self.settings.hashtags)),
                self.run_settings.like_by_tags_settings_amount_per_tag,
                self.run_settings.like_by_tags_settings_skip_top_post
            )
        elif action_name == 'like_by_users':
            self.like_by_users(
                self.run_settings.like_by_users_settings_usernames,
                self.run_settings.like_by_users_settings_amount,
                self.run_settings.like_by_users_settings_validated
            )
        elif action_name == 'like_by_feed':
            self.like_by_feed(
                self.run_settings.like_by_feed_settings_amount
            )
        elif action_name == 'like_by_location':
            self.like_by_location(
                random.sample(self.settings.location_hashtags, len(self.settings.location_hashtags)),
                self.run_settings.like_by_location_settings_amount_per_tag,
                self.run_settings.like_by_location_settings_skip_top_post
            )
        elif action_name == 'follow_user_follow':
            self.follow_user_follow(
                self.run_settings.follow_user_follow_settings_what,
                self.settings.similar_accounts,
                self.run_settings.follow_user_follow_settings_amount,
                self.run_settings.follow_user_follow_settings_randomize
            )
        elif action_name == 'follow_by_list':
            self.follow_by_list(
                self.run_settings.follow_by_list_settings_usernames,
                self.run_settings.follow_by_list_settings_validated
            )
        elif action_name == 'follow_by_tag':
            self.follow_by_tag(
                random.sample(self.settings.hashtags, len(self.settings.hashtags)),
                self.run_settings.follow_by_tags_settings_amount_per_tag,
                self.run_settings.follow_by_tags_settings_skip_top_post
            )
        elif action_name == 'follow_by_location':
            self.follow_by_location(
                random.sample(self.settings.location_hashtags, len(self.settings.location_hashtags)),
                self.run_settings.follow_by_locations_settings_amount_per_tag,
                self.run_settings.follow_by_locations_settings_skip_top_post
            )
        elif action_name == 'unfollow_users':
            self.unfollow_users(
                self.run_settings.unfollow_users_settings_amount,
                self.run_settings.unfollow_users_settings_list,
                self.run_settings.unfollow_users_settings_track,
                self.run_settings.unfollow_users_settings_after_hours,
                self.run_settings.unfollow_users_settings_dont_unfollow_active_users,
                self.run_settings.unfollow_users_settings_posts_to_check,
                self.run_settings.unfollow_users_settings_boundary_to_check
            )
        else:
            self.logger.error("Unknown action in run loop")
            break

        sleep_until_time_or_change(self, action_name)


@LogDecorator()
def sleep_until_time_or_change(self, action: str):
    self.run_settings.refresh_from_db()
    informed = False
    if not self.run_settings.repeat_action_if_ended_before_time and self.until_time:
        while not self.aborting:
            self.run_settings.refresh_from_db()
            settings = self.run_settings.__dict__
            now = datetime.now()
            hour = now.hour
            if action == settings["do_from_{0:02d}".format(hour)] and now < self.until_time:
                if not informed:
                    informed = True
                    self.logger.info("Bot finished {}, will sleep until {} if no change is made, "
                                     "will check every 10 minutes if the settings changed "
                                     "or the bot was stopped".format(action, self.until_time))
                nap = min(600, (self.until_time-now).seconds)
                self.logger.debug("Sleeping {} seconds".format(nap))
                sleep(nap)
            else:
                break
