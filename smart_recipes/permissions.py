from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    
    """ 
     Custom permission to allow only owners of an object to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        #only allow owners of the recipe to edit
        
        return obj.user == request.user    