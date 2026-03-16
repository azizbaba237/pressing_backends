from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CustomerViewSet,
    CategoryServicesViewSet,
    ServiceViewSet,
    OrderViewSet,
    PaymentViewSet,
)
from api.api_client import (
    ClientPortalViewSet,
    ServicePublicViewSet,
    CategoryPublicViewSet,
    customer_register,
    customer_login,
    contact_pressing
)

router = DefaultRouter()

router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'categories', CategoryServicesViewSet, basename='category')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'profile', ClientPortalViewSet, basename='client-portal')

# ✅ Préfixes publics distincts — pas de conflit
router.register(r'public/services', ServicePublicViewSet, basename='services-public')
router.register(r'public/categories', CategoryPublicViewSet, basename='categories-public')

urlpatterns = [
    path('register/', customer_register, name='customer-register'),
    path('login/', customer_login, name='customer-login'),
    path('contact/', contact_pressing, name='contact-pressing'),
    path('', include(router.urls)),
]