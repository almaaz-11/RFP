from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.is_staff
        )

class IsVendor(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'vendor_profile')
        )

class IsAdminOrVendor(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and 
            (user.is_staff or hasattr(user, 'vendor_profile'))
        )

