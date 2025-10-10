# finance/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from membres.models import Member, Family, Group

class TransactionCategory(models.Model):
    """Catégories de transactions financières"""
    
    CATEGORY_TYPE_CHOICES = [
        ('income', 'Recette'),
        ('expense', 'Dépense'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='Nom de la catégorie')
    category_type = models.CharField(
        max_length=10,
        choices=CATEGORY_TYPE_CHOICES,
        verbose_name='Type'
    )
    description = models.TextField(blank=True, verbose_name='Description')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Catégorie de transaction'
        verbose_name_plural = 'Catégories de transactions'
        ordering = ['category_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"

class FinancialTransaction(models.Model):
    """Modèle pour toutes les transactions financières"""
    
    TRANSACTION_TYPE_CHOICES = [
        ('tithe', 'Dîme'),
        ('offering', 'Offrande'),
        ('donation', 'Don'),
        ('contribution', 'Cotisation'),
        ('special', 'Collecte spéciale'),
        ('expense', 'Dépense'),
        ('other', 'Autre'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('check', 'Chèque'),
        ('transfer', 'Virement'),
        ('mobile', 'Mobile Money'),
        ('other', 'Autre'),
    ]
    
    # Informations de base
    transaction_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='ID Transaction'
    )
    date = models.DateField(
        default=timezone.now,
        verbose_name='Date'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name='Type de transaction'
    )
    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Catégorie'
    )
    
    # Montant
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Montant'
    )
    currency = models.CharField(
        max_length=3,
        default='XOF',
        verbose_name='Devise'
    )
    
    # Contributeur (optionnel pour les dons anonymes)
    member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Membre'
    )
    family = models.ForeignKey(
        Family,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Famille'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Groupe'
    )
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name='Don anonyme'
    )
    
    # Détails de paiement
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
        verbose_name='Mode de paiement'
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Numéro de référence'
    )
    
    # Description et notes
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Numéro de reçu'
    )
    
    # Validation
    is_validated = models.BooleanField(
        default=False,
        verbose_name='Validé'
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_transactions',
        verbose_name='Validé par'
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date de validation'
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_transactions',
        verbose_name='Créé par'
    )
    
    class Meta:
        verbose_name = 'Transaction financière'
        verbose_name_plural = 'Transactions financières'
        ordering = ['-date', '-created_at']
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            # Génération de l'ID unique de transaction
            year = timezone.now().year
            month = timezone.now().month
            last_transaction = FinancialTransaction.objects.filter(
                transaction_id__startswith=f'T{year}{month:02d}'
            ).order_by('-transaction_id').first()
            
            if last_transaction:
                last_number = int(last_transaction.transaction_id[7:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.transaction_id = f'T{year}{month:02d}{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        contributor = "Anonyme"
        if not self.is_anonymous:
            if self.member:
                contributor = self.member.get_full_name()
            elif self.family:
                contributor = f"Famille {self.family.name}"
            elif self.group:
                contributor = self.group.name
        
        return f"{self.transaction_id} - {contributor} - {self.amount} {self.currency}"
    
    def validate(self, user):
        """Valide la transaction"""
        self.is_validated = True
        self.validated_by = user
        self.validated_at = timezone.now()
        self.save()


class Budget(models.Model):
    """Modèle pour la gestion des budgets"""
    
    PERIOD_CHOICES = [
        ('monthly', 'Mensuel'),
        ('quarterly', 'Trimestriel'),
        ('annual', 'Annuel'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Nom du budget')
    period = models.CharField(
        max_length=20,
        choices=PERIOD_CHOICES,
        verbose_name='Période'
    )
    year = models.IntegerField(verbose_name='Année')
    month = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Mois'
    )
    quarter = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Trimestre'
    )
    
    # Montants prévus
    expected_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Recettes prévues'
    )
    expected_expense = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Dépenses prévues'
    )
    
    # Notes
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    
    # Statut
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Créé par'
    )
    
    class Meta:
        verbose_name = 'Budget'
        verbose_name_plural = 'Budgets'
        ordering = ['-year', '-month']
        unique_together = ['period', 'year', 'month', 'quarter']
    
    def __str__(self):
        if self.period == 'monthly':
            return f"{self.name} - {self.month}/{self.year}"
        elif self.period == 'quarterly':
            return f"{self.name} - Q{self.quarter}/{self.year}"
        else:
            return f"{self.name} - {self.year}"
    
    def get_actual_income(self):
        """Calcule les recettes réelles pour la période"""
        from django.db.models import Sum

        qs = FinancialTransaction.objects.filter(
            category__category_type='income',
            is_validated=True
        )
        if self.period == 'monthly':
            qs = qs.filter(date__year=self.year, date__month=self.month)
        elif self.period == 'quarterly':
            start_month = (self.quarter - 1) * 3 + 1
            end_month = self.quarter * 3
            qs = qs.filter(date__year=self.year, date__month__gte=start_month, date__month__lte=end_month)
        else:  # annuel
            qs = qs.filter(date__year=self.year)
        
        return qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    def get_actual_expense(self):
        """Calcule les dépenses réelles pour la période"""
        from django.db.models import Sum

        qs = FinancialTransaction.objects.filter(
            category__category_type='expense',
            is_validated=True
        )
        if self.period == 'monthly':
            qs = qs.filter(date__year=self.year, date__month=self.month)
        elif self.period == 'quarterly':
            start_month = (self.quarter - 1) * 3 + 1
            end_month = self.quarter * 3
            qs = qs.filter(date__year=self.year, date__month__gte=start_month, date__month__lte=end_month)
        else:  # annuel
            qs = qs.filter(date__year=self.year)
        
        return qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    def get_variance_income(self):
        """Calcule la variance des recettes"""
        return self.get_actual_income() - self.expected_income
    
    def get_variance_expense(self):
        """Calcule la variance des dépenses"""
        return self.get_actual_expense() - self.expected_expense
    
    def generate_report_data(self):
        """Retourne un dict JSON prêt à être utilisé pour FinancialReport.report_data"""
        return {
            "expected_income": float(self.expected_income),
            "expected_expense": float(self.expected_expense),
            "actual_income": float(self.get_actual_income()),
            "actual_expense": float(self.get_actual_expense()),
            "variance_income": float(self.get_variance_income()),
            "variance_expense": float(self.get_variance_expense())
        }


class FinancialReport(models.Model):
    """Modèle pour les rapports financiers"""
    
    REPORT_TYPE_CHOICES = [
        ('monthly', 'Mensuel'),
        ('quarterly', 'Trimestriel'),
        ('annual', 'Annuel'),
        ('custom', 'Personnalisé'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='Titre du rapport')
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        verbose_name='Type de rapport'
    )
    start_date = models.DateField(verbose_name='Date de début')
    end_date = models.DateField(verbose_name='Date de fin')
    
    # Résumé financier
    total_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Total des recettes'
    )
    total_expense = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Total des dépenses'
    )
    net_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Solde net'
    )
    
    # Contenu du rapport
    report_data = models.JSONField(default=dict, blank=True, verbose_name='Données du rapport')
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    
    # Fichier généré
    pdf_file = models.FileField(
        upload_to='reports/financial/',
        null=True,
        blank=True,
        verbose_name='Fichier PDF'
    )
    
    # Métadonnées
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Généré par'
    )
    
    class Meta:
        verbose_name = 'Rapport financier'
        verbose_name_plural = 'Rapports financiers'
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.title} ({self.start_date} - {self.end_date})"
    
def generate_report_data(self):
    from finance.models import FinancialTransaction
    from django.db.models import Sum

    # Filtrer les transactions de la période
    if self.period == 'monthly':
        transactions = FinancialTransaction.objects.filter(
            date__year=self.year,
            date__month=self.month,
            is_validated=True
        )
    elif self.period == 'quarterly':
        start_month = (self.quarter - 1) * 3 + 1
        end_month = self.quarter * 3
        transactions = FinancialTransaction.objects.filter(
            date__year=self.year,
            date__month__gte=start_month,
            date__month__lte=end_month,
            is_validated=True
        )
    else:
        transactions = FinancialTransaction.objects.filter(
            date__year=self.year,
            is_validated=True
        )

    # Résumé par catégorie
    report_data = {}
    for category in transactions.values_list('category__name', flat=True).distinct():
        cat_income = transactions.filter(category__name=category, category__category_type='income').aggregate(total=Sum('amount'))['total'] or 0
        cat_expense = transactions.filter(category__name=category, category__category_type='expense').aggregate(total=Sum('amount'))['total'] or 0
        report_data[category] = {"income": float(cat_income), "expense": float(cat_expense)}

    return report_data
