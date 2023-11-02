from django.shortcuts import render,redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth import authenticate, login, logout
from .models import Points,Product,CustomUser  
from django.db.models import Sum, Q
from .forms import UserPointsForm,UpdatePointsForm,CustomRegistrationForm
from django.core.exceptions import ObjectDoesNotExist
import requests

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
            return render(request, "admin_home.html", context={'points': user_points})
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

def send_api_request(destination,user,current_points,total_points):
    url = 'https://backend.aisensy.com/campaign/t1/api/v2'

    data = {
        "apiKey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY0YWJkYjUyYzY2ZDBiMGI1YmVmMTJhYiIsIm5hbWUiOiJTdXJwcmlzZSBTYW5pdGF0aW9uIiwiYXBwTmFtZSI6IkFpU2Vuc3kiLCJjbGllbnRJZCI6IjY0YWJkYjUxYzY2ZDBiMGI1YmVmMTJhNCIsImFjdGl2ZVBsYW4iOiJCQVNJQ19NT05USExZIiwiaWF0IjoxNjg4OTg0NDAyfQ.4H0ddPiuhwCLKHrrdkE_Vb-KYQHpK3YMGW0SBfKfX2w",
        "campaignName": "Nitin Website",
        "destination": destination,
        "userName": "info@surprisesanitation.com",
        "templateParams": [str(user),str(current_points),str(total_points)]
    }

    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        print("API request was successful.")
        print(response.text)
    else:
        print(f"API request failed with status code {response.status_code}.")
        print(response.text)

def calculate_total_points(quantity_data):
    total_points = 0
    for item_id, quantity in quantity_data.items():
        item = Product.objects.get(id=item_id)
        total_points += item.point_value * quantity
    return total_points

def add_point(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = UserPointsForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data['user']
                quantity_data = {
                    int(key.split('_')[1]): value
                    for key, value in form.cleaned_data.items()
                    if key.startswith('quantity_')
                }
                current_points = CustomUser.objects.filter(pk=user.pk).annotate(total_points=Sum('points__total_points')).values('total_points').first()
                if current_points['total_points']:
                    total_points = current_points['total_points'] + calculate_total_points(quantity_data)
                else:
                    total_points = calculate_total_points(quantity_data)
                user_points, created = Points.objects.get_or_create(host=user)
                user_points.total_points = total_points
                user_points.save()
                send_api_request(destination="+91"+user.mobile,user=user.username,current_points=calculate_total_points(quantity_data),total_points=total_points)
                
                return redirect('home')
        else:
            form = UserPointsForm()
            return render(request, 'add_points.html', {'form': form})
    else:
        return redirect('login')

def update_points(request, user_id, username):
    if request.user.is_authenticated:
        user_points = Points.objects.get(host_id=user_id)
        if request.method == 'POST':
            new_points = request.POST.get('total_points')
            form = UpdatePointsForm(request.POST)
            if form.is_valid():
                user_points.total_points = new_points
                user_points.save()
                return redirect('home')  
        else:
            form = UpdatePointsForm(instance=user_points)
        return render(request, 'update_points.html', {'form': form, 'username': username, 'current_point': user_points.total_points})
    else:
        return redirect('login')

def delete_points(request, user_id, username):
    if request.user.is_authenticated:
        user_points = Points.objects.get(host_id=user_id)
        error_message = None  
        if request.method == 'POST':
            new_points = int(request.POST.get('total_points'))
            form = UpdatePointsForm(request.POST)
            if form.is_valid():
                if new_points > user_points.total_points:
                    error_message = "New points cannot exceed total points."
                else:
                    user_points.total_points -= new_points
                    user_points.save()
                    return redirect('home')  
        form = UpdatePointsForm(instance=user_points)
        return render(request, 'delete_points.html', {'form': form, 'username': username, 'error_message': error_message})
    else:
        return redirect('login')