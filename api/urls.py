from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *


router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'categories',CategoryServicesViewSet, basename='category')
router.register(r'services',  ServiceViewSet, basename='service')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
  path("", include(router.urls)),
]
