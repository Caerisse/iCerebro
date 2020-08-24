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
        exclude = ['icerebrouser', 'abort', 'running', 'instauser']


class BotRunForm(forms.Form):
    settings_name = forms.ChoiceField()

    def __init__(self, bot_settings_name_list, *args, **kwargs):
        super(BotRunForm, self).__init__(*args, **kwargs)
        self.fields['settings_name'] = forms.ChoiceField(choices=bot_settings_name_list)
