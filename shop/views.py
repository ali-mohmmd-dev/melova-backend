import json
import os
import re
import razorpay
from django.conf import settings
from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Product, Order, Customer, Payment
from .serializers import ProductSerializer, OrderSerializer, CustomerSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().prefetch_related('variants', 'variants__images')
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def _parse_variants_from_request(self, data, files):
        """Parse variants[0][name] style flat keys into a list of dicts."""
        variants = {}
        pattern = re.compile(r'^variants\[(\d+)\]\[(\w+)\]$')

        for key, value in data.items():
            match = pattern.match(key)
            if match:
                idx, field = int(match.group(1)), match.group(2)
                variants.setdefault(idx, {})[field] = value

        for key in files.keys():
            match = pattern.match(key)
            if match:
                idx, field = int(match.group(1)), match.group(2)
                variants.setdefault(idx, {})[field] = files.getlist(key)

        return [variants[i] for i in sorted(variants)]

    def create(self, request, *args, **kwargs):
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

        # Remove variant keys from flat data
        top_level = {k: v for k, v in data.items() if not k.startswith('variants[')}
        top_level['variants'] = self._parse_variants_from_request(data, request.FILES)

        serializer = self.get_serializer(data=top_level)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        from rest_framework import status
        from rest_framework.response import Response
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

        top_level = {k: v for k, v in data.items() if not k.startswith('variants[')}
        top_level['variants'] = self._parse_variants_from_request(data, request.FILES)

        serializer = self.get_serializer(instance, data=top_level, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        from rest_framework.response import Response
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Note: CASCADE will handle related variants and images in DB.
        # If files need to be deleted from disk, we'd add it here.
        self.perform_destroy(instance)
        return Response({'message': 'Product deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer
    
    def get_queryset(self):
        # Only return orders belonging to the logged-in user
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'items__variant', 'items__variant__product')


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class PaymentVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))

        try:
            # Verify the payment signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            # Update the payment record
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'Success'
            payment.save()

            # Update the associated order status
            order = payment.order
            order.status = 'Paid'
            order.save()

            return Response({'status': 'Payment Successful'}, status=status.HTTP_200_OK)

        except razorpay.errors.SignatureVerificationError:
            return Response({'status': 'Signature Verification Failed'}, status=status.HTTP_400_BAD_REQUEST)
        except Payment.DoesNotExist:
            return Response({'status': 'Payment Record Not Found'}, status=status.HTTP_404_NOT_FOUND)
