import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'melova_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

try:
    u = User.objects.get(email='testuser@example.com')
    u.set_password('password123')
    u.save()
    print(f"✅ Password set successfully for {u.email}")
except User.DoesNotExist:
    print("❌ User not found, creating new user...")
    u = User.objects.create_user(
        email='testuser@example.com',
        name='Test User',
        password='password123'
    )
    print(f"✅ Created user: {u.email}")
