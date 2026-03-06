from rest_framework import serializers
from .models import Product, Variant, Order, Customer

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'address', 'city', 'state', 'country', 'pincode', 'created_at']


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ['id', 'name', 'gram', 'price', 'image']

class ProductSerializer(serializers.ModelSerializer):
    variants = VariantSerializer(many=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'intro', 'description', 'image', 'price', 'variants']

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        product = Product.objects.create(**validated_data)
        for variant_data in variants_data:
            Variant.objects.create(product=product, **variant_data)
        return product

class OrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    email = serializers.EmailField(source='customer.email', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer_name', 'email', 'total', 'created_at']
