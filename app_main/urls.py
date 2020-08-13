from django.urls import path, include
from django.contrib import admin

admin.autodiscover()

import app_web.views

urlpatterns = [
    path("", app_web.views.index, name="index"),
    path("admin/", admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path("accounts/register/",
         app_web.views.register, name="register"),
    path("accounts/profile/",
         app_web.views.user_profile, name="user_profile"),
    path("accounts/settings/",
         app_web.views.user_settings, name="user_settings"),
    path("accounts/subscriptions/",
         app_web.views.user_subscriptions, name="user_subscriptions"),
    path("bots/", app_web.views.bots, name="bots"),
    path("bot/settings/<str:username>/<str:settings_name>/",
         app_web.views.bot_settings_view, name="bot_settings"),
    path("bot/run/<str:username>/",
         app_web.views.bot_run, name="bot_run"),
    path("bot/statics/<str:username>/",
         app_web.views.bot_statics, name="bot_statics"),
]
