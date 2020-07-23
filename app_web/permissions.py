

class GreetingPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        #If user is owner and its a read operation return all
        if request.user == obj.user and request.method in permissions.SAFE_METHODS:
            return True

