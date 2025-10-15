from django.urls import path
from django.views.generic import CreateView  # ← Sans 's' à la fin
from  .import views

app_name = 'events'

urlpatterns = [
    path('', views.Eventlist.as_view(), name='event_list'), 
    path('attendance/export/<int:event_pk>/', views.attendance_export_view, name='attendance_export'),
    path('<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('<int:pk>/edit/', views.EventUpdate.as_view(), name='event_update'),
    path('create/', views.EventCreate.as_view(), name='event_create'),
    path('delete/<int:pk>/', views.EventDelete.as_view(), name='event_delete'),
    path('attendance/mark/<int:event_pk>/<int:member_pk>/', views.attendance_mark_view, name='attendance_mark'),
    path('<int:event_pk>/attendance/', views.attendance_list_view, name='event_attendance_list'),
    path('<int:event_pk>/attendance/add/', views.attendance_mark_view, name='attendance_add_members'),
    path('<int:event_pk>/attendance/<int:member_pk>/mark/', views.attendance_mark_view, name='attendance_mark'),
    path('<int:event_pk>/attendance/export/', views.attendance_export_view, name='attendance_export'),
    path('<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('create/', views.EventCreate.as_view(), name='event_create'),
    path('delete/<int:pk>/', views.EventDelete.as_view(), name='event_delete'),
    path('<int:event_pk>/programs/', views.subprogram_manage_view, name='subprogram_manage'),
    #path('program/<int:program_pk>/delete/', views.EventDelete, name='program_delete'),
    path('program/<int:program_pk>/subprograms/', views.subprogram_manage_view, name='subprogram_manage'),
    #path('subprogram/<int:subprogram_pk>/delete/', views.subprogram_delete_view, name='subprogram_delete'),
    path('<int:event_pk>/whatsapp/', views.watsapp_notification_view, name='whatsapp_notification'),
    path('<int:event_pk>/history/', views.EventHistory, name='event_history'),
]