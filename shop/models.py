from django.conf import settings
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    intro = models.TextField()
    description = models.TextField()
    image = models.FileField(upload_to="products/", null=True, blank=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    pincode = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name        

class Variant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    gram = models.IntegerField()  # weight in grams
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.FileField(upload_to="variants/", null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class VariantImage(models.Model):
    variant = models.ForeignKey(Variant, related_name='images', on_delete=models.CASCADE)
    image = models.FileField(upload_to="variant_images/")

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders', on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Shipping Info
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=255, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.email}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.variant.name if self.variant else 'Deleted Variant'}"




class Payment(models.Model):
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.IntegerField()
    status = models.CharField(max_length=50, default='Created')  # Created, Success, Failed
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(Order, related_name='payments', on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.razorpay_order_id} - {self.status}"