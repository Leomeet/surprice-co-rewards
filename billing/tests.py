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

    def test_empty_quantities_ignored(self):
        self.client.post(f'/billing/bill/create/{self.member.pk}/', {
            'product_id': [str(self.product.pk)],
            'quantity': ['0'],
            'note': '',
        })
        self.assertEqual(Bill.objects.count(), 0)
        self.assertEqual(Points.objects.get(host=self.member).total_points, 0)


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

    def test_get_request_redirects(self):
        response = self.client.get(f'/billing/adjust/{self.member.pk}/')
        self.assertRedirects(response, '/')
