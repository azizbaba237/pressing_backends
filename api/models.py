from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils import timezone
from decimal import Decimal
import random

import uuid


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

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('READY', 'Ready'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    # 🔥 Numéro de commande lisible
    order_id = models.CharField(
        max_length=25,
        unique=True,
        editable=False,
        blank=True
    )

    deposit_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    pickup_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders"
    )

    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "orders"
        ordering = ["-deposit_date"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order {self.order_id} - {self.customer}"

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    @property
    def is_paid(self):
        return self.amount_paid >= self.total_amount

    def clean(self):
        """Validation personnalisée"""
        if self.due_date and self.deposit_date:
            if self.due_date <= self.deposit_date:
                raise ValidationError({
                    'due_date': "La date d'échéance doit être après la date de dépôt."
                })

    def save(self, *args, **kwargs):
        """
        Génère automatiquement un numéro de commande :
        CMD-YYYYMMDD-XXXX
        """
        if not self.order_id:
            date_str = timezone.now().strftime("%Y%m%d")

            while True:
                random_part = random.randint(1000, 9999)
                order_id = f"CMD-{date_str}-{random_part}"

                if not Order.objects.filter(order_id=order_id).exists():
                    self.order_id = order_id
                    break

        super().save(*args, **kwargs)

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
    reference = models.CharField(max_length=100, blank=True, unique=True)

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

    def save(self, *args, **kwargs):
        # Get référence if empty
        if not self.reference:
            last_id = Payment.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
            self.reference = f"PAY-{last_id + 1}"
        super().save(*args, **kwargs)

    def __str__(self):
        # Format: "Payment AMOUNT FCFA - Order NUMBER"
        return f"Payment {self.amount} FCFA - Order {self.order.order_id}"