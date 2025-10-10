# finance/views.py

from decimal import InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import FinancialTransaction, TransactionCategory, Budget, FinancialReport
from membres.models import Member, Family, Group
from .forms import TransactionForm, CategoryForm, BudgetForm
import json
import openpyxl
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from io import BytesIO

@login_required
def transaction_list(request):
    """Liste des transactions financières"""
    if not request.user.has_finance_access():
        messages.error(request, 'Vous n\'avez pas l\'autorisation d\'accéder aux finances.')
        return redirect('dashboard:home')
    
    # Paramètres de recherche et filtre
    search_query = request.GET.get('search', '')
    transaction_type = request.GET.get('type', '')
    category_id = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    validated = request.GET.get('validated', '')
    
    # Base queryset
    transactions = FinancialTransaction.objects.select_related(
        'member', 'family', 'group', 'category', 'created_by', 'validated_by'
    )
    
    # Application des filtres
    if search_query:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(reference_number__icontains=search_query) |
            Q(member__first_name__icontains=search_query) |
            Q(member__last_name__icontains=search_query)
        )
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if category_id:
        transactions = transactions.filter(category_id=category_id)
    
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    
    if validated:
        transactions = transactions.filter(is_validated=(validated == 'true'))
    
    # Tri
    sort_by = request.GET.get('sort', '-date')
    transactions = transactions.order_by(sort_by, '-created_at')
    
    # Calcul des totaux
    totals = transactions.aggregate(
        total_income=Sum('amount', filter=Q(category__category_type='income')),
        total_expense=Sum('amount', filter=Q(category__category_type='expense'))
    )
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    categories = TransactionCategory.objects.filter(is_active=True)
    
    context = {
        'title': 'Transactions Financières',
        'transactions': page_obj,
        'categories': categories,
        'search_query': search_query,
        'transaction_type': transaction_type,
        'category_id': category_id,
        'date_from': date_from,
        'date_to': date_to,
        'validated': validated,
        'totals': totals,
        'total_count': paginator.count,
    }
    
    return render(request, 'finance/transaction_list.html', context)

@login_required
def transaction_add(request):
    """Ajouter une nouvelle transaction"""
    if not request.user.has_finance_access():
        messages.error(request, 'Vous n\'avez pas l\'autorisation d\'ajouter des transactions.')
        return redirect('finance:transaction_list')
    
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            
            # Auto-validation pour les administrateurs
            if request.user.role == 'admin':
                transaction.is_validated = True
                transaction.validated_by = request.user
                transaction.validated_at = timezone.now()
            
            transaction.save()
            messages.success(request, f'Transaction {transaction.transaction_id} enregistrée avec succès.')
            
            # Générer un reçu si demandé
            if request.POST.get('generate_receipt'):
                return redirect('finance:transaction_receipt', transaction_id=transaction.id)
            
            return redirect('finance:transaction_detail', transaction_id=transaction.id)
    else:
        form = TransactionForm()
    
    # Données pour les sélections
    members = Member.objects.filter(status='active').order_by('last_name', 'first_name')
    families = Family.objects.all().order_by('name')
    groups = Group.objects.all().order_by('name')
    
    context = {
        'title': 'Nouvelle Transaction',
        'form': form,
        'members': members,
        'families': families,
        'groups': groups,
    }
    
    return render(request, 'finance/transaction_form.html', context)

@login_required
def transaction_edit(request, transaction_id):
    """Modifier une transaction"""
    if not request.user.has_finance_access():
        messages.error(request, 'Vous n\'avez pas l\'autorisation de modifier des transactions.')
        return redirect('finance:transaction_list')
    
    transaction = get_object_or_404(FinancialTransaction, pk=transaction_id)
    
    # Vérifier si la transaction est validée
    if transaction.is_validated and request.user.role != 'admin':
        messages.error(request, 'Seul l\'administrateur peut modifier une transaction validée.')
        return redirect('finance:transaction_detail', transaction_id=transaction.id)
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, f'Transaction {transaction.transaction_id} modifiée avec succès.')
            return redirect('finance:transaction_detail', transaction_id=transaction.id)
    else:
        form = TransactionForm(instance=transaction)
    
    # Données pour les sélections
    members = Member.objects.filter(status='active').order_by('last_name', 'first_name')
    families = Family.objects.all().order_by('name')
    groups = Group.objects.all().order_by('name')
    
    context = {
        'title': f'Modifier Transaction {transaction.transaction_id}',
        'form': form,
        'transaction': transaction,
        'members': members,
        'families': families,
        'groups': groups,
    }
    
    return render(request, 'finance/transaction_form.html', context)

@login_required
def transaction_detail(request, transaction_id):
    """Détails d'une transaction"""
    if not request.user.has_finance_access():
        messages.error(request, 'Vous n\'avez pas l\'autorisation de voir les détails des transactions.')
        return redirect('dashboard:home')
    
    transaction = get_object_or_404(
        FinancialTransaction.objects.select_related(
            'member', 'family', 'group', 'category', 'created_by', 'validated_by'
        ),
        pk=transaction_id
    )
    
    context = {
        'title': f'Transaction {transaction.transaction_id}',
        'transaction': transaction,
    }
    
    return render(request, 'finance/transaction_detail.html', context)


@login_required
def transaction_delete(request, transaction_id):
    """Vue pour supprimer une transaction"""
    user = request.user
    
    # Vérifie l'accès (assume has_finance_access pour finance)
    if not user.has_finance_access():
        messages.warning(request, "Vous n'avez pas les droits pour supprimer une transaction.")
        return redirect('finance:transaction_list')
    
    transaction = get_object_or_404(FinancialTransaction, id=transaction_id)
    
    if request.method == "POST":
        transaction.delete()
        messages.success(request, f"La transaction '{transaction.transaction_id}' a été supprimée.")
        return redirect('finance:transaction_list')
    
    # GET : Affiche confirmation
    context = {
        'title': f'Supprimer {transaction.transaction_id}',
        'transaction': transaction,
    }
    return render(request, 'finance/transaction_delete.html', context)

@login_required
def transaction_validate(request, transaction_id):
    """Valider une transaction"""
    if not request.user.has_finance_access():
        messages.error(request, 'Vous n\'avez pas l\'autorisation de valider des transactions.')
        return redirect('finance:transaction_list')
    
    transaction = get_object_or_404(FinancialTransaction, pk=transaction_id)
    
    if transaction.is_validated:
        messages.warning(request, 'Cette transaction est déjà validée.')
    else:
        transaction.validate(request.user)
        messages.success(request, f'Transaction {transaction.transaction_id} validée avec succès.')
    
    return redirect('finance:transaction_detail', transaction_id=transaction.id)

@login_required
def transaction_receipt(request, transaction_id):
    """Générer un reçu pour une transaction"""
    if not request.user.has_finance_access():
        messages.error(request, 'Vous n\'avez pas l\'autorisation de générer des reçus.')
        return redirect('finance:transaction_list')
    
    transaction = get_object_or_404(FinancialTransaction, pk=transaction_id)
    
    # Génération du PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # En-tête
    from django.conf import settings
    church_config = settings.CHURCH_CONFIG
    
    header = Paragraph(f"<b>{church_config['NAME']}</b><br/>{church_config['ADDRESS']}<br/>{church_config['PHONE']} | {church_config['EMAIL']}", styles['Title'])
    elements.append(header)
    elements.append(Spacer(1, 20))
    
    # Titre
    title = Paragraph("<b>REÇU DE TRANSACTION</b>", styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Informations de la transaction
    data = [
        ['Numéro de transaction:', transaction.transaction_id],
        ['Date:', transaction.date.strftime('%d/%m/%Y')],
        ['Type:', transaction.get_transaction_type_display()],
        ['Montant:', f'{transaction.amount} {transaction.currency}'],
        ['Mode de paiement:', transaction.get_payment_method_display()],
    ]
    
    if not transaction.is_anonymous and transaction.member:
        data.append(['Contributeur:', transaction.member.get_full_name()])
    elif transaction.family:
        data.append(['Famille:', transaction.family.name])
    elif transaction.group:
        data.append(['Groupe:', transaction.group.name])
    
    if transaction.description:
        data.append(['Description:', transaction.description])
    
    # Tableau
    table = Table(data, colWidths=[150, 350])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # Signature
    if transaction.is_validated:
        validation_text = f"Validé par {transaction.validated_by.get_full_name()} le {transaction.validated_at.strftime('%d/%m/%Y à %H:%M')}"
        validation = Paragraph(validation_text, styles['Normal'])
        elements.append(validation)
    
    # Générer le PDF
    doc.build(elements)
    
    # Retourner le PDF
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recu_{transaction.transaction_id}.pdf"'
    
    return response



@login_required
def finance_dashboard(request):
    """Tableau de bord financier (version corrigée pour % budget)"""
    if not request.user.has_finance_access():
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder au tableau de bord financier.")
        return redirect('dashboard:home')

    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Statistiques du mois
    monthly_stats = FinancialTransaction.objects.filter(
        date__gte=month_start,
        is_validated=True
    ).aggregate(
        income=Sum('amount', filter=Q(category__category_type='income')),
        expense=Sum('amount', filter=Q(category__category_type='expense'))
    )

    monthly_income = float(monthly_stats['income'] or 0)
    monthly_expense = float(monthly_stats['expense'] or 0)
    monthly_balance = monthly_income - monthly_expense

    # Statistiques de l'année
    year_start = today.replace(month=1, day=1)
    yearly_stats = FinancialTransaction.objects.filter(
        date__gte=year_start,
        is_validated=True
    ).aggregate(
        income=Sum('amount', filter=Q(category__category_type='income')),
        expense=Sum('amount', filter=Q(category__category_type='expense'))
    )

    yearly_income = float(yearly_stats['income'] or 0)
    yearly_expense = float(yearly_stats['expense'] or 0)
    yearly_balance = yearly_income - yearly_expense

    # Top contributeurs du mois
    top_contributors = FinancialTransaction.objects.filter(
        date__gte=month_start,
        category__category_type='income',
        is_validated=True,
        is_anonymous=False
    ).values('member__first_name', 'member__last_name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]

    # Répartition par type de transaction
    transaction_breakdown = FinancialTransaction.objects.filter(
        date__gte=month_start,
        is_validated=True
    ).values('transaction_type').annotate(
        total=Sum('amount'),
        count=Count('id')
    )

    # Évolution mensuelle (6 derniers mois)
    monthly_evolution = []
    from datetime import timedelta
    for i in range(5, -1, -1):
        date = today - timedelta(days=30 * i)
        month_start_loop = date.replace(day=1)
        month_end = (month_start_loop + timedelta(days=32)).replace(day=1) - timedelta(days=1) if i != 0 else today

        stats = FinancialTransaction.objects.filter(
            date__gte=month_start_loop,
            date__lte=month_end,
            is_validated=True
        ).aggregate(
            income=Sum('amount', filter=Q(category__category_type='income')),
            expense=Sum('amount', filter=Q(category__category_type='expense'))
        )

        monthly_evolution.append({
            'month': month_start_loop.strftime('%B %Y'),
            'income': float(stats['income'] or 0),
            'expense': float(stats['expense'] or 0),
        })

    pending_transactions = FinancialTransaction.objects.filter(
        is_validated=False
    ).order_by('-created_at')[:10]

    current_budget = Budget.objects.filter(
        period='monthly',
        year=today.year,
        month=today.month,
        is_active=True
    ).first()

    # -------- Calcul du pourcentage du budget utilisé (robuste) --------
    percentage = 0.0            # valeur exacte (peut être >100)
    percentage_capped = 0.0     # valeur plafonnée à 100 pour la barre
    expected_expense_val = 0.0

    if current_budget:
        try:
            # convertit Decimal en float en toute sécurité
            expected_expense_val = float(current_budget.expected_income  or 0)
        except (TypeError, InvalidOperation):
            expected_expense_val = 0.0

        if expected_expense_val > 0:
            percentage = (monthly_expense / expected_expense_val) * 100
            percentage_capped = percentage if percentage <= 100 else 100.0
        else:
            percentage = 0.0
            percentage_capped = 0.0

    # arrondir pour l'affichage
    percentage_display = round(percentage, 2)
    percentage_capped_display = round(percentage_capped, 2)

    context = {
        'title': 'Tableau de Bord Financier',
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'monthly_balance': monthly_balance,
        'yearly_income': yearly_income,
        'yearly_expense': yearly_expense,
        'yearly_balance': yearly_balance,
        'top_contributors': top_contributors,
        'transaction_breakdown': list(transaction_breakdown),
        'monthly_evolution': json.dumps(monthly_evolution),
        'pending_transactions': pending_transactions,
        'current_budget': current_budget,
        'percentage': percentage_display,
        'percentage_capped': percentage_capped_display,
        'debug_budget_expected': expected_expense_val,
    }

    return render(request, 'finance/dashboard_finance.html', context)

    