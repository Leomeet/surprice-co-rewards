from django.urls import path
from users import views

urlpatterns = [
    path('',views.index,name='home'),
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logoutUser, name="logout"),
    path('register/', views.registerPage, name="register"),
    path('addpoint/',views.add_point, name='addpoint'),
    path('update_points/<int:user_id>/<str:username>/', views.update_points, name='update_points'),
    path('delete_points/<int:user_id>/<str:username>/', views.delete_points, name='delete_points'),

]
