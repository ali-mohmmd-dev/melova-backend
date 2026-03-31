import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'melova.settings')
django.setup()

from shop.models import Product, Variant, VariantImage

print("--- Products ---")
for p in Product.objects.all():
    print(f"P{p.id}: {p.name} | Img: {p.image}")
    for v in p.variants.all():
        print(f"  V{v.id}: {v.name} | Img: {v.image} | Gallery: {v.images.count()}")
