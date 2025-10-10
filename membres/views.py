from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import random
import string
from tkinter import Canvas
from urllib import request
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from accounts.models import User
from .models import Member, Ministry, Group, Family, Attendance
from .forms import AttendanceForm, MemberForm, MinistryForm, GroupForm, FamilyForm
from .utils import generate_member_card
from finance.models import FinancialTransaction
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode
import csv
from django.template.loader import render_to_string
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
import csv
from datetime import datetime


@login_required
def dashboard_home(request):
    """Vue tableau de bord dynamique selon le rôle"""
    user = request.user
    today = timezone.now().date()
    member = None
    if hasattr(user, 'member'):
        member = user.member
    context = {'title': 'Tableau de Bord', 'user': user ,'member': member, 'today': today}

    # ======== Gestion des accès =========
    if user.has_admin_access() or user.has_membres_management_access():
        # ---- STATISTIQUES GLOBALES ----
        context.update({
            'has_admin_access': True,
            'total_members': Member.objects.filter(status='active').count(),
            'new_members_month': Member.objects.filter(
                membership_date__year=timezone.now().year,
                membership_date__month=timezone.now().month,
                status='active'
            ).count(),
            'total_families': Family.objects.count(),
            'total_ministries': Ministry.objects.count(),
            'total_groups': Group.objects.count(),
        })

        # ---- Statistiques par genre ----
        gender_stats = Member.objects.filter(status='active').values('gender').annotate(count=Count('id'))
        context['gender_stats'] = list(gender_stats)

        # ---- Statistiques par tranche d'âge ----
        age_groups = {
            'Enfants (0-12)': 0,
            'Adolescents (13-17)': 0,
            'Jeunes Adultes (18-24)': 0,
            'Adultes (25-64)': 0,
            'Seniors (65+)': 0
        }
        members_with_age = Member.objects.filter(status='active').exclude(date_of_birth__isnull=True)
        for member in members_with_age:
            age = member.get_age()
            if age <= 12:
                age_groups['Enfants (0-12)'] += 1
            elif age <= 17:
                age_groups['Adolescents (13-17)'] += 1
            elif age <= 24:
                age_groups['Jeunes Adultes (18-24)'] += 1
            elif age <= 64:
                age_groups['Adultes (25-64)'] += 1
            else:
                age_groups['Seniors (65+)'] += 1
        context['age_groups'] = age_groups

        # ---- Statistiques financières (si droit finance) ----
        if user.has_finance_access():
            current_month = timezone.now().replace(day=1)
            monthly_income = FinancialTransaction.objects.filter(
                date__gte=current_month,
                category__category_type='income',
                is_validated=True
            ).aggregate(total=Sum('amount'))['total'] or 0

            monthly_expense = FinancialTransaction.objects.filter(
                date__gte=current_month,
                category__category_type='expense',
                is_validated=True
            ).aggregate(total=Sum('amount'))['total'] or 0

            context['financial_stats'] = {
                'monthly_income': monthly_income,
                'monthly_expense': monthly_expense,
                'balance': monthly_income - monthly_expense,
            }
            context['has_finance_access'] = True
        else:
            context['has_finance_access'] = False

        # ---- Activités récentes ----
        context['recent_members'] = Member.objects.filter(status='active').order_by('-created_at')[:5]
        if user.has_finance_access():
            context['recent_transactions'] = FinancialTransaction.objects.filter(
                is_validated=True
            ).order_by('-date')[:5]

        context['recent_attendances'] = Attendance.objects.select_related('member').order_by('-date')[:10]
        context['upcoming_birthdays'] = get_upcoming_birthdays(10)

    # ======== Utilisateur simple (membre) =========
    elif hasattr(user, 'member_profile'):
        member = user.member_profile
        context.update({
            'has_admin_access': False,
            'has_finance_access': False,
            'member': member,
            'recent_attendances': Attendance.objects.filter(member=member).order_by('-date')[:10],
            'upcoming_birthdays': get_upcoming_birthdays(10),  # Optionnel, selon besoin
        })

    # ======== Cas utilisateur sans profil =========
    else:
        messages.warning(
            request,
            'Votre profil membre n\'est pas encore créé. Veuillez contacter l\'administrateur.'
        )
        return redirect('accounts:profile')

    return render(request, 'members/dashboard.html', context)


def get_upcoming_birthdays(limit=10):
    """Récupère les prochains anniversaires"""
    today = timezone.now().date()
    current_year = today.year

    members = Member.objects.filter(status='active').exclude(date_of_birth__isnull=True)
    birthdays = []

    for member in members:
        # Cas 29 février pour années non bissextiles
        try:
            birthday_this_year = member.date_of_birth.replace(year=current_year)
        except ValueError:
            birthday_this_year = member.date_of_birth.replace(year=current_year, day=28)

        if birthday_this_year < today:
            birthday_this_year = birthday_this_year.replace(year=current_year + 1)

        days_until = (birthday_this_year - today).days
        age_on_birthday = member.get_age() + (1 if birthday_this_year.year > current_year else 0)

        birthdays.append({
            'member': member,
            'date': birthday_this_year,
            'days_until': days_until,
            'age': age_on_birthday
        })

    birthdays.sort(key=lambda x: x['days_until'])
    return birthdays[:limit]

@login_required
def member_list(request):
    """Liste des membres avec filtres et recherche"""
    if not request.user.has_membres_management_access():
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('dashboard')

    members = Member.objects.all().order_by('-created_at')
    context = {
        'members': members,
        'title': 'Liste des Membres',
        'has_membres_management_access': request.user.has_membres_management_access(),  # pour le template
    }
    
    
    # Récupération des paramètres de recherche et filtre
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    ministry_filter = request.GET.get('ministry', '')
    group_filter = request.GET.get('group', '')
    gender_filter = request.GET.get('gender', '')
    
    # Base queryset
    members = Member.objects.select_related('family').prefetch_related('ministries', 'groups')
    
    # Application des filtres
    if search_query:
        members = members.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(member_id__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if status_filter:
        members = members.filter(status=status_filter)
    else:
        members = members.exclude(status='deceased')
    
    if ministry_filter:
        members = members.filter(ministries__id=ministry_filter)
    
    if group_filter:
        members = members.filter(groups__id=group_filter)
    
    if gender_filter:
        members = members.filter(gender=gender_filter)
    
    # Tri
    sort_by = request.GET.get('sort', '-created_at')
    members = members.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(members, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    ministries = Ministry.objects.all()
    groups = Group.objects.all()
    
    context = {
        'title': 'Liste des Membres',
        'members': page_obj,
        'ministries': ministries,
        'groups': groups,
        'search_query': search_query,
        'status_filter': status_filter,
        'ministry_filter': ministry_filter,
        'group_filter': group_filter,
        'gender_filter': gender_filter,
        'total_count': paginator.count,
    }
    
    return render(request, 'members/membre_list.html', context)



@login_required
def export_members(request):
    format_type = request.GET.get('format', 'csv')

    # Récupérer les membres selon les permissions
    if hasattr(request.user, 'has_admin_access') and request.user.has_admin_access():
        members = Member.objects.all().select_related('user', 'family')
    elif hasattr(request.user, 'has_member_management_access') and request.user.has_member_management_access():
        # Si tu as un groupe géré par l'utilisateur
        members = Member.objects.filter(user=request.user).select_related('user', 'family')
    else:
        return HttpResponse("Accès refusé", status=403)

    if format_type == 'pdf':
        return export_pdf(members, request)  # Passe aussi 'request'
    elif format_type == 'csv':
        return export_csv(members)
    else:
        return HttpResponse("Format non supporté", status=400)

def export_pdf(members, request):
    buffer = BytesIO()

    # Document en paysage
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=30,
        bottomMargin=20
    )

    elements = []
    styles = getSampleStyleSheet()

    # --- Header ---
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=15
    )
    elements.append(Paragraph("Liste des Membres", title_style))
    elements.append(Paragraph(f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", subtitle_style))

    # --- Info bar ---
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    elements.append(Paragraph(f"Total: {members.count()} membre{'s' if members.count()>1 else ''} | Document généré automatiquement", info_style))
    elements.append(Spacer(1, 10))

    # --- Table ---
    data = [['N°', 'Nom', 'Prénom', 'Genre', 'Âge', 'Téléphone', 'Groupe', 'Famille', 'Adhésion']]

    # Styles pour badges
    male_style = ParagraphStyle(
        'MaleBadge',
        fontSize=8,
        textColor=colors.HexColor('#1E40AF'),
        backColor=colors.HexColor('#DBEAFE'),
        alignment=TA_CENTER
    )
    female_style = ParagraphStyle(
        'FemaleBadge',
        fontSize=8,
        textColor=colors.HexColor('#9F1239'),
        backColor=colors.HexColor('#FCE7F3'),
        alignment=TA_CENTER
    )

    for m in members:
        # Badge genre
        if m.gender == 'M':
            gender_paragraph = Paragraph("M", male_style)
        else:
            gender_paragraph = Paragraph("F", female_style)

        data.append([
            m.member_id or '-',
            (m.last_name or '-').upper(),
            m.first_name or '-',
            gender_paragraph,
            m.get_age() if hasattr(m, 'get_age') else '-',
            m.phone or '-',
            getattr(m, 'group', '-') if hasattr(m, 'group') else '-',
            m.family.name if m.family else '-',
            m.membership_date.strftime('%d/%m/%Y') if m.membership_date else '-'
        ])

    table = Table(data, repeatRows=1, hAlign='LEFT', colWidths=[2*cm, 3*cm, 3*cm, 1.5*cm, 1.5*cm, 3*cm, 3*cm, 3*cm, 2.5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
    ]))

    # Alternance des lignes
    for i in range(1, len(data)):
        if i % 2 == 0:
            table.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.HexColor('#F9FAFB'))]))

    elements.append(table)
    elements.append(Spacer(1, 15))

    # --- Footer ---
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    elements.append(Paragraph(f"Document généré automatiquement - {datetime.now().strftime('%d/%m/%Y à %H:%M')}", footer_style))

    # --- Build PDF ---
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="membres_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    return response


def export_csv(members):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="membres_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'

    # BOM pour Excel
    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';')

    # En-têtes
    writer.writerow([
        'N°', 'Nom', 'Prénom', 'Genre', 'Date Naissance', 'Âge',
        'Téléphone', 'Email', 'Famille', 'Utilisateur', 'Date Adhésion', 'Statut'
    ])

    for member in members:
        age = ''
        if member.date_of_birth:
            today = timezone.now().date()
            age = today.year - member.date_of_birth.year
        writer.writerow([
            getattr(member, 'member_number', member.member_id),
            member.last_name or '',
            member.first_name or '',
            member.get_gender_display() if hasattr(member, 'get_gender_display') else member.gender,
            member.date_of_birth.strftime('%d/%m/%Y') if member.date_of_birth else '',
            age,
            member.phone or '',
            member.email or '',
            member.family.name if member.family else '',
            member.user.get_full_name() if member.user else '',
            member.membership_date.strftime('%d/%m/%Y') if member.membership_date else '',
            member.status if hasattr(member, 'status') else '-'
        ])

    return response

def send_welcome_email(user, request):
    raise NotImplementedError


def generate_random_password(length=8):
    """Créer un mot de passe aléatoire"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


@login_required
def member_add(request):
    """Ajouter un nouveau membre et envoyer un email de notification"""
    if not request.user.has_membres_management_access():
        messages.error(request, "Vous n'avez pas l'autorisation d'ajouter des membres.")
        return redirect('membres:list')

    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save(commit=False)
            member.created_by = request.user
            member.save()
            form.save_m2m()

            # --- Création du User associé ---
            password = get_random_string(length=8)  # mot de passe aléatoire
            user = User.objects.create_user(
                username=member.email,  # utiliser l'email comme username
                email=member.email,
                first_name=member.first_name,
                last_name=member.last_name,
                password=password
            )

            # --- Préparer le mail ---
            context = {
                'user': user,
                'password': password,
                'login_url': request.build_absolute_uri('/accounts/login/'),
            }
            message = render_to_string('membres/email_new_member.html', context)

            mail = EmailMessage(
                subject='Bienvenue sur la plateforme',
                body=message,
                to=[user.email],
            )
            mail.content_subtype = "html"
            mail.send()

            messages.success(request, f"Le membre a été ajouté et un email a été envoyé à {user.email}.")
            return redirect('membres:detail', member_id=member.id)
    else:
        form = MemberForm()

    context = {
        'title': 'Ajouter un Membre',
        'form': form,
        'families': Family.objects.all(),
    }
    return render(request, 'members/form.html', context)


@login_required
def member_edit(request, member_id):
    """Modifier un membre existant"""
    if not request.user.has_membres_management_access():
        messages.error(request, 'Vous n\'avez pas l\'autorisation de modifier des membres.')
        return redirect('membres:list')
    
    member = get_object_or_404(Member, pk=member_id)
    
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f'Le membre {member.get_full_name()} a été modifié avec succès.')
            return redirect('membres:detail', member_id=member.id)
    else:
        form = MemberForm(instance=member)
    
    context = {
        'title': f'Modifier - {member.get_full_name()}',
        'form': form,
        'member': member,
        'families': Family.objects.all(),
    }
    
    return render(request, 'members/form.html', context)

@login_required
def member_detail(request, member_id):
    """Détails d'un membre"""
    member = get_object_or_404(
        Member.objects.select_related('family', 'user')
        .prefetch_related('ministries', 'groups', 'transactions', 'attendances'),
        pk=member_id
    )

    # Vérification des permissions
    if not request.user.has_membres_management_access():
        if not hasattr(request.user, 'member_profile') or request.user.member_profile != member:
            messages.error(request, 'Vous n\'avez pas l\'autorisation de voir ce profil.')
            return redirect('dashboard')

    # Statistiques de présence (3 derniers mois)
    three_months_ago = timezone.now().date() - timezone.timedelta(days=90)
    attendances_qs = member.attendances.filter(date__gte=three_months_ago).order_by('-date')

    total_attendances = attendances_qs.count()
    present_count = attendances_qs.filter(present=True).count()
    attendance_rate = round((present_count / total_attendances) * 100, 1) if total_attendances else 0

    # Slice après le filtrage
    recent_attendances = attendances_qs[:10]

    # Transactions récentes (si autorisé)
    recent_transactions = None
    total_contributions = 0
    if request.user.has_finance_access():
        recent_transactions = member.transactions.filter(
            is_validated=True
        ).order_by('-date')[:5]
        total_contributions = member.transactions.filter(
            is_validated=True
        ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'title': f'Profil - {member.get_full_name()}',
        'member': member,
        'attendance_stats': {
            'total': total_attendances,
            'present': present_count,
            'rate': attendance_rate
        },
        'recent_attendances': recent_attendances,
        'recent_transactions': recent_transactions,
        'total_contributions': total_contributions,
    }

    return render(request, 'members/membre_detail.html', context)


        
@login_required
def member_delete(request, member_id):
    """Supprimer un membre"""
    if not request.user.has_member_management_access():
        messages.error(request, 'Vous n\'avez pas l\'autorisation de supprimer des membres.')
        return redirect('membres:list')
    
    member = get_object_or_404(Member, pk=member_id)
    
    if request.method == "POST":
        full_name = member.get_full_name()
        member.delete()
        messages.success(request, f'Le membre {full_name} a été supprimé avec succès.')
        return redirect('membres:list')
    
    # Confirmation avant suppression
    context = {
        'title': f'Supprimer - {member.get_full_name()}',
        'member': member,
    }
    return render(request, 'members/member_confirm_delete.html', context)



@login_required 
def generate_card(request, member_id):
    """
    Vue pour générer une carte de membre (PDF) basée sur l'ID du membre.
    Utilise la fonction generate_member_card depuis utils.py pour créer le PDF.
    Télécharge un fichier PDF avec les infos du membre.
    """
    member = get_object_or_404(Member, id=member_id)
    
    # Génération du PDF via la fonction utilitaire
    pdf_buffer = generate_member_card(
        member=member,  # Passe l'objet Member corrigé (pas l'ID)
        include_photo=True,  # Inclure la photo si disponible
        include_qr=True  # Inclure le QR code
    )
    
    # Création de la réponse HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="carte_membre_{member.id}_{member.get_full_name().replace(' ', '_')}.pdf"'
    
    # Écriture du contenu du buffer dans la réponse
    response.write(pdf_buffer.read())
    
    return response

@login_required
def my_profile(request):
    """Affiche le profil de l'utilisateur connecté"""
    member = None
    # Si tu relies User à Member via une relation OneToOne
    if hasattr(request.user, "member_profile"):
        member = request.user.member_profile

    context = {
        "user": request.user,
        "member": member,  # utile si tu as un modèle Member relié à User
        "title": "Mon profil"
    }
    return render(request, "members/my_profile.html", context)

# membres/views.py


def ministry_list(request):
    ministries = Ministry.objects.all()  # Récupérer tous les ministères
    return render(request, "members/ministry_list.html", {"ministries": ministries})

def ministry_add(request):
    if request.method == "POST":
        form = MinistryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ministère ajouté avec succès ✅")
            return redirect("membres:ministry_list")  # redirige vers la liste des ministères
    else:
        form = MinistryForm()
    return render(request, "members/ministry_add.html", {"form": form})

def ministry_edit(request, ministry_id):
    ministry = get_object_or_404(Ministry, id=ministry_id)
    if request.method == "POST":
        form = MinistryForm(request.POST, instance=ministry)
        if form.is_valid():
            form.save()
            messages.success(request, "Ministère modifié avec succès ✅")
            return redirect("membres:ministry_list")
    else:
        form = MinistryForm(instance=ministry)

    return render(request, "members/ministry_edit.html", {"form": form, "ministry": ministry})

def ministry_delete(request, ministry_id):
    ministry = get_object_or_404(Ministry, id=ministry_id)
    if request.method == "POST":
        ministry.delete()
        messages.success(request, "Ministère supprimé avec succès ✅")
        return redirect("membres:ministry_list")
    return render(request, "members/ministry_delete.html", {"ministry": ministry})

def group_list(request):
    groups = Group.objects.all()
    cell_groups_count = Group.objects.filter(group_type='cell').count()
    youth_groups_count = Group.objects.filter(group_type='youth').count()
    total_group_members = sum([g.members.count() for g in groups])

    context = {
        "groups": groups,
        "cell_groups_count": cell_groups_count,
        "youth_groups_count": youth_groups_count,
        "total_group_members": total_group_members,
    }
    return render(request, "members/group_list.html", context)

@login_required
def group_add(request):
    """Vue pour ajouter un nouveau groupe"""
    user = request.user
    
    if not user.has_membres_management_access():
        messages.warning(request, "Vous n'avez pas les droits pour ajouter un groupe.")
        return redirect('membres:group_list')
    
    if request.method == "POST":
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = user  # Applique le créateur (du modèle)
            group.save()  # Sauvegarde avec tous les champs
            messages.success(request, f"Le groupe '{group.name}' a été ajouté avec succès.")
            return redirect("membres:group_list")
    else:
        form = GroupForm()
    
    context = {
        'title': 'Ajouter un Groupe',
        'form': form,
    }
    return render(request, "members/group_add.html", context)


@login_required
def group_edit(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if request.method == "POST":
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, "Le groupe a été modifié avec succès.")
            return redirect("membres:group_list")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = GroupForm(instance=group)

    return render(request, "members/group_edit.html", {"form": form, "group": group})

def group_delete(request, group_id):
    if not request.user.is_staff:  # uniquement admin
        messages.error(request, "Vous n'avez pas la permission de supprimer ce groupe.")
        return redirect('membres:group_list')

    group = get_object_or_404(Group, id=group_id)
    group.delete()
    messages.success(request, "Le groupe a été supprimé avec succès.")
    return redirect('membres:group_list')

def family_list(request):
    families = Family.objects.all()
    return render(request, "members/family_list.html", {"families": families})


def attendance_mark(request):
    """Marquer la présence d'un membre"""
    if request.method == "POST":
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Présence enregistrée ✅")
            return redirect("members:attendance_mark")
    else:
        form = AttendanceForm()

    return render(request, "members/attendance_mark.html", {"form": form})




@login_required
def family_add(request):
    """Vue pour ajouter une nouvelle famille"""
    user = request.user
    
    # Vérifie l'accès
    if not user.has_membres_management_access():
        messages.warning(request, "Vous n'avez pas les droits pour ajouter une famille.")
        return redirect('membres:family_list')
    
    if request.method == "POST":
        form = FamilyForm(request.POST)
        if form.is_valid():
            family = form.save(commit=False)
            family.created_by = user  # Applique le créateur si champ existe
            family.save()
            messages.success(request, f"La famille '{family.name}' a été ajoutée avec succès.")
            return redirect("membres:family_list")
    else:
        form = FamilyForm()
    
    context = {
        'title': 'Ajouter une Famille',
        'form': form,
    }
    return render(request, "members/family_add.html", context)


@login_required
def family_detail(request, family_id):
    """Affiche les détails d'une famille spécifique"""
    family = get_object_or_404(Family, id=family_id)
    return render(request, 'members/family_detail.html', {'family': family})

@login_required
def family_edit(request, family_id):
    """Modifier une famille existante"""
    family = get_object_or_404(Family, id=family_id)

    if request.method == "POST":
        form = FamilyForm(request.POST, instance=family)
        if form.is_valid():
            form.save()
            messages.success(request, f"La famille '{family.name}' a été modifiée avec succès ✅")
            return redirect("membres:family_detail", family_id=family.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = FamilyForm(instance=family)

    return render(request, "members/family_edit.html", {"form": form, "family": family})



def family_delete(request, family_id):
    family = get_object_or_404(Family, id=family_id)
    family.delete()
    messages.success(request, "La famille a été supprimée avec succès.")
    return redirect(request,"membres:family_list") 
