"""
=============================================================================
CONFIGURATION DES URLs DE L'API
=============================================================================
Ce fichier définit toutes les routes de l'API.

Structure :
- /api/auth/          → Authentification unifiée
- /api/customers/     → Gestion des clients (Admin)
- /api/orders/        → Gestion des commandes (Admin)
- /api/services/      → Gestion des services (Admin)
- /api/categories/    → Gestion des catégories (Admin)
- /api/payments/      → Gestion des paiements (Admin)
- /api/profile/       → Profil client (Client)
- /api/public/        → Données publiques (non authentifié)
=============================================================================
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# ========================================
# IMPORT DES VUES ADMIN
# ========================================
from .views import (
    CustomerViewSet,
    CategoryServicesViewSet,
    ServiceViewSet,
    OrderViewSet,
    PaymentViewSet,
)

# ========================================
# IMPORT DES VUES CLIENT
# ========================================
from .api_client import (
    ClientPortalViewSet,
    ServicePublicViewSet,
    CategoryPublicViewSet,
    customer_register,  # Legacy - à garder pour compatibilité
    customer_login,  # Legacy - à garder pour compatibilité
    contact_pressing
)

# ========================================
# IMPORT DES VUES D'AUTHENTIFICATION UNIFIÉE
# ========================================
from .views_auth import (
    unified_login,
    unified_register,
    get_current_user
)

# ========================================
# CONFIGURATION DU ROUTER
# ========================================
router = DefaultRouter()

# Routes Admin (nécessitent authentification + rôle ADMIN/EMPLOYEE)
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'categories', CategoryServicesViewSet, basename='category')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')

# Routes Client (nécessitent authentification + rôle CUSTOMER)
router.register(r'profile', ClientPortalViewSet, basename='client-portal')

# Routes Publiques (pas d'authentification requise)
router.register(r'public/services', ServicePublicViewSet, basename='services-public')
router.register(r'public/categories', CategoryPublicViewSet, basename='categories-public')

# ========================================
# DÉFINITION DES URLs
# ========================================
urlpatterns = [
    # ============================================================
    # AUTHENTIFICATION UNIFIÉE (NOUVELLE MÉTHODE - RECOMMANDÉE)
    # ============================================================
    path('auth/login/', unified_login, name='unified-login'),
    path('auth/register/', unified_register, name='unified-register'),
    path('auth/me/', get_current_user, name='current-user'),

    # ============================================================
    # ROUTES LEGACY (ANCIENNE MÉTHODE - GARDÉES POUR COMPATIBILITÉ)
    # ============================================================
    # ⚠️ Ces routes peuvent être retirées une fois que tout le frontend
    # utilise les nouvelles routes /auth/
    path('register/', customer_register, name='customer-register-legacy'),
    path('login/', customer_login, name='customer-login-legacy'),

    # ============================================================
    # CONTACT (ACCESSIBLE SANS AUTHENTIFICATION)
    # ============================================================
    path('contact/', contact_pressing, name='contact-pressing'),

    # ============================================================
    # ROUTES DU ROUTER (CRUD)
    # ============================================================
    # Toutes les routes définies dans le router sont incluses ici
    # Ex: /api/customers/, /api/orders/, /api/services/, etc.
    path('', include(router.urls)),
]