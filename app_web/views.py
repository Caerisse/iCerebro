from django.shortcuts import render
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required


def index(request):
    return render(request, "index.html")


@login_required
def user_profile(request):
    return render(request, "user_profile.html")


@login_required
def user_settings(request):
    return render(request, "user_settings.html")


@login_required
def user_subscriptions(request):
    return render(request, "user_subscriptions.html")


@login_required
def bot_settings(request):
    return render(request, "bot_settings.html")


@login_required
def bot_run(request):
    return render(request, "bot_run.html")


@login_required
def bot_statics(request):
    return render(request, "bot_statics.html")
