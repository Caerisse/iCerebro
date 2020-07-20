from django.shortcuts import render
from django.http import HttpResponse

from .models import Greeting

# Create your views here.
def index(request):
    # return HttpResponse('Hello from Python!')
    return render(request, "index.html")


def db(request):

    greeting = Greeting()
    greeting.save()

    greetings = Greeting.objects.all()

    return render(request, "db.html", {"greetings": greetings})


def register(request):
    return render(request, "register.html")

def login(request):
    return render(request, "login.html")

def logout(request):
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
