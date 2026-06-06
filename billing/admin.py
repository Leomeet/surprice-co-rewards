from django.contrib import admin
from .models import Product, Bill, BillItem, PointAdjustment, WhatsAppTemplate

admin.site.register(Product)
admin.site.register(Bill)
admin.site.register(BillItem)
admin.site.register(PointAdjustment)
admin.site.register(WhatsAppTemplate)
