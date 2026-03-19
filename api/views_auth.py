"""
=============================================================================
VUES D'AUTHENTIFICATION UNIFIÉE
=============================================================================
Ce fichier gère l'authentification pour tous les types d'utilisateurs :
- Administrateurs
- Employés
- Clients

Il fournit :
- Connexion unifiée (unified_login)
- Inscription client (unified_register)
- Récupération utilisateur connecté (get_current_user)
=============================================================================
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q

# Import des modèles
from .models import UserProfile, Customer


@api_view(['POST'])
@permission_classes([AllowAny])
def unified_login(request):
    """
    =============================================================================
    CONNEXION UNIFIÉE
    =============================================================================
    Point d'entrée unique pour la connexion de tous les utilisateurs.

    Flux :
    1. Authentifie l'utilisateur avec Django
    2. Récupère ou crée son profil (UserProfile)
    3. Détermine son rôle (ADMIN, EMPLOYEE, CUSTOMER)
    4. Retourne les tokens JWT + données utilisateur + URL de redirection

    Paramètres attendus :
    - username : Nom d'utilisateur ou téléphone
    - password : Mot de passe

    Retour en cas de succès :
    {
        "message": "Connexion réussie",
        "user": {...},
        "role": "ADMIN" | "EMPLOYEE" | "CUSTOMER",
        "tokens": { "access": "...", "refresh": "..." },
        "redirect": "/admin/dashboard" | "/client/dashboard",
        "customer": {...}  // Uniquement si rôle = CUSTOMER
    }
    =============================================================================
    """

    # ========================================
    # 1. RÉCUPÉRATION DES DONNÉES
    # ========================================
    username = request.data.get('username')
    password = request.data.get('password')

    # Validation : champs obligatoires
    if not username or not password:
        return Response(
            {'error': 'Nom d\'utilisateur et mot de passe requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ========================================
    # 2. AUTHENTIFICATION DJANGO
    # ========================================
    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {'error': 'Nom d\'utilisateur ou mot de passe incorrect'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # ========================================
    # 3. VÉRIFICATION COMPTE ACTIF
    # ========================================
    if not user.is_active:
        return Response(
            {'error': 'Ce compte a été désactivé'},
            status=status.HTTP_403_FORBIDDEN
        )

    # ========================================
    # 4. RÉCUPÉRATION/CRÉATION DU PROFIL
    # ========================================
    # Le signal post_save de User crée automatiquement un UserProfile
    # Mais on utilise get_or_create par sécurité
    profile, created = UserProfile.objects.get_or_create(user=user)

    # Si le profil vient d'être créé, définir le rôle par défaut
    if created:
        if user.is_superuser or user.is_staff:
            profile.role = 'ADMIN'
        else:
            profile.role = 'CUSTOMER'
        profile.save()

    # Vérifier si le profil est actif
    if not profile.actif:
        return Response(
            {'error': 'Votre compte a été désactivé. Veuillez contacter l\'administrateur.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # ========================================
    # 5. GÉNÉRATION DES TOKENS JWT
    # ========================================
    refresh = RefreshToken.for_user(user)

    # ========================================
    # 6. PRÉPARATION DE LA RÉPONSE DE BASE
    # ========================================
    response_data = {
        'message': 'Connexion réussie',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
        'role': profile.role,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }

    # ========================================
    # 7. TRAITEMENT SELON LE RÔLE
    # ========================================

    # CAS A : ADMINISTRATEUR OU EMPLOYÉ
    if profile.role in ['ADMIN', 'EMPLOYEE']:
        response_data['redirect'] = '/admin/dashboard'
        response_data['user']['is_staff'] = user.is_staff
        response_data['user']['is_superuser'] = user.is_superuser

    # CAS B : CLIENT
    elif profile.role == 'CUSTOMER':
        # Recherche du client associé
        customer = None

        # Méthode 1 : Via le profil
        if profile.customer:
            customer = profile.customer
        else:
            # Méthode 2 : Recherche par email/téléphone
            customer = Customer.objects.filter(
                Q(email=user.email) |
                Q(phone=username) |
                Q(phone=profile.phone)
            ).first()

            # Si trouvé, lier au profil pour les prochaines fois
            if customer:
                profile.customer = customer
                profile.save()

        # Si aucun client trouvé, erreur
        if not customer:
            return Response(
                {'error': 'Profil client non trouvé. Veuillez contacter l\'administrateur.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Ajouter les données client à la réponse
        response_data['customer'] = {
            'id': customer.id,
            'last_name': customer.last_name,
            'first_name': customer.first_name,
            'phone': customer.phone,
            'email': customer.email,
            'adresse': customer.adresse,
            'actif': customer.actif,
        }
        response_data['redirect'] = '/client/dashboard'

    # ========================================
    # 8. RETOUR DE LA RÉPONSE
    # ========================================
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def unified_register(request):
    """
    =============================================================================
    INSCRIPTION CLIENT
    =============================================================================
    Permet à un nouveau client de créer son compte.

    Flux :
    1. Vérifie que le téléphone n'existe pas déjà
    2. Vérifie que le nom d'utilisateur n'existe pas
    3. Crée l'utilisateur Django
    4. Crée le profil Customer
    5. Lie le Customer au UserProfile
    6. Retourne les tokens JWT

    Paramètres attendus :
    - username : Nom d'utilisateur unique
    - password : Mot de passe
    - first_name : Prénom
    - last_name : Nom
    - phone : Téléphone (unique)
    - email : Email (optionnel)
    - adresse : Adresse (optionnel)

    Retour en cas de succès :
    {
        "message": "Compte créé avec succès",
        "user": {...},
        "customer": {...},
        "role": "CUSTOMER",
        "redirect": "/client/dashboard",
        "tokens": { "access": "...", "refresh": "..." }
    }
    =============================================================================
    """

    try:
        # ========================================
        # 1. RÉCUPÉRATION DES DONNÉES
        # ========================================
        phone = request.data.get('phone')
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        adresse = request.data.get('adresse', '')

        # ========================================
        # 2. VÉRIFICATIONS
        # ========================================

        # Vérifier si le téléphone existe déjà
        if Customer.objects.filter(phone=phone).exists():
            return Response(
                {'error': 'Un compte existe déjà avec ce numéro de téléphone'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier si le nom d'utilisateur existe déjà
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Ce nom d\'utilisateur est déjà pris'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ========================================
        # 3. CRÉATION DE L'UTILISATEUR DJANGO
        # ========================================
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )

        # ========================================
        # 4. CRÉATION DU PROFIL CLIENT
        # ========================================
        customer = Customer.objects.create(
            last_name=last_name,
            first_name=first_name,
            phone=phone,
            email=email,
            adresse=adresse,
            actif=True
        )

        # ========================================
        # 5. LIAISON USERPROFILE <-> CUSTOMER
        # ========================================
        # Le signal post_save a déjà créé le UserProfile
        profile = user.profile
        profile.role = 'CUSTOMER'
        profile.customer = customer
        profile.phone = phone
        profile.save()

        # ========================================
        # 6. GÉNÉRATION DES TOKENS JWT
        # ========================================
        refresh = RefreshToken.for_user(user)

        # ========================================
        # 7. RETOUR DE LA RÉPONSE
        # ========================================
        return Response({
            'message': 'Compte créé avec succès',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'customer': {
                'id': customer.id,
                'last_name': customer.last_name,
                'first_name': customer.first_name,
                'phone': customer.phone,
                'email': customer.email,
            },
            'role': 'CUSTOMER',
            'redirect': '/client/dashboard',
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        # En cas d'erreur inattendue, retourner le message
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    =============================================================================
    RÉCUPÉRATION DE L'UTILISATEUR CONNECTÉ
    =============================================================================
    Retourne les informations de l'utilisateur actuellement connecté.

    Nécessite : Token JWT valide dans le header Authorization

    Retour :
    {
        "user": {...},
        "role": "ADMIN" | "EMPLOYEE" | "CUSTOMER",
        "customer": {...}  // Uniquement si rôle = CUSTOMER
    }
    =============================================================================
    """

    # ========================================
    # 1. RÉCUPÉRATION DE L'UTILISATEUR
    # ========================================
    user = request.user
    profile = user.profile

    # ========================================
    # 2. PRÉPARATION DE LA RÉPONSE
    # ========================================
    response_data = {
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
        'role': profile.role,
    }

    # ========================================
    # 3. AJOUT DES DONNÉES CLIENT SI APPLICABLE
    # ========================================
    if profile.role == 'CUSTOMER' and profile.customer:
        response_data['customer'] = {
            'id': profile.customer.id,
            'last_name': profile.customer.last_name,
            'first_name': profile.customer.first_name,
            'phone': profile.customer.phone,
            'email': profile.customer.email,
            'adresse': profile.customer.adresse,
        }

    # ========================================
    # 4. RETOUR DE LA RÉPONSE
    # ========================================
    return Response(response_data)