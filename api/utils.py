from django.utils import timezone
import random
import string


# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def generate_order_id():
    """
    Génère un ID de commande unique basé sur la date et un compteur.
    Format: ORD-YYYYMMDD-XXXX

    Exemple: ORD-20260129-0001

    Returns:
        str: L'order_id généré de façon unique
    """
    # Import local pour éviter les imports circulaires
    from .models import Order

    today = timezone.now()
    # Créer le préfixe avec la date du jour
    prefix = f"CMD-{today.strftime('%Y%m%d')}"

    # Compter les commandes créées aujourd'hui
    count = Order.objects.filter(
        order_id__startswith=prefix
    ).count() + 1

    # Retourner l'ID formaté avec padding de 4 chiffres
    return f"{prefix}-{count:04d}"
