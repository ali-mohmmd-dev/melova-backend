from django.contrib import admin
from .models import Product, Variant, Order, Payment, Customer

class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1
    fields = ('name', 'gram', 'price', 'image')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'get_variants_count')
    list_filter = ('price',)
    search_fields = ('name', 'intro', 'description')
    inlines = [VariantInline]
    
    def get_variants_count(self, obj):
        return obj.variants.count()
    get_variants_count.short_description = 'Variants'

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone', 'city', 'created_at')
    list_filter = ('city', 'state', 'country', 'created_at')
    search_fields = ('name', 'email', 'phone', 'address')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'pincode')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_customer_name', 'total', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('customer__name', 'customer__email')
    readonly_fields = ('created_at',)
    
    def get_customer_name(self, obj):
        return obj.customer.name
    get_customer_name.short_description = 'Customer'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('razorpay_order_id', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('created_at',)