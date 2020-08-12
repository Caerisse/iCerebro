from django.contrib import admin

from app_main.models import *

admin.site.register(ICerebroUser)
admin.site.register(InstaUser)
admin.site.register(FollowRelation)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(BotCookies)
admin.site.register(BotFollowed)
admin.site.register(BotBlacklist)
admin.site.register(BotSettings)
admin.site.register(BotScheduledPost)
