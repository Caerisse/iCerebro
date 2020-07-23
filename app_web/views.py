from django.shortcuts import render
from django.contrib.auth import logout


def index(request):
    return render(request, "index.html")


def register(request):
    return render(request, "register.html")


def login(request):
    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return render(request, "logout.html")


def user_settings(request):
    return render(request, "user_settings.html")


def user_subscriptions(request):
    return render(request, "user_subscriptions.html")


def bot_settings(request):
    return render(request, "bot_settings.html")


def bot_run(request):
    return render(request, "bot_run.html")


def bot_statics(request):
    return render(request, "bot_statics.html")
