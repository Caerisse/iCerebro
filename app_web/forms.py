from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from app_main.models import *


class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class BotSettingsForm(forms.ModelForm):
    insta_username = forms.CharField()

    class Meta:
        model = BotSettings
        fields = '__all__'
        exclude = ['icerebrouser', 'running', 'instauser']
