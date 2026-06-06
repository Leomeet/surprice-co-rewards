from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from decimal import Decimal
import json

from .models import Product, Bill, BillItem, PointAdjustment, WhatsAppTemplate
from .forms import ProductForm, PointAdjustmentForm, WhatsAppTemplateForm
from users.models import CustomUser, Points


def superuser_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped


@login_required
@superuser_required
def product_list(request):
    return render(request, 'billing/product_list.html', {'products': Product.objects.all()})


@login_required
@superuser_required
def product_create(request):
    pass


@login_required
@superuser_required
def product_edit(request, pk):
    pass


@login_required
@superuser_required
def product_delete(request, pk):
    pass


@login_required
@superuser_required
def bill_create(request, user_id):
    pass


@login_required
@superuser_required
def bill_list(request):
    pass


@login_required
@superuser_required
def bill_detail(request, pk):
    pass


@login_required
@superuser_required
def point_adjust(request, user_id):
    pass


@login_required
@superuser_required
def whatsapp_template(request):
    pass
