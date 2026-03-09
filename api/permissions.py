#from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated

class IsAuthenticatedOrOptions(IsAuthenticated):
    """Laisse passer les OPTIONS (CORS preflight) sans authentification."""
    def has_permission(self, request, view):
        if request.method == "OPTIONS":
            return True
        return super().has_permission(request, view)
