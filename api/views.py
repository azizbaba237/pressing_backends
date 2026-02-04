from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    Customer,
    CategoryServices,
    Service,
    Order,
    OrderItem,
    Payment
)

from .serializers import (
    CustomerSerializer,
    CategoryServicesSerializer,
    ServiceSerializer,
    OrderSerializer,
    OrderCreateSerializer,
    OrderItemSerializer,
    PaymentSerializer
)

# ============================================================
# CUSTOMER VIEWSET
# ============================================================

class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet used to manage customers.
    Supports CRUD operations, search, ordering and statistics.
    """

    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    ordering_fields = ['inscription_date', 'first_name', 'last_name']
    ordering = ['-inscription_date']

    def get_queryset(self):
        """
        Optionally filter customers by active status (?actif=true|false).
        """
        queryset = super().get_queryset()
        actif = self.request.query_params.get('actif')

        if actif is not None:
            queryset = queryset.filter(actif=actif.lower() == 'true')

        return queryset

    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        """
        Return all orders belonging to a specific customer.
        """
        customer = self.get_object()
        orders = customer.orders.all()

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Return statistics for a single customer.
        """
        customer = self.get_object()

        stats = {
            "total_orders": customer.orders.count(),
            "orders_pending": customer.orders.filter(status='PENDING').count(),
            "orders_delivered": customer.orders.filter(status='DELIVERED').count(),
            "total_amount_spent": customer.orders.aggregate(
                total=Sum('total_amount')
            )['total'] or 0,
            "amount_pending": customer.orders.aggregate(
                total=Sum(F('total_amount') - F('amount_paid'))
            )['total'] or 0,
        }

        return Response(stats)


# ============================================================
# CATEGORY SERVICES VIEWSET
# ============================================================

class CategoryServicesViewSet(viewsets.ModelViewSet):
    """
    ViewSet used to manage service categories.
    """

    queryset = CategoryServices.objects.all()
    serializer_class = CategoryServicesSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        """
        Optionally filter categories by active status.
        """
        queryset = super().get_queryset()
        actif = self.request.query_params.get('actif')

        if actif is not None:
            queryset = queryset.filter(actif=actif.lower() == 'true')

        return queryset


# ============================================================
# SERVICE VIEWSET
# ============================================================

class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet used to manage services.
    """

    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['name', 'price', 'estimate_time']
    ordering = ['category', 'name']

    def get_queryset(self):
        """
        Optionally filter services by active status and category.
        """
        queryset = super().get_queryset()

        actif = self.request.query_params.get('actif')
        category = self.request.query_params.get('category')

        if actif is not None:
            queryset = queryset.filter(actif=actif.lower() == 'true')

        if category:
            queryset = queryset.filter(category_id=category)

        return queryset


# ============================================================
# ORDER VIEWSET
# ============================================================

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet used to manage orders.
    Handles creation, filtering, payments and statistics.
    """

    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'order_id',
        'customer__first_name',
        'customer__last_name',
        'customer__phone'
    ]
    ordering_fields = [
        'deposit_date',
        'due_date',
        'total_amount',
        'status'
    ]
    ordering = ['-deposit_date']

    def get_serializer_class(self):
        """
        Use different serializers depending on the action.
        """
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        """
        Filter orders by status, customer and date range.
        """
        queryset = super().get_queryset()

        status_param = self.request.query_params.get('status')
        customer = self.request.query_params.get('customer')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if status_param:
            queryset = queryset.filter(status=status_param)

        if customer:
            queryset = queryset.filter(customer_id=customer)

        if start_date:
            queryset = queryset.filter(deposit_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(deposit_date__lte=end_date)

        return queryset

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """
        Change the status of an order.
        """
        order = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status

        # Automatically set pickup date when delivered
        if new_status == 'DELIVERED':
            order.pickup_date = timezone.now()

        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """
        Add a payment to a specific order.
        """
        order = self.get_object()
        serializer = PaymentSerializer(data={
            **request.data,
            "amount": Decimal(request.data.get("amount", "0"))
        })

        if serializer.is_valid():
            payment = serializer.save(
                order=order,
                user=request.user
            )

            # Update the total amount paid for the order
            Order.objects.filter(pk=order.pk).update(
                amount_paid=F('amount_paid') + payment.amount
            )
            order.refresh_from_db()

            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Return global order statistics.
        """
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)

        stats = {
            "total_orders": Order.objects.count(),
            "orders_today": Order.objects.filter(
                deposit_date__date=today
            ).count(),
            "orders_last_30_days": Order.objects.filter(
                deposit_date__date__gte=last_30_days
            ).count(),
            "orders_by_status": {
                status_choice[0]: Order.objects.filter(
                    status=status_choice[0]
                ).count()
                for status_choice in Order.STATUS_CHOICES
            },
            "revenue_last_30_days": Order.objects.filter(
                deposit_date__date__gte=last_30_days
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
            "pending_amount": Order.objects.aggregate(
                total=Sum(F('total_amount') - F('amount_paid'))
            )['total'] or 0,
        }

        return Response(stats)


# ============================================================
# PAYMENT VIEWSET
# ============================================================

class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet used to manage payments.
    """

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order__order_id', 'reference', 'payment_method']
    ordering_fields = ['payment_date', 'amount']
    ordering = ['-payment_date']

    def get_queryset(self):
        """
        Optionally filter payments by order or payment method.
        """
        queryset = super().get_queryset()

        order_id = self.request.query_params.get('order')
        payment_method = self.request.query_params.get('payment_method')

        if order_id:
            queryset = queryset.filter(order_id=order_id)

        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        return queryset

    def perform_create(self, serializer):
        """
        Automatically associate the logged-in user
        and update the related order amount.
        """
        payment = serializer.save(user=self.request.user)

        order = payment.order
        order.amount_paid += payment.amount
        order.save(update_fields=['amount_paid'])
