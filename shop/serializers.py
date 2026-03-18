import razorpay
from django.conf import settings
from rest_framework import serializers
from .models import Product, Variant, VariantImage, Order, OrderItem, Customer


def _media_url(serializer, file_field):
    """Build absolute URL for a FileField using request from context."""
    if not file_field:
        return None
    url = file_field.url
    request = serializer.context.get("request") if serializer else None
    if request:
        if url and not url.startswith("http") and not url.startswith("/"):
            url = "/" + url
        return request.build_absolute_uri(url)
    return url


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'address', 'city', 'state', 'country', 'pincode', 'created_at']


class VariantImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = VariantImage
        fields = ['id', 'image']

    def get_image(self, obj):
        return _media_url(self, obj.image)


class VariantImagesField(serializers.Field):
    """Read: list of {id, image URL}. Write: list of uploaded files (saved to media, path in DB)."""

    def to_representation(self, value):
        if value is None:
            return []
        context = getattr(self, 'context', None) or getattr(self.parent, 'context', {})
        return VariantImageSerializer(value.all(), many=True, context=context).data

    def to_internal_value(self, data):
        if isinstance(data, list):  
            return data  # list of file objects or empty
        return []


class VariantSerializer(serializers.ModelSerializer):
    weight = serializers.IntegerField(source='gram', min_value=0)
    images = VariantImagesField(required=False, default=list)

    class Meta:
        model = Variant
        fields = ['id', 'name', 'weight', 'images', 'price']

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        validated_data.setdefault('gram', 0)
        if not validated_data.get('name'):
            validated_data['name'] = f"{validated_data['gram']}g"
        variant = Variant.objects.create(**validated_data)
        for f in images_data:
            if hasattr(f, 'read'):  # uploaded file
                vi = VariantImage.objects.create(variant=variant, image=f)
                if not variant.image:
                    variant.image = vi.image
                    variant.save(update_fields=['image'])
        return variant

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        if 'gram' in validated_data:
            validated_data['gram'] = validated_data.pop('gram', instance.gram)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if images_data is not None:
            instance.images.all().delete()
            for f in images_data:
                if hasattr(f, 'read'):
                    vi = VariantImage.objects.create(variant=instance, image=f)
                    if not instance.image:
                        instance.image = vi.image
                        instance.save(update_fields=['image'])
        return instance


class ProductSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='name')
    introduction = serializers.CharField(source='intro', required=False, allow_blank=True)
    details = serializers.CharField(source='description', required=False, allow_blank=True)
    image = serializers.SerializerMethodField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    variants = VariantSerializer(many=True)

    class Meta: 
        model = Product
        fields = ['id', 'title', 'introduction', 'details', 'image', 'price', 'variants']

    def get_image(self, obj):
        return _media_url(self, obj.image)

    def _inject_variant_files_from_request(self, variants_data):
        request = self.context.get('request')
        if not request or not getattr(request, 'FILES', None):
            return
        for i in range(len(variants_data)):
            for key in (f'variants[{i}][images]', f'variants[{i}][images][]'):
                files = request.FILES.getlist(key)
                if files:
                    variants_data[i]['images'] = files
                    break

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        self._inject_variant_files_from_request(variants_data)
        # The Product model doesn't have a price field; prices are on variants.
        # title, introduction, details are already mapped to name, intro, description via 'source'
        product = Product.objects.create(**validated_data)
        for v in variants_data:
            images_data = v.pop('images', [])
            gram = v.pop('gram', v.pop('weight', 0))
            v['gram'] = gram
            v.setdefault('name', f"{gram}g")
            variant = Variant.objects.create(product=product, **v)
            for f in images_data:
                if hasattr(f, 'read'):
                    vi = VariantImage.objects.create(variant=variant, image=f)
                    if not variant.image:
                        variant.image = vi.image
                        variant.save(update_fields=['image'])
        first_variant = product.variants.first()
        if first_variant and first_variant.image and not product.image:
            product.image = first_variant.image
            product.save(update_fields=['image'])
        return product

    def update(self, instance, validated_data):
        variants_data = validated_data.pop('variants', None)
        # title, introduction, details are already mapped to name, intro, description via 'source'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if variants_data is not None:
            self._inject_variant_files_from_request(variants_data)
            instance.variants.all().delete()
            for v in variants_data:
                images_data = v.pop('images', [])
                gram = v.pop('gram', v.pop('weight', 0))
                v['gram'] = gram
                v.setdefault('name', f"{gram}g")
                variant = Variant.objects.create(product=instance, **v)
                for f in images_data:
                    if hasattr(f, 'read'):
                        vi = VariantImage.objects.create(variant=variant, image=f)
                        if not variant.image:
                            variant.image = vi.image
                            variant.save(update_fields=['image'])
            first_variant = instance.variants.first()
            if first_variant and first_variant.image and not instance.image:
                instance.image = first_variant.image
                instance.save(update_fields=['image'])
        return instance

class OrderItemSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'variant', 'variant_name', 'product_name', 'quantity', 'price_at_purchase']
        read_only_fields = ['price_at_purchase']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    razorpay_order_id = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user_email', 'total', 'created_at', 'items',
            'full_name', 'email', 'phone', 'address', 'city', 'state', 'pincode',
            'status', 'razorpay_order_id'
        ]
        read_only_fields = ['total', 'created_at', 'status']

    def get_razorpay_order_id(self, obj):
        # Return the razorpay_order_id from the associated payment
        payment = obj.payments.first()
        return payment.razorpay_order_id if payment else None

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required to place an order.")

        # Calculate total and prepare items
        total = 0
        order_items_to_create = []
        for item_data in items_data:
            variant = item_data['variant']
            quantity = item_data['quantity']
            price = variant.price
            total += price * quantity
            order_items_to_create.append({
                'variant': variant,
                'quantity': quantity,
                'price_at_purchase': price
            })
            
        order = Order.objects.create(user=user, total=total, **validated_data)
        
        for item_info in order_items_to_create:
            OrderItem.objects.create(order=order, **item_info)

        # Razorpay Integration
        client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": int(total * 100),  # Amount in paise
            "currency": "INR",
            "receipt": f"order_{order.id}",
            "payment_capture": 1
        })

        # Create Payment record
        from .models import Payment
        Payment.objects.create(
            order=order,
            razorpay_order_id=razorpay_order['id'],
            amount=int(total),
            status='Created'
        )
            
        return order
