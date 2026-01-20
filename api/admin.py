from django.contrib import admin
from .models import *

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'phone', 'email', 'actif', 'inscription_date']
    list_filter = ['actif', 'inscription_date']
    search_fields = ['first_name', 'last_name', 'phone', 'email']
    date_hierarchy = 'inscription_date'

@admin.register(CategoryServices)
class CategoryServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'actif']
    list_filter = ['actif']
    search_fields = ['name']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'estimate_time', 'actif']
    list_filter = ['category', 'actif']
    search_fields = ['name', 'category__name']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'customer', 'deposit_date', 'promise_date', 'status', 'total_amount', 'amount_paid']
    list_filter = ['status', 'deposit_date']
    search_fields = ['numero_commande', 'customer__first_name', 'customer__last_name']
    date_hierarchy = 'deposit_date'
    inlines = [OrderItemInline, PaymentInline]
    readonly_fields = ['order_id', 'total_amount', 'amount_paid']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['Order', 'amount', 'payment_mod', 'payment_date', 'user']
    list_filter = ['payment_mod', 'payment_date']
    search_fields = ['order__order_id', 'reference']
    date_hierarchy = 'payment_date'