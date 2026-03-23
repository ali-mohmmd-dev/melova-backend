from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Product, Variant, VariantImage
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch

User = get_user_model()

class ProductCreateTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(email='admin@test.com', password='password')
        self.regular_user = User.objects.create_user(email='user@test.com', password='password')
        self.url = reverse('product-list')

    def test_create_product_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "title": "Test Product",
            "introduction": "Test Intro",
            "details": "Test Description",
            "variants": [
                {"name": "Variant 1", "weight": 100, "price": "50.00"},
                {"name": "Variant 2", "weight": 200, "price": "90.00"}
            ]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 2)
        # Check title mapping (serializer uses source='name')
        self.assertEqual(Product.objects.first().name, "Test Product")

    def test_create_product_non_admin(self):
        self.client.force_authenticate(user=self.regular_user)
        data = {"title": "Test Product", "variants": []}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_product_unauthenticated(self):
        data = {"title": "Test Product", "variants": []}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class VariantSerializerTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(email='admin_var@test.com', password='password')
        self.client.force_authenticate(user=self.admin_user)
        self.product = Product.objects.create(name="Base Product", intro="Intro", description="Desc")
        self.url = reverse('product-list')

    def test_weight_mapping_and_auto_name(self):
        """Test that 'weight' input maps to 'gram' and generates 'name' if missing."""
        data = {
            "title": "Mapping Product",
            "variants": [
                {"weight": 500, "price": "25.00"} # name is missing
            ]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        variant = Variant.objects.get(product__name="Mapping Product")
        self.assertEqual(variant.gram, 500)
        self.assertEqual(variant.name, "500g")

    def test_multi_image_upload(self):
        """Test uploading multiple images for a variant."""
        image1 = SimpleUploadedFile("test1.jpg", b"file_content_1", content_type="image/jpeg")
        image2 = SimpleUploadedFile("test2.jpg", b"file_content_2", content_type="image/jpeg")
        
        # We need to use multipart/form-data for files
        data = {
            "title": "Image Product",
            "variants[0][weight]": 100,
            "variants[0][price]": "10.00",
            "variants[0][images]": [image1, image2]
        }
        
        # ProductSerializer._inject_variant_files_from_request handles the file mapping
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        variant = Variant.objects.get(product__name="Image Product")
        self.assertEqual(variant.images.count(), 2)
        # Check if the variant itself has a main image set (from the first uploaded image)
        self.assertTrue(variant.image)


class CartAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='cart_user@test.com', password='password')
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(name="Cart Product", intro="Intro", description="Desc")
        self.variant = Variant.objects.create(product=self.product, name="500g", gram=500, price="100.00")
        self.url = reverse('cart-list')

    def test_get_cart_creates_on_demand(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        from .models import Cart
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    def test_add_to_cart(self):
        url = reverse('cart-add-item')
        data = {'variant_id': self.variant.id, 'quantity': 2}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total_price'], 200.0)
        self.assertEqual(len(response.data['items']), 1)

    def test_update_cart_quantity(self):
        # First add an item
        from .models import Cart, CartItem
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        
        url = reverse('cart-update-item')
        data = {'variant_id': self.variant.id, 'quantity': 5}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['quantity'], 5)

    @patch('razorpay.Client')
    def test_checkout_from_cart(self, mock_razorpay):
        # Setup mock
        mock_client = mock_razorpay.return_value
        mock_client.order.create.return_value = {'id': 'rzp_test_123'}

        # Setup cart
        from .models import Cart, CartItem
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=2)
        
        url = reverse('cart-checkout')
        data = {
            'full_name': 'Test User',
            'email': 'test@test.com',
            'phone': '1234567890',
            'address': 'Test Address',
            'city': 'Test City',
            'state': 'Test State',
            'pincode': '123456'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Check order was created
        from .models import Order
        self.assertTrue(Order.objects.filter(user=self.user).exists())
        # Check cart is cleared
        self.assertEqual(cart.items.count(), 0)
