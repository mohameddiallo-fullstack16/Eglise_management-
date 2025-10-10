# membres/signals.py (crée le fichier)

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Member
from django.utils.crypto import get_random_string  # Pour mot de passe random

User = get_user_model()

@receiver(post_save, sender=Member)
def create_user_and_send_email(sender, instance, created, **kwargs):
    """Crée un User lié et envoie un email de confirmation lors de la création d'un Member."""
    if created and instance.email:  # Seulement pour nouveaux membres avec email
        # Crée un username (ex. prénom.nom ou email)
        username = f"{instance.first_name.lower()}.{instance.last_name.lower()}"
        if User.objects.filter(username=username).exists():
            username = instance.email.split('@')[0]  # Fallback sur email
        
        # Mot de passe random (8 chars, envoi par email)
        password = get_random_string(length=8)
        
        # Crée le User
        user = User.objects.create_user(
            username=username,
            email=instance.email,
            password=password,
            first_name=instance.first_name,
            last_name=instance.last_name,
            role='membre'  # Rôle par défaut
        )
        
        # Lie le Member au User
        instance.user = user
        instance.save()  # Mise à jour
        
        # Envoi email
        subject = "Bienvenue ! Votre compte a été créé"
        html_message = render_to_string('membres/email_new_member.html', {
            'member': instance,
            'username': username,
            'password': password,
            'login_url': 'http://127.0.0.1:8000/accounts/login/',  # Adaptez à ton site
        })
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = instance.email
        
        send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)