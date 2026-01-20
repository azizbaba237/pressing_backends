from rest_framework import serializers
#from django.contrib.auth.models import User
from .models import *
from django.utils import timezone
import random
import string


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model            = User
        fields           = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class CustomerSerializer(serializers.ModelSerializer):
    total_orders = serializers.SerializerMethodField()

    class Meta:
        model            = Customer
        fields           = '__all__'
        read_only_fields = ['inscription_date']

    @staticmethod
    def get_total_orders(obj) -> int:
        return obj.orders.count()

    @staticmethod
    def validate_phone(value):
        """Phone number validation"""
        if not value.replace('+', '').replace(' ', '').isdigit():
            raise serializers.ValidationError('Phone number must be entered in the format: +999999999')
        return value

class CategoryServicesSerializer(serializers.ModelSerializer):
    service_count = serializers.SerializerMethodField()

    class Meta:
        model  = CategoryServices
        fields = '__all__'

    @staticmethod
    def get_service_count(obj):
        return obj.services.filter(active=True).count()

class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model  = Service
        fields = '__all__'

    @staticmethod
    def validate_price(value):
        if value <= 0 :
            raise serializers.ValidationError('Price must be greater than 0')
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_detail = ServiceSerializer(source='service', read_only=True)

    class Meta:
        model            = OrderItem
        fields           = '__all__'
        read_only_fields = ['total_price']

    @staticmethod
    def quantity_validate(value):
        if value < 1 :
            raise serializers.ValidationError('Quantity must be greater than 1')
        return value

class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model            = Payment
        fields           = '__all__'
        read_only_fields = ['payment_date']

    @staticmethod
    def get_user_name(obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return None

class OrderSerializers(serializers.ModelSerializer):
    customer_details = CustomerSerializer(source='customer', read_only=True)
    items            = OrderItemSerializer(many=True, read_only=True)
    payments         = PaymentSerializer(many=True, read_only=True)
    user_name        = serializers.SerializerMethodField()
    due_amount       = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    amount_paid      = serializers.BooleanField(read_only=True)

    class Meta:
        model            = Order
        fields           = '__all__'
        read_only_fields = ['order_id', 'deposit_date', 'total_amount', 'amount_paid']

    @staticmethod
    def get_user_name(obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return None

    def create(self, validated_data):
        """Generate id order item """
        validated_data['order_id'] = self.generate_order_id()
        validated_data['user']     = self.context['request'].user
        return super().create(validated_data)

    @staticmethod
    def generate_order_id():
        date       = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f"CMD-{date}-{random_str}"

class OrderCreateSerializers(serializers.ModelSerializer):
    items = serializers.ListSerializer(child=serializers.DictField(), write_only=True)

    class Meta:
        model  = Order
        fields = ['customer', 'due_date', 'notes', 'items']

    def create(self, validated_data):
        items_data  = validated_data.pop('items')

        # Create order
        order = Order.objects.create(
            **validated_data,
            order_id=self.generate_order_id(),
            user=self.context['request'].user

        )

        # create items
        total_amount = 0
        for item_data in items_data:
            service    = Service.objects.get(id=item_data['service_id'])
            quantity   = item_data['quantity']
            unit_price = service.price

            OrderItem.objects.create(
                order=order,
                service=service,
                quantity=quantity,
                unit_price=unit_price,
                total_price=unit_price * quantity,
                description=item_data.get('description', '')
            )
            total_amount += unit_price * quantity
        # update total amount
        order.total_amount = total_amount
        order.save()

        return order

    @staticmethod
    def generate_order_id():
        date       = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f"CMD-{date}-{random_str}"