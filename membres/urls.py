from django.urls import path
from . import views
from .models import Group  # ✅ correction de l'import

app_name = 'membres'

urlpatterns = [
    # Membres
    path('members/', views.member_list, name='list'),
    path('add/', views.member_add, name='add'),
    path('export/', views.export_members, name='export'),
   

    path('members/<int:member_id>/', views.member_detail, name='detail'),  # <-- 'member_id' correspond à la vue
    path('<int:member_id>/edit/', views.member_edit, name='edit'),
    path('<int:member_id>/delete/', views.member_delete, name='delete'),
    path('<int:member_id>/generate-card/', views.generate_card, name='generate_card'),
    path('my-profile/', views.my_profile, name='my_profile'),
    
    # Ministères
    path('ministries/', views.ministry_list, name='ministry_list'),
    path('ministries/add/', views.ministry_add, name='ministry_add'),
    path('ministries/<int:ministry_id>/edit/', views.ministry_edit, name='ministry_edit'),
    path('ministries/<int:ministry_id>/delete/', views.ministry_delete, name='ministry_delete'),  # <-- nouvelle URL
    
    # Groupes
    path('groups/', views.group_list, name='group_list'),
    path('groups/add/', views.group_add, name='group_add'),
    path('groups/<int:group_id>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:group_id>/delete/', views.group_delete, name='group_delete'),

    
    # Familles
    path('families/', views.family_list, name='family_list'),
    path('families/add/', views.family_add, name='family_add'),
    path('families/<int:family_id>/', views.family_detail, name='family_detail'),
    path('families/<int:family_id>/edit/', views.family_edit, name='family_edit'),
    path('families/<int:family_id>/delete/', views.family_delete, name='family_delete'),
    
    # Présences
    path('attendance/mark/', views.attendance_mark, name='attendance_mark'),
]
