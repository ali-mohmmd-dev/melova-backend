from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from .models import Product, Variant

class ProductCreateTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admin', email='admin@test.com', password='password')
        self.regular_user = User.objects.create_user(username='user', email='user@test.com', password='password')
        self.url = reverse('product-list')

    def test_create_product_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "name": "Test Product",
            "intro": "Test Intro",
            "description": "Test Description",
            "price": "100.00",
            "variants": [
                {"name": "Variant 1", "gram": 100, "price": "50.00"},
                {"name": "Variant 2", "gram": 200, "price": "90.00"}
            ]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 2)
        self.assertEqual(Product.objects.first().name, "Test Product")

    def test_create_product_non_admin(self):
        self.client.force_authenticate(user=self.regular_user)
        data = {"name": "Test Product", "price": "100.00", "variants": []}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_product_unauthenticated(self):
        data = {"name": "Test Product", "price": "100.00", "variants": []}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
