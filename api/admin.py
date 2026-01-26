from django.contrib import admin
from .models import Customer, CategoryServices, Service, Order, OrderItem, Payment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin configuration for Customer model"""

    # Fields to display in the list view
    list_display = ['last_name', 'first_name', 'phone', 'email', 'actif', 'inscription_date']

    # Filter options for the right sidebar
    list_filter = ['actif', 'inscription_date']

    # Searchable fields in the admin search box
    search_fields = ['first_name', 'last_name', 'phone', 'email']

    # Date-based navigation at the top of the list
    date_hierarchy = 'inscription_date'

    # Default sorting order
    ordering = ['last_name', 'first_name']


@admin.register(CategoryServices)
class CategoryServiceAdmin(admin.ModelAdmin):
    """Admin configuration for CategoryServices model"""

    # Fields to display in the list view
    list_display = ['name', 'actif']

    # Filter by active status
    list_filter = ['actif']

    # Search by category name
    search_fields = ['name']

    # Alphabetical ordering
    ordering = ['name']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """Admin configuration for Service model"""

    # Fields to display in the list view
    list_display = ['name', 'category', 'price', 'estimate_time', 'actif']

    # Filter by category and active status
    list_filter = ['category', 'actif']

    # Search by service name or category name
    search_fields = ['name', 'category__name']

    # Fields that can be edited directly in the list view
    # WARNING: Be careful with list_editable when using search_fields
    list_editable = ['price', 'actif']


class OrderItemInline(admin.TabularInline):
    """Inline admin for OrderItem within Order admin"""

    # Model to inline
    model = OrderItem

    # Number of empty forms to display
    extra = 1

    # Fields to display in the inline form
    fields = ['service', 'quantity', 'unit_price']

    # Enable autocomplete for service field (useful for many services)
    autocomplete_fields = ['service']


class PaymentInline(admin.TabularInline):
    """Inline admin for Payment within Order admin"""

    # Model to inline
    model = Payment

    # No empty forms by default
    extra = 0

    # Fields that cannot be edited
    readonly_fields = ['payment_date', 'user']

    # Prevent deletion of payments from inline
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for Order model"""

    # Fields to display in the list view
    list_display = ['order_id', 'customer', 'deposit_date', 'due_date', 'status', 'total_amount', 'amount_paid']

    # Filter options
    list_filter = ['status', 'deposit_date']

    # Searchable fields
    search_fields = ['order_id', 'customer__first_name', 'customer__last_name']

    # Date navigation
    date_hierarchy = 'deposit_date'

    # Inline forms for related models
    inlines = [OrderItemInline, PaymentInline]

    # Fields that cannot be edited in the detail view
    readonly_fields = ['order_id', 'total_amount', 'amount_paid']

    # Fields editable directly in list view
    # CAUTION: list_editable may conflict with search/ordering in some cases
    list_editable = ['status']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for Payment model"""

    # Fields to display in the list view
    list_display = ['order', 'amount', 'payment_method', 'payment_date', 'user']

    # Filter options
    list_filter = ['payment_method', 'payment_date']

    # Searchable fields
    search_fields = ['order__order_id', 'reference']

    # Date navigation
    date_hierarchy = 'payment_date'

    # Fields that cannot be edited
    readonly_fields = ['payment_date', 'user']

    # Enable autocomplete for order field
    autocomplete_fields = ['order']
