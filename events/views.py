
import csv
from datetime import date
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .forms import Event, EventForm, EventProgram, EventSubProgram, WhatsAppNotification,EventProgramForm, WhatsAppNotificationForm
from urllib import response
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from .models import *
from django.views.generic import ListView as listViews
from django.db.models import Q
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from membres.models import Member
from django import forms



class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
class Eventlist(listViews):
    model = Event
    template_name ='events/events_list.html'
    context_object_name= 'events'
    paginate_by = 12

    def get_queryset(self):
        queryset = Event.objects.filter(status__in=['published', 'scheduled', 'ongoing'])
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__id=category)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        return queryset.select_related('category', 'organizer')
    
    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['categories'] = EventCategory.objects.filter(is_active=True)
            context['upcoming_count'] = Event.objects.filter(
                status__in=['published', 'scheduled'],
                start_date__gte=date.today()
            ).count()
            return context

class EventDetailView(DetailView):
    model = Event
    template_name = 'events/events_detail.html'
    context_object_name = 'event'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        # Optimisation globale : prefetch pour relations reverse, select pour forward
        return Event.objects.prefetch_related(
            'attendances__member',
            'attendances__recorded_by',
            'programs__sub_programs'
        ).select_related('organizer')  # Ex. si forward 'organizer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object  # self.object est bien reconnu

        # Programmes liés (prefetch déjà fait dans queryset)
        context['programs'] = event.programs.all()

        # Statistiques de présence
        context['attendances_count'] = event.get_attendances_count()
        context['total_expected'] = event.get_total_expected()

        # Attendances (corrigé : prefetch_related pour reverse ManyToOne)
        context['attendances'] = event.attendances.prefetch_related('member', 'recorded_by').all()

        # Vérifier si l'utilisateur est inscrit
        if self.request.user.is_authenticated:
            try:
                member = self.request.user.member_profile
                context['user_attendance'] = EventAttendance.objects.filter(
                    event=event,
                    member=member
                ).first()
            except:
                context['user_attendance'] = None

        # Historique (admin seulement – corrigé : prefetch si reverse)
        if self.request.user.is_authenticated and self.request.user.has_admin_access:
            context['history'] = event.history.prefetch_related('performed_by').all()[:10]  # Corrigé pour reverse

        return context





@login_required
def event_manage_view(request, event_slug=None):
    """Vue pour créer ou modifier un événement (admin only)"""
    if not request.user.has_admin_access():  # Vérifie admin
        messages.error(request, "Accès non autorisé.")
        return redirect('events:event_list')
    
    event = get_object_or_404(Event, slug=event_slug) if event_slug else None

    form = EventForm(request.POST or None, request.FILES or None, instance=event)
    
    if request.method == 'POST':
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.created_by = request.user
            event.save()
            messages.success(request, f"Événement {'modifié' if event_slug else 'créé'} avec succès.")
            return redirect('events:event_detail', slug=event.slug)
        else:
            messages.error(request, "Erreur dans le formulaire.")
    
    context = {
        'form': form,
        'title': f"{'Modifier' if event_slug else 'Créer'} un événement",
        'event': event
    }
    return render(request, 'events/events_create.html', context)
    
class EventUpdate(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name ='events/events_create.html'

    def form_valid(self, form):
        response = super().form_valid(form)

        EventHistory.objects.create(
            event=self.object,
            action='updated',
        description=f"Evenement mis à jour : {self.object.title}",
        performed_by=self.request.user
    )
        messages.success(self.request, f'Evenement "{self.object.title}" mis à jour avec succès.')
        return response
    
    def get_success_url(self):
        return reverse_lazy('events:event_detail', kwargs={'slug': self.object.slug})
    
class EventDelete(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Event
    template_name ='events/events_delete.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(self.request, f'Evenement "{self.object.title}" supprimé avec succès.')
        return redirect('events:event_list')


@login_required
def program_manage_view(request, event_slug):
    """Vue pour gérer les programmes d'un événement (liste + ajout)"""
    if not request.user.has_admin_access():
        messages.error(request, "Accès non autorisé")
        return redirect('events:event_list')

    # Récupérer l'événement
    event = get_object_or_404(Event, slug=event_slug)
    programs = event.programs.all().order_by('order', 'date', 'start_time')

    if request.method == 'POST':
        form = EventProgramForm(request.POST)
        if form.is_valid():
            # Création du programme lié à l'événement
            program = form.save(commit=False)
            program.event = event
            program.save()
            messages.success(request, "Programme ajouté avec succès.")
            return redirect('events:program_manage', event_slug=event.slug)
        else:
            messages.error(request, "Erreur : veuillez corriger les champs ci-dessous.")
    else:
        form = EventProgramForm()

    context = {
        'event': event,
        'programs': programs,
        'form': form,
    }
    return render(request, 'events/program_manage.html', context)

@login_required
def program_delete_view(request, program_pk):
    """Supprimer un programme (admin seulement)"""
    if not request.user.has_admin_access():
        messages.error(request, "Accès non autorisé")
        return redirect('events:event_list')

    program = get_object_or_404(EventProgram, pk=program_pk)
    event_slug = program.event.slug  # On récupère le slug de l'événement parent
    program.delete()
    messages.success(request, f'Programme "{program.title}" supprimé avec succès.')
    return redirect('events:program_manage', event_slug=event_slug)


@login_required
def attendance_list_view(request, event_pk):
    if not request.user.has_admin_access():
        messages.error(request,"Accès non autorisé")
        return redirect('events:event_list')
    
    event = get_object_or_404(Event, pk=event_pk)
    attendance = event.attendances.select_related('member','recorded_by').all()
    total = attendance.count()
    present = attendance.filter(is_present=True).count()
    absent = total - present
    context = {
        'event': event,
        'attendances': attendance,
        'total': total,
        'present': present,
        'absent': absent,
        'rate': round((present / total * 100) if total > 0 else 0, 2)
    }
    return render (request, 'events/attendance_list.html', context)
    

@login_required
def attendance_mark_view(request, event_pk, member_pk):
    if not request.user.has_admin_access:
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    event = get_object_or_404(Event, pk=event_pk)
    member = get_object_or_404(Member, pk=member_pk)
    
    attendance, created = EventAttendance.objects.get_or_create(
        event=event,
        member=member,
        defaults={
            'recorded_by': request.user,
            'is_present':True,
            'check_in_time': timezone.now()
        }
    )
    if not created:
        # Basculer la présence
        attendance.is_present = not attendance.is_present
        if attendance.is_present:
            attendance.check_in_time = timezone.now()
        attendance.recorded_by = request.user
    attendance.save()

    return JsonResponse({
        'success': True,
        'is_present': attendance.is_present,
        'member_name': member.get_full_name()
    })
    

@login_required
def attendance_add_members_view(request, event_pk):
    """Ajouter des membres à la liste de présence"""
    if not request.user.has_admin_access():
        messages.error(request, "Accès non autorisé.")
        return redirect('events:event_list')
    
    event = get_object_or_404(Event, pk=event_pk)
    
    if request.method == 'POST':
        member_ids = request.POST.getlist('members')
        from membres.models import Member
        
        for member_id in member_ids:
            member = Member.objects.get(pk=member_id)
            EventAttendance.objects.get_or_create(
                event=event,
                member=member,
                defaults={'recorded_by': request.user}
            )
        
        messages.success(request, f'{len(member_ids)} membre(s) ajouté(s) à la liste.')
        return redirect('events:attendance_list', event_pk=event.pk)
    
    # Membres déjà dans la liste
    existing_ids = event.attendances.values_list('member_id', flat=True)
    from membres.models import Member
    available_members = Member.objects.exclude(id__in=existing_ids)
    
    context = {
        'event': event,
        'members': available_members,
    }
    return render(request, 'events/attendance_add.html', context)

@login_required
def watsapp_notification_view(request, event_pk):
    if not request.user.has_admin_access():
        messages.error(request, "Accès non autorisé.")
        return redirect('events:event_list')

    event = get_object_or_404(Event, pk=event_pk)

    if request.method == 'POST':
        form = WhatsAppNotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.event = event
            notification.sent_by = request.user
            notification.save()
            form.save_m2m()

            # Calcul des destinataires
            total = 0
            if notification.recipient_type == 'all':
                total = Member.objects.filter(phone__isnull=False).count()
            elif notification.recipient_type == 'group':
                for group in notification.groups.all():
                    total += group.members.filter(phone__isnull=False).count()
            elif notification.recipient_type == 'individual':
                total = notification.individual_members.filter(phone__isnull=False).count()
            notification.total_recipients = total
            notification.save()

            # Historique
            EventHistory.objects.create(
                event=event,
                action='notification_sent',
                description=f"Notification WhatsApp envoyée à {total} destinataire(s)",
                performed_by=request.user
            )

            messages.success(request, f'Notification programmée pour {total} destinataire(s).')
            return redirect('events:event_detail', slug=event.slug)

    else:
        # Pré-remplir message par défaut
        default_message = f"""🎉 *{event.title}*

📅 Date: {event.start_date.strftime('%d/%m/%Y')}
⏰ Heure: {event.start_time.strftime('%H:%M')}
📍 Lieu: {event.location}

{event.short_description}

Nous vous attendons nombreux !
"""
        form = WhatsAppNotificationForm(initial={'message': default_message})

    context = {
        'event': event,
        'form': form,
    }
    return render(request, 'events/whatsapp_notification.html', context)

@login_required
def event_history_view(request, event_pk):
    event = get_object_or_404(Event, pk=event_pk)
    history = event.history.all()  # Utilise le related_name défini sur EventHistory

    context = {
        'event': event,
        'history': history,
    }
    return render(request, 'events/event_history.html', context)


def attendance_export_view(request, event_pk):
    if not request.user.has_admin_access():
        messages.error(request, "Accès non autorisé.")
        return redirect('events:event_list')

    event = get_object_or_404(Event, pk=event_pk)
    attendances = EventAttendance.objects.filter(event=event).select_related('member')

    # Création du fichier CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{event.slug}.csv"'

    writer = csv.writer(response)
    # En-tête
    writer.writerow(['Nom', 'Prénom', 'Présent', 'Heure d’arrivée', 'Notes'])

    for attendance in attendances:
        writer.writerow([
            attendance.member.last_name,
            attendance.member.first_name,
            'Oui' if attendance.is_present else 'Non',
            attendance.check_in_time.strftime('%d/%m/%Y %H:%M') if attendance.check_in_time else '',
            attendance.notes or ''
        ])

    return response