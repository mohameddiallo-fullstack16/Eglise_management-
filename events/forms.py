from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Event, EventProgram, EventSubProgram,
    EventAttendance, WhatsAppNotification
)


class EventForm(forms.ModelForm):
    """Formulaire de création/modification d'événement"""
    
    class Meta:
        model = Event
        fields = [
            'title', 'category', 'description', 'short_description',
            'cover_image', 'thumbnail',
            'start_date', 'start_time', 'end_date', 'end_time',
            'location', 'status', 
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'category': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'rows': 6}),
            'short_description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2 border rounded-lg'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-2 border rounded-lg'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2 border rounded-lg'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-2 border rounded-lg'}),
            'location': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'status': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Vérifier que la date de fin est après la date de début
        if start_date and end_date and end_date < start_date:
            raise ValidationError("La date de fin doit être après la date de début.")
        
        # Si même jour, vérifier les heures
        if start_date and end_date and start_date == end_date:
            if start_time and end_time and end_time <= start_time:
                raise ValidationError("L'heure de fin doit être après l'heure de début.")
        
        return cleaned_data


class EventProgramForm(forms.ModelForm):
    """Formulaire pour ajouter un programme"""
    
    class Meta:
        model = EventProgram
        fields = ['title', 'description', 'date', 'start_time', 'end_time', 'location', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'placeholder': 'Ex: Jour 1 - Matinée'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'rows': 3}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2 border rounded-lg'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-2 border rounded-lg'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-2 border rounded-lg'}),
            'location': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'placeholder': 'Optionnel'}),
            'order': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'value': 0}),
        }


class EventSubProgramForm(forms.ModelForm):
    """Formulaire pour ajouter un sous-programme (activité)"""
    
    class Meta:
        model = EventSubProgram
        fields = ['title', 'description', 'start_time', 'end_time', 'speaker', 'location', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'placeholder': 'Ex: Louange et Adoration'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'rows': 2, 'placeholder': 'Optionnel'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-2 border rounded-lg'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-2 border rounded-lg'}),
            'speaker': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'placeholder': 'Ex: Pasteur Jean'}),
            'location': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'placeholder': 'Optionnel'}),
            'order': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'value': 0}),
        }


class EventAttendanceForm(forms.ModelForm):
    """Formulaire pour enregistrer une présence"""
    
    class Meta:
        model = EventAttendance
        fields = ['is_present', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'rows': 2}),
        }


class WhatsAppNotificationForm(forms.ModelForm):
    """Formulaire pour envoyer une notification WhatsApp"""
    
    class Meta:
        model = WhatsAppNotification
        fields = [
            'recipient_type', 'message',
            'groups', 'individual_members'
        ]
        widgets = {
            'recipient_type': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'rows': 8,
                'placeholder': 'Rédigez votre message...'
            }),
            'groups': forms.SelectMultiple(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'size': 5}),
            'individual_members': forms.SelectMultiple(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'size': 10}),
        }
    
    def clean_message(self):
        message = self.cleaned_data.get('message')
        if len(message) < 10:
            raise ValidationError("Le message doit contenir au moins 10 caractères.")
        return message