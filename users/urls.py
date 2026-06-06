from django.urls import path
from users import views

urlpatterns = [
    path('',views.index,name='home'),
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logoutUser, name="logout"),
    path('register/', views.registerPage, name="register"),
    path('users/create/', views.create_user, name='create_user'),

]
