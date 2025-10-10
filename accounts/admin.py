# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    # Champs à afficher dans la liste
    list_display = ('username', 'email', 'get_full_name', 'role', 'phone', 'is_active', 'is_active_membre', 'created_at')
    
    # Champs filtrables
    list_filter = ('role', 'is_active', 'is_active_membre', 'is_staff', 'is_superuser')
    
    # Champs éditables directement depuis la liste
    list_editable = ('role', 'is_active_membre')
    
    # Barre de recherche
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    
    # Organisation du formulaire d'édition
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'email', 'phone', 'role', 'is_active_membre')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    # Champs uniquement en lecture
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    
    # Champs pour ajouter un nouvel utilisateur
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'phone', 'role', 'password1', 'password2', 'is_active', 'is_active_membre')
        }),
    )
    
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)
