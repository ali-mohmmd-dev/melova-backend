import os
import django
from django.conf import settings
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'melova_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from shop.models import Product, Variant, Order, OrderItem, Payment

User = get_user_model()

def create_dummy_data():
    # 1. Get or Create User
    user, _ = User.objects.get_or_create(
        email="testuser@example.com",
        defaults={"name": "Test User", "is_active": True}
    )
    if not user.has_usable_password():
        user.set_password("password123")
        user.save()

    # 2. Get or Create a Product and Variant
    product, _ = Product.objects.get_or_create(
        name="Dummy Honey Bottle",
        defaults={
            "intro": "A tasty dummy product for testing.",
            "description": "Longer description of the tasty bottle."
        }
    )

    variant, _ = Variant.objects.get_or_create(
        product=product,
        name="500g Glass Jar",
        defaults={
            "gram": 500,
            "price": Decimal("250.00")
        }
    )

    # 3. Create a Dummy Order
    order = Order.objects.create(
        user=user,
        total=Decimal("500.00"),
        full_name="Test Recipient",
        email="testuser@example.com",
        phone="1234567890",
        address="123 Dummy Lane",
        city="Test City",
        state="Test State",
        pincode="000000"
    )

    # 4. Create Order Items
    OrderItem.objects.create(
        order=order,
        variant=variant,
        quantity=2,
        price_at_purchase=variant.price
    )

    # 5. Create a Dummy Payment
    Payment.objects.create(
        order=order,
        razorpay_order_id="order_dummy_123456",
        amount=500,
        status="Success" # Mark it as paid
    )

    print(f"✅ Dummy Order #{order.id} created successfully for {user.email}")
    print(f"   Checkout the admin panel to see it!")

if __name__ == "__main__":
    create_dummy_data()
