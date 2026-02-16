from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from django.contrib.auth import get_user_model
from .utils import generate_order_id
from django.utils import timezone


from .models import (
    Customer,
    CategoryServices,
    Service,
    Order,
    OrderItem,
    Payment
)


# ============================================================
# USER SERIALIZER
# ============================================================

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for Django User model.
    Used mainly for READ operations.
    """

    class Meta:
        User = get_user_model()
        fields = ['id', 'username', 'first_name', 'last_name']
        read_only_fields = ['id']


# ============================================================
# CUSTOMER SERIALIZER
# ============================================================

class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for Customer model.
    Adds a computed field for total orders.
    """

    total_orders = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = '__all__'
        # inscription_date is automatically set by the system
        read_only_fields = ['inscription_date']

    def get_total_orders(self, obj):
        """
        Return the total number of orders made by this customer.
        """
        return obj.orders.count()

    def validate_phone(self, value):
        """
        Validate phone number format.

        Accepted:
        +237 690000000
        690000000
        """
        cleaned_value = value.replace('+', '').replace(' ', '')
        if not cleaned_value.isdigit():
            raise serializers.ValidationError(
                "Phone number must contain only digits and an optional '+' sign."
            )
        return value


# ============================================================
# CATEGORY SERVICES SERIALIZER
# ============================================================

class CategoryServicesSerializer(serializers.ModelSerializer):
    """
    Serializer for service categories.
    Adds the number of active services per category.
    """

    service_count = serializers.SerializerMethodField()

    class Meta:
        model = CategoryServices
        fields = '__all__'

    def get_service_count(self, obj):
        """
        Return the number of active services in this category.
        """
        return obj.services.filter(actif=True).count()


# ============================================================
# SERVICE SERIALIZER
# ============================================================

class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for Service model.
    Includes category name for display purposes.
    """

    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    class Meta:
        model = Service
        fields = '__all__'

    def validate_price(self, value):
        """
        Ensure service price is strictly positive.
        """
        if value <= 0:
            raise serializers.ValidationError(
                "Service price must be greater than zero."
            )
        return value


# ============================================================
# ORDER ITEM SERIALIZERS
# ============================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """
    READ-ONLY serializer for OrderItem.
    Used when displaying order details.
    """

    service_name = serializers.CharField(
        source='service.name',
        read_only=True
    )

    service_detail = ServiceSerializer(
        source='service',
        read_only=True
    )

    class Meta:
        model = OrderItem
        fields = '__all__'
        # Prices are calculated by the backend
        read_only_fields = ['unit_price', 'total_price']


class OrderItemCreateSerializer(serializers.Serializer):
    """
    WRITE serializer for creating order items.
    Used only during order creation.
    """

    service_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    description = serializers.CharField(
        required=False,
        allow_blank=True
    )


# ============================================================
# PAYMENT SERIALIZER
# ============================================================

class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Payment model.
    Displays user full name instead of raw user ID.
    """

    user_name = serializers.SerializerMethodField(read_only=True)
    order_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'amount',
            'payment_method',
            'reference',
            'notes',
            'payment_date',
            'order_id',
            'user_name',
        ]
        read_only_fields = ['id', 'payment_date', 'order_id', 'user_name']

    def get_user_name(self, obj):
        if obj.user:
            full_name = obj.user.get_full_name().strip()
            if full_name:
                return full_name
            return obj.user.username
        return None

    def get_order_id(self, obj):
        if obj.order:
            return obj.order.order_id
        return None


# ============================================================
# ORDER SERIALIZERS
# ============================================================

class OrderSerializer(serializers.ModelSerializer):
    """
    READ serializer for Order model.
    Includes nested relationships for detailed display.
    """

    customer_details = CustomerSerializer(
        source='customer',
        read_only=True
    )

    items = OrderItemSerializer(
        many=True,
        read_only=True
    )

    payments = PaymentSerializer(
        many=True,
        read_only=True
    )

    user_name = serializers.SerializerMethodField()

    due_amount = serializers.SerializerMethodField()
    def get_due_amount(self, obj):
        return obj.total_amount - obj.amount_paid

    amount_paid = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Order
        fields = '__all__'
        # These fields are generated or calculated by the backend
        read_only_fields = [
            'order_id',
            'deposit_date',
            'total_amount',
            'amount_paid'
        ]

    def get_user_name(self, obj):
        """
        Return full name of the user who created the order.
        """
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return None

    def validate(self, data):
        if data.get('due_date') and data['due_date'] <= timezone.now():
            raise serializers.ValidationError({
                'due_date': 'La date d\'échéance doit être dans le futur.'
            })
        return data


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    WRITE serializer for creating orders with nested items.
    """

    items = OrderItemCreateSerializer(many=True)

    class Meta:
        model = Order
        fields = ['customer', 'due_date', 'notes', 'items']

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user

        order = Order.objects.create(
            **validated_data,
            order_id=generate_order_id(),
            user=user
        )

        total_amount = Decimal('0.00')

        for item in items_data:
            try:
                service = Service.objects.get(id=item['service_id'])
            except Service.DoesNotExist:
                raise serializers.ValidationError(
                    f"Service with id {item['service_id']} does not exist."
                )

            quantity = item['quantity']
            unit_price = service.price
            total_price = unit_price * quantity

            OrderItem.objects.create(
                order=order,
                service=service,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                description=item.get('description', '')
            )

            total_amount += total_price

        order.total_amount = total_amount
        order.save(update_fields=['total_amount'])

        return order