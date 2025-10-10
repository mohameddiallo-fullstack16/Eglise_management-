from django.contrib import admin
from .models import *

# Enregistrement simple des modèles
admin.site.register(TransactionCategory)
admin.site.register(FinancialTransaction)
admin.site.register(Budget)
admin.site.register(FinancialReport)
