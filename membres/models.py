# members/models.py

from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid

class Ministry(models.Model):
    """Modèle pour les ministères/départements"""
    name = models.CharField(max_length=100, verbose_name='Nom du ministère')
    description = models.TextField(blank=True, verbose_name='Description')
    leader = models.ForeignKey(
        'Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_ministries',
        verbose_name='Responsable'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Ministère'
        verbose_name_plural = 'Ministères'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Group(models.Model):
    """Modèle pour les groupes (cellules, chorales, etc.)"""
    GROUP_TYPE_CHOICES = [
        ('cell', 'Cellule de prière'),
        ('choir', 'Chorale'),
        ('youth', 'Jeunesse'),
        ('women', 'Femmes'),
        ('men', 'Hommes'),
        ('children', 'Enfants'),
        ('other', 'Autre'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='Nom du groupe')
    group_type = models.CharField(
        max_length=20,
        choices=GROUP_TYPE_CHOICES,
        default='other',
        verbose_name='Type de groupe'
    )
    description = models.TextField(blank=True, verbose_name='Description')
    meeting_day = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Jour de réunion'
    )
    meeting_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Heure de réunion'
    )
    leader = models.ForeignKey(
        'Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_groups',
        verbose_name='Responsable'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Groupe'
        verbose_name_plural = 'Groupes'
        ordering = ['group_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_group_type_display()})"

class Family(models.Model):
    """Modèle pour les familles"""
    name = models.CharField(max_length=100, verbose_name='Nom de famille')
    head = models.ForeignKey(
        'Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_family',
        verbose_name='Chef de famille'
    )
    address = models.TextField(blank=True, verbose_name='Adresse')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Famille'
        verbose_name_plural = 'Familles'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_members_count(self):
        return self.members.count()

class Member(models.Model):
    """Modèle principal pour les membres de l'église"""
    
    GENDER_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Célibataire'),
        ('married', 'Marié(e)'),
        ('widowed', 'Veuf/Veuve'),
        ('divorced', 'Divorcé(e)'),
    ]
    
    MEMBER_STATUS_CHOICES = [
        ('active', 'Actif'),
        ('inactive', 'Inactif'),
        ('visitor', 'Visiteur'),
        ('transferred', 'Transféré'),
        ('deceased', 'Décédé'),
    ]
    
    # Informations de base
    member_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='ID Membre'
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='member_profile',
        verbose_name='Compte utilisateur'
    )
    
    # Informations personnelles
    first_name = models.CharField(max_length=100, verbose_name='Prénom')
    last_name = models.CharField(max_length=100, verbose_name='Nom')
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        verbose_name='Sexe'
    )
    date_of_birth = models.DateField(verbose_name='Date de naissance')
    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        verbose_name='État civil'
    )
    profession = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Profession'
    )
    
    # Contact
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Format: '+227XXXXXXXX'. Jusqu'à 15 chiffres."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        verbose_name='Téléphone'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    address = models.TextField(verbose_name='Adresse')
    
    # Photo
    photo = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True,
        verbose_name='Photo'
    )
    
    # Informations spirituelles
    baptism_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date de baptême'
    )
    membership_date = models.DateField(
        default=timezone.now,
        verbose_name='Date d\'adhésion'
    )
    
    # Relations
    family = models.ForeignKey(
        Family,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name='Famille'
    )
    ministries = models.ManyToManyField(
        Ministry,
        blank=True,
        related_name='members',
        verbose_name='Ministères'
    )
    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name='members',
        verbose_name='Groupes'
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=MEMBER_STATUS_CHOICES,
        default='active',
        verbose_name='Statut'
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='members_created',
        verbose_name='Créé par'
    )
    
    class Meta:
        verbose_name = 'Membre'
        verbose_name_plural = 'Membres'
        ordering = ['last_name', 'first_name']
    
    def save(self, *args, **kwargs):
        if not self.member_id:
            # Génération de l'ID unique du membre
            year = timezone.now().year
            last_member = Member.objects.filter(
                member_id__startswith=f'M{year}'
            ).order_by('-member_id').first()
            
            if last_member:
                last_number = int(last_member.member_id[5:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.member_id = f'M{year}{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.member_id})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_age(self):
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def is_baptized(self):
        return self.baptism_date is not None

class Attendance(models.Model):
    """Modèle pour le suivi de présence"""
    
    EVENT_TYPE_CHOICES = [
        ('sunday_service', 'Culte dominical'),
        ('wednesday_service', 'Culte de mercredi'),
        ('prayer_meeting', 'Réunion de prière'),
        ('bible_study', 'Étude biblique'),
        ('special_event', 'Événement spécial'),
        ('other', 'Autre'),
    ]
    
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='Membre'
    )
    date = models.DateField(verbose_name='Date')
    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPE_CHOICES,
        verbose_name='Type d\'événement'
    )
    event_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nom de l\'événement'
    )
    present = models.BooleanField(
        default=True,
        verbose_name='Présent'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Enregistré par'
    )
    
    class Meta:
        verbose_name = 'Présence'
        verbose_name_plural = 'Présences'
        ordering = ['-date', 'member']
        unique_together = ['member', 'date', 'event_type']
    
    def __str__(self):
        status = "Présent" if self.present else "Absent"
        return f"{self.member.get_full_name()} - {self.date} - {status}"