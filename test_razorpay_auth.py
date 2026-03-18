import os
import django
import razorpay
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'melova_backend.settings')
django.setup()

def test_razorpay_auth():
    print(f"Testing Razorpay with Key ID: {settings.RAZOR_KEY_ID}")
    try:
        client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
        # Try a simple fetch to verify auth
        orders = client.order.all({'count': 1})
        print("✅ SUCCESS: Razorpay authentication works!")
    except Exception as e:
        print(f"❌ FAILURE: Razorpay authentication failed!")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_razorpay_auth()
