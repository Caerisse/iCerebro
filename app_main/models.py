from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from multiselectfield import MultiSelectField


class ICerebroUser(models.Model):
    objects = models.Manager()

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # all other fields must have blank=True option
    # TODO: add fixed options
    subscription_type = models.TextField(blank=True, null=True)
    subscription_end = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = "icerebrouser"
        verbose_name_plural = "icerebrousers"
        db_table = 'icerebro_users'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        ICerebroUser.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.icerebrouser.save()


class InstaUser(models.Model):
    objects = models.Manager()

    date_checked = models.DateTimeField(auto_now=True)
    username = models.CharField(max_length=50, unique=True)
    followers_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    following_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    posts_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    following = models.ManyToManyField('self',
                                       through='FollowRelation',
                                       symmetrical=False,
                                       related_name='followers')

    def add_follower(self, instauser):
        relation, created = FollowRelation.objects.get_or_create(followed=self, follower=instauser)
        return relation

    def add_following(self, instauser):
        relation, created = FollowRelation.objects.get_or_create(followed=instauser, follower=self)
        return relation

    def remove_follower(self, instauser):
        FollowRelation.objects.filter(followed=self, follower=instauser).delete()
        return

    def remove_following(self, instauser):
        FollowRelation.objects.filter(followed=instauser, follower=self).delete()
        return

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "instauser"
        verbose_name_plural = "instausers"
        db_table = "insta_users"


class FollowRelation(models.Model):
    objects = models.Manager()

    follower = models.ForeignKey(InstaUser, related_name='follow_relations_is_follower', on_delete=models.CASCADE)
    followed = models.ForeignKey(InstaUser, related_name='follow_relations_is_followed', on_delete=models.CASCADE)

    def __str__(self):
        return "Relationship: {} follows {}".format(self.follower.username, self.followed.username)

    class Meta:
        unique_together = ('follower', 'followed')
        db_table = "follow_relations"


class Post(models.Model):
    objects = models.Manager()

    date_posted = models.DateTimeField()
    instauser = models.ForeignKey(InstaUser, null=True, on_delete=models.SET_NULL, related_name='posts')
    link = models.CharField(max_length=500, unique=True)
    src = ArrayField(models.CharField(max_length=500, blank=True), blank=True, null=True)
    caption = models.TextField(blank=True)
    likes = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    ig_desciption = ArrayField(models.TextField(blank=True), blank=True, null=True)
    objects_detected = ArrayField(models.TextField(blank=True), blank=True, null=True)
    classified_as = ArrayField(models.TextField(blank=True), blank=True, null=True)

    def __str__(self):
        return "Post by {}, link: {}".format(self.instauser.username, self.link)

    class Meta:
        db_table = "posts"


class Comment(models.Model):
    objects = models.Manager()

    date_posted = models.DateTimeField(null=False)
    instauser = models.ForeignKey(InstaUser, on_delete=models.SET_NULL, related_name='comments', null=True)
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, related_name='comments', null=True)
    text = models.TextField(blank=True)

    def __str__(self):
        return "Comment by {}, text: {}".format(self.instauser.username, self.text)

    class Meta:
        unique_together = ('date_posted', 'instauser', 'post')
        db_table = "comments"


class BotCookies(models.Model):
    objects = models.Manager()

    bot = models.ForeignKey(InstaUser, on_delete=models.CASCADE, related_name='cookies')
    date = models.DateTimeField(auto_now=True)
    cookie_name = models.TextField()
    cookie_value = models.TextField()

    class Meta:
        unique_together = ('bot', 'cookie_name')
        db_table = "cookies"


class BotFollowed(models.Model):
    objects = models.Manager()

    bot = models.ForeignKey(InstaUser, on_delete=models.CASCADE, related_name='bot')
    followed = models.ForeignKey(InstaUser, on_delete=models.CASCADE, related_name='followed')
    times = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    date = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('bot', 'followed')
        db_table = "bot_followed"


class BotBlacklist(models.Model):
    objects = models.Manager()

    bot = models.ForeignKey(InstaUser, on_delete=models.CASCADE, related_name='blacklist')
    instauser = models.ForeignKey(InstaUser, on_delete=models.CASCADE, related_name='blacklisted')
    date = models.DateTimeField(auto_now_add=True)
    campaign = models.TextField()
    action = models.TextField()

    class Meta:
        unique_together = ('bot', 'instauser', 'campaign', 'action')
        db_table = "bot_blacklists"


class BotSettings(models.Model):
    objects = models.Manager()

    icerebrouser = models.ForeignKey(ICerebroUser, on_delete=models.CASCADE, related_name='bot_settings', null=True)
    instauser = models.ForeignKey(InstaUser, on_delete=models.CASCADE, related_name='bot_settings', null=True)
    name = models.CharField(max_length=100, blank=False)
    # TODO: encrypt
    password = models.CharField(max_length=50, blank=False)

    abort = models.BooleanField(default=False)
    running = models.BooleanField(default=False)

    page_delay = models.IntegerField(default=5, validators=[MinValueValidator(0)])

    use_proxy = models.BooleanField(default=False)
    proxy_address = models.CharField(max_length=20, blank=True)
    proxy_port = models.TextField(max_length=5, blank=True)

    disable_image_load = models.BooleanField(default=True)
    want_check_browser = models.BooleanField(default=False)

    CHOICES_BYPASS = (('EMAIL', 'Email'), ('SMS', 'SMS'))
    bypass_security_challenge_using = models.CharField(choices=CHOICES_BYPASS, default="EMAIL", max_length=5)

    dont_include = ArrayField(models.TextField(blank=True), blank=True, null=True)
    blacklist_campaign = models.TextField(blank=True)
    # TODO: check usage
    white_list = ArrayField(models.TextField(blank=True), blank=True, null=True)

    follow_times = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    share_times = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    comment_times = models.IntegerField(default=1, validators=[MinValueValidator(0)])

    do_follow = models.BooleanField(default=False)
    follow_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])

    do_like = models.BooleanField(default=False)
    like_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])

    do_story = models.BooleanField(default=False)
    story_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    story_simulate = models.BooleanField(default=False)

    do_comment = models.BooleanField(default=False)
    comment_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])

    comments = ArrayField(models.TextField(blank=True), blank=True, null=True)
    photo_comments = ArrayField(models.TextField(blank=True), blank=True, null=True)
    video_comments = ArrayField(models.TextField(blank=True), blank=True, null=True)
    do_reply_to_comments = models.BooleanField(default=False)
    reply_to_comments_percent = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    comment_replies = ArrayField(models.TextField(blank=True), blank=True, null=True)
    photo_comment_replies = ArrayField(models.TextField(blank=True), blank=True, null=True)
    video_comment_replies = ArrayField(models.TextField(blank=True), blank=True, null=True)

    hashtags = ArrayField(models.TextField(blank=True), blank=True, null=True)
    location_hashtags = ArrayField(models.TextField(blank=True), blank=True, null=True)
    similar_accounts = ArrayField(models.TextField(blank=True), blank=True, null=True)

    dont_like = ArrayField(models.TextField(blank=True), blank=True, null=True)
    mandatory_words = ArrayField(models.TextField(blank=True), blank=True, null=True)
    ignore_if_contains = ArrayField(models.TextField(blank=True), blank=True, null=True)
    ignore_users = ArrayField(models.TextField(blank=True), blank=True, null=True)

    user_interact_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    user_interact_amount = models.IntegerField(default=3, validators=[MinValueValidator(0)])
    CHOICES_MEDIA = (('PHOTO', 'Photos'), ('CAROUSEL', 'Carousel'), ('VIDEO', 'Videos'))
    user_interact_media = MultiSelectField(choices=CHOICES_MEDIA, blank=True, null=True,
                                           default='1,2,3')
    user_interact_random = models.BooleanField(default=False)

    delimit_liking = models.BooleanField(default=False)
    max_likes = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    min_likes = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)

    delimit_commenting = False
    max_comments = 35
    min_comments = 0
    comments_mandatory_words = []

    delimit_by_numbers = models.BooleanField(default=False)
    potency_ratio = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    max_followers = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    max_following = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    min_followers = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    min_following = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    max_posts = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    min_posts = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)

    CHOICES_BUSINESS = (
        ('Advertising Agency', 'Advertising Agency'),
        ('Advertising/Marketing', 'Advertising/Marketing'),
        ('Art', 'Art'),
        ('Art Gallery', 'Art Gallery'),
        ('Art Museum', 'Art Museum'),
        ('Artist', 'Artist'),
        ('Arts & Entertainment', 'Arts & Entertainment'),
        ('Arts & Humanities Website', 'Arts & Humanities Website'),
        ('Athlete', 'Athlete'),
        ('Auto Dealers', 'Auto Dealers'),
        ('Business & Utility Services', 'Business & Utility Services'),
        ('Clothing Store', 'Clothing Store'),
        ('Community', 'Community'),
        ('Community Organization', 'Community Organization'),
        ('Company', 'Company'),
        ('Consulting Agency', 'Consulting Agency'),
        ('Content & Apps', 'Content & Apps'),
        ('Creators & Celebrities', 'Creators & Celebrities'),
        ('Education', 'Education'),
        ('Food & Personal Goods', 'Food & Personal Goods'),
        ('General Interest', 'General Interest'),
        ('Graphic Designer', 'Graphic Designer'),
        ('Home Goods Stores', 'Home Goods Stores'),
        ('Home Services', 'Home Services'),
        ('Jewelry/Watches', 'Jewelry/Watches'),
        ('Lifestyle Services', 'Lifestyle Services'),
        ('Local Business', 'Local Business'),
        ('Local Events', 'Local Events'),
        ('Management Service', 'Management Service'),
        ('Media/News Company', 'Media/News Company'),
        ('Non-Profits & Religious Organizations',
         'Non-Profits & Religious Organizations'),
        ('Party Entertainment Service', 'Party Entertainment Service'),
        ('Personal Goods & General Merchandise Stores',
         'Personal Goods & General Merchandise Stores'),
        ('Photographer', 'Photographer'),
        ('Photography Videography', 'Photography Videography'),
        ('Product/Service', 'Product/Service'),
        ('Professional Service', 'Professional Service'),
        ('Professional Sports Team', 'Professional Sports Team'),
        ('Public Figure', 'Public Figure'),
        ('Public Relations Agency', 'Public Relations Agency'),
        ('Publishers', 'Publishers'),
        ('Restaurants', 'Restaurants'),
        ('Ski Resort', 'Ski Resort'),
        ('Sport', 'Sport'),
        ('Sports & Recreation', 'Sports & Recreation'),
        ('Transportation & Accomodation Services',
         'Transportation & Accomodation Services'),
        ('Travel Agency', 'Travel Agency'),
        ('Wine/Spirits', 'Wine/Spirits')
    )

    skip_business = models.BooleanField(default=False)
    skip_business_categories = MultiSelectField(choices=CHOICES_BUSINESS, blank=True, null=True)
    dont_skip_business_categories = MultiSelectField(choices=CHOICES_BUSINESS, blank=True, null=True)
    skip_non_business = models.BooleanField(default=False)
    skip_no_profile_pic = models.BooleanField(default=True)
    skip_private = models.BooleanField(default=True)
    skip_bio_keyword = []
    skip_business_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    skip_no_profile_pic_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    skip_private_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])

    # relationship_data = {username: {"all_following": [], "all_followers": []}}
    # simulation = {"enabled": True, "percentage": 100}
    CHOICES_LANGUAGE = (
        ("LATIN", "Latin"),
        ("GREEK", "Greek"),
        ("CYRILLIC", "Cyrillic"),
        ("ARABIC", "Arabic"),
        ("HEBREW", "Hebrew"),
        ("CJK", "CJK"),
        ("HANGUL", "Hangul"),
        ("HIRAGANA", "Hiragana"),
        ("KATAKANA", "Katakana"),
        ("THAI", "Thai"),
        ("MATHEMATICAL", "Mathematical")
    )
    mandatory_language = models.BooleanField(default=False)
    mandatory_character = MultiSelectField(choices=CHOICES_LANGUAGE, blank=True, null=True)

    use_image_analysis = models.BooleanField(default=False)
    # classification_model_name
    # detection_model_name

    action_delays_enabled = models.BooleanField(default=True)
    action_delays_like = models.IntegerField(validators=[MinValueValidator(1)], default=2)
    action_delays_comment = models.IntegerField(validators=[MinValueValidator(1)], default=2)
    action_delays_follow = models.IntegerField(validators=[MinValueValidator(1)], default=3)
    action_delays_unfollow = models.IntegerField(validators=[MinValueValidator(1)], default=7)
    action_delays_story = models.IntegerField(validators=[MinValueValidator(1)], default=3)
    action_delays_randomize = models.BooleanField(default=True)
    action_delays_random_range_from = models.FloatField(
        validators=[MinValueValidator(0.5), MaxValueValidator(1)],
        default=0.75)
    action_delays_random_range_to = models.FloatField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=1.25)

    CHOICES_SLEEP = (
        ('like', 'like'),
        ('comment', 'comment'),
        ('follow', 'follow'),
        ('unfollow', 'unfollow'),
        ('server_call', 'server_call')
    )
    quota_supervisor_enabled = models.BooleanField(default=True),
    qs_sleep_after = MultiSelectField(choices=CHOICES_SLEEP, blank=True, null=True)
    qs_randomize_sleep_time = models.BooleanField(default=True)
    qs_max_extra_sleep_minutes = models.IntegerField(
        validators=[MinValueValidator(0)], default=10, blank=True, null=True)
    qs_peak_server_calls_hourly = models.IntegerField(
        validators=[MinValueValidator(0)], default=None, blank=True, null=True)
    qs_peak_server_calls_daily = models.IntegerField(
        validators=[MinValueValidator(0)], default=4700, blank=True, null=True)
    qs_peak_likes_hourly = models.IntegerField(
        validators=[MinValueValidator(0)], default=57, blank=True, null=True)
    qs_peak_likes_daily = models.IntegerField(
        validators=[MinValueValidator(0)], default=585, blank=True, null=True)
    qs_peak_comments_hourly = models.IntegerField(
        validators=[MinValueValidator(0)], default=21, blank=True, null=True)
    qs_peak_comments_daily = models.IntegerField(
        validators=[MinValueValidator(0)], default=182, blank=True, null=True)
    qs_peak_follows_hourly = models.IntegerField(
        validators=[MinValueValidator(0)], default=48, blank=True, null=True)
    qs_peak_follows_daily = models.IntegerField(
        validators=[MinValueValidator(0)], default=None, blank=True, null=True)
    qs_peak_unfollows_hourly = models.IntegerField(
        validators=[MinValueValidator(0)], default=35, blank=True, null=True)
    qs_peak_unfollows_daily = models.IntegerField(
        validators=[MinValueValidator(0)], default=402, blank=True, null=True)
    qs_peak_story_hourly = models.IntegerField(
        validators=[MinValueValidator(0)], default=None, blank=True, null=True)
    qs_peak_story_daily = models.IntegerField(
        validators=[MinValueValidator(0)], default=4700, blank=True, null=True)
    qs_randomize_peak_number = models.BooleanField(default=True, blank=True, null=True)
    qs_random_range_from = models.FloatField(
        validators=[MinValueValidator(0.5), MaxValueValidator(1)],
        default=0.75, blank=True, null=True)
    qs_random_range_to = models.FloatField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=1.25, blank=True, null=True)

    def __str__(self):
        return "Bot Settings for account {}, settings name: {}".format(
            self.instauser.username if self.instauser is not None else None,
            self.name)

    class Meta:
        unique_together = ('instauser', 'name')
        db_table = "bot_settings"


class BotScheduledPost(models.Model):
    objects = models.Manager()

    bot = models.ForeignKey(InstaUser, on_delete=models.CASCADE, related_name="scheduled_posts")
    date = models.DateTimeField(auto_now_add=True)
    images_links = ArrayField(models.CharField(max_length=500))
    caption = models.TextField(blank=True)

    class Meta:
        db_table = "bot_scheduled_post"


class BotRunSettings(models.Model):
    objects = models.Manager()

    bot = models.OneToOneField(InstaUser, on_delete=models.CASCADE, related_name="run_settings")

    CHOICES_ACTIONS = (
        ('None', 'None'),
        ('like_by_tags', 'Like by tags'),
        ('like_by_users', 'Like by users'),
        ('like_by_feed', 'Like by feed'),
        ('like_by_location', 'Like by location'),
        ('follow_user_follow', 'Follow user follow'),
        ('follow_by_list', 'Follow by list'),
        ('follow_by_tag', 'Follow by tag'),
        ('follow_by_locations', 'Follow by locations'),
        ('unfollow_users', 'Unfollow users')
    )
    do_from_00 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_01 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_02 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_03 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_04 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_05 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_06 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_07 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_08 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_09 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_10 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_11 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_12 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_13 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_14 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_15 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_16 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_17 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_18 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_19 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_20 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_21 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_22 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)
    do_from_23 = models.CharField(choices=CHOICES_ACTIONS, default='None', max_length=30)

    # Like by Tags
    # Will randomly order hashtags in BotSettings and like amount_per_tag before moving to the next
    like_by_tags_settings_amount_per_tag = models.IntegerField(validators=[MinValueValidator(1)], default=10)
    like_by_tags_settings_skip_top_post = models.BooleanField(default=False)
    # Like by Users
    like_by_users_settings_usernames = ArrayField(models.TextField())
    like_by_users_settings_amount = models.IntegerField(validators=[MinValueValidator(1)], default=3)
    like_by_users_settings_validated = models.BooleanField(default=False)
    # Like by Feed
    like_by_feed_settings_amount = models.IntegerField(validators=[MinValueValidator(1)], default=30)
    # Like by Location
    # Same as like by tags but using locations_hashtags
    like_by_location_settings_amount_per_tag = models.IntegerField(validators=[MinValueValidator(1)], default=3)
    like_by_location_settings_skip_top_post = models.BooleanField(default=False)
    # Follow user Follow
    # Follow user that follow or are followed by users in similar account list in BotSettings
    CHOICES_WHAT = (
        ('followers', 'Followers'),
        ('followings', 'Followings'),
    )
    follow_user_follow_settings_what = models.CharField(choices=CHOICES_WHAT, default='followers', max_length=20)
    follow_user_follow_settings_amount = models.IntegerField(validators=[MinValueValidator(1)], default=10)
    follow_user_follow_settings_randomize = models.BooleanField(default=False)
    # Follow by list
    follow_by_list_settings_usernames = ArrayField(models.TextField())
    follow_by_list_settings_validated = models.BooleanField(default=False)
    # Follow by tag
    # Same as like by tag but will follow users instead of liking their images
    follow_by_tags_settings_amount_per_tag = models.IntegerField(validators=[MinValueValidator(1)], default=10)
    follow_by_tags_settings_skip_top_post = models.BooleanField(default=False)
    # Like by Location
    # Same as follow by tags but using locations_hashtags
    follow_by_locations_settings_amount_per_tag = models.IntegerField(validators=[MinValueValidator(1)], default=10)
    follow_by_locations_settings_skip_top_post = models.BooleanField(default=False)
    # Unfollow users
    # unfollows users in selected list and track.
    # If List is Followed by bot then you can choose to unfollow only users  that the bot followed
    # more than unfollow_users_settings_after_hours hours.
    # If you choose to not unfollow active users the bot will check the users who liked your lasts
    # unfollow_users_settings_posts_to_check with the given boundary, if none it gill grab all users, if
    # 0 it will grab the visible users when clicking to see who liked the image, else will grab users until it has
    # the requested number or all users
    CHOICES_LIST = (
        ('all', 'All'),
        ('iCerebro_followed', 'Followed by bot'),
    )
    CHOICES_TRACK = (
        ('all', 'All'),
        ('nonfollowers', 'Non Followers'),
    )
    unfollow_users_settings_amount = models.IntegerField(validators=[MinValueValidator(1)], default=10)
    unfollow_users_settings_list = models.CharField(choices=CHOICES_LIST, default='iCerebro_followed', max_length=20)
    unfollow_users_settings_track = models.CharField(choices=CHOICES_TRACK, default='nonfollowers', max_length=20)
    unfollow_users_settings_after_hours = models.IntegerField(validators=[MinValueValidator(0)], default=48)
    unfollow_users_settings_dont_unfollow_active_users = models.BooleanField(default=False)
    unfollow_users_settings_posts_to_check = models.IntegerField(validators=[MinValueValidator(1)], default=3)
    unfollow_users_settings_boundary_to_check = models.IntegerField(validators=[MinValueValidator(0)],
                                                                    default=None, null=True)

    class Meta:
        db_table = "bot_run_settings"
