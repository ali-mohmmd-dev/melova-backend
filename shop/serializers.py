from rest_framework import serializers
from .models import Product, Variant, VariantImage, Order, OrderItem, Cart, CartItem


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
        # Return empty list if the variant instance does not have a primary key (unsaved or deleted)
        # to avoid ValueError: 'Variant' instance needs to have a primary key value...
        if not getattr(value.instance, 'pk', None):
            return []
            
        context = getattr(self, 'context', None) or getattr(self.parent, 'context', {})
        return VariantImageSerializer(value.all(), many=True, context=context).data

    def to_internal_value(self, data):
        if isinstance(data, list):
            return data
        elif data:
            return [data]  # handle single file
        return []


class VariantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_blank=True)
    weight = serializers.IntegerField(source='gram', min_value=0)
    images = VariantImagesField(required=False, default=list)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Variant
        fields = ['id', 'name', 'weight', 'images', 'price', 'image']

    def get_image(self, obj):
        return _media_url(self, obj.image)

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
    image = serializers.ImageField(required=False, allow_null=True)
    price = serializers.SerializerMethodField()
    variants = VariantSerializer(many=True)

    class Meta: 
        model = Product
        fields = ['id', 'title', 'introduction', 'details', 'image', 'price', 'variants']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Custom image logic for return
        image = instance.image
        if not image:
            first_variant = instance.variants.first()
            if first_variant:
                image = first_variant.image
        ret['image'] = _media_url(self, image)
        return ret

    def get_price(self, obj):
        """Return the lowest variant price as the product's display price."""
        first_variant = obj.variants.order_by('price').first()
        return float(first_variant.price) if first_variant else None

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
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
            
        # Refresh to ensure to_representation sees all newly created variants/images
        product.refresh_from_db()
        return product

    def update(self, instance, validated_data):
        variants_data = validated_data.pop('variants', None)
        # title, introduction, details are already mapped to name, intro, description via 'source'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if variants_data is not None:
            existing_variants = {v.id: v for v in instance.variants.all()}
            updated_variant_ids = []

            for v_data in variants_data:
                # Images are already in v_data from VariantImagesField.to_internal_value
                images_data = v_data.pop('images', [])
                
                # Check for existing variant
                variant_id = v_data.get('id')
                variant_instance = None
                if variant_id and int(variant_id) in existing_variants:
                    variant_instance = existing_variants[int(variant_id)]
                
                if variant_instance:
                    # Update existing
                    v_serializer = VariantSerializer(variant_instance, data=v_data, partial=True, context=self.context)
                    if v_serializer.is_valid(raise_exception=True):
                        variant = v_serializer.save()
                        updated_variant_ids.append(variant.id)
                else:
                    # Create new
                    v_data.pop('id', None) # Remove ID if it's a new or invalid ID
                    v_serializer = VariantSerializer(data=v_data, context=self.context)
                    if v_serializer.is_valid(raise_exception=True):
                        # Ensure we link to the product
                        variant = v_serializer.save(product=instance)
                        updated_variant_ids.append(variant.id)
                
                # Re-handle images for either created or updated variant
                for f in images_data:
                    if hasattr(f, 'read'):
                        vi = VariantImage.objects.create(variant=variant, image=f)
                        if not variant.image:
                            variant.image = vi.image
                            variant.save(update_fields=['image'])
            
            for v_id, v_obj in existing_variants.items():
                if v_id not in updated_variant_ids:
                    v_obj.delete()

            first_variant = instance.variants.first()
            if first_variant and first_variant.image and not instance.image:
                instance.image = first_variant.image
                instance.save(update_fields=['image'])
                
            # Clear relationship cache to ensure to_representation sees current state
            instance.refresh_from_db()
        return instance

class OrderItemSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product = serializers.IntegerField(source='variant.product.id', read_only=True)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, source='price_at_purchase', read_only=True
    )
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'variant',
            'product',
            'variant_name',
            'product_name',
            'quantity',
            'price',
            'price_at_purchase',
            'product_image',
        ]
        read_only_fields = ['price_at_purchase', 'price', 'product']

    def get_product_image(self, obj):
        # Provide an absolute media URL for the product image.
        if not obj.variant or not obj.variant.product or not obj.variant.product.image:
            return None
        return _media_url(self, obj.variant.product.image)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    razorpay_order_id = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user_email', 'total', 'created_at', 'items',
            'full_name', 'email', 'phone', 'address', 'city', 'state', 'pincode',
            'status', 'razorpay_order_id'
        ]
        read_only_fields = ['total', 'created_at']

    def get_razorpay_order_id(self, obj):
        # Return the razorpay_order_id from the associated payment
        payment = obj.payments.first()
        return payment.razorpay_order_id if payment else None


class CartItemSerializer(serializers.ModelSerializer):
    variant_details = VariantSerializer(source='variant', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'variant', 'variant_details', 'quantity', 'subtotal']

    def get_subtotal(self, obj):
        return obj.variant.price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return sum(item.variant.price * item.quantity for item in obj.items.all())
from rest_framework import serializers
from .models import Product, Variant, VariantImage, Order, OrderItem, Cart, CartItem


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
        # Return empty list if the variant instance does not have a primary key (unsaved or deleted)
        # to avoid ValueError: 'Variant' instance needs to have a primary key value...
        if not getattr(value.instance, 'pk', None):
            return []
            
        context = getattr(self, 'context', None) or getattr(self.parent, 'context', {})
        return VariantImageSerializer(value.all(), many=True, context=context).data

    def to_internal_value(self, data):
        if isinstance(data, list):
            return data
        elif data:
            return [data]  # handle single file
        return []


class VariantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_blank=True)
    weight = serializers.IntegerField(source='gram', min_value=0)
    images = VariantImagesField(required=False, default=list)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Variant
        fields = ['id', 'name', 'weight', 'images', 'price', 'image']

    def get_image(self, obj):
        return _media_url(self, obj.image)

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
    image = serializers.ImageField(required=False, allow_null=True)
    price = serializers.SerializerMethodField()
    variants = VariantSerializer(many=True)

    class Meta: 
        model = Product
        fields = ['id', 'title', 'introduction', 'details', 'image', 'price', 'variants']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Custom image logic for return
        image = instance.image
        if not image:
            first_variant = instance.variants.first()
            if first_variant:
                image = first_variant.image
        ret['image'] = _media_url(self, image)
        return ret

    def get_price(self, obj):
        """Return the lowest variant price as the product's display price."""
        first_variant = obj.variants.order_by('price').first()
        return float(first_variant.price) if first_variant else None

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
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
            
        # Refresh to ensure to_representation sees all newly created variants/images
        product.refresh_from_db()
        return product

    def update(self, instance, validated_data):
        variants_data = validated_data.pop('variants', None)
        # title, introduction, details are already mapped to name, intro, description via 'source'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if variants_data is not None:
            existing_variants = {v.id: v for v in instance.variants.all()}
            updated_variant_ids = []

            for v_data in variants_data:
                # Images are already in v_data from VariantImagesField.to_internal_value
                images_data = v_data.pop('images', [])
                
                # Check for existing variant
                variant_id = v_data.get('id')
                variant_instance = None
                if variant_id and int(variant_id) in existing_variants:
                    variant_instance = existing_variants[int(variant_id)]
                
                if variant_instance:
                    # Update existing
                    v_serializer = VariantSerializer(variant_instance, data=v_data, partial=True, context=self.context)
                    if v_serializer.is_valid(raise_exception=True):
                        variant = v_serializer.save()
                        updated_variant_ids.append(variant.id)
                else:
                    # Create new
                    v_data.pop('id', None) # Remove ID if it's a new or invalid ID
                    v_serializer = VariantSerializer(data=v_data, context=self.context)
                    if v_serializer.is_valid(raise_exception=True):
                        # Ensure we link to the product
                        variant = v_serializer.save(product=instance)
                        updated_variant_ids.append(variant.id)
                
                # Re-handle images for either created or updated variant
                for f in images_data:
                    if hasattr(f, 'read'):
                        vi = VariantImage.objects.create(variant=variant, image=f)
                        if not variant.image:
                            variant.image = vi.image
                            variant.save(update_fields=['image'])
            
            for v_id, v_obj in existing_variants.items():
                if v_id not in updated_variant_ids:
                    v_obj.delete()

            first_variant = instance.variants.first()
            if first_variant and first_variant.image and not instance.image:
                instance.image = first_variant.image
                instance.save(update_fields=['image'])
                
            # Clear relationship cache to ensure to_representation sees current state
            instance.refresh_from_db()
        return instance

class OrderItemSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product = serializers.IntegerField(source='variant.product.id', read_only=True)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, source='price_at_purchase', read_only=True
    )
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'variant',
            'product',
            'variant_name',
            'product_name',
            'quantity',
            'price',
            'price_at_purchase',
            'product_image',
        ]
        read_only_fields = ['price_at_purchase', 'price', 'product']

    def get_product_image(self, obj):
        # Provide an absolute media URL for the product image.
        if not obj.variant or not obj.variant.product or not obj.variant.product.image:
            return None
        return _media_url(self, obj.variant.product.image)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    razorpay_order_id = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user_email', 'total', 'created_at', 'items',
            'full_name', 'email', 'phone', 'address', 'city', 'state', 'pincode',
            'status', 'razorpay_order_id'
        ]
        read_only_fields = ['total', 'created_at']

    def get_razorpay_order_id(self, obj):
        # Return the razorpay_order_id from the associated payment
        payment = obj.payments.first()
        return payment.razorpay_order_id if payment else None


class CartItemSerializer(serializers.ModelSerializer):
    variant_details = VariantSerializer(source='variant', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'variant', 'variant_details', 'quantity', 'subtotal']

    def get_subtotal(self, obj):
        return obj.variant.price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return sum(item.variant.price * item.quantity for item in obj.items.all())
