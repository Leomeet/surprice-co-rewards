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
    form = ProductForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('billing:product_list')
    return render(request, 'billing/product_form.html', {'form': form, 'title': 'Add Product'})


@login_required
@superuser_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        form.save()
        return redirect('billing:product_list')
    return render(request, 'billing/product_form.html', {'form': form, 'title': 'Edit Product'})


@login_required
@superuser_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
    return redirect('billing:product_list')


@login_required
@superuser_required
def bill_create(request, user_id):
    member = get_object_or_404(CustomUser, pk=user_id, is_superuser=False)
    products = Product.objects.all()
    products_json = json.dumps(
        [{'id': p.pk, 'name': p.name, 'price': float(p.price), 'point_value': p.point_value}
         for p in products]
    )

    if request.method == 'POST':
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')
        note = request.POST.get('note', '')

        items = []
        total_amount = Decimal('0')
        total_points = 0

        for pid, qty_str in zip(product_ids, quantities):
            try:
                qty = int(qty_str)
                if qty <= 0:
                    continue
                product = Product.objects.get(pk=pid)
            except (ValueError, Product.DoesNotExist):
                continue
            line_amount = product.price * qty
            line_points = product.point_value * qty
            items.append({
                'product': product,
                'quantity': qty,
                'unit_price': product.price,
                'unit_points': product.point_value,
                'line_total_amount': line_amount,
                'line_total_points': line_points,
            })
            total_amount += line_amount
            total_points += line_points

        if items:
            with transaction.atomic():
                bill = Bill.objects.create(
                    user=member,
                    total_amount=total_amount,
                    total_points=total_points,
                    note=note,
                )
                for item in items:
                    BillItem.objects.create(bill=bill, **item)
                pts, _ = Points.objects.get_or_create(host=member, defaults={'total_points': 0})
                Points.objects.filter(pk=pts.pk).update(total_points=F('total_points') + total_points)

        return redirect('home')

    return render(request, 'billing/bill_create.html', {
        'member': member,
        'products': products,
        'products_json': products_json,
    })


@login_required
@superuser_required
def bill_list(request):
    from itertools import groupby

    bills = Bill.objects.select_related('user').prefetch_related('items').order_by('-created_at')
    user_id = request.GET.get('user')
    if user_id:
        bills = bills.filter(user_id=user_id)

    grouped = []
    for date, day_bills in groupby(bills, key=lambda b: b.created_at.date()):
        day_list = list(day_bills)
        grouped.append({
            'date': date,
            'bills': day_list,
            'total_amount': sum(b.total_amount for b in day_list),
            'total_points': sum(b.total_points for b in day_list),
            'bill_count': len(day_list),
        })

    members = CustomUser.objects.filter(is_superuser=False)
    return render(request, 'billing/bill_list.html', {
        'grouped': grouped,
        'members': members,
        'selected_user': user_id,
    })


@login_required
@superuser_required
def bill_detail(request, pk):
    bill = get_object_or_404(
        Bill.objects.select_related('user').prefetch_related('items__product'), pk=pk
    )
    return render(request, 'billing/bill_detail.html', {'bill': bill})


@login_required
@superuser_required
def point_adjust(request, user_id):
    if request.method != 'POST':
        return redirect('home')
    member = get_object_or_404(CustomUser, pk=user_id, is_superuser=False)
    form = PointAdjustmentForm(request.POST)
    if form.is_valid():
        delta = form.cleaned_data['delta']
        reason = form.cleaned_data['reason']
        with transaction.atomic():
            PointAdjustment.objects.create(user=member, delta=delta, reason=reason)
            pts, _ = Points.objects.get_or_create(host=member, defaults={'total_points': 0})
            Points.objects.filter(pk=pts.pk).update(total_points=F('total_points') + delta)
    return redirect('home')


@login_required
@superuser_required
def whatsapp_template(request):
    tmpl, _ = WhatsAppTemplate.objects.get_or_create(
        pk=1,
        defaults={'body': 'Hi {name}! You have earned {points} reward points (₹{amount} purchase). Thank you!'},
    )
    form = WhatsAppTemplateForm(request.POST or None, instance=tmpl)
    if form.is_valid():
        form.save()
        return redirect('billing:whatsapp_template')
    return render(request, 'billing/whatsapp_template.html', {'form': form})
