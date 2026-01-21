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

# ============================================================
# API ROUTER CONFIGURATION
# ============================================================

# DefaultRouter automatically generates RESTful routes
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

# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [
    # Include all automatically generated router URLs
    path('', include(router.urls)),
]
