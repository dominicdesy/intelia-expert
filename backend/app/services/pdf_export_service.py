"""
Service d'exportation de conversations en PDF
Génère un PDF professionnel avec logo Intelia et mise en page élégante
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image as RLImage,
    KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

logger = logging.getLogger(__name__)


class PDFExportService:
    """Service pour générer des exports PDF de conversations"""

    # Couleurs Intelia (à ajuster selon votre charte graphique)
    INTELIA_BLUE = HexColor('#1E40AF')  # Bleu principal
    INTELIA_LIGHT_BLUE = HexColor('#3B82F6')  # Bleu clair
    INTELIA_GRAY = HexColor('#6B7280')  # Gris pour texte secondaire
    USER_BG = HexColor('#EFF6FF')  # Fond bleu clair pour messages utilisateur
    ASSISTANT_BG = HexColor('#F9FAFB')  # Fond gris clair pour messages assistant

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configure les styles personnalisés pour le PDF"""

        # Style pour le titre principal
        self.styles.add(ParagraphStyle(
            name='InteliaTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.INTELIA_BLUE,
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='InteliaSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.INTELIA_GRAY,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        # Style pour les métadonnées
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.INTELIA_GRAY,
            spaceAfter=6,
            fontName='Helvetica'
        ))

        # Style pour le nom du rôle (User/Assistant)
        self.styles.add(ParagraphStyle(
            name='RoleLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.INTELIA_BLUE,
            fontName='Helvetica-Bold',
            spaceAfter=4
        ))

        # Style pour les messages utilisateur
        self.styles.add(ParagraphStyle(
            name='UserMessage',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            fontName='Helvetica',
            leading=14,
            leftIndent=10,
            rightIndent=10,
            spaceBefore=6,
            spaceAfter=6
        ))

        # Style pour les messages assistant
        self.styles.add(ParagraphStyle(
            name='AssistantMessage',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            fontName='Helvetica',
            leading=14,
            leftIndent=10,
            rightIndent=10,
            spaceBefore=6,
            spaceAfter=6
        ))

        # Style pour le footer
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.INTELIA_GRAY,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))

    def _get_logo_path(self) -> str:
        """Retourne le chemin vers le logo Intelia"""
        # Le logo est dans backend/app/static/images/logo.png
        app_dir = Path(__file__).parent.parent  # Remonter à app/
        logo_path = app_dir / "static" / "images" / "logo.png"

        if logo_path.exists():
            return str(logo_path)
        else:
            logger.warning(f"Logo non trouvé à: {logo_path}")
            return None

    def _add_header_footer(self, canvas_obj, doc):
        """Ajoute header et footer à chaque page"""
        canvas_obj.saveState()

        # Footer
        footer_text = f"Intelia Expert - Expert en Aviculture • Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        canvas_obj.setFont('Helvetica-Oblique', 8)
        canvas_obj.setFillColor(self.INTELIA_GRAY)
        canvas_obj.drawCentredString(
            doc.width / 2 + doc.leftMargin,
            0.5 * inch,
            footer_text
        )

        # Numéro de page
        canvas_obj.drawRightString(
            doc.width + doc.leftMargin,
            0.5 * inch,
            f"Page {canvas_obj.getPageNumber()}"
        )

        canvas_obj.restoreState()

    def export_conversation(
        self,
        conversation_data: Dict[str, Any],
        messages: List[Dict[str, Any]],
        user_info: Dict[str, Any]
    ) -> BytesIO:
        """
        Génère un PDF de la conversation

        Args:
            conversation_data: Métadonnées de la conversation
            messages: Liste des messages (role, content, timestamp)
            user_info: Informations utilisateur (nom, email)

        Returns:
            BytesIO contenant le PDF généré
        """
        buffer = BytesIO()

        # Créer le document PDF
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=1*inch
        )

        # Liste des éléments du PDF
        story = []

        # === TITRE PRINCIPAL ===
        main_title = "Intelia Cognito"
        story.append(Paragraph(main_title, self.styles['InteliaTitle']))

        # === TITRE CONVERSATION ===
        title = conversation_data.get('title', 'Conversation sans titre')
        # Créer un style pour le titre de conversation (plus petit)
        conv_title_style = ParagraphStyle(
            name='ConversationTitle',
            parent=self.styles['InteliaTitle'],
            fontSize=16,
            spaceAfter=6
        )
        story.append(Paragraph(title, conv_title_style))

        # === SOUS-TITRE ===
        subtitle = f"Export de conversation - {messages[0].get('created_at', 'Date inconnue')[:10] if messages else 'N/A'}"
        story.append(Paragraph(subtitle, self.styles['InteliaSubtitle']))

        story.append(Spacer(1, 0.2*inch))

        # === MÉTADONNÉES ===
        # Formater la date de création
        created_at = conversation_data.get('created_at', 'N/A')
        if hasattr(created_at, 'strftime'):
            # C'est un objet datetime
            created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(created_at, str):
            # C'est déjà une string
            created_at_str = created_at[:19].replace('T', ' ')
        else:
            created_at_str = 'N/A'

        metadata_table_data = [
            ['Utilisateur:', user_info.get('email', 'N/A')],
            ['Date de création:', created_at_str],
            ['Langue:', conversation_data.get('language', 'fr').upper()],
            ['Nombre de messages:', str(len(messages))],
        ]

        metadata_table = Table(metadata_table_data, colWidths=[1.5*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.INTELIA_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        story.append(metadata_table)
        story.append(Spacer(1, 0.4*inch))

        # === LIGNE SÉPARATRICE ===
        story.append(Table([['']], colWidths=[6.5*inch], rowHeights=[2]))
        story[-1].setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 2, self.INTELIA_BLUE),
        ]))
        story.append(Spacer(1, 0.3*inch))

        # === MESSAGES ===
        for i, message in enumerate(messages):
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            timestamp = message.get('created_at', '')

            # Label du rôle avec timestamp
            if role == 'user':
                role_label = "👤 Utilisateur"
                bg_color = self.USER_BG
                message_style = self.styles['UserMessage']
            else:
                role_label = "🤖 Intelia Expert"
                bg_color = self.ASSISTANT_BG
                message_style = self.styles['AssistantMessage']

            # Timestamp formaté
            time_str = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M')
                except:
                    time_str = ""

            role_text = f"{role_label} {time_str}" if time_str else role_label

            # Créer une table pour le message avec fond coloré
            message_content = Paragraph(content, message_style)

            message_table = Table(
                [[Paragraph(role_text, self.styles['RoleLabel'])],
                 [message_content]],
                colWidths=[6.5*inch]
            )

            message_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                ('ROUNDEDCORNERS', [5, 5, 5, 5]),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))

            story.append(message_table)
            story.append(Spacer(1, 0.15*inch))

        # === FOOTER FINAL ===
        story.append(Spacer(1, 0.3*inch))
        story.append(Table([['']], colWidths=[6.5*inch], rowHeights=[1]))
        story[-1].setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 1, self.INTELIA_GRAY),
        ]))
        story.append(Spacer(1, 0.1*inch))

        footer_final = Paragraph(
            "Intelia Expert - Votre assistant intelligent en aviculture<br/>"
            "📧 support@intelia.com | 🌐 www.intelia.com",
            self.styles['Footer']
        )
        story.append(footer_final)

        # === GÉNÉRER LE PDF ===
        doc.build(
            story,
            onFirstPage=self._add_header_footer,
            onLaterPages=self._add_header_footer
        )

        buffer.seek(0)
        logger.info(f"PDF généré: {len(messages)} messages, {buffer.getbuffer().nbytes} bytes")
        return buffer


# Singleton instance
_pdf_service = None


def get_pdf_export_service() -> PDFExportService:
    """Retourne l'instance singleton du service PDF"""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFExportService()
    return _pdf_service
