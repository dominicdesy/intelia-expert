"""Email templates for multi-client broiler reports."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Import translation manager with fallback handling
try:
    from core.notifications.translation_manager import get_translation_manager
    TRANSLATION_MANAGER_AVAILABLE = True
except ImportError:
    try:
        from .translation_manager import get_translation_manager
        TRANSLATION_MANAGER_AVAILABLE = True
    except ImportError:
        try:
            from translation_manager import get_translation_manager
            TRANSLATION_MANAGER_AVAILABLE = True
        except ImportError:
            TRANSLATION_MANAGER_AVAILABLE = False
            logger.error("Translation manager not available")

# Import barn client with fallback
try:
    from core.data.barn_list_parser import BarnClient
    BARN_CLIENT_AVAILABLE = True
except ImportError:
    try:
        from .barn_list_parser import BarnClient
        BARN_CLIENT_AVAILABLE = True
    except ImportError:
        BARN_CLIENT_AVAILABLE = False
        @dataclass
        class BarnClient:
            barn_id: str
            language: str
            email: str
            name: Optional[str] = None
            company: Optional[str] = None


@dataclass
class EmailPackage:
    """Email package with delivery components."""
    client: BarnClient
    subject: str
    body_html: str
    body_text: str
    attachments: List[Dict[str, Any]]
    language: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "status": "success",
            "recipient": self.client.email,
            "client_email": self.client.email,
            "language": self.language,
            "subject": self.subject,
            "body_html": self.body_html,
            "body_text": self.body_text,
            "attachments": self.attachments
        }


class MultiLanguageEmailTemplates:
    """Email template manager with multi-language support."""
    
    def __init__(self):
        """Initialize email templates."""
        if not TRANSLATION_MANAGER_AVAILABLE:
            logger.warning("Translation manager not available")
            self.translation_manager = None
        else:
            try:
                self.translation_manager = get_translation_manager()
                logger.info("Translation manager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize translation manager: {e}")
                self.translation_manager = None
    
    def prepare_email_package_for_client(
        self,
        client: BarnClient,
        barn_id: str,
        broiler_data: Dict[str, Any],
        analysis_text: Optional[str] = None,
        pdf_content: Optional[bytes] = None
    ) -> EmailPackage:
        """Generate email package with translated content."""
        language = client.language if hasattr(client, 'language') else 'en'
        current_time = datetime.now()
        
        # Set language for translation manager
        if self.translation_manager:
            try:
                self.translation_manager.set_language(language)
            except Exception as e:
                logger.warning(f"Failed to set language to {language}: {e}")
                language = "en"
        
        # Extract client name from email if not provided
        client_name = getattr(client, 'name', None)
        if not client_name:
            client_name = client.email.split('@')[0].replace('.', ' ').title()
        
        template_variables = {
            "client_name": client_name,
            "company": getattr(client, 'company', None),
            "barn_id": barn_id,
            "date": current_time.strftime("%B %d, %Y"),
            "time": current_time.strftime("%H:%M"),
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "analysis_text": analysis_text
        }
        
        # Build email components
        subject = self._build_subject(barn_id, template_variables, language)
        html_body = self._build_html_body(template_variables, language)
        text_body = self._build_text_body(template_variables, language)
        
        # Prepare attachments
        attachments = []
        if pdf_content:
            timestamp = current_time.strftime("%Y%m%d_%H%M%S")
            attachments.append({
                "filename": f"broiler_report_{barn_id}_{language}_{timestamp}.pdf",
                "content": pdf_content,
                "content_type": "application/pdf"
            })
        
        return EmailPackage(
            client=client,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            attachments=attachments,
            language=language
        )
    
    def _get_translation(self, key: str, **kwargs) -> str:
        """Get translation with safe fallback."""
        if not self.translation_manager:
            logger.warning(f"Translation manager not available for key: {key}")
            return key
        
        try:
            result = self.translation_manager.get(key)
            if result == key:
                logger.warning(f"Translation not found for key: {key}")
                return key
            
            # Handle template formatting
            if kwargs and isinstance(result, str):
                try:
                    return result.format(**kwargs)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Template formatting failed for key '{key}': {e}")
                    return result
            
            return str(result)
        except Exception as e:
            logger.warning(f"Translation error for key '{key}': {e}")
            return key
    
    def _build_subject(self, barn_id: str, template_variables: Dict, language: str) -> str:
        """Build email subject."""
        try:
            subject_template = self._get_translation("email.subject.broiler_analysis")
            house_label = self._get_translation("common.house")
            
            # Build subject with proper formatting
            return f"{subject_template}\n{house_label} #{barn_id}"
            
        except Exception as e:
            logger.error(f"Error building subject: {e}")
            return f"email.subject.broiler_analysis\ncommon.house #{barn_id}"
    
    def _build_html_body(self, template_variables: Dict, language: str) -> str:
        """Build HTML email body."""
        try:
            # Get all translated texts using translation manager
            greeting = self._get_translation("email.greeting.dear", client_name=template_variables['client_name'])
            intro_text = self._get_translation("email.content.intro")
            pdf_instruction = self._get_translation("email.content.pdf_note")
            contact_text = self._get_translation("email.content.support")
            tagline = self._get_translation("email.content.tagline")
            closing = self._get_translation("email.closing.regards")
            team_signature = self._get_translation("email.signature.team")
            generated_text = self._get_translation("email.footer.generated", 
                                                 date=template_variables['date'], 
                                                 time=template_variables['time'])
            house_label = self._get_translation("common.house")
            
            # HTML template structure
            html_template = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._get_translation("email.subject.broiler_analysis")}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333333;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .header h2 {{
            margin: 10px 0 0 0;
            font-size: 18px;
            font-weight: 400;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .greeting {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #2c3e50;
        }}
        .paragraph {{
            margin-bottom: 18px;
            font-size: 15px;
            line-height: 1.7;
        }}
        .highlight {{
            background-color: #e8f5e8;
            border-left: 4px solid #28a745;
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 0 6px 6px 0;
        }}
        .tagline {{
            font-style: italic;
            font-weight: 600;
            color: #6c757d;
            text-align: center;
            margin: 25px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 6px;
        }}
        .signature {{
            margin-top: 30px;
            font-weight: 600;
            color: #2c3e50;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #dee2e6;
            font-size: 12px;
            color: #6c757d;
        }}
        .company-name {{
            color: #667eea;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>{self._get_translation("email.subject.broiler_analysis")}</h1>
            <h2>{house_label} #{template_variables['barn_id']}</h2>
        </div>
        
        <div class="content">
            <div class="greeting">{greeting}</div>
            
            <div class="paragraph">{intro_text}</div>
            
            <div class="highlight">
                <strong>{pdf_instruction}</strong>
            </div>
            
            <div class="paragraph">{contact_text}</div>
            
            <div class="tagline">
                <strong>{tagline}</strong>
            </div>
            
            <div class="signature">
                {closing}<br>
                <span class="company-name">{team_signature}</span>
            </div>
        </div>
        
        <div class="footer">
            {generated_text}
        </div>
    </div>
</body>
</html>"""
            
            return html_template
            
        except Exception as e:
            logger.error(f"Error building HTML body: {e}")
            return self._build_emergency_html(template_variables)
    
    def _build_emergency_html(self, template_variables: Dict) -> str:
        """Emergency HTML template when translation fails."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Broiler Report</title>
</head>
<body style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
    <h1>Broiler Analysis Report</h1>
    <h2>House #{template_variables['barn_id']}</h2>
    <p><strong>Hello {template_variables['client_name']},</strong></p>
    <p>Report attached as PDF.</p>
    <p>Generated on {template_variables['date']} at {template_variables['time']}</p>
</body>
</html>"""
    
    def _build_text_body(self, template_variables: Dict, language: str) -> str:
        """Build text email body."""
        try:
            # Get translated texts using translation manager only
            greeting = self._get_translation("email.greeting.dear", client_name=template_variables['client_name'])
            intro_text = self._get_translation("email.content.intro")
            pdf_instruction = self._get_translation("email.content.pdf_note")
            contact_text = self._get_translation("email.content.support")
            tagline = self._get_translation("email.content.tagline")
            closing = self._get_translation("email.closing.regards")
            team_signature = self._get_translation("email.signature.team")
            generated_text = self._get_translation("email.footer.generated", 
                                                 date=template_variables['date'], 
                                                 time=template_variables['time'])
            house_label = self._get_translation("common.house")
            
            # Text template structure
            text_template = f"""{self._get_translation("email.subject.broiler_analysis")}
{house_label} #{template_variables['barn_id']}

{greeting}

{intro_text}

{pdf_instruction}

{contact_text}

{tagline}

{closing}
{team_signature}

{generated_text}"""
            
            return text_template
            
        except Exception as e:
            logger.error(f"Error building text body: {e}")
            return self._build_emergency_text(template_variables)
    
    def _build_emergency_text(self, template_variables: Dict) -> str:
        """Emergency text template when translation fails."""
        return f"""Broiler Analysis Report
House #{template_variables['barn_id']}

Hello {template_variables['client_name']},

Report attached as PDF.

Generated on {template_variables['date']} at {template_variables['time']}"""


# Global instance
_template_manager = None

def get_template_manager() -> MultiLanguageEmailTemplates:
    """Get the global template manager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = MultiLanguageEmailTemplates()
    return _template_manager


def prepare_email_package_for_client(
    client: BarnClient,
    barn_id: str,
    broiler_data: Dict[str, Any],
    analysis_text: Optional[str] = None,
    pdf_content: Optional[bytes] = None
) -> Dict[str, Any]:
    """Prepare email package for client and return as dict."""
    try:
        manager = get_template_manager()
        package = manager.prepare_email_package_for_client(
            client, barn_id, broiler_data, analysis_text, pdf_content
        )
        result = package.to_dict()
        logger.info(f"Email package prepared successfully for {client.email}")
        return result
    except Exception as e:
        logger.error(f"Error preparing email package: {e}")
        return {
            "status": "error",
            "error": str(e),
            "recipient": getattr(client, 'email', 'unknown'),
            "barn_id": barn_id
        }


def prepare_email_packages_for_barn(
    barn_id: str,
    clients: List[BarnClient],
    broiler_data: Dict[str, Any],
    ai_analyses: Dict[str, str],
    pdf_reports: Dict[str, bytes]
) -> List[Dict[str, Any]]:
    """Prepare email packages for all clients of a barn."""
    packages = []
    
    try:
        manager = get_template_manager()
        
        for client in clients:
            try:
                client_key = f"{client.email}_{client.language}"
                analysis_text = ai_analyses.get(client_key)
                pdf_content = pdf_reports.get(client_key)
                
                package = manager.prepare_email_package_for_client(
                    client, barn_id, broiler_data, analysis_text, pdf_content
                )
                packages.append(package.to_dict())
                logger.info(f"Email package prepared for {client.email}")
                
            except Exception as e:
                logger.error(f"Error preparing package for client {client.email}: {e}")
                packages.append({
                    "status": "error",
                    "error": str(e),
                    "recipient": client.email,
                    "barn_id": barn_id
                })
    
    except Exception as e:
        logger.error(f"Error preparing packages for barn {barn_id}: {e}")
        for client in clients:
            packages.append({
                "status": "error",
                "error": str(e),
                "recipient": client.email,
                "barn_id": barn_id
            })
    
    return packages


def test_email_templates():
    """Test function for email templates."""
    try:
        print("Testing email templates...")
        
        # Create test client
        test_client = BarnClient("604", "en", "dominic.desy@intelia.com")
        if hasattr(test_client, 'name'):
            test_client.name = "Dominic Desy"
        
        test_data = {
            "age": 35,
            "breed": "Ross 308",
            "observed_weight": 2120,
            "expected_weight": 2050,
            "gain_observed": 97,
            "gain_expected": 90
        }
        
        # Test with dummy PDF content
        dummy_pdf = b"dummy pdf content for testing"
        
        result = prepare_email_package_for_client(
            test_client, "604", test_data, "Sample AI analysis text", dummy_pdf
        )
        
        print(f"Email package status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"Subject: {result.get('subject', 'N/A')}")
            print(f"Language: {result.get('language', 'N/A')}")
            print(f"Recipient: {result.get('recipient', 'N/A')}")
            print(f"Attachments: {len(result.get('attachments', []))}")
                
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"Failed to test email templates: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_email_templates()


# Global instance
_template_manager = None

def get_template_manager() -> MultiLanguageEmailTemplates:
    """Get the global template manager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = MultiLanguageEmailTemplates()
    return _template_manager


def prepare_email_package_for_client(
    client: BarnClient,
    barn_id: str,
    broiler_data: Dict[str, Any],
    analysis_text: Optional[str] = None,
    pdf_content: Optional[bytes] = None
) -> Dict[str, Any]:
    """Prepare email package for client and return as dict."""
    try:
        manager = get_template_manager()
        package = manager.prepare_email_package_for_client(
            client, barn_id, broiler_data, analysis_text, pdf_content
        )
        result = package.to_dict()
        logger.info(f"Email package prepared successfully for {client.email} (barn {barn_id}, language {client.language})")
        return result
    except Exception as e:
        logger.error(f"Error preparing email package for {getattr(client, 'email', 'unknown')}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "recipient": getattr(client, 'email', 'unknown'),
            "barn_id": barn_id
        }


def prepare_email_packages_for_barn(
    barn_id: str,
    clients: List[BarnClient],
    broiler_data: Dict[str, Any],
    ai_analyses: Dict[str, str],
    pdf_reports: Dict[str, bytes]
) -> List[Dict[str, Any]]:
    """Prepare email packages for all clients of a barn."""
    packages = []
    
    try:
        manager = get_template_manager()
        
        for client in clients:
            try:
                client_key = f"{client.email}_{client.language}"
                analysis_text = ai_analyses.get(client_key)
                pdf_content = pdf_reports.get(client_key)
                
                package = manager.prepare_email_package_for_client(
                    client, barn_id, broiler_data, analysis_text, pdf_content
                )
                packages.append(package.to_dict())
                logger.info(f"Email package prepared for {client.email} (barn {barn_id})")
                
            except Exception as e:
                logger.error(f"Error preparing package for client {client.email}: {e}")
                packages.append({
                    "status": "error",
                    "error": str(e),
                    "recipient": client.email,
                    "barn_id": barn_id
                })
    
    except Exception as e:
        logger.error(f"Error preparing packages for barn {barn_id}: {e}")
        for client in clients:
            packages.append({
                "status": "error",
                "error": str(e),
                "recipient": client.email,
                "barn_id": barn_id
            })
    
    return packages


def test_email_templates():
    """Test function for email templates."""
    try:
        print("Testing email templates...")
        
        # Create test client
        test_client = BarnClient("604", "en", "dominic.desy@intelia.com")
        if hasattr(test_client, 'name'):
            test_client.name = "Dominic Desy"
        
        test_data = {
            "age": 35,
            "breed": "Ross 308",
            "observed_weight": 2120,
            "expected_weight": 2050,
            "gain_observed": 97,
            "gain_expected": 90
        }
        
        # Test with dummy PDF content
        dummy_pdf = b"dummy pdf content for testing"
        
        result = prepare_email_package_for_client(
            test_client, "604", test_data, "Sample AI analysis text", dummy_pdf
        )
        
        print(f"✅ Email package status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"   Subject: {result.get('subject', 'N/A')}")
            print(f"   Language: {result.get('language', 'N/A')}")
            print(f"   Recipient: {result.get('recipient', 'N/A')}")
            print(f"   Attachments: {len(result.get('attachments', []))}")
            
            # Check if format matches reference
            subject = result.get('subject', '')
            if '🐔 Broiler Analysis Report' in subject and 'House #604' in subject:
                print("✅ Subject format matches reference")
            else:
                print("❌ Subject format doesn't match reference")
                
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Failed to test email templates: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_email_templates()