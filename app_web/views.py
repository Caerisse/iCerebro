from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from app_db_logger.models import StatusLog

from app_main.models import *
from app_web.forms import *


def index(request):
    return render(request, "index.html")


def register(response):
    if response.method == "POST":
        form = RegisterForm(response.POST)
        if form.is_valid():
            form.save()
        return redirect("/registration/login.html")
    else:
        form = RegisterForm()
    return render(response, "registration/register.html", {"form": form})


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


def user_subscriptions(request):
    try:
        user = ICerebroUser.objects.get(user=request.user)
        return render(request, 'user_subscriptions.html', {'user': user})
    except ObjectDoesNotExist:
        return render(request, 'subscriptions.html')


@login_required
def bots(request):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    bot_settings_list = []
    try:
        bot_settings_list = BotSettings.objects.filter(icerebrouser=user)
    except ObjectDoesNotExist:
        pass
        # User will have the option to register a new bot
    return render(request, 'bots.html', {'bot_settings_list': bot_settings_list})


@login_required
def bot_settings_view(request, username=None, settings_name=None):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    form_args = {}
    if username is not None and settings_name is not None:
        try:
            bot_account = InstaUser.objects.get(username=username)
            bot_settings = BotSettings.objects.get(icerebrouser=user, instauser=bot_account, name=settings_name)
            form_args['instance'] = bot_settings
        except ObjectDoesNotExist:
            raise Http404("Bot does not exist")
    if request.POST:
        form_args['data'] = request.POST
        bot_settings_form = BotSettingsForm(**form_args)
        if bot_settings_form.is_valid():
            bot_settings = bot_settings_form.save(commit=True)
            bot_settings.icerebrouser = user
            bot_settings.instauser, _ = InstaUser.objects.get_or_create(username=bot_settings.insta_username)
            bot_settings.save()
            return redirect("/bot/run/{}/".format(bot_settings.instauser.username))
    else:
        bot_settings_form = BotSettingsForm(**form_args)

    return render(request, 'bot_settings.html', {'bot_settings_form': bot_settings_form})


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
    bot_logs = StatusLog.objects.filter(bot_username=bot_account.instauser.username)[:10]
    latest_logs = reversed(bot_logs)
    return render(request, 'bot_run.html',
                  {'bot_settings_list': bot_settings_list, 'latest_logs': latest_logs}
                  )


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
