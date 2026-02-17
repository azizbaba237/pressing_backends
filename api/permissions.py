#from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated

#class IsAdminOrReadOnly(BasePermission):
#    def has_permission(self, request, view):
#        if request.method in ("GET","HEAD","OPTIONS"):
#            return True
#        return request.user.is_staff

class IsAuthenticatedOrOptions(IsAuthenticated):
    """Laisse passer les OPTIONS (CORS preflight) sans authentification."""
    def has_permission(self, request, view):
        if request.method == "OPTIONS":
            return True
        return super().has_permission(request, view)
