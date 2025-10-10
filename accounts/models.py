from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrateur principal'),
        ('secretary', 'Secrétaire'),  # Corrigé l'accent
        ('treasurer', 'Trésorier'),   # Corrigé l'accent
        ('leader', 'Responsable de groupe'),
        ('membre', 'Membre'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='membre',
        verbose_name="Rôle de l'utilisateur"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Numéro de téléphone"
    )
    is_active_membre = models.BooleanField(
        default=True,
        verbose_name="Membre actif"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification"  # Corrigé l'accent
    )
    is_validated = models.BooleanField(default=False, verbose_name="Compte validé")

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.get_full_name()} - {self.get_role_display()}"

    # Vérifie si l'utilisateur a accès admin
    def has_admin_access(self):
        if self.is_superuser:  # Superuser Django natif
            return True
        return self.role in ['admin']

    # Vérifie si l'utilisateur a accès finance
    def has_finance_access(self):
        if self.is_superuser:
            return True
        return self.role in ['admin', 'treasurer']

    # Vérifie si l'utilisateur peut gérer les membres (corrigé le nom)
    def has_membres_management_access(self):
        if self.is_superuser:
            return True
        return self.role in ['admin', 'secretary', 'leader']