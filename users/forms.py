from django.db import models
from django import forms
from .models import Product,Points,CustomUser
from django.contrib.auth.forms import UserCreationForm


# Create your models here.

class LoginForm(forms.Form):
    username = forms.CharField(max_length=65)
    password = forms.CharField(max_length=65, widget=forms.PasswordInput)

class UserPointsForm(forms.Form):
    user = forms.ModelChoiceField(queryset=CustomUser.objects.all().order_by('username'), empty_label=None)

    def __init__(self, *args, **kwargs):
        super(UserPointsForm, self).__init__(*args, **kwargs)
        items = Product.objects.all()

        for item in items:
            field_name = f'quantity_{item.id}'
            label = item.name
            widget = forms.NumberInput(attrs={'placeholder': '0', 'min': '0'})
            initial = 0
            min_value = 0
            max_value = 100000  # Adjust the maximum quantity as needed

            self.fields[field_name] = forms.IntegerField(
                label=label, widget=widget, initial=initial, min_value=min_value, max_value=max_value
            )

class UpdatePointsForm(forms.ModelForm):
    class Meta:
        model = Points
        fields = ('total_points',)

class CustomRegistrationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'mobile' ,'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Enter Username'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Enter Password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm Password'})
        self.fields['mobile'].widget.attrs.update({'placeholder': 'Enter Number'})

class CreateUserForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30, required=False)
    mobile = forms.CharField(max_length=15)
    password = forms.CharField(widget=forms.PasswordInput)
    initial_points = forms.IntegerField(min_value=0, initial=0, required=False)

    def clean_initial_points(self):
        return self.cleaned_data.get('initial_points') or 0

    def clean_username(self):
        username = self.cleaned_data['username'].lower()
        from users.models import CustomUser
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already taken.')
        return username
