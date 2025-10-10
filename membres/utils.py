from io import BytesIO
import os
from django.conf import settings
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
from PIL import Image, ImageDraw
import qrcode


def generate_qr_code(data):
    """Génère un QR code optimisé"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#2563eb", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def create_circular_photo(photo_path, size=80):
    """Crée une photo circulaire avec bordure"""
    try:
        img = Image.open(photo_path).convert("RGBA")
        
        # Créer une image carrée
        min_side = min(img.size)
        left = (img.width - min_side) // 2
        top = (img.height - min_side) // 2
        img = img.crop((left, top, left + min_side, top + min_side))
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Masque circulaire
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        # Appliquer le masque
        output = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        output.paste(img, (0, 0), mask)
        
        buffer = BytesIO()
        output.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    except Exception:
        return None


def generate_member_card(member, include_photo=True, include_qr=True):
    """
    Carte de membre professionnelle avec design épuré
    Format: 350×220 px (équivalent CR80)
    """
    
    # Configuration
    card_width, card_height = 350, 220
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(card_width, card_height))
    
    # Récupération config église
    church_config = getattr(settings, 'CHURCH_CONFIG', {})
    primary_color = HexColor(church_config.get('PRIMARY_COLOR', '#2563eb'))
    
    # ========== FOND BLANC ==========
    c.setFillColor(HexColor('#FFFFFF'))
    c.rect(0, 0, card_width, card_height, fill=1, stroke=0)
    
    # Bordure élégante
    c.setStrokeColor(HexColor('#e5e7eb'))
    c.setLineWidth(2)
    c.rect(0, 0, card_width, card_height, fill=0, stroke=1)
    
    # ========== BANDE SUPÉRIEURE COLORÉE ==========
    header_height = 60
    c.setFillColor(primary_color)
    c.rect(0, card_height - header_height, card_width, header_height, fill=1, stroke=0)
    
    # Logo église
    logo_path = os.path.join(settings.MEDIA_ROOT, church_config.get('LOGO_PATH', ''))
    logo_size = 35
    if os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            logo_img.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
            logo_buffer = BytesIO()
            logo_img.save(logo_buffer, format='PNG')
            logo_buffer.seek(0)
            c.drawImage(ImageReader(logo_buffer), 15, card_height - 50, 
                       width=logo_size, height=logo_size, mask='auto')
        except Exception:
            pass
    
    # Nom de l'église
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(HexColor('#FFFFFF'))
    church_name = church_config.get('NAME', 'Église')
    c.drawString(60, card_height - 30, church_name.upper())
    
    # Sous-titre
    c.setFont("Helvetica", 8)
    c.drawString(60, card_height - 42, "CARTE DE MEMBRE")
    
    # ========== PHOTO DU MEMBRE ==========
    photo_size = 80
    photo_x = 20
    photo_y = card_height - header_height - photo_size - 15
    
    if include_photo and getattr(member, 'photo', None):
        try:
            photo_buffer = create_circular_photo(member.photo.path, photo_size)
            if photo_buffer:
                # Bordure photo
                c.setFillColor(primary_color)
                c.circle(photo_x + photo_size/2, photo_y + photo_size/2, photo_size/2 + 3, fill=1, stroke=0)
                
                c.drawImage(ImageReader(photo_buffer), photo_x, photo_y, 
                           width=photo_size, height=photo_size, mask='auto')
            else:
                include_photo = False
        except Exception:
            include_photo = False
    
    if not include_photo:
        # Placeholder professionnel
        c.setFillColor(HexColor('#f3f4f6'))
        c.circle(photo_x + photo_size/2, photo_y + photo_size/2, photo_size/2, fill=1, stroke=0)
        
        c.setStrokeColor(HexColor('#d1d5db'))
        c.setLineWidth(2)
        c.circle(photo_x + photo_size/2, photo_y + photo_size/2, photo_size/2, fill=0, stroke=1)
        
        c.setFillColor(HexColor('#9ca3af'))
        c.setFont("Helvetica", 24)
        c.drawCentredString(photo_x + photo_size/2, photo_y + photo_size/2 - 8, "👤")
    
    # ========== INFORMATIONS MEMBRE ==========
    info_x = photo_x + photo_size + 20
    info_y = photo_y + photo_size - 5
    max_width = card_width - info_x - 85  # Espace pour QR code
    
    # NOM PRÉNOM (grande taille, prioritaire)
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(HexColor('#111827'))
    full_name = f"{member.first_name} {member.last_name}".upper()
    c.drawString(info_x, info_y, full_name)
    
    # ID Membre
    info_y -= 18
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor('#6b7280'))
    c.drawString(info_x, info_y, f"ID: {member.member_id}")
    
    # Ligne séparatrice
    info_y -= 8
    c.setStrokeColor(HexColor('#e5e7eb'))
    c.setLineWidth(1)
    c.line(info_x, info_y, info_x + max_width, info_y)
    
    # Informations détaillées
    info_y -= 15
    line_height = 13
    c.setFont("Helvetica", 8.5)
    c.setFillColor(HexColor('#374151'))
    
    # Famille (si existe)
    if getattr(member, 'family', None):
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(info_x, info_y, "Famille:")
        c.setFont("Helvetica", 8.5)
        c.drawString(info_x + 35, info_y, member.family.name[:25])
        info_y -= line_height
    
    # Ministères (si existe)
    ministries = member.ministries.all() if hasattr(member, 'ministries') else []
    if ministries.exists():
        ministry_names = ", ".join([m.name for m in ministries[:2]])
        if len(ministry_names) > 30:
            ministry_names = ministry_names[:27] + "..."
        
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(info_x, info_y, "Ministère:")
        c.setFont("Helvetica", 8.5)
        c.drawString(info_x + 42, info_y, ministry_names)
        info_y -= line_height
    
    # Groupes (si existe)
    groups = member.groups.all() if hasattr(member, 'groups') else []
    if groups.exists():
        group_names = ", ".join([g.name for g in groups[:2]])
        if len(group_names) > 30:
            group_names = group_names[:27] + "..."
        
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(info_x, info_y, "Groupe:")
        c.setFont("Helvetica", 8.5)
        c.drawString(info_x + 35, info_y, group_names)
        info_y -= line_height
    
    # Situation matrimoniale
    if getattr(member, 'marital_status', None):
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(info_x, info_y, "Situation:")
        c.setFont("Helvetica", 8.5)
        c.drawString(info_x + 42, info_y, member.get_marital_status_display())
        info_y -= line_height
    
    # Date de baptême
    if getattr(member, 'baptism_date', None):
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(info_x, info_y, "Baptême:")
        c.setFont("Helvetica", 8.5)
        c.drawString(info_x + 38, info_y, member.baptism_date.strftime('%d/%m/%Y'))
        info_y -= line_height
    
    # Date d'adhésion
    if getattr(member, 'membership_date', None):
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(info_x, info_y, "Membre depuis:")
        c.setFont("Helvetica", 8.5)
        c.drawString(info_x + 60, info_y, member.membership_date.strftime('%d/%m/%Y'))
        info_y -= line_height
    
    # Contact (téléphone)
    if getattr(member, 'phone', None):
        info_y -= 3
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor('#6b7280'))
        c.drawString(info_x, info_y, f"📞 {member.phone}")
    
    # ========== QR CODE ==========
    if include_qr:
        qr_size = 70
        qr_x = card_width - qr_size - 12
        qr_y = photo_y + 5
        
        # Cadre QR code
        c.setFillColor(HexColor('#f9fafb'))
        c.roundRect(qr_x - 5, qr_y - 5, qr_size + 10, qr_size + 10, 8, fill=1, stroke=0)
        
        c.setStrokeColor(HexColor('#e5e7eb'))
        c.setLineWidth(1)
        c.roundRect(qr_x - 5, qr_y - 5, qr_size + 10, qr_size + 10, 8, fill=0, stroke=1)
        
        # QR code
        qr_data = f"https://votre-eglise.com/membre/{member.id}"
        qr_buffer = generate_qr_code(qr_data)
        c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)
    
    # ========== FOOTER ==========
    footer_y = 12
    
    # Barre de séparation
    c.setStrokeColor(HexColor('#e5e7eb'))
    c.setLineWidth(1)
    c.line(15, footer_y + 10, card_width - 15, footer_y + 10)
    
    # Texte footer
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor('#9ca3af'))
    
    # Date de validité
    validity_text = f"Émise le {timezone.now().strftime('%d/%m/%Y')}"
    c.drawString(15, footer_y, validity_text)
    
    # Note validité
    c.drawRightString(card_width - 15, footer_y, "Valable 12 mois")
    
    # Petite marque centrée
    c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(card_width/2, footer_y, "•")
    
    c.save()
    buffer.seek(0)
    return buffer