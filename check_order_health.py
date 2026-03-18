"""
Order API Health Check Script
Tests the full order flow: Login -> Create Order -> Verify Response
"""
import os
import django
import requests
import json

# Server settings
BASE_URL = "http://127.0.0.1:8000"

# Test user credentials (change these if needed)
EMAIL = "testuser@example.com"
PASSWORD = "password123"


def get_access_token():
    """Login and get JWT access token."""
    print("🔑 Logging in...")
    response = requests.post(f"{BASE_URL}/api/auth/login/", json={
        "email": EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        token = response.json().get("access")
        print(f"   ✅ Logged in as {EMAIL}")
        return token
    else:
        print(f"   ❌ Login failed: {response.status_code} - {response.text}")
        return None


def get_first_variant(token):
    """Get the ID of the first available variant."""
    print("📦 Fetching products...")
    response = requests.get(f"{BASE_URL}/api/shop/products/")
    if response.status_code == 200:
        products = response.json()
        if products and len(products) > 0:
            variants = products[0].get("variants", [])
            if variants:
                variant_id = variants[0]["id"]
                print(f"   ✅ Using Variant ID: {variant_id}")
                return variant_id
    print("   ❌ No products/variants found. Please add a product first.")
    return None


def create_order(token, variant_id):
    """Create a test order."""
    print("🛒 Creating order...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "full_name": "Test Health Check",
        "email": "test@health.com",
        "phone": "9999999999",
        "address": "123 Test Street",
        "city": "Test City",
        "state": "Test State",
        "pincode": "400001",
        "items": [
            {"variant": variant_id, "quantity": 1}
        ]
    }
    response = requests.post(f"{BASE_URL}/api/shop/orders/", json=payload, headers=headers)
    return response


def run_health_check():
    print("\n" + "=" * 50)
    print("    ORDER API HEALTH CHECK")
    print("=" * 50 + "\n")

    # 1. Login
    token = get_access_token()
    if not token:
        print("\n⚠️  Cannot proceed. Create a user first with: py create_dummy_order.py")
        return

    # 2. Get a variant to order
    variant_id = get_first_variant(token)
    if not variant_id:
        return

    # 3. Create order
    response = create_order(token, variant_id)
    print(f"\n📋 ORDER CREATION RESULT:")
    print(f"   Status Code: {response.status_code}")

    if response.status_code == 201:
        data = response.json()
        print(f"\n✅ SUCCESS! Order created.")
        print(f"   Order ID:          #{data.get('id')}")
        print(f"   Total:             ₹{data.get('total')}")
        print(f"   Razorpay Order ID: {data.get('razorpay_order_id')}")
        print(f"   Items:             {len(data.get('items', []))} item(s)")
        print("\n   Check Django Admin: http://127.0.0.1:8000/admin/shop/order/")
    else:
        print(f"\n❌ FAILED! Response:")
        try:
            print(f"   {json.dumps(response.json(), indent=3)}")
        except:
            print(f"   {response.text}")

    print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    run_health_check()
