from rest_framework import permissions

class IsCompanyUser(permissions.BasePermission):
    """
    Permission class to ensure only company users can access the API.
    """
    message = "Only company accounts can access this resource."

    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user type is company
        user_type = request.user.get_user_type()
        return user_type == 'company'


class IsIndividualUser(permissions.BasePermission):
    """
    Permission class to ensure only individual users can access the API.
    """
    message = "Only individual accounts can access this resource."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_type = request.user.get_user_type()
        return user_type == 'individual'