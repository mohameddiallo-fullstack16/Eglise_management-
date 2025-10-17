from datetime import datetime
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from django.urls import reverse
from decimal import Decimal
import uuid




User = get_user_model()


class EventCategory(models.Model):
    name = models.CharField(max_length= 100, unique=True,verbose_name="Nom") 
    description = models.TextField(blank=True, null=True,verbose_name="Description") 
    color = models.CharField(max_length= 7, default= '#4A90E2',verbose_name='Couleur')
    icon = models.CharField(max_length=50, blank= True, null=True , verbose_name="Icone") 
    is_active = models.BooleanField(default=True,verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    class Meta:
        verbose_name = "Catégorie d'événement"
        verbose_name_plural = "Catégories d'événements"
        ordering = ['name']
        
        def __str__(self):
            return self.name
        
        
class Event(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('scheduled', 'Programmé'),
        ('published', 'Publié'),
        ('ongoing', 'En cours'),
        ('archived', 'Archivé'),
        ('canceled', 'Annulé'),
    ]
    # identifiant unique pour chaque événement
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(unique=True, blank=True, max_length=200)
    category = models.ForeignKey(
        EventCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='events', verbose_name="Catégorie"
    )

    description = models.TextField(verbose_name="Description Complete de l'événement")
    short_description = models.CharField(max_length=300, blank=True , null= True, verbose_name="Description Courte")
    cover_image = models.ImageField(upload_to='evenements/images/%Y/%m/%d/', blank=True, null=True, verbose_name="Image de couverture", help_text="Taille recommandée: 1200x600px")
    thumbnail = models.ImageField(upload_to='evenements/thumbnails/%Y/%m/%d/', blank=True, null=True, verbose_name="Miniature")
    start_date = models.DateField(verbose_name="Date de début")
    start_time = models.TimeField(verbose_name="Heure de début")
    end_date = models.DateField(verbose_name="Date de fin")
    end_time = models.TimeField(verbose_name= "Heure de fin")
    location = models.CharField(max_length=255, blank=True , null=True, verbose_name="Lieu")
    adress = models.CharField(max_length=255, blank=True, null=True, verbose_name="Adresse complete" )
    organizer = models.ForeignKey(
        User, on_delete=models.CASCADE, 
        related_name='organized_events', 
        verbose_name="Organisateur"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Statut")
    
    watsapp_notifications_sent = models.BooleanField(default=False, verbose_name="Notifications Watsapp envoyées")
    watsapp_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Date d'envoi des notifications Watsapp")
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,related_name='created_events', verbose_name="Créé par")

    class Meta :
        
        verbose_name = "Evenement"
        verbose_name_plural = "Evenements"
        ordering = ['-start_date', '-start_time']
        indexes = [
            models.Index(fields=['start_date', 'start_time']),
            models.Index(fields=['slug'])  
        ]

    def __str__(self):
        return f"{self.title} - {self.start_date.strftime('%d/%m/%Y')}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Event.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if not self.short_description:
            self.short_description = self.description[:297] + '...'   
        super().save(*args, **kwargs)        
    
    def get_absolute_url(self):
        return reverse("events:events_detail", kwargs={"slug": self.slug})
    
    def is_past(self):
        events_end = datetime.combine(self.end_date, self.end_time)
        return timezone.make_aware(events_end) < timezone.now()
    
    def is_ongoing(self):
        now = timezone.now()
        start = timezone.make_aware(datetime.combine(self.start_date, self.start_time))
        end = timezone.make_aware(datetime.combine(self.end_date, self.end_time))
        return start <= now <= end
    
    def is_upcoming(self):
        start = timezone.make_aware(datetime.combine(self.start_date, self.start_time))
        return start > timezone.now()
    
    def get_duration_days(self):
        return (self.end_date - self.start_date).days + 1
    
    def get_attendances_count(self):
        return self.attendances.filter(is_present=True).count()
    
    def get_total_expected(self):
        return self.attendances.count()
            
class EventProgram(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='programs', verbose_name="Événement")
    title = models.CharField(max_length=200, verbose_name="Titre du programme")
    description = models.TextField(blank=True, verbose_name="Description")
    date = models.DateField(verbose_name="Date")
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(verbose_name="Heure de fin")
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Lieu spécifique"
    )
    order = models.IntegerField(default=0, verbose_name="ordre d'affichage")
    
    
    class Meta:
        verbose_name = "Programme d'événement"
        verbose_name_plural = "Programmes d'événements"
        ordering = ['date','start_time', 'order']
        def __str__(self):
            return f"{self.title} - {self.date.strftime('%d/%m/%Y')}"
 
 
class EventSubProgram(models.Model):
    program = models.ForeignKey(EventProgram, on_delete= models.CASCADE, related_name='sub_programs', verbose_name="programme parent")
    title = models.CharField(max_length=200, verbose_name="Titre de l'activité")
    description = models.TextField(blank=True , null=True, verbose_name="Description")
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(verbose_name="Heure de fin")
    speaker = models.CharField(max_length=100, blank=True, null=True, verbose_name="Intervenant/Responsable")
    location = models.CharField(max_length=200, blank=True, null=True,verbose_name="Lieu")
    order = models.IntegerField(default=0, verbose_name="ordre d'affichage")
    
    class Meta:
        verbose_name = "Sous-programme"
        verbose_name_plural = "Sous-programmes"
        ordering = ['start_time', 'order']
    
    def __str__(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.title}"
    
class EventAttendance(models.Model):
    notes = models.TextField(
        verbose_name="Notes",
        blank=True,
        null=True
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Événement"
    )
    member = models.ForeignKey(
        'membres.Member',
        on_delete=models.CASCADE,
        related_name='event_attendances',
        verbose_name="Membre"
    )
    is_present = models.BooleanField(default=False, verbose_name="Présent")
    check_in_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Heure d'arrivée"
    )
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Enregistré par"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Présence"
        verbose_name_plural = "Présences"
        unique_together = ['event', 'member']
        ordering = ['-check_in_time']
    
    def __str__(self):
        status = "✓ Présent" if self.is_present else "✗ Absent"
        return f"{self.member.get_full_name()} - {status}"
    

class WhatsAppNotification(models.Model):
    """
    Historique des notifications WhatsApp envoyées
    """
    RECIPIENT_TYPE_CHOICES = [
        ('all', 'Tous les membres'),
        ('group', 'Groupe spécifique'),
        ('individual', 'Membres individuels'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sending', 'En cours d\'envoi'),
        ('sent', 'Envoyé'),
        ('failed', 'Échoué'),
    ]
    
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='whatsapp_notifications',
        verbose_name="Événement"
    )
    recipient_type = models.CharField(
        max_length=20,choices=RECIPIENT_TYPE_CHOICES,
        verbose_name="Type de destinataires"
    )
    message = models.TextField(verbose_name="Message")
    
    # Destinataires
    groups = models.ManyToManyField(
        'membres.Group',  # Correction de la référence au modèle Group
        blank=True,
        verbose_name="Groupes"
    )
    
    individual_members = models.ManyToManyField(
        'membres.Member',
        blank=True,
        verbose_name="Membres individuels"
    )
    
 # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    total_recipients = models.IntegerField(default=0, verbose_name="Nombre de destinataires")
    successful_sends = models.IntegerField(default=0, verbose_name="Envois réussis")
    failed_sends = models.IntegerField(default=0, verbose_name="Envois échoués")
    
    # Métadonnées
    sent_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_whatsapp_notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Notification WhatsApp"
        verbose_name_plural = "Notifications WhatsApp"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"WhatsApp - {self.event.title} ({self.get_status_display()})"


class EventHistory(models.Model):
    """
    Historique des modifications d'un événement
    """
    ACTION_CHOICES = [
        ('created', 'Créé'),
        ('updated', 'Modifié'),
        ('published', 'Publié'),
        ('scheduled', 'Programmé'),
        ('cancelled', 'Annulé'),
        ('completed', 'Terminé'),
        ('notification_sent', 'Notification envoyée'),
    ]
    
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name="Événement"
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name="Action"
    )
    description = models.TextField(verbose_name="Description")
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Effectué par"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Historique"
        verbose_name_plural = "Historiques"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"