from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from .models import Customer, Order, Service, CategoryServices
from .serializers import (
    CustomerSerializer, OrderSerializer, ServiceSerializer,
    CategoryServicesSerializer
)


# Inscription client
@api_view(['POST'])
@permission_classes([AllowAny])
def customer_register(request):
    """
    Inscription d'un nouveau client
    """
    try:
        # Vérifier si le téléphone existe déjà
        phone = request.data.get('phone')
        if Customer.objects.filter(phone=phone).exists():
            return Response(
                {'error': 'Un compte existe déjà avec ce numéro de téléphone'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer l'utilisateur Django
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Ce nom d\'utilisateur est déjà pris'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=request.data.get('first_name', ''),
            last_name=request.data.get('last_name', '')
        )

        # Créer le profil client
        customer = Customer.objects.create(
            last_name=request.data.get('last_name'),
            first_name=request.data.get('first_name'),
            phone=phone,
            email=email,
            adresse=request.data.get('adresse', ''),
            actif=True
        )

        # Générer le token JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Compte créé avec succès',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            },
            'customer': CustomerSerializer(customer).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# Connexion client
@api_view(['POST'])
@permission_classes([AllowAny])
def customer_login(request):
    """
    Connexion d'un client
    """
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if user is not None:
        try:
            # Récupérer le profil client
            # On cherche par email ou par nom d'utilisateur
            customer = Customer.objects.filter(
                Q(email=user.email) |
                Q(phone=username)
            ).first()

            if not customer:
                return Response(
                    {'error': 'Profil client non trouvé'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if not customer.actif:
                return Response(
                    {'error': 'Votre compte a été désactivé. Veuillez contacter le pressing.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Générer le token JWT
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'Connexion réussie',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'customer': CustomerSerializer(customer).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        return Response(
            {'error': 'Nom d\'utilisateur ou mot de passe incorrect'},
            status=status.HTTP_401_UNAUTHORIZED
        )


# ViewSet pour les clients (accès client)
class ClientPortalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour que les clients puissent voir leurs propres informations
    """
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Le client ne peut voir que son propre profil
        user = self.request.user
        return Customer.objects.filter(
            Q(email=user.email) | Q(phone=user.username)
        )

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """Récupérer les commandes du client connecté"""
        try:
            customer = Customer.objects.filter(
                Q(email=request.user.email) | Q(phone=request.user.username)
            ).first()

            if not customer:
                return Response(
                    {'error': 'Profil client non trouvé'},
                    status=status.HTTP_404_NOT_FOUND
                )

            orders = Order.objects.filter(customer=customer).order_by('-deposit_date')
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques du client connecté"""
        try:
            customer = Customer.objects.filter(
                Q(email=request.user.email) | Q(phone=request.user.username)
            ).first()

            if not customer:
                return Response(
                    {'error': 'Profil client non trouvé'},
                    status=status.HTTP_404_NOT_FOUND
                )

            orders = Order.objects.filter(customer=customer)

            stats = {
                'total_orders': orders.count(),
                'IN_PROGRESS': orders.filter(
                    status__in=['PENDING', 'IN_PROGRESS']
                ).count(),
                'orders_ready': orders.filter(status='READY').count(),
                'orders_delivered': orders.filter(status='DELIVERED').count(),
                'total_amount_spend': sum([float(c.total_amount) for c in orders]),
                'amount_pending': sum([
                    float(c.total_amount) - float(c.amount_payed) for c in orders
                ]),
            }

            return Response(stats)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """Mettre à jour le profil du client"""
        try:
            customer = Customer.objects.filter(
                Q(email=request.user.email) | Q(phone=request.user.username)
            ).first()

            if not customer:
                return Response(
                    {'error': 'Profil client non trouvé'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Mise à jour des champs autorisés
            customer.adresse = request.data.get('adresse', customer.adresse)
            customer.email = request.data.get('email', customer.email)
            customer.first_name = request.data.get('first_name', customer.first_name)
            customer.last_name = request.data.get('last_name', customer.last_name)
            customer.save()

            # Mise à jour de l'utilisateur Django
            user = request.user
            user.email = request.data.get('email', user.email)
            user.first_name = request.data.get('first_name', user.first_name)
            user.last_name = request.data.get('last_name', user.last_name)
            user.save()

            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ViewSet pour les services (accessible publiquement)
class ServicePublicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour que les clients puissent voir les services disponibles
    """
    queryset = Service.objects.filter(actif=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
        return queryset


# ViewSet pour les catégories (accessible publiquement)
class CategoryPublicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour que les clients puissent voir les catégories
    """
    queryset = CategoryServices.objects.filter(actif=True)
    serializer_class = CategoryServicesSerializer
    permission_classes = [AllowAny]


# Contact - Envoyer un message
@api_view(['POST'])
@permission_classes([AllowAny])
def contact_pressing(request):
    """
    Permettre aux clients d'envoyer un message au pressing
    """
    try:
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        sujet = request.data.get('sujet')
        message = request.data.get('message')

        # Ici, vous pouvez enregistrer le message dans la base de données
        # ou envoyer un email au pressing
        # Pour l'instant, on retourne juste une confirmation.

        return Response({
            'message': 'Votre message a été envoyé avec succès. Nous vous contacterons bientôt.'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )