from rest_framework import serializers
from .models import Product, Variant, VariantImage, Order, Customer


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
        validated_data['name'] = validated_data.pop('name', '')
        validated_data['intro'] = validated_data.pop('intro', '')
        validated_data['description'] = validated_data.pop('description', '')
        first_price = next((v.get('price') for v in variants_data if v.get('price') is not None), None)
        validated_data['price'] = first_price or 0
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
        if 'name' in validated_data:
            instance.name = validated_data.pop('name')
        if 'intro' in validated_data:
            instance.intro = validated_data.pop('intro')
        if 'description' in validated_data:
            instance.description = validated_data.pop('description')
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

class OrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    email = serializers.EmailField(source='customer.email', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer_name', 'email', 'total', 'created_at']
