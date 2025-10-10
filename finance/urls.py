from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.finance_dashboard, name='dashboard'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/add/', views.transaction_add, name='transaction_add'),
    path('transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:transaction_id>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:transaction_id>/validate/', views.transaction_validate, name='transaction_validate'),
    path('transactions/<int:transaction_id>/receipt/', views.transaction_receipt, name='transaction_receipt'),
    path('transactions/<int:transaction_id>/delete/', views.transaction_delete, name='transaction_delete'),  
]