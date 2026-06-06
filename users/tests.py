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
