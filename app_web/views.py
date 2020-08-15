from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from app_db_logger.models import StatusLog

from app_main.models import *
from app_web.forms import *
from iCerebro import ICerebro


def index(request):
    return render(request, "index.html")


def subscriptions(request):
    return render(request, 'subscriptions.html')


def register(request):
    form_args = {}
    if request.method == "POST":
        form_args['data'] = request.POST
        form = RegisterForm(**form_args)
        if form.is_valid():
            print('valid')
            form.save()
            return redirect("/accounts/login")
    else:
        form = RegisterForm(**form_args)
    return render(request, "registration/register.html", {"form": form})


@login_required
def user_profile(request):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    return render(request, 'user_profile.html', {'ice_user': user})


@login_required
def user_settings(request):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    return render(request, 'user_settings.html', {'ice_user': user})


@login_required
def user_subscriptions(request):
    try:
        user = ICerebroUser.objects.get(user=request.user)
        return render(request, 'user_subscriptions.html', {'ice_user': user})
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    

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
        except ObjectDoesNotExist:
            raise Http404("Bot does not exist")
        try:
            bot_settings = BotSettings.objects.get(icerebrouser=user, instauser=bot_account, name=settings_name)
            form_args['instance'] = bot_settings
        except ObjectDoesNotExist:
            raise Http404("Bot settings does not exist")
    if request.POST:
        form_args['data'] = request.POST
        insta_username = form_args['data']['insta_username']
        bot_settings_form = BotSettingsForm(**form_args)
        if bot_settings_form.is_valid():
            bot_settings = bot_settings_form.save(commit=False)
            bot_settings.icerebrouser = user
            bot_settings.instauser, _ = InstaUser.objects.get_or_create(username=insta_username)
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
        bot_settings_name_list = []
        running_with = None
        bot_account = InstaUser.objects.get(username=username)
    except ObjectDoesNotExist:
        raise Http404("Bot does not exist")
    bot_settings_list = BotSettings.objects.filter(icerebrouser=user, instauser=bot_account)
    for bot_settings in bot_settings_list:
        bot_settings_name_list.append((bot_settings.pk, bot_settings.name))
        if bot_settings.running:
            running_with = bot_settings
    if not bot_settings_name_list:
        raise Http404("No bot with username {} registered in your account".format(username))
    bot_run_form = BotRunForm(tuple(bot_settings_name_list))
    if request.POST:
        if running_with:
            iCerebro = ICerebro(running_with)
            iCerebro.stop()
            running_with = None
        else:
            running_with = BotSettings.objects.get(pk=request.POST['settings_name'])
            iCerebro = ICerebro(running_with)
            iCerebro.start()
    return render(request, 'bot_run.html',
                  {
                      'bot_username': username,
                      'bot_run_form': bot_run_form,
                      'running_with': running_with.name if running_with else None
                  }
                  )


@login_required
def get_latest_logs(request, username):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    try:
        bot_account = InstaUser.objects.get(username=username)
        BotSettings.objects.get(icerebrouser=user, instauser=bot_account)
    except ObjectDoesNotExist:
        raise Http404("No bot with username {} registered in your account".format(username))
    bot_logs = StatusLog.objects.filter(bot_username=username)[:10]
    latest_logs = reversed(bot_logs)
    return HttpResponse(latest_logs)


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
