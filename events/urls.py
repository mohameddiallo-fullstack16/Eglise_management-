# events/urls.py (version nettoyée et corrigée)

from django.urls import path
from . import views

app_name = 'events'  # Namespace pour éviter conflits

urlpatterns = [
    # Liste des événements
    path('', views.Eventlist.as_view(), name='event_list'),
    path('create/', views.event_manage_view, name='event_create'),
    # Détail d'un événement
    path('<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('<slug:slug>/edit/', views.EventUpdate.as_view(), name='event_edit'),

    path('delete/<int:pk>/', views.EventDelete.as_view(), name='event_delete'),
    
    # Gestion des programmes/sous-programmes
    path('program/<slug:event_slug>/manage/', views.program_manage_view, name='program_manage'),
    path('program/<int:program_pk>/delete/', views.program_delete_view, name='program_delete'),
   
    # Présences (attendance)
    path('<int:event_pk>/attendance/', views.attendance_list_view, name='attendance_list'),
    path('<int:event_pk>/attendance/add/', views.attendance_add_members_view, name='attendance_add_members'),
    path('<int:event_pk>/attendance/<int:member_pk>/mark/', views.attendance_mark_view, name='attendance_mark'),
    
    
    # Export présence
    path('<int:event_pk>/attendance/export/', views.attendance_export_view, name='attendance_export'),
    
    # Notifications WhatsApp
    path('<int:event_pk>/whatsapp/', views.watsapp_notification_view, name='whatsapp_notification'),
    
    # Historique
    path('<int:event_pk>/history/', views.event_history_view, name='event_history'),
]