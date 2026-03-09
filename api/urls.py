from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import ViewSets explicitly for better readability
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

# ============================================================
# API ROUTER CONFIGURATION
# ============================================================

# DefaultRouter automatically generates RESTFul routes
# for all registered ViewSets (list, retrieve, create, update, delete)
router = DefaultRouter()

# ------------------------------------------------------------
# Customers endpoints
# /api/customers/
# /api/customers/{id}/
# ------------------------------------------------------------
router.register(
    r'customers',
    CustomerViewSet,
    basename='customer'
)

# ------------------------------------------------------------
# Service categories endpoints
# /api/categories/
# ------------------------------------------------------------
router.register(
    r'categories',
    CategoryServicesViewSet,
    basename='category'
)

# ------------------------------------------------------------
# Services endpoints
# /api/services/
# ------------------------------------------------------------
router.register(
    r'services',
    ServiceViewSet,
    basename='service'
)

# ------------------------------------------------------------
# Orders endpoints
# /api/orders/
# ------------------------------------------------------------
router.register(
    r'orders',
    OrderViewSet,
    basename='order'
)

# ------------------------------------------------------------
# Payments endpoints
# /api/payments/
# ------------------------------------------------------------
router.register(
    r'payments',
    PaymentViewSet,
    basename='payment'
)

# ------------------------------------------------------------
# Profile endpoints
# /api/profile/
# ------------------------------------------------------------
router.register(
    r'profile',
    ClientPortalViewSet,
    basename='client-portal'
)

# ------------------------------------------------------------
# services endpoints for customers
# /api/services/
# ------------------------------------------------------------
router.register(
    r'services',
    ServicePublicViewSet,
    basename='services-public'
)

# ------------------------------------------------------------
# categories endpoints for customers
# /api/categories/
# ------------------------------------------------------------
router.register(
    r'categories',
    CategoryPublicViewSet,
    basename='categories-public'
)

# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [
    # Include all automatically generated router URLs
    path('register/', customer_register, name='customer-register'),
    path('login/', customer_login, name='customer-login'),
    path('contact/', contact_pressing, name='contact-pressing'),

    path('', include(router.urls)),
]
