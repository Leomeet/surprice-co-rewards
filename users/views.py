from django.shortcuts import render,redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth import authenticate, login, logout
from .models import Points, CustomUser
from django.db.models import Sum, Q
from .forms import CustomRegistrationForm, CreateUserForm
from django.core.exceptions import ObjectDoesNotExist
import os

def index(request):
    if request.user.is_authenticated:
        search = request.GET.get('search')
        user_points = CustomUser.objects.exclude(is_superuser=True)
        if search:
            user_points = user_points.annotate(total_points=Sum('points__total_points')).values().filter(
                Q(username__startswith=search)
            )
        else:
            user_points = user_points.annotate(total_points=Sum('points__total_points')).values()

        try:
            point = Points.objects.get(host=request.user)
        except ObjectDoesNotExist:
            point = None
        if request.user.is_superuser:
            from billing.models import WhatsAppTemplate
            tmpl = WhatsAppTemplate.objects.filter(pk=1).first()
            wa_template_body = tmpl.body if tmpl else 'Hi {name}! You have {points} reward points.'
            return render(request, "admin_home.html", context={
                'points': user_points,
                'wa_template_body': wa_template_body,
            })
        else:
            return render(request, "user_home.html", context={'points': point})
    else:
        return redirect('login')

def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('Password')
        try:
            user = CustomUser.objects.get(username=username)
        except:
            messages.error(request, 'User does not exist')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')    
        else:
            messages.error(request, 'Username or password does not exits')
    context = {'page':page}
    return render(request, 'login_register.html', context)

def logoutUser(request):
    logout(request)
    return redirect('login')

def registerPage(request):
    form = CustomRegistrationForm()
    if request.method == 'POST':
        form = CustomRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.username = user.username.lower()
            user.save()
            Points.objects.create(host=user, total_points=0)
            login(request, user)
            if user.is_authenticated:
                return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Error in {field}: {error}')
    return render(request, 'login_register.html', {'form': form})


def create_user(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('home')
    from .forms import CreateUserForm
    form = CreateUserForm(request.POST or None)
    if form.is_valid():
        user = CustomUser(
            username=form.cleaned_data['username'],
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data.get('last_name', ''),
            mobile=form.cleaned_data['mobile'],
        )
        user.set_password(form.cleaned_data['password'])
        user.save()
        Points.objects.create(host=user, total_points=form.cleaned_data['initial_points'])
        return redirect('home')
    return render(request, 'create_user.html', {'form': form})
