from django import forms

from blog.models import Deal


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Логин",
        widget=forms.TextInput(attrs={
            "class": "input --glassmorphism",
            "name": "login",
            "type": "text",
            "autocomplete": "username",
            "placeholder": "* Введите логин",
            "required": True,
        })
    )
    password = forms.CharField(
        required=True,
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            "class": "input --glassmorphism",
            "name": "password",
            "type": "password",
            "autocomplete": "current-password",
            "placeholder": "* Введите пароль",
            "required": True,
        })
    )

class DealForm(forms.ModelForm):
    class Meta:
        model = Deal
        fields = ['personal', 'services', 'service', 'payment', 'whom', 'maney']