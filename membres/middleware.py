from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:
    """Force l'utilisateur à changer son mot de passe s'il vient d'être créé"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            member = getattr(user, 'member', None)
            if member and getattr(member, 'force_password_change', False):
                allowed_paths = [
                    reverse('change_password'),
                    reverse('logout'),
                ]
                if request.path not in allowed_paths:
                    return redirect('change_password')
        return self.get_response(request)
