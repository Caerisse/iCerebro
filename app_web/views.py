from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from app_main.models import *


def index(request):
    return render(request, "index.html")


@login_required
def user_profile(request):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    return render(request, 'user_profile.html', {'user': user})


@login_required
def user_settings(request):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    return render(request, 'user_settings.html', {'user': user})


@login_required
def user_subscriptions(request):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    return render(request, 'user_subscriptions.html', {'user': user})


@login_required
def bots(request):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    return render(request, 'bots.html', {'user': user})


@login_required
def bot_settings(request, username, settings_name):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    try:
        bot_account = InstaUser.objects.get(username=username)
        bot_settings = BotSettings.objects.get(icerebrouser=user, instauser=bot_account, name=settings_name)
    except ObjectDoesNotExist:
        raise Http404("Bot does not exist")
    return render(request, 'bot_settings.html', {'bot_settings': bot_settings})


@login_required
def bot_run(request, username):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    try:
        bot_account = InstaUser.objects.get(username=username)
        bot_settings_list = BotSettings.objects.filter(icerebrouser=user, instauser=bot_account)
    except ObjectDoesNotExist:
        raise Http404("Bot does not exist")
    return render(request, 'bot_run.html', {'bot_settings_list': bot_settings_list})


@login_required
def bot_statics(request, username):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    try:
        bot_account = InstaUser.objects.get(username=username)
    except ObjectDoesNotExist:
        raise Http404("Bot does not exist")
    return render(request, 'bot_statics.html', {'bot_account': bot_account})
