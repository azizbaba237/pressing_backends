from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Customer(models.Model):
    """Customer model"""
    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)
    phone      = models.CharField(max_length=20, unique=True)
    email      = models.EmailField(blank=True, null=True)
    adresse    = models.TextField(blank=True)
    actif      = models.BooleanField(null=True)
    inscription_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = "customer"
        ordering            = ["-inscription_date"]
        verbose_name        = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class CategoryServices(models.Model):
    """Services Categories (Nettoyage à sec, Repassage, etc.)"""
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    actif       = models.BooleanField(null=True)

    class Meta:
        db_table            = "categories_services"
        ordering            = ['name']
        verbose_name        = "Categories Services"
        verbose_name_plural = "Categories Services"

    def __str__(self):
        return self.name

class Service(models.Model):
    objects = models.Manager()
    """Services models"""
    category      = models.ForeignKey(CategoryServices, on_delete=models.CASCADE, related_name="services")
    name          = models.CharField(max_length=100)
    description   = models.TextField(blank=True)
    price         = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    estimate_time = models.IntegerField(help_text='Durée en Heure', default=24)
    actif         = models.BooleanField(null=True)

    class Meta:
        db_table            = "services"
        ordering            = ["category", 'name']
        unique_together     = ["category", "name"]
        verbose_name        = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        return f"{self.category.name} {self.name}"

class Order(models.Model):
    objects = models.Manager()
    """Customer Orders"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('READY', 'Ready'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    customer     = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    order_id     = models.CharField(max_length=10, unique=True)
    deposit_date = models.DateTimeField(auto_now_add=True)
    due_date     = models.DateTimeField()
    pickup_date  = models.DateTimeField(null=True, blank=True)
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    total_amount: Decimal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid : Decimal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="orders")


    class Meta:
        db_table            = "orders"
        ordering            = ["-deposit_date"]
        verbose_name        = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f" Order {self.order_id} - {self.customer}"

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    @property
    def is_paid(self):
        return self.amount_paid >= self.total_amount

class OrderItem(models.Model):
    objects = models.Manager()
    """Order Items model"""
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="Items")
    service    = models.ForeignKey(Service, on_delete=models.CASCADE)
    quantity   : int     = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price : Decimal = models.DecimalField(max_digits=10, decimal_places=2)
    total_price: Decimal = models.DecimalField(max_digits=10, decimal_places=2)
    description= models.TextField(blank=True, help_text="Item's description (color, state, etc.)")

    class Meta:
        db_table            = "order_item"
        verbose_name        = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.service.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

class Payment(models.Model):
    """PAYMENT METHOD"""
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Credit/Debit Card'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('CHECK', 'Check'),
    ]
    order         = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    amount        = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])
    payment_mod   = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_date = models.DateTimeField(auto_date_add=True)
    reference     = models.CharField(max_length=100, blank=True)
    notes         = models.TextField(blank=True)
    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table            = "payments"
        ordering            = ["-payment_date"]
        verbose_name        = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment {self.amount} FCFA - {self.order.name}"