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

    def _format_message_content(self, content: str) -> List[Any]:
        """
        Formate le contenu d'un message pour améliorer la lisibilité
        Gère les paragraphes, listes à puces, titres et espacements
        """
        from reportlab.platypus import ListFlowable, ListItem

        # Style pour les sous-titres dans les messages
        if 'MessageSubtitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='MessageSubtitle',
                parent=self.styles['Normal'],
                fontSize=11,
                textColor=self.INTELIA_BLUE,
                fontName='Helvetica-Bold',
                spaceAfter=6,
                spaceBefore=8,
                leading=14
            ))

        # Style pour les paragraphes normaux avec meilleur espacement
        if 'MessageParagraph' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='MessageParagraph',
                parent=self.styles['Normal'],
                fontSize=11,
                textColor=colors.black,
                fontName='Helvetica',
                leading=15,
                spaceAfter=8,
                alignment=TA_LEFT
            ))

        # Style pour les items de liste
        if 'ListItem' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='ListItem',
                parent=self.styles['Normal'],
                fontSize=11,
                textColor=colors.black,
                fontName='Helvetica',
                leading=14,
                leftIndent=0
            ))

        elements = []

        # Nettoyer le contenu
        content = content.strip()

        # Séparer par lignes
        lines = content.split('\n')

        current_paragraph = []
        current_list = []

        for line in lines:
            line_stripped = line.strip()

            # Ligne vide = fin de paragraphe ou liste
            if not line_stripped:
                if current_list:
                    # Créer la liste à puces
                    list_items = []
                    for item in current_list:
                        list_items.append(Paragraph(item, self.styles['ListItem']))
                    elements.append(ListFlowable(
                        list_items,
                        bulletType='bullet',
                        leftIndent=20,
                        bulletFontSize=10,
                        bulletOffsetY=-1,
                        start='•'
                    ))
                    elements.append(Spacer(1, 0.08*inch))
                    current_list = []
                elif current_paragraph:
                    # Créer le paragraphe
                    para_text = ' '.join(current_paragraph)
                    # Vérifier si c'est un titre (se termine par :)
                    if para_text.endswith(':'):
                        elements.append(Paragraph(para_text, self.styles['MessageSubtitle']))
                    else:
                        elements.append(Paragraph(para_text, self.styles['MessageParagraph']))
                    current_paragraph = []
                continue

            # Détecter une liste à puces
            if line_stripped.startswith('- ') or line_stripped.startswith('• '):
                # Finir le paragraphe en cours si nécessaire
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    if para_text.endswith(':'):
                        elements.append(Paragraph(para_text, self.styles['MessageSubtitle']))
                    else:
                        elements.append(Paragraph(para_text, self.styles['MessageParagraph']))
                    current_paragraph = []

                # Ajouter à la liste
                item_text = line_stripped[2:].strip()  # Enlever le tiret
                current_list.append(item_text)
            else:
                # Finir la liste en cours si nécessaire
                if current_list:
                    list_items = []
                    for item in current_list:
                        list_items.append(Paragraph(item, self.styles['ListItem']))
                    elements.append(ListFlowable(
                        list_items,
                        bulletType='bullet',
                        leftIndent=20,
                        bulletFontSize=10,
                        bulletOffsetY=-1,
                        start='•'
                    ))
                    elements.append(Spacer(1, 0.08*inch))
                    current_list = []

                # Détecter si c'est une ligne de titre (se termine par :)
                if line_stripped.endswith(':') and len(line_stripped) < 100:
                    # Si on a un paragraphe en cours, le terminer d'abord
                    if current_paragraph:
                        para_text = ' '.join(current_paragraph)
                        elements.append(Paragraph(para_text, self.styles['MessageParagraph']))
                        current_paragraph = []
                    # Ajouter le titre
                    elements.append(Paragraph(line_stripped, self.styles['MessageSubtitle']))
                else:
                    # Ajouter au paragraphe en cours
                    current_paragraph.append(line_stripped)

        # Traiter le dernier élément
        if current_list:
            list_items = []
            for item in current_list:
                list_items.append(Paragraph(item, self.styles['ListItem']))
            elements.append(ListFlowable(
                list_items,
                bulletType='bullet',
                leftIndent=20,
                bulletFontSize=10,
                bulletOffsetY=-1,
                start='•'
            ))
        elif current_paragraph:
            para_text = ' '.join(current_paragraph)
            if para_text.endswith(':'):
                elements.append(Paragraph(para_text, self.styles['MessageSubtitle']))
            else:
                elements.append(Paragraph(para_text, self.styles['MessageParagraph']))

        # Si aucun élément n'a été créé (contenu simple), créer un paragraphe unique
        if not elements:
            elements.append(Paragraph(content, self.styles['MessageParagraph']))

        return elements

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
            else:
                role_label = "🤖 Intelia Expert"
                bg_color = self.ASSISTANT_BG

            # Timestamp formaté
            time_str = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M')
                except:
                    time_str = ""

            role_text = f"{role_label} {time_str}" if time_str else role_label

            # Formater le contenu avec gestion des paragraphes et listes
            formatted_content = self._format_message_content(content)

            # Créer la structure du message avec en-tête et contenu
            message_elements = [
                [Paragraph(role_text, self.styles['RoleLabel'])],
            ]

            # Ajouter chaque élément formaté dans une cellule de tableau
            for element in formatted_content:
                message_elements.append([element])

            message_table = Table(
                message_elements,
                colWidths=[6.5*inch]
            )

            message_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                ('ROUNDEDCORNERS', [5, 5, 5, 5]),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (1, 0), (-1, -1), 5),
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
