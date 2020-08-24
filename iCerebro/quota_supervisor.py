from copy import deepcopy
from time import sleep
from datetime import datetime
import random


class QuotaSupervisor:
    SERVER_CALL = "server_call"
    LIKE = "like"
    COMMENT = "comment"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    STORY = "story"
    ACTIONS = [SERVER_CALL, LIKE, COMMENT, FOLLOW, UNFOLLOW, STORY]
    HOUR = "hour"
    DAY = "day"

    def __init__(self, iCerebro):
        self.logger = iCerebro.logger
        self.settings = iCerebro.settings
        self.enabled = self.settings.quota_supervisor_enabled
        self.sleep_after = self.settings.qs_sleep_after
        self.randomize_sleep_time = self.settings.qs_randomize_sleep_time
        self.max_extra_minutes = self.settings.qs_max_extra_sleep_minutes if self.settings.qs_max_extra_sleep_minutes else 5
        self.randomize_peak_number = self.settings.qs_randomize_peak_number
        self.random_range_from = self.settings.qs_random_range_from if self.settings.qs_random_range_from else 1
        self.random_range_to = self.settings.qs_random_range_to if self.settings.qs_random_range_to else 1

        self.peak_values_original = {
            self.SERVER_CALL: {
                self.HOUR: self.settings.qs_peak_server_calls_hourly,
                self.DAY: self.settings.qs_peak_server_calls_daily
            },
            self.LIKE: {
                self.HOUR: self.settings.qs_peak_likes_hourly,
                self.DAY: self.settings.qs_peak_likes_daily
            },
            self.COMMENT: {
                self.HOUR: self.settings.qs_peak_comments_hourly,
                self.DAY: self.settings.qs_peak_comments_daily
            },
            self.FOLLOW: {
                self.HOUR: self.settings.qs_peak_follows_hourly,
                self.DAY: self.settings.qs_peak_follows_daily
            },
            self.UNFOLLOW: {
                self.HOUR: self.settings.qs_peak_unfollows_hourly,
                self.DAY: self.settings.qs_peak_unfollows_daily
            },
            self.STORY: {
                self.HOUR: self.settings.qs_peak_story_hourly,
                self.DAY: self.settings.qs_peak_story_daily
            },
        }

        self.peak_values_current = deepcopy(self.peak_values_original)

        self.action_delays = {
            self.LIKE: self.settings.action_delays_like,
            self.COMMENT: self.settings.action_delays_comment,
            self.FOLLOW: self.settings.action_delays_follow,
            self.UNFOLLOW: self.settings.action_delays_unfollow,
            self.STORY: self.settings.action_delays_story
        }

        now = datetime.now()
        self.last_day = now.day
        self.last_hour = now.hour

        self.calls = {
            self.SERVER_CALL: {
                self.HOUR: 0,
                self.DAY: 0
            },
            self.LIKE: {
                self.HOUR: 0,
                self.DAY: 0
            },
            self.COMMENT: {
                self.HOUR: 0,
                self.DAY: 0
            },
            self.FOLLOW: {
                self.HOUR: 0,
                self.DAY: 0
            },
            self.UNFOLLOW: {
                self.HOUR: 0,
                self.DAY: 0
            },
            self.STORY: {
                self.HOUR: 0,
                self.DAY: 0
            },
        }

    def add_server_call(self, action: str = None):
        try:
            if not self.enabled:
                return
            self.check_time()
            self.calls[self.SERVER_CALL][self.HOUR] += 1
            self.calls[self.SERVER_CALL][self.DAY] += 1
            if action:
                self.calls[action][self.HOUR] += 1
                self.calls[action][self.DAY] += 1
        finally:
            self.sleep_after_action(action)

    def add_like(self):
        self.add_server_call(self.LIKE)

    def add_comment(self):
        self.add_server_call(self.COMMENT)

    def add_follow(self):
        self.add_server_call(self.FOLLOW)

    def add_unfollow(self):
        self.add_server_call(self.UNFOLLOW)

    def sleep_after_action(self, action):
        if not self.settings.action_delays_enabled or action not in self.action_delays:
            sleep(1)
        elif not self.settings.action_delays_randomize:
            sleep(self.action_delays[action])
        else:
            sleep(
                random.uniform(
                    self.action_delays[action]*self.settings.action_delays_random_range_from,
                    self.action_delays[action]*self.settings.action_delays_random_range_to
                )
            )

    def jump(self, action: str) -> bool:
        if not self.enabled:
            return False
        self.check_time()
        if not self.peak_values_current[action][self.DAY] and not self.peak_values_current[action][self.HOUR]:
            return False
        if (
                self.peak_values_current[action][self.DAY] and
                self.calls[action][self.DAY] >= self.peak_values_current[action][self.DAY]
        ):
            return True
        if (
                self.peak_values_current[action][self.HOUR] and
                self.calls[action][self.HOUR] >= self.peak_values_current[action][self.HOUR]
        ):
            if action in self.sleep_after:
                self.sleep_till_next_hour(action)
                return False
            else:
                return True
        return False

    def jump_like(self) -> bool:
        return self.jump(self.LIKE)

    def jump_comment(self) -> bool:
        return self.jump(self.COMMENT)

    def jump_follow(self) -> bool:
        return self.jump(self.FOLLOW)

    def jump_unfollow(self) -> bool:
        return self.jump(self.UNFOLLOW)

    def sleep_till_next_hour(self, action: str):
        now = datetime.now()
        delay = (60 - now.minute) * 60 + 60 - now.second
        if self.randomize_sleep_time:
            delay += random.randint(0, self.max_extra_minutes*60)
        self.logger.info(
            "Quota Supervisor: hourly {}s reached maximum allowed value. "
            "Sleeping {} minutes and {} seconds".format(
                action,
                int(delay/60),
                delay % 60
            )
        )
        sleep(delay)

    def check_time(self):
        now = datetime.now()
        if self.last_day != now.day:
            self.last_day = now.day

            for action in self.ACTIONS:
                self.calls[action][self.DAY] = 0

            if self.randomize_peak_number:
                for action in self.ACTIONS:
                    if self.peak_values_original[action][self.DAY]:
                        self.peak_values_current[action][self.DAY] = random.randrange(
                            int(self.peak_values_original[action][self.DAY]*self.random_range_from),
                            int(self.peak_values_original[action][self.DAY]*self.random_range_to)
                        )

        if self.last_hour != now.hour:
            self.last_hour = now.hour

            for action in self.ACTIONS:
                self.calls[action][self.HOUR] = 0

            if self.randomize_peak_number:
                for action in self.ACTIONS:
                    if self.peak_values_original[action][self.HOUR]:
                        self.peak_values_current[action][self.HOUR] = random.randrange(
                            int(self.peak_values_original[action][self.HOUR]*self.random_range_from),
                            int(self.peak_values_original[action][self.HOUR]*self.random_range_to)
                        )
