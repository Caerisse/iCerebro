import logging
import os
import socket
from contextlib import closing
from requests import get

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from rest_framework import status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, renderer_classes, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.response import Response

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
            return redirect("/bot/run/settings/{}/".format(bot_settings.instauser.username))
    else:
        bot_settings_form = BotSettingsForm(**form_args)

    return render(request, 'bot_settings.html', {'bot_settings_form': bot_settings_form})


@login_required
def bot_run_settings_view(request, username):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")
    try:
        bot_account = InstaUser.objects.get(username=username)
    except ObjectDoesNotExist:
        raise Http404("Bot does not exist")

    form_args = {}
    try:
        bot_run_settings = BotRunSettings.objects.get(bot=bot_account)
        form_args['instance'] = bot_run_settings
    except ObjectDoesNotExist:
        pass

    if request.POST:
        form_args['data'] = request.POST
        bot_run_settings_form = BotRunSettingsForm(**form_args)
        if bot_run_settings_form.is_valid():
            bot_run_settings = bot_run_settings_form.save(commit=False)
            bot_run_settings.bot = bot_account
            bot_run_settings.save()
            return redirect("/bot/run/{}/".format(bot_run_settings.bot.username))
    else:
        bot_run_settings_form = BotRunSettingsForm(**form_args)

    return render(request, 'bot_run_settings.html', {'bot_run_settings_form': bot_run_settings_form})


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
            running_with.abort = True
            running_with.save()
        else:
            try:
                bot_run_settings = BotRunSettings.objects.get(bot=bot_account)
            except ObjectDoesNotExist:
                raise Http404("No bot run settings for bot with username {}".format(username))
            running_with = BotSettings.objects.get(pk=request.POST['settings_name'])
            iCerebro = ICerebro(running_with, bot_run_settings)
            if not iCerebro.proxy:
                pass  # TODO: raise error
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
    bot_logs = StatusLog.objects.filter(bot_username=username)[:20]
    latest_logs = reversed(bot_logs)
    return render(request, 'latest_logs.html', {'latest_logs': latest_logs})


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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@login_required
def save_user_pub_key(request):
    if request.method != 'POST':
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        return Response({"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)

    if (
            not request.data["key"]
            or len(request.data["key"].split(" ")) < 2
            or request.data["key"].split(" ")[0] != "ssh-rsa"
    ):
        return Response({"error": "Provided key is not appropriate. Key: " + request.data["key"]}, status=status.HTTP_400_BAD_REQUEST)

    provided_key = request.data["key"].rstrip('\n')
    authorized_keys_path = os.getenv("HOME") + "/.ssh/authorized_keys"
    authorized_keys = open(authorized_keys_path, "a+")
    authorized_keys.seek(0)
    try:
        for line in authorized_keys:
            key = line.rstrip('\n')
            if key == provided_key:
                break
        else:
            authorized_keys.write(provided_key + "\n")
            print("Saved new ssh key")
    finally:
        authorized_keys.close()
    return Response({}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@login_required
def get_proxy_port(request, try_n=0):
    try:
        user = ICerebroUser.objects.get(user=request.user)
    except ObjectDoesNotExist:
        raise Http404("User does not exist")

    # Local ip for testing
    ip = '192.168.1.101'

    # Public IP
    #ip = get('https://api.ipify.org').text

    port = 0
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = s.getsockname()[1]

    try:
        proxy_address, created = ProxyAddress.objects.get_or_create(
            user=user,
            defaults={
                "host": ip,
                "port": port,
            }
        )
        return Response({"host": proxy_address.host, "port": proxy_address.port}, status.HTTP_200_OK)
    except IntegrityError:
        if try_n > 4:
            return Response({"error": "No free ports found, try again later"}, status.HTTP_503_SERVICE_UNAVAILABLE)
        get_proxy_port(request, try_n + 1)
