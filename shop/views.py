import json
import os
import re
import razorpay
from django.conf import settings
from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Product, Order, Payment, Cart, CartItem, Variant
from .serializers import ProductSerializer, OrderSerializer, CartSerializer, CartItemSerializer
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action

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

        # If variants is already in request.data (e.g. JSON request), use it
        if 'variants' in request.data and isinstance(request.data['variants'], list):
            top_level = request.data
        else:
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

        if 'variants' in request.data and isinstance(request.data['variants'], list):
            top_level = request.data
        else:
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

    def get_permissions(self):
        # Only staff/admin can create/update orders (including status changes).
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Order.objects.exclude(status='Pending').prefetch_related('items', 'items__variant', 'items__variant__product').order_by('-created_at')
        return Order.objects.filter(user=user).prefetch_related('items', 'items__variant', 'items__variant__product').order_by('-created_at')

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        user = request.user
        orders = Order.objects.filter(user=user, status='Paid').prefetch_related('items', 'items__variant', 'items__variant__product').order_by('-created_at')
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)




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
            payment = Payment.objects.select_related("order").get(razorpay_order_id=razorpay_order_id)
            order = payment.order

            # Ownership check: normal users can only verify their own orders.
            if not (request.user.is_staff or request.user.is_superuser) and order.user_id != request.user.id:
                return Response({"status": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

            # Idempotency: if it's already verified, keep response contract stable.
            if payment.status == "Success" and order.status == "Paid":
                return Response({'status': 'Payment Successful'}, status=status.HTTP_200_OK)

            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'Success'
            payment.save()

            # Update the associated order status
            order.status = 'Paid'
            order.save()

            return Response({'status': 'Payment Successful'}, status=status.HTTP_200_OK)

        except razorpay.errors.SignatureVerificationError:
            return Response({'status': 'Signature Verification Failed'}, status=status.HTTP_400_BAD_REQUEST)
        except Payment.DoesNotExist:
            return Response({'status': 'Payment Record Not Found'}, status=status.HTTP_404_NOT_FOUND)


class CartViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def get_cart(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def list(self, request):
        cart = self.get_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        variant_id = request.data.get('variant_id')
        quantity = int(request.data.get('quantity', 1))
        
        variant = get_object_or_404(Variant, id=variant_id)
        cart = self.get_cart()
        
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()
        
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        variant_id = request.data.get('variant_id')
        quantity = int(request.data.get('quantity'))
        
        cart = self.get_cart()
        cart_item = get_object_or_404(CartItem, cart=cart, variant_id=variant_id)
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
            
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        variant_id = request.data.get('variant_id')
        cart = self.get_cart()
        cart_item = get_object_or_404(CartItem, cart=cart, variant_id=variant_id)
        cart_item.delete()
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        cart = self.get_cart()
        cart.items.all().delete()
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        cart = self.get_cart()
        cart_items = cart.items.select_related('variant').all()
        
        if not cart_items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate address/contact fields via the serializer
        order_data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
        serializer = OrderSerializer(data=order_data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Build order and items directly (items is read_only on the serializer)
        total = 0
        order_items_to_create = []
        for ci in cart_items:
            price = ci.variant.price
            total += price * ci.quantity
            order_items_to_create.append({
                'variant': ci.variant,
                'quantity': ci.quantity,
                'price_at_purchase': price,
            })

        from .models import Order, OrderItem, Payment
        order = Order.objects.create(
            user=request.user,
            total=total,
            **serializer.validated_data,
        )
        for item_info in order_items_to_create:
            OrderItem.objects.create(order=order, **item_info)

        # Razorpay Integration
        client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": int(total * 100),
            "currency": "INR",
            "receipt": f"order_{order.id}",
            "payment_capture": 1,
        })
        Payment.objects.create(
            order=order,
            razorpay_order_id=razorpay_order['id'],
            amount=int(total),
            status='Created',
        )

        # Clear cart after successful order creation
        cart_items.delete()

        # Re-serialize the created order for the response
        response_serializer = OrderSerializer(order, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
