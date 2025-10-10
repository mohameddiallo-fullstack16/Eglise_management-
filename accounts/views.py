from pyexpat.errors import messages
from urllib import request
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView
from .forms import CustomUserCreationForm, LoginForm, UserProfileForm
import membres
from .models import User
from django.views.generic import CreateView  # ← Sans 's' à la fin
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash


def login_views(request):
    # Si l'utilisateur est déjà connecté
    if request.user.is_authenticated:
        if request.user.has_admin_access():
            return redirect('dashboard')  # admin → dashboard
        else:
            return redirect('accounts:profile')  # membre → profil

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenue {user.get_full_name() or user.username}')

                # ✅ Vérifie si c’est la première connexion
                if user.last_login is None:
                    messages.info(
                        request,
                        "C’est votre première connexion. Merci de changer votre mot de passe pour sécuriser votre compte."
                    )
                    return redirect('accounts:change_password')

                # ✅ Sinon, redirection selon le rôle
                if user.has_admin_access():
                    return redirect('dashboard')
                else:
                    return redirect('accounts:profile')
            else:
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
        else:
            messages.error(request, "Formulaire invalide. Veuillez vérifier vos informations.")
    else:
        form = LoginForm()

    context = {
        'form': form,
        'title': 'Connexion',
    }
    return render(request, 'accounts/login.html', context)


def logout_views(request):
    # Déconnexion
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('accounts:login')

class RegistrerViews(CreateView):
    # vue inscrption nouvel 
    
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    
    def form_valid(self,form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Compte créé avec succès pour {self.object.get_full_name()}. Vous pouvez maintenant vous connecter.'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inscription'
        return context



@login_required
def profile_view(request):
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():  # ← vérifie si le formulaire est valide
            form.save()
            messages.success(request, 'Votre profil a été mis à jour avec succès.')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)  # formulaire pré-rempli pour GET

    context = {
        'form': form,
        'title': 'Mon profil',
        'user': user
    }
    return render(request, 'accounts/profile.html', context)



@login_required
def change_password_views(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # évite la déconnexion
            messages.success(request, 'Votre mot de passe a été mis à jour avec succès.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = PasswordChangeForm(request.user)

    # Ce return est en dehors du if → fonctionne pour POST ET GET
    context = {
        'form': form,
        'title': 'Changer le mot de passe',
    }
    return render(request, 'accounts/change_password.html', context)


@login_required
def user_list_view(request):
    """Vue pour lister les utilisateurs"""
    if not request.user.has_admin_access():
        messages.error(request, "Vous n'avez pas la permission d'accéder à cette page.")
        return redirect('dashboard')

    users = User.objects.all().order_by('-created_at')

    # Comptages par rôle
    total_users = users.count()
    total_admins = users.filter(role='admin').count()
    total_active = users.filter(is_active=True).count()
    total_inactive = users.filter(is_active=False).count()

    context = {
        'users': users,
        'title': 'Liste des utilisateurs',
        'total_users': total_users,
        'total_admins': total_admins,
        'total_active': total_active,
        'total_inactive': total_inactive,
    }
    return render(request, 'accounts/user_list.html', context)




@login_required
def toggle_user_status(request, user_id):
    """Vue pour activer/désactiver un utilisateur"""
    if not request.user.has_admin_access():
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('dashboard:home')
    
    try:
        user = User.objects.get(id=user_id)
        if user != request.user:
            user.is_active = not user.is_active
            user.save()
            status = 'activé' if user.is_active else 'désactivé'
            messages.success(request, f'L\'utilisateur {user.get_full_name()} a été {status} avec succès.')
        else:
            messages.error(request, 'Vous ne pouvez pas désactiver votre propre compte.')
    except User.DoesNotExist:
        messages.error(request, 'Utilisateur non trouvé.')
    
    
    return redirect('accounts:user_list')


@login_required
def assign_role(request, user_id):
    """Attribuer un rôle à un utilisateur (admin uniquement)"""
    if not request.user.has_admin_access():
        messages.error(request, "Vous n'avez pas la permission d'accéder à cette page.")
        return redirect('dashboard')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(User.ROLE_CHOICES).keys():
            user.role = new_role
            user.save()
            messages.success(request, f"Le rôle de {user.get_full_name()} a été mis à jour vers '{new_role}'.")
        else:
            messages.error(request, "Rôle invalide.")

    return redirect('accounts:user_list')


@login_required
def validate_user(request, user_id):
    """Valider ou rejeter un compte utilisateur"""
    if not request.user.has_admin_access():
        messages.error(request, "Vous n'avez pas la permission d'accéder à cette page.")
        return redirect('dashboard')

    user = get_object_or_404(User, id=user_id)

    action = request.GET.get('action')  # 'validate' ou 'reject'

    if action == 'validate':
        user.is_validated = True
        messages.success(request, f"Le compte de {user.get_full_name()} a été validé.")
    elif action == 'reject':
        user.is_validated = False
        messages.warning(request, f"Le compte de {user.get_full_name()} a été rejeté.")
    else:
        messages.error(request, "Action invalide.")

    user.save()
    return redirect('accounts:user_list')

    

