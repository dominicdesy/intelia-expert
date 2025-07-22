"""
Notifications and communication package.
Handles email templates, PDF generation, and message delivery.
"""

try:
    from .email_templates import prepare_email_package_for_client
    from .microsoft_graph_sender import MicrosoftGraphSender
    from .pdf_generator import generate_pdf_for_client
    from .translation_manager import get_translation_manager
except ImportError:
    pass

__all__ = [
    'prepare_email_package_for_client',
    'MicrosoftGraphSender', 
    'generate_pdf_for_client',
    'get_translation_manager'
]
