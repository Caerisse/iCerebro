from django.urls import path, include
from django.contrib import admin
from rest_framework.authtoken.views import obtain_auth_token

import app_web.views

admin.autodiscover()

urlpatterns = [
    path("", app_web.views.index, name="index"),
    path("admin/", admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('rest-auth/token', obtain_auth_token),
    path("rest-auth/", include("dj_rest_auth.urls")),
    path("rest-auth/registration/", include("dj_rest_auth.registration.urls")),
    path("subscriptions/",
         app_web.views.subscriptions, name="subscriptions"),
    path("accounts/register/",
         app_web.views.register, name="register"),
    path("accounts/profile/",
         app_web.views.user_profile, name="user_profile"),
    path("accounts/settings/",
         app_web.views.user_settings, name="user_settings"),
    path("accounts/subscriptions/",
         app_web.views.user_subscriptions, name="user_subscriptions"),
    path("bots/", app_web.views.bots, name="bots"),
    path("bot/settings/",
         app_web.views.bot_settings_view, name="bot_settings_new"),
    path("bot/settings/<str:username>/<str:settings_name>/",
         app_web.views.bot_settings_view, name="bot_settings"),
    path("bot/run/settings/<str:username>/",
         app_web.views.bot_run_settings_view, name="bot_run_settings"),
    path("bot/run/<str:username>/",
         app_web.views.bot_run, name="bot_run"),
    path("bot/run/<str:username>/get_latest_logs/",
         app_web.views.get_latest_logs, name="bot_run"),
    path("bot/statics/<str:username>/",
         app_web.views.bot_statics, name="bot_statics"),
    path("proxy/pubkey/",
         app_web.views.save_user_pub_key, name="save_user_pub_key"),
    path("proxy/address/",
         app_web.views.get_proxy_port, name="get_proxy_port"),
]
