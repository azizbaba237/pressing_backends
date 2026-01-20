from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from .models import *
from .serializers import (
        CustomerSerializer,
        ServiceSerializer,
        OrderItemSerializer,
        PaymentSerializer,
        OrderCreateSerializers,
        CategoryServicesSerializer,
        OrderSerializers
)



class CustomerViewSet(viewsets.ModelViewSet):
    """for manage customers"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields   = ['name', 'last_name', 'email']
    ordering_fields = ('inscription_date', 'name', 'last_name')
    ordering = ['-inscription_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        actif    = self.request.query_params.get('actif', None)
        if actif is not None:
            queryset = queryset.filter(actif.actif.lower() == 'True')
        return queryset

    @action(detail=True, methods=['get'])
    def orders(self):
        """to return customer orders"""
        customer = self.get_object()
        order    = customer.orders.all()
        serializer = OrderItemSerializer(order, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statistics(self):
        """Customer statistics"""
        customer = self.get_object()
        stats    = {
            'total_orders'      : customer.orders.count(),
            'order_in_pending'  : customer.orders.filter(statut__in=['PENDING', 'Pending']).count(),
            'order_delivered'   : customer.orders.filter(status='DELIVERED').cout(),
            'total_amount_spend': customer.orders.aggregate(total=Sum('total_amount'))['total'] or 0,
            'amount_pending'    : customer.orders.aggregate(
                total=Sum('total_amount') - Sum('amount_paid')
                )['total'] or 0,
        }
        return Response(stats)

class CategoryServicesViewSet(viewsets.ModelViewSet):
    """To manage services categories"""
    queryset = CategoryServices.objects.all()
    serializer_class = CategoryServicesSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        actif = self.request.query_params.get('actif', None)
        if actif is not None:
            queryset = queryset.filter(actif=actif.lower() == 'true')
        return queryset

class ServiceViewSet(viewsets.ModelViewSet):
    """To manage services"""
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['name', 'price', 'estimate_time']
    ordering = ['category', 'name']

    def get_queryset(self):
        queryset = super().get_queryset()
        actif = self.request.query_params.get('actif', None)
        category = self.request.query_params.get('category', None)

        if actif is not None:
            queryset = queryset.filter(actif=actif.lower() == 'true')
        if category:
            queryset = queryset.filter(categorie_id=category)

        return queryset

class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les commandes"""
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order_id', 'customer__first_name', 'customer__last_name', 'customer__phone']
    ordering_fields = ['deposit_date', 'promise_date', 'total_amount', 'status']
    ordering = ['-deposit_date']

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializers
        return OrderSerializers

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.query_params.get('status', None)
        customer = self.request.query_params.get('customer', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        if status:
            queryset = queryset.filter(status=status)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        if start_date:
            queryset = queryset.filter(deposit_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(deposit_date__lte=end_date)

        return queryset

    @action(detail=True, methods=['post'])
    def change_staus(self, request):
        """Change order status"""
        order = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid staus'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status
        if new_status == 'DELIVERED':
            order.pickup_date = timezone.now()
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_payment(self, request):
        """Add payment to the order"""
        order = self.get_object()
        serializer = PaymentSerializer(data=request.data)

        if serializer.is_valid():
            payment = serializer.save(
                order=order,
                user=request.user
            )

            # Update amount paid
            order.amount_paid += payment.amout
            order.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def statistics(self):
        """Global order statistics"""
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)

        stats = {
            'total_order': Order.objects.count(),
            'order_days': Order.objects.filter(deposit__date=today).count(),
            'order_30_days': Order.objects.filter(deposit__date__gte=last_30_days).count(),
            'order_by_status': {
                statut[0]: Order.objects.filter(status=statut[0]).count()
                for statut in Order.STATUS_CHOICES
            },
            'revenue_last_30_days': Order.objects.filter(
                date_depot__date__gte=last_30_days
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
            'pending_amounts': Order.objects.aggregate(
                total=Sum('total_amount') - Sum('amount_paid')
            )['total'] or 0,
        }
        return Response(stats)

class PaymentViewSet(viewsets.ModelViewSet):
    """To manage payments"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order__order_id', 'reference', 'payment_mod']
    ordering_fields = ['payment_date', 'amount']
    ordering = ['-payment_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        order = self.request.query_params.get('order', None)
        payment_mod = self.request.query_params.get('payment_mod', None)

        if order:
            queryset = queryset.filter(order_id=order)
        if payment_mod:
            queryset = queryset.filter(payment_mod=payment_mod)
        return queryset

    def perform_create(self, serializer):
        payment = serializer.save(user=self.request.user)
        # Update orders amount
        order = payment.order
        order.amount_paid += payment.amount
        order.save()



