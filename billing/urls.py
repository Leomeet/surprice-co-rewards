from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('bill/create/<int:user_id>/', views.bill_create, name='bill_create'),
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/<int:pk>/', views.bill_detail, name='bill_detail'),
    path('adjust/<int:user_id>/', views.point_adjust, name='point_adjust'),
    path('whatsapp-template/', views.whatsapp_template, name='whatsapp_template'),
]
