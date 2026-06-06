# Billing Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `billing` Django app with Product CRUD, procurement bills that auto-award points, point adjustments, and a WhatsApp notify modal — replacing the old add/update/deduct point views.

**Architecture:** New `billing` app alongside `users`. Bills and PointAdjustments update `Points.total_points` via Django `F()` expressions. Old `users.Product` is migrated to `billing.Product` via a data migration. Old views (`add_point`, `update_points`, `delete_points`) are removed. Admin dashboard gets 3 per-user buttons (Bill / Adjust / Notify) with Bootstrap modals.

**Tech Stack:** Django 4.2, psycopg2-binary, Bootstrap 5.3 CDN, Font Awesome 6.5 CDN, vanilla JS. No new pip packages needed.

---

## File Map

### Created
- `billing/__init__.py`
- `billing/apps.py`
- `billing/models.py`
- `billing/forms.py`
- `billing/views.py`
- `billing/urls.py`
- `billing/admin.py`
- `billing/tests.py`
- `billing/migrations/__init__.py`
- `billing/migrations/0001_initial.py` — auto-generated
- `billing/migrations/0002_data_migration.py` — manual: copy users.Product rows + seed WhatsAppTemplate
- `templates/billing/product_list.html`
- `templates/billing/product_form.html`
- `templates/billing/bill_create.html`
- `templates/billing/bill_list.html`
- `templates/billing/bill_detail.html`
- `templates/billing/whatsapp_template.html`
- `templates/create_user.html`

### Modified
- `reward/settings.py` — add `billing` to INSTALLED_APPS; add SQLite test DB config
- `reward/urls.py` — include `billing.urls`
- `users/models.py` — remove `Product` model
- `users/views.py` — remove `add_point`, `update_points`, `delete_points`, `calculate_total_points`, `send_api_request`; add `create_user`; update `index` to pass `wa_template_body`
- `users/forms.py` — remove `UserPointsForm`; add `CreateUserForm`
- `users/urls.py` — remove old point URLs; add `create_user` URL
- `users/admin.py` — remove `Product` registration
- `users/migrations/0004_remove_product.py` — auto-generated
- `templates/admin_home.html` — full revamp: Bill/Adjust/Notify buttons + modals
- `templates/base.html` — add Products and Bills nav links for superuser

---

## Task 1 — Test database + billing app skeleton

**Files:**
- Modify: `reward/settings.py`
- Create: `billing/__init__.py`, `billing/apps.py`, `billing/migrations/__init__.py`
- Modify: `reward/urls.py`

- [ ] **Step 1: Add SQLite test DB and billing to INSTALLED_APPS in `reward/settings.py`**

Add at the bottom of `reward/settings.py`:

```python
import sys
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
```

Change `INSTALLED_APPS` to:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'billing',
]
```

- [ ] **Step 2: Create `billing/__init__.py`** (empty file)

- [ ] **Step 3: Create `billing/apps.py`**

```python
from django.apps import AppConfig

class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'
```

- [ ] **Step 4: Create `billing/migrations/__init__.py`** (empty file)

- [ ] **Step 5: Wire billing URLs in `reward/urls.py`**

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('billing/', include('billing.urls', namespace='billing')),
    path('', include('users.urls')),
]
```

- [ ] **Step 6: Verify Django check passes**

```bash
.venv/bin/python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 7: Commit**

```bash
git add reward/settings.py reward/urls.py billing/
git commit -m "feat: add billing app skeleton and register in settings/urls"
```

---

## Task 2 — Billing models

**Files:**
- Create: `billing/models.py`, `billing/tests.py`
- Auto-generate: `billing/migrations/0001_initial.py`

- [ ] **Step 1: Write failing test in `billing/tests.py`**

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from billing.models import Product, Bill, BillItem, PointAdjustment, WhatsAppTemplate
from users.models import Points

User = get_user_model()


class ProductModelTest(TestCase):
    def test_product_fields_exist(self):
        p = Product.objects.create(name='Gold Wash', price='150.00', point_value=75)
        self.assertEqual(p.price, 150)
        self.assertEqual(p.point_value, 75)
        self.assertEqual(p.description, '')


class BillModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='member', password='pass')
        Points.objects.create(host=self.user, total_points=0)
        self.product = Product.objects.create(name='Silver Wash', price='100.00', point_value=50)

    def test_bill_and_items_created(self):
        bill = Bill.objects.create(user=self.user, total_amount='100.00', total_points=50)
        BillItem.objects.create(
            bill=bill, product=self.product, quantity=1,
            unit_price='100.00', unit_points=50,
            line_total_amount='100.00', line_total_points=50,
        )
        self.assertEqual(bill.items.count(), 1)
        self.assertEqual(bill.items.first().line_total_points, 50)


class PointAdjustmentModelTest(TestCase):
    def test_adjustment_created(self):
        user = User.objects.create_user(username='adj_user', password='pass')
        adj = PointAdjustment.objects.create(user=user, delta=30, reason='Bonus')
        self.assertEqual(adj.delta, 30)


class WhatsAppTemplateModelTest(TestCase):
    def test_template_created(self):
        tmpl = WhatsAppTemplate.objects.create(body='Hi {name}! You have {points} points.')
        self.assertIn('{name}', tmpl.body)
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
.venv/bin/python manage.py test billing.tests --verbosity=2
```

Expected: `ImportError: cannot import name 'Product' from 'billing.models'`

- [ ] **Step 3: Create `billing/models.py`**

```python
from django.db import models
from django.conf import settings


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    point_value = models.IntegerField()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Bill(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bills',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_points = models.IntegerField(default=0)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Bill #{self.pk} – {self.user}'


class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_points = models.IntegerField()
    line_total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    line_total_points = models.IntegerField()

    def __str__(self):
        return f'{self.product} × {self.quantity}'


class PointAdjustment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='adjustments',
    )
    delta = models.IntegerField()
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Adjustment {self.delta:+d} for {self.user}'


class WhatsAppTemplate(models.Model):
    body = models.TextField()

    def __str__(self):
        return 'WhatsApp Template'
```

- [ ] **Step 4: Generate migration**

```bash
.venv/bin/python manage.py makemigrations billing
```

Expected: `Migrations for 'billing': billing/migrations/0001_initial.py`

- [ ] **Step 5: Run tests — expect passing**

```bash
.venv/bin/python manage.py test billing.tests --verbosity=2
```

Expected: `4 tests, 0 failures`

- [ ] **Step 6: Commit**

```bash
git add billing/models.py billing/tests.py billing/migrations/0001_initial.py
git commit -m "feat: add billing models (Product, Bill, BillItem, PointAdjustment, WhatsAppTemplate)"
```

---

## Task 3 — Data migration: copy users.Product rows + seed WhatsAppTemplate

**Files:**
- Create: `billing/migrations/0002_data_migration.py`

- [ ] **Step 1: Create `billing/migrations/0002_data_migration.py`**

```python
from django.db import migrations


DEFAULT_WA_TEMPLATE = (
    'Hi {name}! You have earned {points} reward points '
    '(purchase of ₹{amount}). Thank you for shopping with us!'
)


def copy_products_and_seed_template(apps, schema_editor):
    OldProduct = apps.get_model('users', 'Product')
    NewProduct = apps.get_model('billing', 'Product')
    WhatsAppTemplate = apps.get_model('billing', 'WhatsAppTemplate')

    for old in OldProduct.objects.all():
        NewProduct.objects.get_or_create(
            name=old.name,
            defaults={'price': '0.00', 'point_value': old.point_value, 'description': ''},
        )

    WhatsAppTemplate.objects.get_or_create(pk=1, defaults={'body': DEFAULT_WA_TEMPLATE})


def reverse_migration(apps, schema_editor):
    apps.get_model('billing', 'Product').objects.all().delete()
    apps.get_model('billing', 'WhatsAppTemplate').objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
        ('users', '0003_alter_customuser_options'),
    ]

    operations = [
        migrations.RunPython(copy_products_and_seed_template, reverse_migration),
    ]
```

- [ ] **Step 2: Apply migration**

```bash
.venv/bin/python manage.py migrate billing
```

Expected: `Running migrations: Applying billing.0002_data_migration... OK`

- [ ] **Step 3: Verify in shell**

```bash
.venv/bin/python manage.py shell -c "
from billing.models import Product, WhatsAppTemplate
print('Products:', list(Product.objects.values('name','price','point_value')))
print('Template:', WhatsAppTemplate.objects.filter(pk=1).first())
"
```

Expected: prints existing product names and the WhatsApp template.

- [ ] **Step 4: Commit**

```bash
git add billing/migrations/0002_data_migration.py
git commit -m "feat: data migration — copy users.Product to billing.Product, seed WhatsAppTemplate"
```

---

## Task 4 — Billing forms, admin, and URL file

**Files:**
- Create: `billing/forms.py`, `billing/admin.py`, `billing/urls.py`

- [ ] **Step 1: Create `billing/forms.py`**

```python
from django import forms
from .models import Product, PointAdjustment, WhatsAppTemplate


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('name', 'description', 'price', 'point_value')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class PointAdjustmentForm(forms.Form):
    delta = forms.IntegerField(
        label='Points (negative to deduct)',
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 50 or -20'}),
    )
    reason = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'placeholder': 'e.g. Loyalty bonus'}))


class WhatsAppTemplateForm(forms.ModelForm):
    class Meta:
        model = WhatsAppTemplate
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={'rows': 5}),
        }
```

- [ ] **Step 2: Create `billing/admin.py`**

```python
from django.contrib import admin
from .models import Product, Bill, BillItem, PointAdjustment, WhatsAppTemplate

admin.site.register(Product)
admin.site.register(Bill)
admin.site.register(BillItem)
admin.site.register(PointAdjustment)
admin.site.register(WhatsAppTemplate)
```

- [ ] **Step 3: Create `billing/urls.py`**

```python
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
```

- [ ] **Step 4: Create placeholder `billing/views.py`** (stubs so URL wiring doesn't error)

```python
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
    pass  # implemented in Task 5


@login_required
@superuser_required
def product_edit(request, pk):
    pass  # implemented in Task 5


@login_required
@superuser_required
def product_delete(request, pk):
    pass  # implemented in Task 5


@login_required
@superuser_required
def bill_create(request, user_id):
    pass  # implemented in Task 6


@login_required
@superuser_required
def bill_list(request):
    pass  # implemented in Task 7


@login_required
@superuser_required
def bill_detail(request, pk):
    pass  # implemented in Task 7


@login_required
@superuser_required
def point_adjust(request, user_id):
    pass  # implemented in Task 8


@login_required
@superuser_required
def whatsapp_template(request):
    pass  # implemented in Task 9
```

- [ ] **Step 5: Verify check + URL resolution**

```bash
.venv/bin/python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```bash
git add billing/forms.py billing/admin.py billing/urls.py billing/views.py
git commit -m "feat: billing forms, admin, urls, and view stubs"
```

---

## Task 5 — Product CRUD views + templates

**Files:**
- Modify: `billing/views.py`
- Create: `templates/billing/product_list.html`, `templates/billing/product_form.html`

- [ ] **Step 1: Write product view tests in `billing/tests.py`** (append to existing file)

```python
class ProductCRUDTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin', password='admin')
        self.client.login(username='admin', password='admin')
        self.product = Product.objects.create(name='Test', price='100.00', point_value=10)

    def test_product_list_200(self):
        response = self.client.get('/billing/products/')
        self.assertEqual(response.status_code, 200)

    def test_product_create(self):
        response = self.client.post('/billing/products/create/', {
            'name': 'New Product', 'description': '', 'price': '200.00', 'point_value': 20,
        })
        self.assertRedirects(response, '/billing/products/')
        self.assertTrue(Product.objects.filter(name='New Product').exists())

    def test_product_edit(self):
        response = self.client.post(f'/billing/products/{self.product.pk}/edit/', {
            'name': 'Updated', 'description': '', 'price': '150.00', 'point_value': 15,
        })
        self.assertRedirects(response, '/billing/products/')
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated')

    def test_product_delete(self):
        response = self.client.post(f'/billing/products/{self.product.pk}/delete/')
        self.assertRedirects(response, '/billing/products/')
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_non_superuser_redirected(self):
        self.client.logout()
        regular = User.objects.create_user(username='reg', password='pass')
        self.client.login(username='reg', password='pass')
        response = self.client.get('/billing/products/')
        self.assertRedirects(response, '/')
```

- [ ] **Step 2: Run tests — expect failures on redirects/200s**

```bash
.venv/bin/python manage.py test billing.tests.ProductCRUDTest --verbosity=2
```

Expected: failures because view stubs return `None`.

- [ ] **Step 3: Implement product views in `billing/views.py`** (replace the three stub functions)

```python
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
```

- [ ] **Step 4: Create `templates/billing/product_list.html`**

```html
{% extends "base.html" %}
{% block style %}
<style>
  .page-wrapper { padding: 40px 20px 60px; min-height: calc(100vh - 60px); }
  .page-title { font-size: 1.75rem; font-weight: 700; color: #1e2a4a; display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
  .title-icon { width: 42px; height: 42px; background: linear-gradient(135deg, #3b82f6, #6366f1); border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 1rem; flex-shrink: 0; box-shadow: 0 6px 18px rgba(59,130,246,.35); }
  .page-subtitle { color: #7e8cab; font-size: .88rem; margin-left: 54px; margin-bottom: 28px; }
  .tbl-wrap { background: rgba(255,255,255,.55); backdrop-filter: blur(20px) saturate(160%); border: 1px solid rgba(255,255,255,.7); border-radius: 20px; box-shadow: 0 8px 28px rgba(59,130,246,.12); overflow: hidden; }
  .prod-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
  .prod-table thead th { padding: 16px 20px; font-size: .72rem; text-transform: uppercase; letter-spacing: .6px; color: #8493b0; font-weight: 600; background: rgba(59,130,246,.05); border-bottom: 1px solid rgba(59,130,246,.1); text-align: left; }
  .prod-table tbody td { padding: 14px 20px; border-bottom: 1px solid rgba(59,130,246,.07); color: #1e2a4a; vertical-align: middle; }
  .prod-table tbody tr:last-child td { border-bottom: none; }
  .prod-table tbody tr:hover { background: rgba(59,130,246,.04); }
  .btn-sm-edit { background: rgba(59,130,246,.1); border: 1px solid rgba(59,130,246,.25); color: #3b82f6; font-size: .78rem; font-weight: 600; font-family: 'Poppins',sans-serif; border-radius: 8px; padding: 5px 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 5px; transition: all .2s; }
  .btn-sm-edit:hover { background: rgba(59,130,246,.2); color: #1d4ed8; }
  .btn-sm-del { background: rgba(244,63,94,.1); border: 1px solid rgba(244,63,94,.25); color: #e11d48; font-size: .78rem; font-weight: 600; font-family: 'Poppins',sans-serif; border-radius: 8px; padding: 5px 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 5px; transition: all .2s; cursor: pointer; }
  .btn-sm-del:hover { background: rgba(244,63,94,.2); color: #be123c; }
</style>
{% endblock style %}

{% block content %}
<div class="page-wrapper">
  <div class="container-fluid px-2 px-md-3">
    <div class="d-flex align-items-start justify-content-between mb-2">
      <div>
        <div class="page-title"><div class="title-icon"><i class="fas fa-box"></i></div>Products</div>
        <div class="page-subtitle">Manage your product catalogue</div>
      </div>
      <a href="{% url 'billing:product_create' %}" class="btn-primary-glass mt-1"><i class="fas fa-plus me-1"></i>Add Product</a>
    </div>

    <div class="tbl-wrap">
      <table class="prod-table">
        <thead>
          <tr><th>Name</th><th>Description</th><th>Price (₹)</th><th>Points/unit</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {% for p in products %}
          <tr>
            <td><strong>{{ p.name }}</strong></td>
            <td style="color:#7e8cab;">{{ p.description|default:"—" }}</td>
            <td>₹{{ p.price }}</td>
            <td><span style="font-weight:700;color:#6366f1;">{{ p.point_value }}</span></td>
            <td>
              <div style="display:flex;gap:8px;">
                <a href="{% url 'billing:product_edit' p.pk %}" class="btn-sm-edit"><i class="fas fa-pen"></i> Edit</a>
                <form method="POST" action="{% url 'billing:product_delete' p.pk %}" style="display:inline;" onsubmit="return confirm('Delete {{ p.name }}?')">
                  {% csrf_token %}
                  <button type="submit" class="btn-sm-del"><i class="fas fa-trash"></i> Delete</button>
                </form>
              </div>
            </td>
          </tr>
          {% empty %}
          <tr><td colspan="5" style="text-align:center;padding:40px;color:#8493b0;">No products yet. <a href="{% url 'billing:product_create' %}">Add one.</a></td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
{% endblock content %}
```

- [ ] **Step 5: Create `templates/billing/product_form.html`**

```html
{% extends "base.html" %}
{% block style %}
<style>
  .form-page { min-height: calc(100vh - 64px); display: flex; align-items: center; justify-content: center; padding: 40px 20px; }
  .form-card { background: rgba(255,255,255,.55); backdrop-filter: blur(24px) saturate(160%); border: 1px solid rgba(255,255,255,.7); border-radius: 24px; padding: 40px; width: 100%; max-width: 520px; box-shadow: 0 12px 48px rgba(59,130,246,.15); }
  .form-title { font-size: 1.4rem; font-weight: 700; color: #1e2a4a; margin-bottom: 28px; display: flex; align-items: center; gap: 10px; }
  .form-title i { color: #3b82f6; }
  .field-group { margin-bottom: 20px; }
  .field-group label { font-size: .82rem; font-weight: 600; color: #5a6a8a; text-transform: uppercase; letter-spacing: .5px; display: block; margin-bottom: 6px; }
  .glass-input { width: 100%; background: rgba(255,255,255,.6); border: 1px solid rgba(59,130,246,.2); border-radius: 10px; padding: 10px 14px; font-family: 'Poppins',sans-serif; font-size: .9rem; color: #1e2a4a; outline: none; transition: all .2s; }
  .glass-input:focus { background: rgba(255,255,255,.85); border-color: rgba(59,130,246,.5); box-shadow: 0 0 0 3px rgba(59,130,246,.12); }
  .form-actions { display: flex; gap: 12px; margin-top: 28px; }
</style>
{% endblock style %}

{% block content %}
<div class="form-page">
  <div class="form-card">
    <div class="form-title"><i class="fas fa-box"></i>{{ title }}</div>
    <form method="POST">
      {% csrf_token %}
      {% for field in form %}
      <div class="field-group">
        <label for="{{ field.id_for_label }}">{{ field.label }}</label>
        {% if field.field.widget.input_type == 'textarea' %}
        <textarea name="{{ field.html_name }}" id="{{ field.id_for_label }}" class="glass-input" rows="3">{{ field.value|default:'' }}</textarea>
        {% else %}
        <input type="{{ field.field.widget.input_type }}" name="{{ field.html_name }}" id="{{ field.id_for_label }}" class="glass-input" value="{{ field.value|default:'' }}">
        {% endif %}
        {% if field.errors %}<div style="color:#e11d48;font-size:.8rem;margin-top:4px;">{{ field.errors.0 }}</div>{% endif %}
      </div>
      {% endfor %}
      <div class="form-actions">
        <button type="submit" class="btn-primary-glass"><i class="fas fa-check me-1"></i>Save</button>
        <a href="{% url 'billing:product_list' %}" class="btn-danger-glass"><i class="fas fa-xmark me-1"></i>Cancel</a>
      </div>
    </form>
  </div>
</div>
{% endblock content %}
```

- [ ] **Step 6: Run product tests**

```bash
.venv/bin/python manage.py test billing.tests.ProductCRUDTest --verbosity=2
```

Expected: `5 tests, 0 failures`

- [ ] **Step 7: Commit**

```bash
git add billing/views.py billing/tests.py templates/billing/
git commit -m "feat: product CRUD views and templates"
```

---

## Task 6 — Bill Create view + template

**Files:**
- Modify: `billing/views.py`, `billing/tests.py`
- Create: `templates/billing/bill_create.html`

- [ ] **Step 1: Write bill create tests in `billing/tests.py`** (append)

```python
class BillCreateViewTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin2', password='admin')
        self.member = User.objects.create_user(username='buyer', password='pass')
        Points.objects.create(host=self.member, total_points=0)
        self.product = Product.objects.create(name='Wash', price='100.00', point_value=10)
        self.client.login(username='admin2', password='admin')

    def test_bill_create_page_loads(self):
        response = self.client.get(f'/billing/bill/create/{self.member.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_bill_create_updates_points(self):
        self.client.post(f'/billing/bill/create/{self.member.pk}/', {
            'product_id': [str(self.product.pk)],
            'quantity': ['2'],
            'note': '',
        })
        pts = Points.objects.get(host=self.member)
        self.assertEqual(pts.total_points, 20)

    def test_bill_and_items_persisted(self):
        self.client.post(f'/billing/bill/create/{self.member.pk}/', {
            'product_id': [str(self.product.pk)],
            'quantity': ['3'],
            'note': 'test',
        })
        self.assertEqual(Bill.objects.count(), 1)
        bill = Bill.objects.first()
        self.assertEqual(bill.total_points, 30)
        self.assertEqual(bill.items.count(), 1)
        item = bill.items.first()
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.unit_price, self.product.price)

    def test_empty_quantities_ignored(self):
        self.client.post(f'/billing/bill/create/{self.member.pk}/', {
            'product_id': [str(self.product.pk)],
            'quantity': ['0'],
            'note': '',
        })
        self.assertEqual(Bill.objects.count(), 0)
        self.assertEqual(Points.objects.get(host=self.member).total_points, 0)
```

- [ ] **Step 2: Run tests — expect failures**

```bash
.venv/bin/python manage.py test billing.tests.BillCreateViewTest --verbosity=2
```

Expected: failures (stub returns None).

- [ ] **Step 3: Implement `bill_create` in `billing/views.py`** (replace stub)

```python
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
```

- [ ] **Step 4: Create `templates/billing/bill_create.html`**

```html
{% extends "base.html" %}
{% block style %}
<style>
  .page-wrapper { padding: 40px 20px 60px; min-height: calc(100vh - 60px); }
  .page-title { font-size: 1.5rem; font-weight: 700; color: #1e2a4a; display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
  .title-icon { width: 42px; height: 42px; background: linear-gradient(135deg, #3b82f6, #6366f1); border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 1rem; flex-shrink: 0; }
  .page-subtitle { color: #7e8cab; font-size: .88rem; margin-left: 54px; margin-bottom: 28px; }
  .bill-card { background: rgba(255,255,255,.55); backdrop-filter: blur(20px) saturate(160%); border: 1px solid rgba(255,255,255,.7); border-radius: 20px; padding: 28px; box-shadow: 0 8px 28px rgba(59,130,246,.12); margin-bottom: 20px; }
  .member-badge { display: flex; align-items: center; gap: 14px; padding: 16px; background: rgba(59,130,246,.06); border: 1px solid rgba(59,130,246,.15); border-radius: 14px; margin-bottom: 24px; }
  .member-avatar { width: 48px; height: 48px; border-radius: 14px; background: linear-gradient(135deg,#3b82f6,#6366f1); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 700; color: #fff; text-transform: uppercase; }
  .items-table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
  .items-table th { padding: 10px 12px; font-size: .72rem; text-transform: uppercase; letter-spacing: .6px; color: #8493b0; font-weight: 600; background: rgba(59,130,246,.04); border-bottom: 1px solid rgba(59,130,246,.1); text-align: left; }
  .items-table td { padding: 10px 12px; border-bottom: 1px solid rgba(59,130,246,.07); vertical-align: middle; }
  .items-table tbody tr:last-child td { border-bottom: none; }
  .glass-select, .glass-qty { background: rgba(255,255,255,.7); border: 1px solid rgba(59,130,246,.2); border-radius: 8px; padding: 7px 10px; font-family: 'Poppins',sans-serif; font-size: .85rem; color: #1e2a4a; outline: none; }
  .glass-select:focus, .glass-qty:focus { border-color: rgba(59,130,246,.5); box-shadow: 0 0 0 3px rgba(59,130,246,.1); }
  .glass-qty { width: 80px; }
  .line-val { font-weight: 600; color: #6366f1; }
  .totals-row { background: rgba(59,130,246,.05); }
  .totals-row td { padding: 14px 12px; font-weight: 700; color: #1e2a4a; font-size: .95rem; }
  .btn-add-row { background: rgba(59,130,246,.1); border: 1px dashed rgba(59,130,246,.4); color: #3b82f6; font-family: 'Poppins',sans-serif; font-size: .85rem; font-weight: 600; border-radius: 10px; padding: 9px 18px; cursor: pointer; width: 100%; transition: all .2s; }
  .btn-add-row:hover { background: rgba(59,130,246,.18); }
  .btn-remove { background: none; border: none; color: #e11d48; cursor: pointer; font-size: .9rem; padding: 4px 8px; border-radius: 6px; transition: background .15s; }
  .btn-remove:hover { background: rgba(244,63,94,.1); }
  .note-input { width: 100%; background: rgba(255,255,255,.6); border: 1px solid rgba(59,130,246,.2); border-radius: 10px; padding: 10px 14px; font-family: 'Poppins',sans-serif; font-size: .9rem; color: #1e2a4a; outline: none; resize: vertical; }
  .note-input:focus { border-color: rgba(59,130,246,.5); box-shadow: 0 0 0 3px rgba(59,130,246,.1); }
  .summary-box { background: rgba(59,130,246,.07); border: 1px solid rgba(59,130,246,.18); border-radius: 14px; padding: 16px 20px; display: flex; gap: 32px; flex-wrap: wrap; margin-bottom: 20px; }
  .summary-item { text-align: center; }
  .summary-val { font-size: 1.4rem; font-weight: 700; background: linear-gradient(135deg,#3b82f6,#6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
  .summary-lbl { font-size: .72rem; color: #8493b0; text-transform: uppercase; letter-spacing: .6px; }
</style>
{% endblock style %}

{% block content %}
<div class="page-wrapper">
  <div class="container-fluid px-2 px-md-3" style="max-width:820px;">
    <div class="page-title"><div class="title-icon"><i class="fas fa-receipt"></i></div>Create Bill</div>
    <div class="page-subtitle">Add purchased items to calculate and award points</div>

    <form method="POST" id="billForm">
      {% csrf_token %}
      <div class="bill-card">
        <div class="member-badge">
          <div class="member-avatar">{{ member.username|first }}</div>
          <div>
            <div style="font-weight:600;color:#1e2a4a;">{{ member.first_name|default:member.username }} {{ member.last_name }}</div>
            <div style="font-size:.8rem;color:#8493b0;">@{{ member.username }} · {{ member.mobile|default:"no phone" }}</div>
          </div>
        </div>

        <table class="items-table" id="itemsTable">
          <thead>
            <tr>
              <th>Product</th>
              <th>Qty</th>
              <th>Unit Price</th>
              <th>Unit Pts</th>
              <th>Line Total</th>
              <th>Line Pts</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="itemsBody">
            <!-- rows added by JS -->
          </tbody>
          <tfoot>
            <tr class="totals-row">
              <td colspan="4" style="text-align:right;">Grand Total</td>
              <td>₹<span id="grandAmount">0.00</span></td>
              <td><span id="grandPoints">0</span> pts</td>
              <td></td>
            </tr>
          </tfoot>
        </table>

        <button type="button" class="btn-add-row" onclick="addRow()">
          <i class="fas fa-plus me-1"></i>Add Item
        </button>
      </div>

      <div class="bill-card">
        <label style="font-size:.82rem;font-weight:600;color:#5a6a8a;text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:8px;">Note (optional)</label>
        <textarea name="note" class="note-input" rows="2" placeholder="Any notes about this bill…"></textarea>
      </div>

      <div class="summary-box" id="summaryBox">
        <div class="summary-item">
          <div class="summary-val" id="sumAmount">₹0.00</div>
          <div class="summary-lbl">Total Amount</div>
        </div>
        <div class="summary-item">
          <div class="summary-val" id="sumPoints">0</div>
          <div class="summary-lbl">Points Awarded</div>
        </div>
        <div class="summary-item">
          <div class="summary-val" id="sumItems">0</div>
          <div class="summary-lbl">Line Items</div>
        </div>
      </div>

      <div style="display:flex;gap:12px;">
        <button type="submit" class="btn-primary-glass"><i class="fas fa-check me-1"></i>Save Bill & Award Points</button>
        <a href="/" class="btn-danger-glass"><i class="fas fa-xmark me-1"></i>Cancel</a>
      </div>
    </form>
  </div>
</div>

<script>
const PRODUCTS = {{ products_json|safe }};
const productMap = {};
PRODUCTS.forEach(p => { productMap[p.id] = p; });

function buildSelect(name, selectedId) {
  let opts = '<option value="">— select product —</option>';
  PRODUCTS.forEach(p => {
    opts += `<option value="${p.id}" ${p.id == selectedId ? 'selected' : ''}>${p.name} (₹${p.price.toFixed(2)}, ${p.point_value} pts)</option>`;
  });
  return `<select name="${name}" class="glass-select" onchange="recalc(this.closest('tr'))" required>${opts}</select>`;
}

let rowCount = 0;

function addRow() {
  const tbody = document.getElementById('itemsBody');
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>${buildSelect('product_id', '')}</td>
    <td><input type="number" name="quantity" class="glass-qty" value="1" min="1" oninput="recalc(this.closest('tr'))" required></td>
    <td class="line-unit-price">—</td>
    <td class="line-unit-pts">—</td>
    <td class="line-val line-amount">₹0.00</td>
    <td class="line-val line-points">0 pts</td>
    <td><button type="button" class="btn-remove" onclick="removeRow(this)"><i class="fas fa-times"></i></button></td>
  `;
  tbody.appendChild(tr);
  rowCount++;
  updateTotals();
}

function removeRow(btn) {
  btn.closest('tr').remove();
  updateTotals();
}

function recalc(row) {
  const select = row.querySelector('select[name="product_id"]');
  const qtyInput = row.querySelector('input[name="quantity"]');
  const pid = parseInt(select.value);
  const qty = parseInt(qtyInput.value) || 0;
  const p = productMap[pid];
  if (p && qty > 0) {
    row.querySelector('.line-unit-price').textContent = '₹' + p.price.toFixed(2);
    row.querySelector('.line-unit-pts').textContent = p.point_value + ' pts';
    row.querySelector('.line-amount').textContent = '₹' + (p.price * qty).toFixed(2);
    row.querySelector('.line-points').textContent = (p.point_value * qty) + ' pts';
  } else {
    row.querySelector('.line-unit-price').textContent = '—';
    row.querySelector('.line-unit-pts').textContent = '—';
    row.querySelector('.line-amount').textContent = '₹0.00';
    row.querySelector('.line-points').textContent = '0 pts';
  }
  updateTotals();
}

function updateTotals() {
  let totalAmt = 0, totalPts = 0, items = 0;
  document.querySelectorAll('#itemsBody tr').forEach(row => {
    const pid = parseInt(row.querySelector('select').value);
    const qty = parseInt(row.querySelector('input[name="quantity"]').value) || 0;
    const p = productMap[pid];
    if (p && qty > 0) {
      totalAmt += p.price * qty;
      totalPts += p.point_value * qty;
      items++;
    }
  });
  document.getElementById('grandAmount').textContent = totalAmt.toFixed(2);
  document.getElementById('grandPoints').textContent = totalPts;
  document.getElementById('sumAmount').textContent = '₹' + totalAmt.toFixed(2);
  document.getElementById('sumPoints').textContent = totalPts;
  document.getElementById('sumItems').textContent = items;
}

// Start with one row
addRow();
</script>
{% endblock content %}
```

- [ ] **Step 5: Run bill create tests**

```bash
.venv/bin/python manage.py test billing.tests.BillCreateViewTest --verbosity=2
```

Expected: `4 tests, 0 failures`

- [ ] **Step 6: Commit**

```bash
git add billing/views.py billing/tests.py templates/billing/bill_create.html
git commit -m "feat: bill create view with dynamic line items and live point calculation"
```

---

## Task 7 — Bill List + Bill Detail

**Files:**
- Modify: `billing/views.py`, `billing/tests.py`
- Create: `templates/billing/bill_list.html`, `templates/billing/bill_detail.html`

- [ ] **Step 1: Write tests** (append to `billing/tests.py`)

```python
class BillListDetailTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin3', password='admin')
        self.member = User.objects.create_user(username='buyer2', password='pass')
        Points.objects.create(host=self.member, total_points=50)
        self.product = Product.objects.create(name='Wax', price='200.00', point_value=20)
        self.bill = Bill.objects.create(user=self.member, total_amount='200.00', total_points=20)
        BillItem.objects.create(
            bill=self.bill, product=self.product, quantity=1,
            unit_price='200.00', unit_points=20,
            line_total_amount='200.00', line_total_points=20,
        )
        self.client.login(username='admin3', password='admin')

    def test_bill_list_200(self):
        response = self.client.get('/billing/bills/')
        self.assertEqual(response.status_code, 200)

    def test_bill_detail_200(self):
        response = self.client.get(f'/billing/bills/{self.bill.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_bill_detail_shows_item(self):
        response = self.client.get(f'/billing/bills/{self.bill.pk}/')
        self.assertContains(response, 'Wax')
```

- [ ] **Step 2: Implement `bill_list` and `bill_detail` in `billing/views.py`** (replace stubs)

```python
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
```

- [ ] **Step 3: Create `templates/billing/bill_list.html`**

```html
{% extends "base.html" %}
{% block style %}
<style>
  .page-wrapper { padding: 40px 20px 60px; min-height: calc(100vh - 60px); }
  .page-title { font-size: 1.75rem; font-weight: 700; color: #1e2a4a; display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
  .title-icon { width: 42px; height: 42px; background: linear-gradient(135deg,#3b82f6,#6366f1); border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 1rem; }
  .page-subtitle { color: #7e8cab; font-size:.88rem; margin-left:54px; margin-bottom:28px; }
  .filter-bar { display:flex; gap:12px; margin-bottom:24px; flex-wrap:wrap; align-items:center; }
  .glass-select-filter { background:rgba(255,255,255,.6); border:1px solid rgba(59,130,246,.2); border-radius:10px; padding:8px 14px; font-family:'Poppins',sans-serif; font-size:.85rem; color:#1e2a4a; outline:none; }
  .day-group { margin-bottom:24px; }
  .day-header { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:12px; }
  .day-label { font-size:1rem; font-weight:700; color:#1e2a4a; }
  .day-stats { display:flex; gap:16px; flex-wrap:wrap; }
  .day-stat { font-size:.78rem; color:#7e8cab; }
  .day-stat strong { color:#3b82f6; font-weight:700; }
  .tbl-wrap { background:rgba(255,255,255,.55); backdrop-filter:blur(20px) saturate(160%); border:1px solid rgba(255,255,255,.7); border-radius:16px; box-shadow:0 8px 28px rgba(59,130,246,.12); overflow:hidden; }
  .bill-table { width:100%; border-collapse:collapse; font-size:.88rem; }
  .bill-table th { padding:12px 18px; font-size:.7rem; text-transform:uppercase; letter-spacing:.6px; color:#8493b0; font-weight:600; background:rgba(59,130,246,.04); border-bottom:1px solid rgba(59,130,246,.1); text-align:left; }
  .bill-table td { padding:12px 18px; border-bottom:1px solid rgba(59,130,246,.07); color:#1e2a4a; vertical-align:middle; }
  .bill-table tbody tr:last-child td { border-bottom:none; }
  .bill-table tbody tr:hover { background:rgba(59,130,246,.04); }
  .pts-badge { font-weight:700; color:#6366f1; }
  .btn-sm-view { background:rgba(59,130,246,.1); border:1px solid rgba(59,130,246,.25); color:#3b82f6; font-size:.78rem; font-weight:600; font-family:'Poppins',sans-serif; border-radius:8px; padding:5px 12px; text-decoration:none; display:inline-flex; align-items:center; gap:5px; transition:all .2s; }
  .btn-sm-view:hover { background:rgba(59,130,246,.2); color:#1d4ed8; }
</style>
{% endblock style %}

{% block content %}
<div class="page-wrapper">
  <div class="container-fluid px-2 px-md-3">
    <div class="page-title"><div class="title-icon"><i class="fas fa-file-invoice"></i></div>Bill History</div>
    <div class="page-subtitle">Procurement records grouped by date</div>

    <form method="GET" class="filter-bar">
      <select name="user" class="glass-select-filter" onchange="this.form.submit()">
        <option value="">All Members</option>
        {% for m in members %}
        <option value="{{ m.pk }}" {% if selected_user == m.pk|stringformat:"s" %}selected{% endif %}>{{ m.first_name|default:m.username }} {{ m.last_name }}</option>
        {% endfor %}
      </select>
      {% if selected_user %}<a href="/billing/bills/" style="font-size:.85rem;color:#e11d48;align-self:center;">✕ Clear</a>{% endif %}
    </form>

    {% for group in grouped %}
    <div class="day-group">
      <div class="day-header">
        <div class="day-label"><i class="fas fa-calendar-day me-2" style="color:#3b82f6;"></i>{{ group.date }}</div>
        <div class="day-stats">
          <div class="day-stat"><strong>{{ group.bill_count }}</strong> bills</div>
          <div class="day-stat"><strong>₹{{ group.total_amount }}</strong> total</div>
          <div class="day-stat"><strong>{{ group.total_points }}</strong> points awarded</div>
        </div>
      </div>
      <div class="tbl-wrap">
        <table class="bill-table">
          <thead><tr><th>#</th><th>Member</th><th>Items</th><th>Amount</th><th>Points</th><th>Note</th><th></th></tr></thead>
          <tbody>
            {% for bill in group.bills %}
            <tr>
              <td style="color:#8493b0;">#{{ bill.pk }}</td>
              <td><strong>{{ bill.user.first_name|default:bill.user.username }}</strong></td>
              <td>{{ bill.items.count }}</td>
              <td>₹{{ bill.total_amount }}</td>
              <td><span class="pts-badge">{{ bill.total_points }}</span></td>
              <td style="color:#7e8cab;">{{ bill.note|default:"—"|truncatechars:30 }}</td>
              <td><a href="{% url 'billing:bill_detail' bill.pk %}" class="btn-sm-view"><i class="fas fa-eye"></i> View</a></td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    {% empty %}
    <div style="text-align:center;padding:80px 20px;color:#8493b0;">
      <i class="fas fa-receipt" style="font-size:3rem;opacity:.2;display:block;margin-bottom:16px;"></i>
      No bills yet.
    </div>
    {% endfor %}
  </div>
</div>
{% endblock content %}
```

- [ ] **Step 4: Create `templates/billing/bill_detail.html`**

```html
{% extends "base.html" %}
{% block style %}
<style>
  .page-wrapper { padding: 40px 20px 60px; min-height: calc(100vh - 60px); }
  .page-title { font-size:1.5rem; font-weight:700; color:#1e2a4a; display:flex; align-items:center; gap:12px; margin-bottom:4px; }
  .title-icon { width:42px; height:42px; background:linear-gradient(135deg,#3b82f6,#6366f1); border-radius:12px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:1rem; }
  .page-subtitle { color:#7e8cab; font-size:.88rem; margin-left:54px; margin-bottom:28px; }
  .detail-card { background:rgba(255,255,255,.55); backdrop-filter:blur(20px) saturate(160%); border:1px solid rgba(255,255,255,.7); border-radius:20px; padding:28px; box-shadow:0 8px 28px rgba(59,130,246,.12); margin-bottom:20px; }
  .meta-row { display:flex; gap:32px; flex-wrap:wrap; margin-bottom:20px; }
  .meta-item label { font-size:.7rem; text-transform:uppercase; letter-spacing:.6px; color:#8493b0; display:block; margin-bottom:2px; }
  .meta-item span { font-weight:600; color:#1e2a4a; }
  .items-table { width:100%; border-collapse:collapse; font-size:.88rem; }
  .items-table th { padding:12px 16px; font-size:.7rem; text-transform:uppercase; letter-spacing:.6px; color:#8493b0; font-weight:600; background:rgba(59,130,246,.04); border-bottom:1px solid rgba(59,130,246,.1); text-align:left; }
  .items-table td { padding:12px 16px; border-bottom:1px solid rgba(59,130,246,.07); color:#1e2a4a; }
  .items-table tbody tr:last-child td { border-bottom:none; }
  .items-table tfoot td { padding:14px 16px; font-weight:700; background:rgba(59,130,246,.05); color:#1e2a4a; }
  .pts { color:#6366f1; font-weight:700; }
</style>
{% endblock style %}

{% block content %}
<div class="page-wrapper">
  <div class="container-fluid px-2 px-md-3" style="max-width:820px;">
    <a href="{% url 'billing:bill_list' %}" style="font-size:.85rem;color:#3b82f6;text-decoration:none;display:inline-flex;align-items:center;gap:6px;margin-bottom:16px;"><i class="fas fa-arrow-left"></i> Back to Bills</a>
    <div class="page-title"><div class="title-icon"><i class="fas fa-receipt"></i></div>Bill #{{ bill.pk }}</div>
    <div class="page-subtitle">{{ bill.created_at|date:"d M Y, H:i" }}</div>

    <div class="detail-card">
      <div class="meta-row">
        <div class="meta-item"><label>Member</label><span>{{ bill.user.first_name|default:bill.user.username }} {{ bill.user.last_name }}</span></div>
        <div class="meta-item"><label>Username</label><span>@{{ bill.user.username }}</span></div>
        <div class="meta-item"><label>Date</label><span>{{ bill.created_at|date:"d M Y" }}</span></div>
        <div class="meta-item"><label>Time</label><span>{{ bill.created_at|time:"H:i" }}</span></div>
        {% if bill.note %}<div class="meta-item"><label>Note</label><span>{{ bill.note }}</span></div>{% endif %}
      </div>

      <table class="items-table">
        <thead>
          <tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Unit Points</th><th>Line Amount</th><th>Line Points</th></tr>
        </thead>
        <tbody>
          {% for item in bill.items.all %}
          <tr>
            <td><strong>{{ item.product.name|default:"(deleted)" }}</strong></td>
            <td>{{ item.quantity }}</td>
            <td>₹{{ item.unit_price }}</td>
            <td class="pts">{{ item.unit_points }}</td>
            <td>₹{{ item.line_total_amount }}</td>
            <td class="pts">{{ item.line_total_points }}</td>
          </tr>
          {% endfor %}
        </tbody>
        <tfoot>
          <tr>
            <td colspan="4" style="text-align:right;">Grand Total</td>
            <td>₹{{ bill.total_amount }}</td>
            <td class="pts">{{ bill.total_points }} pts</td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</div>
{% endblock content %}
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python manage.py test billing.tests.BillListDetailTest --verbosity=2
```

Expected: `3 tests, 0 failures`

- [ ] **Step 6: Commit**

```bash
git add billing/views.py billing/tests.py templates/billing/bill_list.html templates/billing/bill_detail.html
git commit -m "feat: bill list and detail views"
```

---

## Task 8 — Point Adjustment view

**Files:**
- Modify: `billing/views.py`, `billing/tests.py`

- [ ] **Step 1: Write tests** (append to `billing/tests.py`)

```python
class PointAdjustViewTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin4', password='admin')
        self.member = User.objects.create_user(username='adj_member', password='pass')
        Points.objects.create(host=self.member, total_points=100)
        self.client.login(username='admin4', password='admin')

    def test_positive_adjustment(self):
        self.client.post(f'/billing/adjust/{self.member.pk}/', {'delta': 50, 'reason': 'Bonus'})
        self.assertEqual(Points.objects.get(host=self.member).total_points, 150)

    def test_negative_adjustment(self):
        self.client.post(f'/billing/adjust/{self.member.pk}/', {'delta': -30, 'reason': 'Correction'})
        self.assertEqual(Points.objects.get(host=self.member).total_points, 70)

    def test_adjustment_record_saved(self):
        self.client.post(f'/billing/adjust/{self.member.pk}/', {'delta': 25, 'reason': 'Test'})
        self.assertEqual(PointAdjustment.objects.filter(user=self.member).count(), 1)
        self.assertEqual(PointAdjustment.objects.get(user=self.member).delta, 25)

    def test_get_request_redirects(self):
        response = self.client.get(f'/billing/adjust/{self.member.pk}/')
        self.assertRedirects(response, '/')
```

- [ ] **Step 2: Implement `point_adjust` in `billing/views.py`** (replace stub)

```python
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
```

- [ ] **Step 3: Run tests**

```bash
.venv/bin/python manage.py test billing.tests.PointAdjustViewTest --verbosity=2
```

Expected: `4 tests, 0 failures`

- [ ] **Step 4: Commit**

```bash
git add billing/views.py billing/tests.py
git commit -m "feat: point adjustment view with F() expression update"
```

---

## Task 9 — WhatsApp Template view

**Files:**
- Modify: `billing/views.py`
- Create: `templates/billing/whatsapp_template.html`

- [ ] **Step 1: Implement `whatsapp_template` in `billing/views.py`** (replace stub)

```python
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
```

- [ ] **Step 2: Create `templates/billing/whatsapp_template.html`**

```html
{% extends "base.html" %}
{% block style %}
<style>
  .form-page { min-height:calc(100vh - 64px); display:flex; align-items:center; justify-content:center; padding:40px 20px; }
  .form-card { background:rgba(255,255,255,.55); backdrop-filter:blur(24px) saturate(160%); border:1px solid rgba(255,255,255,.7); border-radius:24px; padding:40px; width:100%; max-width:560px; box-shadow:0 12px 48px rgba(59,130,246,.15); }
  .form-title { font-size:1.3rem; font-weight:700; color:#1e2a4a; margin-bottom:8px; display:flex; align-items:center; gap:10px; }
  .form-title i { color:#25d366; }
  .hint { font-size:.82rem; color:#8493b0; margin-bottom:24px; }
  .hint code { background:rgba(59,130,246,.08); border-radius:5px; padding:2px 6px; color:#3b82f6; font-size:.8rem; }
  .glass-textarea { width:100%; background:rgba(255,255,255,.6); border:1px solid rgba(59,130,246,.2); border-radius:10px; padding:12px 14px; font-family:'Poppins',sans-serif; font-size:.9rem; color:#1e2a4a; outline:none; resize:vertical; }
  .glass-textarea:focus { border-color:rgba(59,130,246,.5); box-shadow:0 0 0 3px rgba(59,130,246,.12); }
  .saved-msg { color:#059669; font-size:.85rem; margin-top:8px; }
</style>
{% endblock style %}

{% block content %}
<div class="form-page">
  <div class="form-card">
    <div class="form-title"><i class="fab fa-whatsapp"></i>WhatsApp Message Template</div>
    <div class="hint">
      Use <code>{name}</code> for member's name, <code>{points}</code> for current points balance, <code>{amount}</code> for bill total amount.
    </div>
    <form method="POST">
      {% csrf_token %}
      <div style="margin-bottom:20px;">
        <label style="font-size:.82rem;font-weight:600;color:#5a6a8a;text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:8px;">Message Template</label>
        <textarea name="body" class="glass-textarea" rows="6">{{ form.body.value }}</textarea>
        {% if form.body.errors %}<div style="color:#e11d48;font-size:.8rem;margin-top:4px;">{{ form.body.errors.0 }}</div>{% endif %}
      </div>
      <button type="submit" class="btn-primary-glass"><i class="fas fa-check me-1"></i>Save Template</button>
    </form>
    {% if request.method == 'GET' and not form.errors %}
    <div class="saved-msg" style="display:none;">✓ Template saved.</div>
    {% endif %}
  </div>
</div>
{% endblock content %}
```

- [ ] **Step 3: Quick smoke test**

```bash
.venv/bin/python manage.py check
```

Expected: `0 issues`

- [ ] **Step 4: Commit**

```bash
git add billing/views.py templates/billing/whatsapp_template.html
git commit -m "feat: WhatsApp template edit view"
```

---

## Task 10 — Add Create User to users app

**Files:**
- Modify: `users/forms.py`, `users/views.py`, `users/urls.py`
- Create: `templates/create_user.html`

- [ ] **Step 1: Write test in `users/tests.py`**

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from users.models import Points

User = get_user_model()


class CreateUserViewTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='superadmin', password='admin')
        self.client.login(username='superadmin', password='admin')

    def test_create_user_page_200(self):
        response = self.client.get('/users/create/')
        self.assertEqual(response.status_code, 200)

    def test_create_user_creates_user_and_points(self):
        response = self.client.post('/users/create/', {
            'username': 'newmember',
            'first_name': 'New',
            'last_name': 'Member',
            'mobile': '9876543210',
            'password': 'testpass123',
            'initial_points': 50,
        })
        self.assertRedirects(response, '/')
        self.assertTrue(User.objects.filter(username='newmember').exists())
        user = User.objects.get(username='newmember')
        self.assertEqual(Points.objects.get(host=user).total_points, 50)

    def test_non_superuser_blocked(self):
        self.client.logout()
        reg = User.objects.create_user(username='reg2', password='pass')
        self.client.login(username='reg2', password='pass')
        response = self.client.get('/users/create/')
        self.assertRedirects(response, '/')
```

- [ ] **Step 2: Run tests — expect failures**

```bash
.venv/bin/python manage.py test users.tests --verbosity=2
```

Expected: `ImportError` or `404` (URL doesn't exist yet).

- [ ] **Step 3: Add `CreateUserForm` to `users/forms.py`** (append to existing file)

```python
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
```

- [ ] **Step 4: Add `create_user` view to `users/views.py`** (append before the last line)

```python
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
```

- [ ] **Step 5: Add URL to `users/urls.py`**

```python
from django.urls import path
from users import views

urlpatterns = [
    path('', views.index, name='home'),
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
    path('register/', views.registerPage, name='register'),
    path('addpoint/', views.add_point, name='addpoint'),
    path('update_points/<int:user_id>/<str:username>/', views.update_points, name='update_points'),
    path('delete_points/<int:user_id>/<str:username>/', views.delete_points, name='delete_points'),
    path('users/create/', views.create_user, name='create_user'),
]
```

- [ ] **Step 6: Create `templates/create_user.html`**

```html
{% extends "base.html" %}
{% block style %}
<style>
  .form-page { min-height:calc(100vh - 64px); display:flex; align-items:center; justify-content:center; padding:40px 20px; }
  .form-card { background:rgba(255,255,255,.55); backdrop-filter:blur(24px) saturate(160%); border:1px solid rgba(255,255,255,.7); border-radius:24px; padding:40px; width:100%; max-width:520px; box-shadow:0 12px 48px rgba(59,130,246,.15); }
  .form-title { font-size:1.4rem; font-weight:700; color:#1e2a4a; margin-bottom:28px; display:flex; align-items:center; gap:10px; }
  .form-title i { color:#3b82f6; }
  .field-group { margin-bottom:18px; }
  .field-group label { font-size:.82rem; font-weight:600; color:#5a6a8a; text-transform:uppercase; letter-spacing:.5px; display:block; margin-bottom:6px; }
  .glass-input { width:100%; background:rgba(255,255,255,.6); border:1px solid rgba(59,130,246,.2); border-radius:10px; padding:10px 14px; font-family:'Poppins',sans-serif; font-size:.9rem; color:#1e2a4a; outline:none; transition:all .2s; }
  .glass-input:focus { background:rgba(255,255,255,.85); border-color:rgba(59,130,246,.5); box-shadow:0 0 0 3px rgba(59,130,246,.12); }
  .row-2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  .form-actions { display:flex; gap:12px; margin-top:28px; }
  .err { color:#e11d48; font-size:.8rem; margin-top:4px; }
</style>
{% endblock style %}

{% block content %}
<div class="form-page">
  <div class="form-card">
    <div class="form-title"><i class="fas fa-user-plus"></i>Add New Member</div>
    <form method="POST">
      {% csrf_token %}
      <div class="row-2">
        <div class="field-group">
          <label>First Name *</label>
          <input type="text" name="first_name" class="glass-input" value="{{ form.first_name.value|default:'' }}" placeholder="First name">
          {% if form.first_name.errors %}<div class="err">{{ form.first_name.errors.0 }}</div>{% endif %}
        </div>
        <div class="field-group">
          <label>Last Name</label>
          <input type="text" name="last_name" class="glass-input" value="{{ form.last_name.value|default:'' }}" placeholder="Last name">
        </div>
      </div>
      <div class="field-group">
        <label>Username *</label>
        <input type="text" name="username" class="glass-input" value="{{ form.username.value|default:'' }}" placeholder="Unique login username">
        {% if form.username.errors %}<div class="err">{{ form.username.errors.0 }}</div>{% endif %}
      </div>
      <div class="field-group">
        <label>Mobile Number *</label>
        <input type="text" name="mobile" class="glass-input" value="{{ form.mobile.value|default:'' }}" placeholder="10-digit number">
        {% if form.mobile.errors %}<div class="err">{{ form.mobile.errors.0 }}</div>{% endif %}
      </div>
      <div class="field-group">
        <label>Password *</label>
        <input type="password" name="password" class="glass-input" placeholder="Set a password">
      </div>
      <div class="field-group">
        <label>Initial Points</label>
        <input type="number" name="initial_points" class="glass-input" value="{{ form.initial_points.value|default:'0' }}" min="0" placeholder="0">
      </div>
      <div class="form-actions">
        <button type="submit" class="btn-primary-glass"><i class="fas fa-user-plus me-1"></i>Create Member</button>
        <a href="/" class="btn-danger-glass"><i class="fas fa-xmark me-1"></i>Cancel</a>
      </div>
    </form>
  </div>
</div>
{% endblock content %}
```

- [ ] **Step 7: Run tests**

```bash
.venv/bin/python manage.py test users.tests --verbosity=2
```

Expected: `3 tests, 0 failures`

- [ ] **Step 8: Commit**

```bash
git add users/forms.py users/views.py users/urls.py templates/create_user.html users/tests.py
git commit -m "feat: admin create user with initial points"
```

---

## Task 11 — Remove old users app code + migrate

**Files:**
- Modify: `users/models.py`, `users/views.py`, `users/urls.py`, `users/forms.py`, `users/admin.py`
- Auto-generate: `users/migrations/0004_remove_product.py`

- [ ] **Step 1: Remove `Product` from `users/models.py`**

Delete the entire `Product` class (lines ~54–61 in the original file). The final `users/models.py` should only contain `CustomUserManager`, `CustomUser`, and `Points`.

- [ ] **Step 2: Remove old views from `users/views.py`**

Delete these functions entirely:
- `send_api_request`
- `calculate_total_points`
- `add_point`
- `update_points`
- `delete_points`

Also remove unused import at top: change `from .models import Points,Product,CustomUser` to `from .models import Points, CustomUser`.

Also remove `from .forms import UserPointsForm,UpdatePointsForm,CustomRegistrationForm` — change to `from .forms import CustomRegistrationForm, CreateUserForm`.

- [ ] **Step 3: Remove `UserPointsForm` and `UpdatePointsForm` from `users/forms.py`**

Delete `UserPointsForm` and `UpdatePointsForm` classes. Keep `LoginForm`, `CustomRegistrationForm`, and `CreateUserForm`.

Also remove top import `from .models import Product,Points,CustomUser` — change to `from .models import CustomUser`.

- [ ] **Step 4: Update `users/admin.py`**

```python
from django.contrib import admin
from .models import CustomUser, Points

admin.site.register(CustomUser)
admin.site.register(Points)
```

- [ ] **Step 5: Update `users/urls.py`** — remove the three old point URLs

```python
from django.urls import path
from users import views

urlpatterns = [
    path('', views.index, name='home'),
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
    path('register/', views.registerPage, name='register'),
    path('users/create/', views.create_user, name='create_user'),
]
```

- [ ] **Step 6: Generate migration to remove Product from users**

```bash
.venv/bin/python manage.py makemigrations users --name remove_product
```

Expected: `Migrations for 'users': users/migrations/0004_remove_product.py`

Open `users/migrations/0004_remove_product.py` and ensure it has a dependency on `('billing', '0002_data_migration')` so product data is preserved before the table is dropped:

```python
class Migration(migrations.Migration):
    dependencies = [
        ('users', '0003_alter_customuser_options'),
        ('billing', '0002_data_migration'),
    ]
    operations = [
        migrations.DeleteModel(name='Product'),
    ]
```

- [ ] **Step 7: Apply all pending migrations**

```bash
.venv/bin/python manage.py migrate
```

Expected: `Running migrations: Applying users.0004_remove_product... OK`

- [ ] **Step 8: Run all tests — everything should still pass**

```bash
.venv/bin/python manage.py test billing.tests users.tests --verbosity=2
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add users/models.py users/views.py users/urls.py users/forms.py users/admin.py users/migrations/0004_remove_product.py
git commit -m "feat: remove old Product model and add/update/deduct views from users app"
```

---

## Task 12 — Revamp admin dashboard + update navbar

**Files:**
- Modify: `users/views.py`, `templates/admin_home.html`, `templates/base.html`

- [ ] **Step 1: Update `index` view in `users/views.py`** to pass `wa_template_body`

Replace the superuser branch of `index`:

```python
if request.user.is_superuser:
    from billing.models import WhatsAppTemplate
    tmpl = WhatsAppTemplate.objects.filter(pk=1).first()
    wa_template_body = tmpl.body if tmpl else 'Hi {name}! You have {points} reward points.'
    return render(request, "admin_home.html", context={
        'points': user_points,
        'wa_template_body': wa_template_body,
    })
```

- [ ] **Step 2: Add Products + Bills nav links to `templates/base.html`**

In the superuser navbar section, replace the existing `<ul>`:

```html
<ul class="navbar-nav me-auto gap-1 ms-2">
  <li class="nav-item">
    <a class="nav-link" href="/"><i class="fas fa-grid-2 me-1"></i>Dashboard</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" href="{% url 'billing:product_list' %}"><i class="fas fa-box me-1"></i>Products</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" href="{% url 'billing:bill_list' %}"><i class="fas fa-file-invoice me-1"></i>Bills</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" href="{% url 'create_user' %}"><i class="fas fa-user-plus me-1"></i>Add Member</a>
  </li>
</ul>
```

- [ ] **Step 3: Replace `templates/admin_home.html`** with the following complete file

```html
{% extends "base.html" %}

{% block style %}
<style>
  .page-wrapper { padding: 40px 20px 60px; min-height: calc(100vh - 60px); }
  .page-title { font-size: 1.75rem; font-weight: 700; color: #1e2a4a; display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
  .title-icon { width: 42px; height: 42px; background: linear-gradient(135deg, #3b82f6, #6366f1); border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 1rem; flex-shrink: 0; box-shadow: 0 6px 18px rgba(59,130,246,.35); }
  .page-subtitle { color: #7e8cab; font-size: .88rem; margin-left: 54px; }
  .stats-bar { display: flex; gap: 16px; margin: 28px 0; flex-wrap: wrap; align-items: center; }
  .stat-chip { background: rgba(255,255,255,.55); backdrop-filter: blur(16px) saturate(160%); border: 1px solid rgba(255,255,255,.7); border-radius: 12px; padding: 10px 18px; display: flex; align-items: center; gap: 10px; box-shadow: 0 6px 20px rgba(59,130,246,.1); }
  .stat-chip-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: .85rem; }
  .stat-chip-val { font-size: 1.1rem; font-weight: 700; color: #1e2a4a; }
  .stat-chip-lbl { font-size: .72rem; color: #8493b0; text-transform: uppercase; letter-spacing: .6px; }
  .view-toggle { display: inline-flex; margin-left: auto; align-self: center; background: rgba(255,255,255,.55); backdrop-filter: blur(16px) saturate(160%); border: 1px solid rgba(255,255,255,.7); border-radius: 12px; padding: 4px; gap: 4px; box-shadow: 0 6px 20px rgba(59,130,246,.1); }
  .view-toggle button { border: none; background: transparent; color: #7e8cab; font-family: 'Poppins',sans-serif; font-size: .82rem; font-weight: 600; border-radius: 9px; padding: 7px 16px; cursor: pointer; display: flex; align-items: center; gap: 7px; transition: all .2s; }
  .view-toggle button:hover { color: #3b82f6; }
  .view-toggle button.active { background: linear-gradient(135deg,#3b82f6,#6366f1); color: #fff; box-shadow: 0 4px 12px rgba(59,130,246,.3); }
  .is-hidden { display: none !important; }

  /* ── Table view ── */
  .users-table-wrap { background: rgba(255,255,255,.55); backdrop-filter: blur(20px) saturate(160%); border: 1px solid rgba(255,255,255,.7); border-radius: 20px; box-shadow: 0 8px 28px rgba(59,130,246,.12); overflow: hidden; }
  .users-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
  .users-table thead th { text-align: left; padding: 16px 18px; font-size: .72rem; text-transform: uppercase; letter-spacing: .6px; color: #8493b0; font-weight: 600; background: rgba(59,130,246,.05); border-bottom: 1px solid rgba(59,130,246,.1); }
  .users-table tbody td { padding: 14px 18px; border-bottom: 1px solid rgba(59,130,246,.07); color: #1e2a4a; vertical-align: middle; }
  .users-table tbody tr:last-child td { border-bottom: none; }
  .users-table tbody tr:hover { background: rgba(59,130,246,.04); }
  .table-member { display: flex; align-items: center; gap: 12px; }
  .table-avatar { width: 38px; height: 38px; border-radius: 11px; background: linear-gradient(135deg,#3b82f6,#6366f1); display: flex; align-items: center; justify-content: center; font-size: .95rem; font-weight: 700; color: #fff; text-transform: uppercase; flex-shrink: 0; }
  .table-points { font-weight: 700; font-size: 1.05rem; background: linear-gradient(135deg,#3b82f6,#6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
  .table-actions { display: flex; gap: 6px; flex-wrap: wrap; }
  .tbl-bill { background: rgba(59,130,246,.1); border: 1px solid rgba(59,130,246,.25); color: #3b82f6; font-size: .75rem; font-weight: 600; font-family: 'Poppins',sans-serif; border-radius: 8px; padding: 5px 10px; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; transition: all .2s; }
  .tbl-bill:hover { background: rgba(59,130,246,.2); color: #1d4ed8; transform: translateY(-1px); }
  .tbl-adjust { background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.25); color: #059669; font-size: .75rem; font-weight: 600; font-family: 'Poppins',sans-serif; border-radius: 8px; padding: 5px 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; transition: all .2s; }
  .tbl-adjust:hover { background: rgba(16,185,129,.2); color: #047857; transform: translateY(-1px); }
  .tbl-notify { background: rgba(37,211,102,.1); border: 1px solid rgba(37,211,102,.3); color: #15803d; font-size: .75rem; font-weight: 600; font-family: 'Poppins',sans-serif; border-radius: 8px; padding: 5px 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; transition: all .2s; }
  .tbl-notify:hover { background: rgba(37,211,102,.2); color: #166534; transform: translateY(-1px); }

  /* ── Card view ── */
  .users-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap: 20px; }
  .user-card { background: rgba(255,255,255,.55); backdrop-filter: blur(20px) saturate(160%); border: 1px solid rgba(255,255,255,.7); border-radius: 20px; padding: 24px; box-shadow: 0 8px 28px rgba(59,130,246,.12); transition: transform .2s,box-shadow .2s; position: relative; overflow: hidden; }
  .user-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg,#3b82f6,#6366f1); opacity:0; transition:opacity .2s; }
  .user-card:hover { transform: translateY(-4px); box-shadow: 0 18px 44px rgba(59,130,246,.22); }
  .user-card:hover::before { opacity:1; }
  .card-top { display:flex; align-items:center; gap:14px; margin-bottom:18px; }
  .avatar { width:48px; height:48px; border-radius:14px; background:linear-gradient(135deg,#3b82f6,#6366f1); display:flex; align-items:center; justify-content:center; font-size:1.2rem; font-weight:700; color:#fff; text-transform:uppercase; flex-shrink:0; }
  .user-name { font-size:1rem; font-weight:600; color:#1e2a4a; }
  .user-role { font-size:.75rem; color:#8493b0; margin-top:1px; }
  .points-section { background:rgba(59,130,246,.06); border:1px solid rgba(59,130,246,.12); border-radius:12px; padding:14px 16px; margin-bottom:16px; display:flex; align-items:center; justify-content:space-between; }
  .points-label { font-size:.78rem; color:#8493b0; text-transform:uppercase; letter-spacing:.8px; }
  .points-value { font-size:1.6rem; font-weight:700; background:linear-gradient(135deg,#3b82f6,#6366f1); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; line-height:1; }
  .card-actions { display:flex; gap:8px; flex-wrap:wrap; }
  .btn-card-bill { flex:1; background:rgba(59,130,246,.1); border:1px solid rgba(59,130,246,.25); color:#3b82f6; font-size:.78rem; font-weight:600; font-family:'Poppins',sans-serif; border-radius:10px; padding:7px 10px; text-align:center; text-decoration:none; transition:all .2s; display:flex; align-items:center; justify-content:center; gap:5px; }
  .btn-card-bill:hover { background:rgba(59,130,246,.2); color:#1d4ed8; transform:translateY(-1px); }
  .btn-card-adjust { flex:1; background:rgba(16,185,129,.1); border:1px solid rgba(16,185,129,.25); color:#059669; font-size:.78rem; font-weight:600; font-family:'Poppins',sans-serif; border-radius:10px; padding:7px 10px; text-align:center; cursor:pointer; transition:all .2s; display:flex; align-items:center; justify-content:center; gap:5px; }
  .btn-card-adjust:hover { background:rgba(16,185,129,.2); color:#047857; transform:translateY(-1px); }
  .btn-card-notify { flex:1; background:rgba(37,211,102,.1); border:1px solid rgba(37,211,102,.3); color:#15803d; font-size:.78rem; font-weight:600; font-family:'Poppins',sans-serif; border-radius:10px; padding:7px 10px; text-align:center; cursor:pointer; transition:all .2s; display:flex; align-items:center; justify-content:center; gap:5px; }
  .btn-card-notify:hover { background:rgba(37,211,102,.2); color:#166534; transform:translateY(-1px); }

  /* ── Modals ── */
  .modal-content { background:rgba(255,255,255,.9); backdrop-filter:blur(24px) saturate(160%); border:1px solid rgba(255,255,255,.7); border-radius:20px; box-shadow:0 12px 48px rgba(59,130,246,.2); }
  .modal-header { border-bottom:1px solid rgba(59,130,246,.1); }
  .modal-footer { border-top:1px solid rgba(59,130,246,.1); }
  .modal-title { font-weight:700; color:#1e2a4a; font-size:1.1rem; }
  .modal-member { font-size:.85rem; color:#7e8cab; margin-bottom:16px; }
  .glass-input-modal { width:100%; background:rgba(255,255,255,.7); border:1px solid rgba(59,130,246,.2); border-radius:10px; padding:10px 14px; font-family:'Poppins',sans-serif; font-size:.9rem; color:#1e2a4a; outline:none; margin-bottom:14px; }
  .glass-input-modal:focus { border-color:rgba(59,130,246,.5); box-shadow:0 0 0 3px rgba(59,130,246,.12); }
  .glass-textarea-modal { width:100%; background:rgba(255,255,255,.7); border:1px solid rgba(59,130,246,.2); border-radius:10px; padding:10px 14px; font-family:'Poppins',sans-serif; font-size:.88rem; color:#1e2a4a; outline:none; resize:vertical; }
  .glass-textarea-modal:focus { border-color:rgba(59,130,246,.5); box-shadow:0 0 0 3px rgba(59,130,246,.12); }

  /* Empty state */
  .empty-state { text-align:center; padding:80px 20px; }
  .empty-icon { font-size:3.5rem; margin-bottom:20px; color:#b9c7e8; }
  .empty-title { font-size:1.2rem; font-weight:600; color:#48557a; margin-bottom:8px; }
  .empty-sub { font-size:.85rem; color:#8493b0; }

  @media (max-width:640px) {
    .users-table thead { display:none; }
    .users-table, .users-table tbody, .users-table tr, .users-table td { display:block; width:100%; }
    .users-table tr { padding:10px 4px; border-bottom:1px solid rgba(59,130,246,.12); }
    .users-table tbody tr:last-child { border-bottom:none; }
    .users-table td { padding:6px 18px; border:none; }
    .table-actions { flex-wrap:wrap; }
  }
</style>
{% endblock style %}

{% block content %}
{% if user.is_authenticated %}
<div class="page-wrapper">
  <div class="container-fluid px-2 px-md-3">

    <div class="page-title">
      <div class="title-icon"><i class="fas fa-users"></i></div>
      Member Dashboard
    </div>
    <div class="page-subtitle">Manage procurement bills and reward points</div>

    {% if points %}
    <div class="stats-bar">
      <div class="stat-chip">
        <div class="stat-chip-icon" style="background:rgba(59,130,246,.15);"><i class="fas fa-users" style="color:#3b82f6;"></i></div>
        <div><div class="stat-chip-val">{{ points|length }}</div><div class="stat-chip-lbl">Members</div></div>
      </div>
      <a href="{% url 'create_user' %}" style="text-decoration:none;">
        <div class="stat-chip" style="cursor:pointer;border-color:rgba(59,130,246,.3);">
          <div class="stat-chip-icon" style="background:linear-gradient(135deg,#3b82f6,#6366f1);"><i class="fas fa-user-plus" style="color:#fff;"></i></div>
          <div><div class="stat-chip-val" style="font-size:.9rem;color:#3b82f6;">Add Member</div><div class="stat-chip-lbl">Create account</div></div>
        </div>
      </a>
      <a href="{% url 'billing:bill_list' %}" style="text-decoration:none;">
        <div class="stat-chip" style="cursor:pointer;border-color:rgba(99,102,241,.3);">
          <div class="stat-chip-icon" style="background:rgba(99,102,241,.15);"><i class="fas fa-file-invoice" style="color:#6366f1;"></i></div>
          <div><div class="stat-chip-val" style="font-size:.9rem;color:#6366f1;">Bill History</div><div class="stat-chip-lbl">All records</div></div>
        </div>
      </a>
      <div class="view-toggle" role="group">
        <button type="button" id="btn-table-view" class="active" onclick="setView('table')"><i class="fas fa-table-list"></i> Table</button>
        <button type="button" id="btn-card-view" onclick="setView('cards')"><i class="fas fa-th-large"></i> Cards</button>
      </div>
    </div>

    <!-- TABLE VIEW -->
    <div class="users-table-wrap" id="tableView">
      <table class="users-table">
        <thead>
          <tr><th>Member</th><th>Mobile</th><th>Points</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {% for i in points %}
          <tr>
            <td>
              <div class="table-member">
                <div class="table-avatar">{{ i.username|first }}</div>
                <div>
                  <div style="font-weight:600;">{{ i.first_name|default:'' }} {{ i.last_name|default:'' }}</div>
                  <div style="font-size:.75rem;color:#8493b0;">@{{ i.username }}</div>
                </div>
              </div>
            </td>
            <td style="color:#7e8cab;">{{ i.mobile|default:"—" }}</td>
            <td><span class="table-points">{% if i.total_points %}{{ i.total_points }}{% else %}0{% endif %}</span></td>
            <td>
              <div class="table-actions">
                <a href="{% url 'billing:bill_create' i.id %}" class="tbl-bill"><i class="fas fa-receipt"></i> Bill</a>
                <button type="button" class="tbl-adjust"
                  data-user-id="{{ i.id }}"
                  data-user-name="{{ i.first_name|default:i.username }}"
                  onclick="openAdjust(this)"><i class="fas fa-sliders"></i> Adjust</button>
                <button type="button" class="tbl-notify"
                  data-user-id="{{ i.id }}"
                  data-name="{{ i.first_name|default:i.username }}"
                  data-points="{% if i.total_points %}{{ i.total_points }}{% else %}0{% endif %}"
                  data-mobile="{{ i.mobile|default:'' }}"
                  onclick="openNotify(this)"><i class="fab fa-whatsapp"></i> Notify</button>
              </div>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <!-- CARD VIEW -->
    <div class="users-grid is-hidden" id="cardsView">
      {% for i in points %}
      <div class="user-card">
        <div class="card-top">
          <div class="avatar">{{ i.username|first }}</div>
          <div>
            <div class="user-name">{{ i.first_name|default:'' }} {{ i.last_name|default:i.username }}</div>
            <div class="user-role">@{{ i.username }} · {{ i.mobile|default:"no phone" }}</div>
          </div>
        </div>
        <div class="points-section">
          <div>
            <div class="points-label">Total Points</div>
            <div class="points-value">{% if i.total_points %}{{ i.total_points }}{% else %}0{% endif %}</div>
          </div>
          <i class="fas fa-star" style="font-size:1.4rem;opacity:.2;color:#6366f1;"></i>
        </div>
        <div class="card-actions">
          <a href="{% url 'billing:bill_create' i.id %}" class="btn-card-bill"><i class="fas fa-receipt"></i> Bill</a>
          <button type="button" class="btn-card-adjust"
            data-user-id="{{ i.id }}"
            data-user-name="{{ i.first_name|default:i.username }}"
            onclick="openAdjust(this)"><i class="fas fa-sliders"></i> Adjust</button>
          <button type="button" class="btn-card-notify"
            data-user-id="{{ i.id }}"
            data-name="{{ i.first_name|default:i.username }}"
            data-points="{% if i.total_points %}{{ i.total_points }}{% else %}0{% endif %}"
            data-mobile="{{ i.mobile|default:'' }}"
            onclick="openNotify(this)"><i class="fab fa-whatsapp"></i> Notify</button>
        </div>
      </div>
      {% endfor %}
    </div>

    {% else %}
    <div class="empty-state">
      <div class="empty-icon"><i class="fas fa-users-slash"></i></div>
      <div class="empty-title">No members yet</div>
      <div class="empty-sub">Add your first member to get started</div>
      <a href="{% url 'create_user' %}" class="btn-primary-glass mt-3 d-inline-flex"><i class="fas fa-user-plus me-1"></i>Add First Member</a>
    </div>
    {% endif %}

  </div>
</div>

<!-- ── Adjust Modal ── -->
<div class="modal fade" id="adjustModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title"><i class="fas fa-sliders me-2" style="color:#059669;"></i>Adjust Points</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <form method="POST" id="adjustForm">
        {% csrf_token %}
        <div class="modal-body">
          <p class="modal-member" id="adjustMemberName"></p>
          <label style="font-size:.82rem;font-weight:600;color:#5a6a8a;text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px;">Points (negative to deduct)</label>
          <input type="number" name="delta" class="glass-input-modal" placeholder="e.g. 50 or -20" required>
          <label style="font-size:.82rem;font-weight:600;color:#5a6a8a;text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px;">Reason</label>
          <input type="text" name="reason" class="glass-input-modal" maxlength="200" placeholder="e.g. Loyalty bonus" required>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
          <button type="submit" class="btn-primary-glass">Save Adjustment</button>
        </div>
      </form>
    </div>
  </div>
</div>

<!-- ── Notify Modal ── -->
<div class="modal fade" id="notifyModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title"><i class="fab fa-whatsapp me-2" style="color:#25d366;"></i>WhatsApp Notify</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <p class="modal-member" id="notifyMemberName"></p>
        <label style="font-size:.82rem;font-weight:600;color:#5a6a8a;text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px;">Message (editable)</label>
        <textarea id="notifyMessage" class="glass-textarea-modal" rows="5"></textarea>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        <button type="button" class="btn-success-glass" id="openWaBtn"><i class="fab fa-whatsapp me-1"></i>Open WhatsApp</button>
      </div>
    </div>
  </div>
</div>

<input type="hidden" id="waTemplateBody" value="{{ wa_template_body }}">

<script>
  var _notifyMobile = '';

  function openAdjust(btn) {
    var userId = btn.dataset.userId;
    var userName = btn.dataset.userName;
    document.getElementById('adjustMemberName').textContent = 'Member: ' + userName;
    document.getElementById('adjustForm').action = '/billing/adjust/' + userId + '/';
    new bootstrap.Modal(document.getElementById('adjustModal')).show();
  }

  function openNotify(btn) {
    var name = btn.dataset.name;
    var points = btn.dataset.points;
    _notifyMobile = btn.dataset.mobile;
    var tmpl = document.getElementById('waTemplateBody').value;
    var msg = tmpl.replace('{name}', name).replace('{points}', points).replace('{amount}', '');
    document.getElementById('notifyMemberName').textContent = 'To: ' + name + ' (+91' + _notifyMobile + ')';
    document.getElementById('notifyMessage').value = msg;
    new bootstrap.Modal(document.getElementById('notifyModal')).show();
  }

  document.getElementById('openWaBtn').addEventListener('click', function () {
    var text = document.getElementById('notifyMessage').value;
    var url = 'https://wa.me/91' + _notifyMobile + '?text=' + encodeURIComponent(text);
    window.open(url, '_blank');
  });

  function setView(view) {
    var cards = document.getElementById('cardsView');
    var table = document.getElementById('tableView');
    var btnT = document.getElementById('btn-table-view');
    var btnC = document.getElementById('btn-card-view');
    if (!cards || !table) return;
    var showTable = view !== 'cards';
    table.classList.toggle('is-hidden', !showTable);
    cards.classList.toggle('is-hidden', showTable);
    btnT.classList.toggle('active', showTable);
    btnC.classList.toggle('active', !showTable);
    try { localStorage.setItem('dashboardView', showTable ? 'table' : 'cards'); } catch(e){}
  }

  document.addEventListener('DOMContentLoaded', function () {
    var saved = 'table';
    try { saved = localStorage.getItem('dashboardView') || 'table'; } catch(e){}
    setView(saved);
  });
</script>
{% else %}
<div style="text-align:center;padding:80px 20px;color:#7e8cab;">
  Please <a href="{% url 'login' %}" style="color:#3b82f6;">log in</a> to continue.
</div>
{% endif %}
{% endblock content %}
```

- [ ] **Step 4: Run full test suite**

```bash
.venv/bin/python manage.py test billing.tests users.tests --verbosity=2
```

Expected: all tests pass.

- [ ] **Step 5: Start dev server and smoke-test manually**

```bash
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Verify:
- Log in as `admin`/`admin` → dashboard shows table with Bill/Adjust/Notify buttons
- Click **Bill** for a user → bill create page loads with product dropdown and live totals
- Add items, save → redirects to dashboard; user's points updated
- Click **Adjust** → modal opens, submit → points change reflected immediately on next page load
- Click **Notify** → modal opens with pre-filled WhatsApp message; "Open WhatsApp" opens `wa.me` URL in new tab
- Nav links: Products, Bills, Add Member all work

- [ ] **Step 6: Commit**

```bash
git add users/views.py templates/admin_home.html templates/base.html
git commit -m "feat: revamp admin dashboard — Bill/Adjust/Notify buttons and WhatsApp modal"
```

---

## Task 13 — Final migration run and cleanup

- [ ] **Step 1: Run all migrations against Supabase**

```bash
.venv/bin/python manage.py migrate
```

Expected: `No migrations to apply.` (all already applied during development).

- [ ] **Step 2: Run full test suite one final time**

```bash
.venv/bin/python manage.py test billing.tests users.tests --verbosity=2
```

Expected: all tests pass, 0 failures.

- [ ] **Step 3: Verify Django check**

```bash
.venv/bin/python manage.py check --deploy 2>&1 | grep -v "WARNINGS"
```

Expected: no errors (warnings about HTTPS/HSTS are expected for local dev).

- [ ] **Step 4: Final commit**

```bash
git add -A
git status  # review — should be clean or only untracked test_db.sqlite3
git commit -m "feat: billing module complete — products, bills, adjustments, WhatsApp notify"
```

Add `test_db.sqlite3` to `.gitignore` if not already excluded:

```bash
echo "test_db.sqlite3" >> .gitignore
git add .gitignore
git commit -m "chore: ignore test SQLite database"
```
