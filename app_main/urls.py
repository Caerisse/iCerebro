from django.urls import path, include

from django.contrib import admin

admin.autodiscover()

import app_web.views

urlpatterns = [
    path("", app_web.views.index, name="index"),
    path("admin/", admin.site.urls),
    path("db/", app_web.views.db, name="db"),
    path("register/", app_web.views.register, name="register"),
    path("login/", app_web.views.login, name="login"),
    path("logout/", app_web.views.logout, name="logout"),
    path("user_settings/<str:username>/",
         app_web.views.user_settings, name="user_settings"),
    path("user_subscriptions/<str:username>/",
         app_web.views.user_subscriptions, name="user_subscriptions"),
    path("bot_settings/<str:instagramusername>/",
         app_web.views.bot_settings, name="bot_settings"),
    path("bot_run/<str:instagramusername>/",
         app_web.views.bot_run, name="bot_run"),
    path("bot_statics/<str:instagramusername>/",
         app_web.views.bot_statics, name="bot_statics"),
]
