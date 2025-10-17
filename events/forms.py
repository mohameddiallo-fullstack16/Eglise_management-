from django import forms
from django.core.exceptions import ValidationError
from .models import Event, EventProgram, EventSubProgram, EventAttendance, WhatsAppNotification

class EventForm(forms.ModelForm):
    """Formulaire de création/modification d'événement"""
    
    class Meta:
        model = Event
        fields = [
            'title', 'category', 'description', 'short_description',
            'cover_image', 'thumbnail', 'start_date', 'start_time',
            'end_date', 'end_time', 'location', 'adress', 'status',
            'organizer', 'watsapp_notifications_sent', 'watsapp_sent_at'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Ex: Cultes de Pâques'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 6
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 3
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Ex: Église de la Grâce'
            }),
            'adress': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': '123 Rue de l\'Église, Niamey'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'organizer': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'watsapp_notifications_sent': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 focus:ring-indigo-500'
            }),
            'watsapp_sent_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError("La date de fin doit être après la date de début.")
        
        if start_date and end_date and start_date == end_date:
            if start_time and end_time and end_time <= start_time:
                raise ValidationError("L'heure de fin doit être après l'heure de début.")
        
        return cleaned_data
    
class EventProgramForm(forms.ModelForm):
 

    class Meta:
        model = EventProgram
        fields = ['title', 'description', 'date', 'start_time', 'end_time', 'location', 'order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg',
                'placeholder': 'Titre du programme'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg',
                'rows': 3,
                'placeholder': 'Description du programme (optionnel)'
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg',
                'placeholder': 'Lieu (optionnel)'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg',
                'placeholder': 'Ordre d’affichage'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        date = cleaned_data.get('date')

        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("L'heure de fin doit être après l'heure de début.")
        if not date:
            raise forms.ValidationError("La date est obligatoire.")
        return cleaned_data
    
    # events/forms.py
from django import forms
from .models import WhatsAppNotification
from membres.models import Group, Member

class WhatsAppNotificationForm(forms.ModelForm):
    class Meta:
        model = WhatsAppNotification
        fields = ['recipient_type', 'groups', 'individual_members', 'message']
        widgets = {
            'recipient_type': forms.Select(attrs={'class': 'form-select'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'individual_members': forms.SelectMultiple(attrs={'class': 'form-multiselect'}),
            'message': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Facultatif : masquer les champs qui ne sont pas pertinents selon recipient_type
        self.fields['groups'].queryset = Group.objects.all()
        self.fields['individual_members'].queryset = Member.objects.all()
