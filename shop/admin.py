from django.contrib import admin
from .models import Product, Variant, Order, OrderItem, Payment

class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1
    fields = ('name', 'gram', 'price', 'image')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'get_variants_count')
    list_filter = ('name',)
    search_fields = ('name', 'intro', 'description')
    inlines = [VariantInline]
    
    def get_variants_count(self, obj):
        return obj.variants.count()
    get_variants_count.short_description = 'Variants'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('variant', 'quantity', 'price_at_purchase')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'full_name', 'email')
    readonly_fields = ('created_at', 'total')
    inlines = [OrderItemInline]
    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'total', 'created_at')
        }),
        ('Shipping Details', {
            'fields': ('full_name', 'email', 'phone', 'address', 'city', 'state', 'pincode')
        }),
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('razorpay_order_id', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('created_at',)