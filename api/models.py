from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils.timezone import now
from decimal import Decimal


class Customer(models.Model):
    """Model representing a laundry customer"""

    # Customer's first name
    first_name = models.CharField(max_length=100, default='')

    # Customer's last name
    last_name = models.CharField(max_length=100, default='')

    # Customer's phone number (unique to avoid duplicate customers)
    phone = models.CharField(max_length=20, unique=True)

    # Customer's email address (optional for communication)
    email = models.EmailField(blank=True, null=True)

    # Customer's physical address
    adresse = models.TextField(blank=True)

    # Customer status (active/inactive)
    # NOTE: Avoid null=True for BooleanField, use default=True/False instead
    actif = models.BooleanField(null=True)

    # Automatic registration date
    inscription_date = models.DateTimeField(default=now)

    class Meta:
        # Database table configuration
        db_table = "customer"
        # Default ordering: most recent first
        ordering = ["-inscription_date"]
        # Admin panel display names
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        # Human-readable representation for admin and debugging
        return f"{self.first_name} {self.last_name}"


class CategoryServices(models.Model):
    """Service categories (Dry Cleaning, Ironing, etc.)"""

    # Category name (e.g., "Dry Cleaning")
    name = models.CharField(max_length=100)

    # Detailed category description
    description = models.TextField(blank=True)

    # Category status (active/inactive)
    actif = models.BooleanField(null=True)

    class Meta:
        # Database table name
        db_table = "categories_services"
        # Alphabetical ordering by name
        ordering = ['name']
        # Admin panel display names
        verbose_name = "Categories Services"
        verbose_name_plural = "Categories Services"

    def __str__(self):
        # Simple name display
        return self.name


class Service(models.Model):
    """Model representing a specific service offered by the laundry"""

    # Relationship to parent category
    # CASCADE: If category is deleted, all its services are deleted
    category = models.ForeignKey(CategoryServices, on_delete=models.CASCADE, related_name="services")

    # Service name (e.g., "Men's Shirt")
    name = models.CharField(max_length=100)

    # Detailed service description
    description = models.TextField(blank=True)

    # Service price with minimum value validation
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    # Estimated processing time in hours
    # Default 24 hours - adjust based on actual requirements
    estimate_time = models.IntegerField(help_text='Duration in Hours', default=24)

    # Service status (active/inactive)
    actif = models.BooleanField(null=True)

    class Meta:
        # Database table name
        db_table = "services"
        # Order by category then name
        ordering = ["category", 'name']
        # Prevent duplicate service names within same category
        unique_together = ["category", "name"]
        # Admin panel display names
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        # Format: "CategoryName ServiceName"
        return f"{self.category.name} {self.name}"


class Order(models.Model):
    """Model representing a laundry order"""

    # Available order status choices
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('READY', 'Ready'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Customer who placed the order
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")

    # Unique order identifier
    # IMPORTANT: Should be auto-generated to avoid duplicates
    order_id = models.CharField(max_length=30, unique=True)

    # Automatic deposit date on creation
    deposit_date = models.DateTimeField(auto_now_add=True)

    # Due date for order completion
    # TODO: Add validation to ensure due_date > deposit_date
    due_date = models.DateTimeField()

    # Actual pickup date (filled when customer collects)
    pickup_date = models.DateTimeField(null=True, blank=True)

    # Current order status
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')

    # Total order amount (sum of all OrderItems)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Amount already paid (sum of related Payments)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # User who created the order
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="orders")

    # Some note for the order
    notes = models.TextField(blank=True, default="")

    class Meta:
        # Database table configuration
        db_table = "orders"
        # Order by most recent deposit date first
        ordering = ["-deposit_date"]
        # Admin panel display names
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        # Format: "Order NUMBER - CustomerName"
        # FIX: Remove leading space before "Order"
        return f" Order {self.order_id} - {self.customer}"

    @property
    def balance(self):
        """Calculate remaining balance to pay"""
        # Remaining amount = total - paid
        return self.total_amount - self.amount_paid

    @property
    def is_paid(self):
        """Check if order is fully paid"""
        # True if paid amount >= total amount
        return self.amount_paid >= self.total_amount


class OrderItem(models.Model):
    """Line item in an order (link between Order and Service)"""

    # Parent order
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")

    # Service being ordered
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # Quantity ordered (minimum 1)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    # Unit price at time of order
    # IMPORTANT: Should be copied from Service.price to freeze the price
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Total price = unit_price * quantity
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Specific notes for this item
    description = models.TextField(blank=True)

    class Meta:
        # Database table name
        db_table = "order_item"
        # Admin panel display names
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        # Format: "ServiceName x Quantity"
        return f"{self.service.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        """Override save method to automatically calculate total_price"""
        # Calculate total before saving
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Model representing a payment for an order"""

    # Available payment methods
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Credit/Debit Card'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('CHECK', 'Check'),
    ]

    # Associated order
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")

    # Payment amount (minimum 1 monetary unit)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])

    # Payment method used
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)

    # Automatic payment date and time
    payment_date = models.DateTimeField(auto_now_add=True)

    # Transaction reference/number
    reference = models.CharField(max_length=100, blank=True)

    # Additional payment notes
    notes = models.TextField(blank=True)

    # User who recorded the payment
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        # Database table configuration
        db_table = "payments"
        # Order by most recent payment first
        ordering = ["-payment_date"]
        # Admin panel display names
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        # Format: "Payment AMOUNT FCFA - Order NUMBER"
        return f"Payment {self.amount} FCFA - Order {self.order.order_id}"