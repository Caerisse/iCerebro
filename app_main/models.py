from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from multiselectfield import MultiSelectField


class ICerebroUser(models.Model):
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


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        ICerebroUser.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.icerebrouser.save()


class InstaUser(models.Model):
    date_checked = models.DateTimeField(auto_now_add=True)
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


class FollowRelation(models.Model):
    follower = models.ForeignKey(InstaUser, related_name='followers', on_delete=models.CASCADE)
    followed = models.ForeignKey(InstaUser, related_name='following', on_delete=models.CASCADE)

    def __str__(self):
        return "Relationship: {} follows {}".format(self.follower.username, self.followed.username)

    class Meta:
        verbose_name = "follow_relation"
        verbose_name_plural = "follow_relations"
        unique_together = ('follower', 'followed')


class Post(models.Model):
    date_posted = models.DateTimeField(null=False)
    instauser = models.ForeignKey(InstaUser, null=True, on_delete=models.SET_NULL)
    link = models.CharField(max_length=500, blank=False, unique=True)
    src = ArrayField(models.CharField(max_length=500, blank=True))
    caption = models.TextField(blank=True)
    likes = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    ig_desciption = ArrayField(models.TextField(blank=True), blank=True, null=True)
    objects_detected = ArrayField(models.TextField(blank=True), blank=True, null=True)
    classified_as = ArrayField(models.TextField(blank=True), blank=True, null=True)

    def __str__(self):
        return "Post by {}, link: {}".format(self.instauser.username, self.link)

    class Meta:
        verbose_name = "post"
        verbose_name_plural = "posts"


class Comment(models.Model):
    date_posted = models.DateTimeField(null=False)
    instauser = models.ForeignKey(InstaUser, on_delete=models.SET_NULL)
    post = models.ForeignKey(Post, on_delete=models.SET_NULL)
    text = models.TextField(blank=True)

    def __str__(self):
        return "Comment by {}, text: {}".format(self.instauser.username, self.text)

    class Meta:
        verbose_name = "comment"
        verbose_name_plural = "comments"
        unique_together = ('date_posted', 'instauser', 'post')


class BotSettings(models.Model):
    icerebrouser = models.ForeignKey(ICerebroUser, on_delete=models.CASCADE)
    instauser = models.ForeignKey(InstaUser, on_delete=models.SET_NULL)
    # TODO: encrypt
    password = models.TextField(blank=False)

    page_delay = models.IntegerField(default=5, validators=[MinValueValidator(0)])
    # proxy_address =
    # proxy_port =
    disable_image_load = models.BooleanField(default=True)
    want_check_browser = models.BooleanField(default=False)
    CHOICES_BYPASS = ((1, 'EMAIL'), (2, 'SMS'))
    bypass_security_challenge_using = models.IntegerField(choices=CHOICES_BYPASS, default=1)

    dont_include = ArrayField(models.TextField(blank=True), blank=True, null=True)
    white_list = ArrayField(models.TextField(blank=True), blank=True, null=True)
    # TODO: check how this is used
    # self.blacklist = {"enabled": "True", "campaign": ""}
    # self.automatedFollowedPool = {"all": [], "eligible": []}

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

    comments = ArrayField(models.TextField(blank=True), blank=True, null=True,
                          default=["Cool!", "Nice!", "Looks good!"])
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
    CHOICES_MEDIA = ((1, 'PHOTO'), (2, 'CAROUSEL'), (3, 'VIDEO'))
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
        (1, "Advertising Agency"),
        (2, "Advertising/Marketing"),
        (3, "Art"),
        (4, "Art Gallery"),
        (5, "Art Museum"),
        (6, "Artist"),
        (7, "Arts & Entertainment"),
        (8, "Arts & Humanities Website"),
        (9, "Athlete"),
        (10, "Auto Dealers"),
        (11, "Business & Utility Services"),
        (12, "Clothing Store"),
        (13, "Community"),
        (14, "Community Organization"),
        (15, "Company"),
        (16, "Consulting Agency"),
        (17, "Content & Apps"),
        (18, "Creators & Celebrities"),
        (19, "Education"),
        (20, "Food & Personal Goods"),
        (21, "General Interest"),
        (22, "Graphic Designer"),
        (23, "Home Goods Stores"),
        (24, "Home Services"),
        (25, "Jewelry/Watches"),
        (26, "Lifestyle Services"),
        (27, "Local Business"),
        (28, "Local Events"),
        (29, "Management Service"),
        (30, "Media/News Company"),
        (31, "Non-Profits & Religious Organizations"),
        (32, "Party Entertainment Service"),
        (33, "Personal Goods & General Merchandise Stores"),
        (34, "Photographer"),
        (35, "Photography Videography"),
        (36, "Product/Service"),
        (37, "Professional Service"),
        (38, "Professional Sports Team"),
        (39, "Public Figure"),
        (40, "Public Relations Agency"),
        (41, "Publishers"),
        (42, "Restaurants"),
        (43, "Ski Resort"),
        (44, "Sport"),
        (45, "Sports & Recreation"),
        (46, "Transportation & Accomodation Services"),
        (47, "Travel Agency"),
        (48, "Wine/Spirits"),
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
        (1, "LATIN"),
        (2, "GREEK"),
        (3, "CYRILLIC"),
        (4, "ARABIC"),
        (5, "HEBREW"),
        (6, "CJK"),
        (7, "HANGUL"),
        (8, "HIRAGANA"),
        (9, "KATAKANA"),
        (10, "THAI"),
    )
    mandatory_language = models.BooleanField(default=False)
    mandatory_character = MultiSelectField(choices=CHOICES_LANGUAGE, blank=True, null=True)

    use_image_analysis = models.BooleanField(default=False)
    # classification_model_name
    # detection_model_name

    action_delays_enabled = models.BooleanField(default=False)
    action_delays_like = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    action_delays_comment = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    action_delays_follow = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    action_delays_unfollow = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    action_delays_story = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    action_delays_randomize = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    action_delays_random_range_from = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    action_delays_random_range_to = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    action_delays_safety_match = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True)


class BotScheduledPost(models.Model):
    pass

