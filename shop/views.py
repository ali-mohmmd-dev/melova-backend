from rest_framework import viewsets
from .models import Product, Order, Customer
from .serializers import ProductSerializer, OrderSerializer, CustomerSerializer
import json
import os
import razorpay
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView




from rest_framework import permissions

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().prefetch_related('variants')
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
