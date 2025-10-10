from django.urls import path
from django.views.generic import CreateView  # ← Sans 's' à la fin
from  .import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_views, name='login'),
    path('logout/', views.logout_views, name='logout'),
    path('register/', views.RegistrerViews.as_view(), name='register'),  # Correction du nom de la route
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_views, name='change_password'),
    path('users/', views.user_list_view, name='user_list'),  
    path('users/<int:user_id>/toggle_status/', views.toggle_user_status, name='toggle_user_status'), 
    path('users/<int:user_id>/assign-role/', views.assign_role, name='assign_role'),
    path('users/<int:user_id>/validate/', views.validate_user, name='validate_user'),  
]