from django.urls import path, include
from django.contrib import admin

admin.autodiscover()

import app_web.views

urlpatterns = [
    path("", app_web.views.index, name="index"),
    path("admin/", admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path("accounts/profile/<str:username>",
         app_web.views.user_profile, name="user_profile"),
    path("accounts/settings/<str:username>/",
         app_web.views.user_settings, name="user_settings"),
    path("accounts/subscriptions/<str:username>/",
         app_web.views.user_subscriptions, name="user_subscriptions"),
    path("bot/settings/<str:instausername>/",
         app_web.views.bot_settings, name="bot_settings"),
    path("bot/run/<str:instausername>/",
         app_web.views.bot_run, name="bot_run"),
    path("bot/statics/<str:instausername>/",
         app_web.views.bot_statics, name="bot_statics"),
]
