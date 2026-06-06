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
