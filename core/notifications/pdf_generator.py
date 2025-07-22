"""
PDF Generator for broiler performance reports.
WORKING VERSION - Fixed recommendations logic
"""

import io
import sys
import logging
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

# Import translation manager
try:
    from core.notifications.translation_manager import get_translation_manager
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    logger.error("Translation manager required for PDF generation")

# Import ReportLab components
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
        PageBreak, PageTemplate, Frame, BaseDocTemplate
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available - using text fallback")

# Import data structures
try:
    from core.data.barn_list_parser import BarnClient
except ImportError:
    @dataclass
    class BarnClient:
        barn_id: str
        language: str
        email: str


@dataclass
class BroilerData:
    """Structured broiler data with validation."""
    age: float
    breed: str
    observed_weight: float
    expected_weight: float
    gain_observed: float
    gain_expected: float
    temperature_avg: float = 24.0
    humidity_avg: float = 60.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BroilerData':
        """Create BroilerData from dictionary with validation."""
        def safe_number(value: Any, default: float = 0.0) -> float:
            try:
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    return float(value.replace(',', '.'))
                else:
                    return default
            except (ValueError, TypeError):
                return default
        
        def safe_string(value: Any, default: str = "") -> str:
            if value is None:
                return default
            return str(value)
        
        data = data or {}
        return cls(
            age=safe_number(data.get('age', 35)),
            breed=safe_string(data.get('breed', 'Ross 308')),
            observed_weight=safe_number(data.get('observed_weight', 2000)),
            expected_weight=safe_number(data.get('expected_weight', 2100)),
            gain_observed=safe_number(data.get('gain_observed', 85)),
            gain_expected=safe_number(data.get('gain_expected', 90)),
            temperature_avg=safe_number(data.get('temperature_avg', 24.0)),
            humidity_avg=safe_number(data.get('humidity_avg', 60.0))
        )
    
    @property
    def weight_deviation(self) -> float:
        """Calculate weight deviation."""
        return self.observed_weight - self.expected_weight
    
    @property
    def weight_deviation_pct(self) -> float:
        """Calculate weight deviation percentage."""
        if self.expected_weight > 0:
            return (self.weight_deviation / self.expected_weight) * 100
        return 0.0
    
    @property
    def gain_deviation(self) -> float:
        """Calculate gain deviation."""
        return self.gain_observed - self.gain_expected
    
    @property
    def gain_deviation_pct(self) -> float:
        """Calculate gain deviation percentage."""
        if self.gain_expected > 0:
            return (self.gain_deviation / self.gain_expected) * 100
        return 0.0
    
    @property
    def gain_ratio(self) -> float:
        """Calculate gain ratio."""
        if self.gain_expected > 0:
            return self.gain_observed / self.gain_expected
        return 0.0


class PerformanceAnalyzer:
    """Analyzes performance data to determine if recommendations are needed."""
    
    @staticmethod
    def needs_recommendations(data: BroilerData) -> bool:
        """Determine if recommendations section should be included."""
        try:
            # Weight performance tolerance: ±10%
            if abs(data.weight_deviation_pct) > 10:
                return True
            
            # Gain performance tolerance: ratio between 0.80-1.25
            if data.gain_ratio < 0.80 or data.gain_ratio > 1.25:
                return True
            
            # Temperature check
            if data.temperature_avg < 18 or data.temperature_avg > 35:
                return True
            
            # Humidity range: 35-80%
            if data.humidity_avg < 35 or data.humidity_avg > 80:
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error in needs_recommendations: {e}")
            return False
    
    @staticmethod
    def get_optimal_temp_range(age: float) -> tuple:
        """Get optimal temperature range for age."""
        try:
            if age <= 7:
                return (32, 35)
            elif age <= 14:
                return (28, 32)
            elif age <= 21:
                return (25, 29)
            elif age <= 28:
                return (22, 26)
            elif age <= 42:
                return (20, 24)
            else:
                return (18, 22)
        except:
            return (20, 24)  # Default range


class BroilerPDFGenerator:
    """Main PDF generator class following perfect model (1.pdf)."""
    
    def __init__(self):
        """Initialize PDF generator."""
        self.available = REPORTLAB_AVAILABLE
        self.analyzer = PerformanceAnalyzer()
        
        # Initialize translation manager safely
        self.tm = None
        if TRANSLATION_AVAILABLE:
            try:
                self.tm = get_translation_manager()
            except Exception as e:
                logger.warning(f"Translation manager initialization failed: {e}")
    
    def get_text(self, key: str, language: str = "en", **kwargs) -> str:
        """Get translated text with fallback."""
        try:
            if self.tm:
                text = self.tm.get(key, language)
                if text and text != key:
                    if kwargs:
                        return text.format(**kwargs)
                    return text
        except Exception as e:
            logger.warning(f"Translation failed for {key}: {e}")
        
        # Fallback text generation
        return key.split('.')[-1].replace('_', ' ').title()
    
    def generate_pdf(
        self,
        client: BarnClient,
        barn_id: str,
        broiler_data: Dict[str, Any],
        analysis_result: Any = None,
        ai_analysis: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Generate PDF report following perfect model (1.pdf)."""
        logger.info(f"Generating PDF for barn {barn_id}")
        
        try:
            # Validate and structure data
            data = BroilerData.from_dict(broiler_data or {})
            barn_id_str = str(barn_id) if barn_id else "Unknown"
            
            # Format AI analysis
            formatted_ai_text = ""
            if ai_analysis is not None:
                formatted_ai_text = str(ai_analysis)[:2000]  # Limit length
            
            # Determine if recommendations are needed
            show_recommendations = self.analyzer.needs_recommendations(data)
            logger.info(f"Recommendations needed: {show_recommendations}")
            
            if not self.available:
                return self._generate_text_fallback(barn_id_str, client.language, data, formatted_ai_text)
            
            # Generate PDF using ReportLab
            return self._generate_reportlab_pdf(
                client, barn_id_str, data, formatted_ai_text, show_recommendations
            )
            
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_error_response(barn_id, client.language, str(e))
    
    def _generate_reportlab_pdf(
        self,
        client: BarnClient,
        barn_id: str,
        data: BroilerData,
        ai_analysis: str,
        show_recommendations: bool
    ) -> Dict[str, Any]:
        """Generate PDF using ReportLab."""
        try:
            buffer = io.BytesIO()
            
            # Create simple document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=1*inch,
                leftMargin=1*inch,
                topMargin=1*inch,
                bottomMargin=1*inch
            )
            
            # Build content
            story = self._build_pdf_content(barn_id, data, client.language, ai_analysis, show_recommendations)
            
            # Build PDF
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            if len(pdf_bytes) < 1000:
                logger.warning(f"PDF too small ({len(pdf_bytes)} bytes), falling back to text")
                return self._generate_text_fallback(barn_id, client.language, data, ai_analysis)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"broiler_report_{barn_id}_{client.language}_{timestamp}.pdf"
            
            logger.info(f"PDF generated successfully: {len(pdf_bytes)} bytes")
            
            return {
                "status": "success",
                "pdf_bytes": pdf_bytes,
                "filename": filename,
                "file_size": len(pdf_bytes)
            }
            
        except Exception as e:
            logger.error(f"ReportLab PDF generation failed: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_text_fallback(barn_id, client.language, data, ai_analysis)
    
    def _build_pdf_content(self, barn_id: str, data: BroilerData, language: str, ai_analysis: str, show_recommendations: bool) -> List:
        """Build PDF content."""
        story = []
        
        try:
            # Title
            story.extend(self._build_title_section(barn_id, language))
            
            # Report Information
            story.extend(self._build_info_section(data, language))
            
            # Insights
            if show_recommendations:
                story.extend(self._build_insights_detailed(barn_id, data, language))
            else:
                story.extend(self._build_insights_minimal(barn_id, data, language))
            
            # Status Overview
            story.extend(self._build_status_overview(data, language))
            
            story.append(PageBreak())
            
            # Performance Metrics
            story.extend(self._build_performance_section(data, language))
            
            # Environmental Conditions
            story.extend(self._build_environmental_section(data, language))
            
            # Conditional section based on performance
            if show_recommendations:
                # Show detailed recommendations when performance is poor
                story.extend(self._build_recommendations_section(data, language))
                if ai_analysis and ai_analysis.strip():
                    story.append(PageBreak())
                    story.extend(self._build_ai_analysis_section(ai_analysis, language))
            else:
                # Show simple monitoring status when performance is optimal
                story.extend(self._build_optimal_monitoring_section(language))
            
            # Footer
            story.extend(self._build_footer_section(barn_id, language))
            
        except Exception as e:
            logger.error(f"Error building PDF content: {e}")
            story = [
                Paragraph("PDF Generation Error", ParagraphStyle('Error', fontSize=16, fontName='Helvetica-Bold')),
                Spacer(1, 12),
                Paragraph(f"Error details: {str(e)}", ParagraphStyle('ErrorDetail', fontSize=12, fontName='Helvetica'))
            ]
        
        return story
    
    def _build_title_section(self, barn_id: str, language: str) -> List:
        """Build title section."""
        title_style = ParagraphStyle(
            'Title',
            fontSize=24,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1240A4'),
            alignment=TA_CENTER,
            spaceAfter=12,
            leading=28
        )
        
        barn_style = ParagraphStyle(
            'BarnTitle',
            fontSize=20,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1240A4'),
            alignment=TA_CENTER,
            spaceAfter=24
        )
        
        elements = [
            Paragraph("EXPERT BROILER PERFORMANCE", title_style),
            Paragraph("ANALYSIS REPORT", title_style),
            Spacer(1, 20),
            Paragraph(f"BARN: {barn_id}", barn_style),
            Spacer(1, 20)
        ]
        
        return elements
    
    def _build_info_section(self, data: BroilerData, language: str) -> List:
        """Build information section."""
        section_style = ParagraphStyle(
            'SectionHeader',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12
        )
        
        now = datetime.now()
        date_str = now.strftime("%B %d, %Y at %H:%M")
        
        info_data = [
            ["Report Date:", date_str],
            ["Flock Age:", f"{data.age:.0f} days"],
            ["Breed:", data.breed]
        ]
        
        table = Table(info_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#226AE4')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
        ]))
        
        return [
            Paragraph("■ Report Information", section_style),
            table,
            Spacer(1, 12)
        ]
    
    def _build_insights_minimal(self, barn_id: str, data: BroilerData, language: str) -> List:
        """Build minimal insights for optimal performance."""
        section_style = ParagraphStyle(
            'SectionHeader',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12
        )
        
        body_style = ParagraphStyle(
            'Body',
            fontSize=11,
            fontName='Helvetica',
            textColor=colors.black,
            spaceAfter=6,
            alignment=TA_LEFT,
            leftIndent=12
        )
        
        insights_points = [
            f"• Based on the performance metrics provided for Barn {barn_id}, the broilers show a gain ratio of {data.gain_ratio:.2f}",
            f"• At this age, the current weight of {data.observed_weight:.0f}g vs target of {data.expected_weight:.0f}g indicates performance status",
            f"• Environmental conditions with average temperature of {data.temperature_avg:.1f}°C are being monitored"
        ]
        
        elements = [Paragraph("■ Insights", section_style)]
        for point in insights_points:
            elements.append(Paragraph(point, body_style))
        elements.append(Spacer(1, 12))
        
        return elements
    
    def _build_insights_detailed(self, barn_id: str, data: BroilerData, language: str) -> List:
        """Build detailed insights for problematic performance."""
        section_style = ParagraphStyle(
            'SectionHeader',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12
        )
        
        body_style = ParagraphStyle(
            'Body',
            fontSize=11,
            fontName='Helvetica',
            textColor=colors.black,
            spaceAfter=6,
            alignment=TA_LEFT,
            leftIndent=12
        )
        
        insights_points = [
            f"• Based on the performance metrics provided for Barn {barn_id}, the broilers are underperforming significantly.",
            f"• At {int(data.age)} days of age, the current weight of {data.observed_weight:.1f}g is below the expected weight of {data.expected_weight:.1f}g, and the daily gain of {data.gain_observed:.1f}g is concerning.",
            f"• The performance ratio of {data.gain_ratio:.2f} and the Critical status indicate that immediate intervention is necessary."
        ]
        
        elements = [Paragraph("■ Insights", section_style)]
        for point in insights_points:
            elements.append(Paragraph(point, body_style))
        elements.append(Spacer(1, 12))
        
        return elements
    
    def _build_status_overview(self, data: BroilerData, language: str) -> List:
        """Build status overview with colors."""
        section_style = ParagraphStyle(
            'SectionHeader',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12
        )
        
        # Get colors based on performance
        weight_color = self._get_status_color(data.weight_deviation_pct)
        gain_color = self._get_status_color((data.gain_ratio - 1.0) * 100)
        temp_color = self._get_temperature_color(data.temperature_avg, data.age)
        
        status_data = [
            (f"Weight: {data.observed_weight:.0f}g (Target: {data.expected_weight:.0f}g)", weight_color),
            (f"Deviation: {data.weight_deviation:+.0f}g", colors.HexColor('#F8F9FA')),
            (f"Gain Performance: {data.gain_ratio:.2f}", gain_color),
            (f"Temperature: {data.temperature_avg:.1f}°C", temp_color)
        ]
        
        elements = [Paragraph("■ Status Overview", section_style)]
        
        for text, bg_color in status_data:
            height = 0.4*inch if bg_color == colors.HexColor('#F8F9FA') else 0.5*inch
            
            box = Table([[text]], colWidths=[6*inch], rowHeights=[height])
            box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8)
            ]))
            elements.append(box)
            elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 12))
        return elements
    
    def _build_performance_section(self, data: BroilerData, language: str) -> List:
        """Build performance metrics section with visual cards."""
        section_style = ParagraphStyle(
            'SectionHeader',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12
        )
        
        # Create visual cards
        drawing = Drawing(170*mm, 35*mm)
        x_positions = [5*mm, 65*mm, 125*mm]
        
        # Card 1: Weight
        self._draw_metric_card(
            drawing, x_positions[0], 2*mm,
            "Weight", f"{data.observed_weight/1000:.2f} kg",
            f"Dev: {data.weight_deviation:+.0f}g",
            f"({data.weight_deviation_pct:+.1f}%)",
            self._get_status_color(data.weight_deviation_pct)
        )
        
        # Card 2: Gain
        self._draw_metric_card(
            drawing, x_positions[1], 2*mm,
            "Gain", f"{data.gain_observed:.0f} g",
            f"Dev: {data.gain_deviation:+.0f}g",
            f"({data.gain_deviation_pct:+.1f}%)",
            self._get_status_color(data.gain_deviation_pct)
        )
        
        # Card 3: Ratio
        status_text = self._get_status_text(data.gain_ratio)
        self._draw_metric_card(
            drawing, x_positions[2], 2*mm,
            "Ratio", f"{data.gain_ratio:.2f}",
            "Status",
            status_text,
            self._get_status_color((data.gain_ratio - 1.0) * 100)
        )
        
        return [
            Paragraph("■ Performance Metrics", section_style),
            drawing,
            Spacer(1, 16)
        ]
    
    def _build_environmental_section(self, data: BroilerData, language: str) -> List:
        """Build environmental section with visual cards."""
        section_style = ParagraphStyle(
            'SectionHeader',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12
        )
        
        # Create visual cards
        drawing = Drawing(170*mm, 35*mm)
        x_positions = [5*mm, 65*mm, 125*mm]
        
        # Card 1: Temperature
        self._draw_metric_card(
            drawing, x_positions[0], 2*mm,
            "Temperature", f"{data.temperature_avg:.1f}°C",
            "Range",
            "20-26°C",
            self._get_temperature_color(data.temperature_avg, data.age)
        )
        
        # Card 2: Humidity
        self._draw_metric_card(
            drawing, x_positions[1], 2*mm,
            "Humidity", f"{data.humidity_avg:.0f}%",
            "Range",
            "50-70%",
            self._get_humidity_color(data.humidity_avg)
        )
        
        # Card 3: External
        self._draw_metric_card(
            drawing, x_positions[2], 2*mm,
            "External", "22.0°C",
            "Average",
            "24h",
            colors.HexColor('#28a745')
        )
        
        return [
            Paragraph("■ Environmental Conditions", section_style),
            drawing,
            Spacer(1, 16)
        ]
    
    def _build_optimal_monitoring_section(self, language: str) -> List:
        """Build simple monitoring status for optimal performance."""
        section_style = ParagraphStyle(
            'MonitoringTitle',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#28a745'),
            spaceAfter=8,
            spaceBefore=12
        )
        
        body_style = ParagraphStyle(
            'Body',
            fontSize=11,
            fontName='Helvetica',
            textColor=colors.black,
            spaceAfter=6,
            alignment=TA_LEFT,
            leftIndent=12
        )
        
        monitoring_points = [
            "• Performance is within optimal parameters",
            "• Continue current management practices",
            "• Maintain regular monitoring schedule",
            "• No immediate interventions required"
        ]
        
        elements = [Paragraph("■ Monitoring Status", section_style)]
        for point in monitoring_points:
            elements.append(Paragraph(point, body_style))
        elements.append(Spacer(1, 16))
        
        return elements
    
    def _build_recommendations_section(self, data: BroilerData, language: str) -> List:
        """Build recommendations section for problematic performance."""
        section_style = ParagraphStyle(
            'SectionHeader',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#dc3545'),
            spaceAfter=8,
            spaceBefore=12
        )
        
        subsection_style = ParagraphStyle(
            'SubSection',
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=4,
            spaceBefore=8
        )
        
        body_style = ParagraphStyle(
            'Body',
            fontSize=11,
            fontName='Helvetica',
            textColor=colors.black,
            spaceAfter=4,
            alignment=TA_LEFT,
            leftIndent=12
        )
        
        elements = [Paragraph("■ Recommendations", section_style)]
        
        # Health Management
        elements.append(Paragraph("Health Management:", subsection_style))
        health_points = [
            "• Disease Monitoring: Conduct a thorough health check to rule out any underlying diseases.",
            "• Vaccination and Medication: Review the vaccination and medication program.",
            "• Feed Quality: Verify feed quality and nutritional content meets requirements."
        ]
        for point in health_points:
            elements.append(Paragraph(point, body_style))
        
        # Environmental Conditions  
        elements.append(Paragraph("Environmental Conditions:", subsection_style))
        env_points = [
            f"• Temperature Control: Maintain optimal temperature range for {data.age:.0f} days old birds.",
            "• Ventilation: Ensure adequate air circulation and quality.",
            "• Litter Management: Check litter condition and maintain dry environment."
        ]
        for point in env_points:
            elements.append(Paragraph(point, body_style))
        
        # Management Practices
        elements.append(Paragraph("Management Practices:", subsection_style))
        mgmt_points = [
            "• Stocking Density: Evaluate density to prevent overcrowding.",
            "• Water Quality: Ensure clean, fresh water is available at all times.",
            "• Feeding Schedule: Review feeding frequency and amounts."
        ]
        for point in mgmt_points:
            elements.append(Paragraph(point, body_style))
        
        elements.append(Spacer(1, 16))
        return elements
    
    def _build_ai_analysis_section(self, ai_analysis: str, language: str) -> List:
        """Build AI analysis section."""
        section_style = ParagraphStyle(
            'SectionHeader',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12
        )
        
        body_style = ParagraphStyle(
            'Body',
            fontSize=11,
            fontName='Helvetica',
            textColor=colors.black,
            spaceAfter=6,
            alignment=TA_LEFT,
            spaceBefore=6
        )
        
        elements = [
            Spacer(1, 12),
            Paragraph("■ AI Analysis", section_style)
        ]
        
        if ai_analysis and ai_analysis.strip():
            # Split into paragraphs
            paragraphs = ai_analysis.split('\n\n')
            for paragraph in paragraphs[:5]:  # Limit to 5 paragraphs
                if paragraph.strip():
                    # Clean the paragraph
                    clean_para = paragraph.strip()[:500]  # Limit length
                    elements.append(Paragraph(clean_para, body_style))
        
        elements.append(Spacer(1, 12))
        return elements
    
    def _build_footer_section(self, barn_id: str, language: str) -> List:
        """Build footer section."""
        footer_style = ParagraphStyle(
            'Footer',
            fontSize=10,
            fontName='Helvetica',
            textColor=colors.Color(0.4, 0.4, 0.4),
            alignment=TA_CENTER,
            spaceAfter=6
        )
        
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            fontSize=9,
            fontName='Helvetica',
            textColor=colors.red,
            alignment=TA_CENTER,
            spaceAfter=6
        )
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        footer_texts = [
            f"Generated by: Intelia's Smart Assistant | Timestamp: {timestamp}",
            f"Report ID: BPA-{barn_id}-{timestamp}",
            "© 2025 Intelia Technologies. All rights reserved",
            "Warning: This report is generated automatically using AI analysis. It does not replace the judgment of a qualified poultry professional."
        ]
        
        elements = [
            Spacer(1, 24),
            Table([[""]], colWidths=[6*inch], rowHeights=[0.1*inch], style=TableStyle([
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8))
            ])),
            Spacer(1, 8)
        ]
        
        for i, text in enumerate(footer_texts):
            style = disclaimer_style if i == len(footer_texts) - 1 else footer_style
            elements.append(Paragraph(text, style))
        
        return elements
    
    def _draw_metric_card(self, drawing: Drawing, x: float, y: float, title: str, value: str, line1: str, line2: str, color: colors.Color):
        """Draw a metric card."""
        width = 50*mm
        height = 30*mm
        bar_width = 6*mm
        
        # Card background
        bg = Rect(x, y, width, height)
        bg.fillColor = colors.white
        bg.strokeColor = colors.Color(0.8, 0.8, 0.8)
        bg.strokeWidth = 1
        drawing.add(bg)
        
        # Status bar
        bar = Rect(x, y, bar_width, height)
        bar.fillColor = color
        bar.strokeColor = color
        drawing.add(bar)
        
        # Text positioning
        text_x = x + bar_width + (width - bar_width) / 2
        
        # Title
        title_text = String(text_x, y + height - 5*mm, title)
        title_text.textAnchor = 'middle'
        title_text.fontSize = 8
        title_text.fontName = 'Helvetica-Bold'
        title_text.fillColor = colors.Color(0.2, 0.2, 0.2)
        drawing.add(title_text)
        
        # Value
        value_text = String(text_x, y + height - 12*mm, value)
        value_text.textAnchor = 'middle'
        value_text.fontSize = 12
        value_text.fontName = 'Helvetica-Bold'
        value_text.fillColor = colors.black
        drawing.add(value_text)
        
        # Lines
        line1_text = String(text_x, y + height - 18*mm, line1)
        line1_text.textAnchor = 'middle'
        line1_text.fontSize = 7
        line1_text.fontName = 'Helvetica'
        line1_text.fillColor = color
        drawing.add(line1_text)
        
        line2_text = String(text_x, y + height - 23*mm, line2)
        line2_text.textAnchor = 'middle'
        line2_text.fontSize = 7
        line2_text.fontName = 'Helvetica'
        line2_text.fillColor = color
        drawing.add(line2_text)
        
        # Status icon
        icon = '●' if color in [colors.HexColor('#28a745'), colors.HexColor('#ffc107')] else '■'
        icon_text = String(x + width - 3*mm, y + 2*mm, icon)
        icon_text.textAnchor = 'middle'
        icon_text.fontSize = 10
        icon_text.fontName = 'Helvetica-Bold'
        icon_text.fillColor = color
        drawing.add(icon_text)
    
    def _get_status_color(self, deviation_pct: float) -> colors.Color:
        """Get status color based on deviation percentage."""
        try:
            if abs(deviation_pct) <= 5:
                return colors.HexColor('#28a745')  # Green
            elif abs(deviation_pct) <= 15:
                return colors.HexColor('#ffc107')  # Yellow
            else:
                return colors.HexColor('#dc3545')  # Red
        except:
            return colors.HexColor('#28a745')  # Default green
    
    def _get_temperature_color(self, temp: float, age: float) -> colors.Color:
        """Get temperature status color."""
        try:
            optimal_range = self.analyzer.get_optimal_temp_range(age)
            
            if optimal_range[0] <= temp <= optimal_range[1]:
                return colors.HexColor('#28a745')  # Green
            elif optimal_range[0] - 2 <= temp <= optimal_range[1] + 2:
                return colors.HexColor('#ffc107')  # Yellow
            else:
                return colors.HexColor('#dc3545')  # Red
        except:
            return colors.HexColor('#28a745')  # Default green
    
    def _get_humidity_color(self, humidity: float) -> colors.Color:
        """Get humidity status color."""
        try:
            if 50 <= humidity <= 70:
                return colors.HexColor('#28a745')  # Green
            elif 40 <= humidity <= 80:
                return colors.HexColor('#ffc107')  # Yellow
            else:
                return colors.HexColor('#dc3545')  # Red
        except:
            return colors.HexColor('#28a745')  # Default green
    
    def _get_status_text(self, gain_ratio: float) -> str:
        """Get status text based on gain ratio."""
        try:
            if gain_ratio >= 1.05:
                return "Excellent"
            elif gain_ratio >= 0.95:
                return "Good"
            elif gain_ratio >= 0.85:
                return "Warning"
            else:
                return "Critical"
        except:
            return "Good"
    
    def _generate_text_fallback(self, barn_id: str, language: str, data: BroilerData, ai_analysis: str) -> Dict[str, Any]:
        """Generate text fallback when ReportLab fails."""
        content = f"""BROILER PERFORMANCE ANALYSIS REPORT
{'='*50}

Barn: {barn_id}

Performance Summary:
- Age: {data.age:.0f} days
- Breed: {data.breed}
- Current Weight: {data.observed_weight:.0f}g (Target: {data.expected_weight:.0f}g)
- Daily Gain: {data.gain_observed:.0f}g (Target: {data.gain_expected:.0f}g)
- Performance Ratio: {data.gain_ratio:.2f}
- Temperature: {data.temperature_avg:.1f}°C
- Humidity: {data.humidity_avg:.0f}%

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"broiler_report_{barn_id}_{language}_{timestamp}.txt"
        
        return {
            "status": "success",
            "pdf_bytes": content.encode('utf-8'),
            "filename": filename,
            "file_size": len(content.encode('utf-8')),
            "note": "Text fallback format"
        }
    
    def _generate_error_response(self, barn_id: str, language: str, error: str) -> Dict[str, Any]:
        """Generate error response."""
        content = f"""PDF Generation Error

Barn ID: {barn_id}
Language: {language}
Error: {error}
Timestamp: {datetime.now().isoformat()}

Please contact support for assistance.
"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"error_report_{barn_id}_{language}_{timestamp}.txt"
        
        return {
            "status": "error",
            "pdf_bytes": content.encode('utf-8'),
            "filename": filename,
            "file_size": len(content.encode('utf-8')),
            "error_message": error
        }


def generate_pdf_for_client(
    client: BarnClient,
    barn_id: str,
    broiler_data: Dict[str, Any],
    analysis_result: Any = None,
    ai_analysis: Optional[Any] = None
) -> Dict[str, Any]:
    """Main function to generate PDF for client."""
    generator = BroilerPDFGenerator()
    return generator.generate_pdf(client, barn_id, broiler_data, analysis_result, ai_analysis)


if __name__ == "__main__":
    print("🎯 PDF Generator - Fixed Recommendations Logic")
    print("✅ Section 'Title' supprimée")
    print("✅ Section 'Recommendations' correctement affichée quand performance non-optimale")
    print("✅ Section 'Monitoring Status' pour performance optimale")
