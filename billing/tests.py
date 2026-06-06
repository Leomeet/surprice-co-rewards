from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from billing.models import Product, Bill, BillItem, PointAdjustment, WhatsAppTemplate
from users.models import Points

User = get_user_model()


class ProductModelTest(TestCase):
    def test_product_fields_exist(self):
        p = Product.objects.create(name='Gold Wash', price='150.00', point_value=75)
        p.refresh_from_db()
        self.assertEqual(p.price, Decimal('150.00'))
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
