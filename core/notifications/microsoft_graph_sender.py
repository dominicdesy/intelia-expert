print("📧📧📧 NOUVEAU EMAIL SENDER LOADED - VERSION 2.0 📧📧📧")
"""Microsoft Graph Email Sender for automated broiler reports."""

import base64
import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MicrosoftGraphSender:
    """Sends emails via Microsoft Graph API with Azure authentication."""
    
    def __init__(self):
        """Initialize Graph sender with configuration from secrets."""
        self.tenant_id = None
        self.client_id = None
        self.client_secret = None
        self.from_email = None
        self.access_token = None
        self.token_expires = None
        self.configured = False
        
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load Microsoft Graph configuration from secrets."""
        try:
            import streamlit as st
            config = st.secrets.get("microsoft_graph", {})
            
            self.tenant_id = config.get("tenant_id") or st.secrets.get("microsoft_graph_tenant_id")
            self.client_id = config.get("client_id") or st.secrets.get("microsoft_graph_client_id")
            self.client_secret = config.get("client_secret") or st.secrets.get("microsoft_graph_client_secret")
            self.from_email = config.get("from_email") or st.secrets.get("microsoft_graph_from_email")
            
        except ImportError:
            # Fallback for non-Streamlit environments
            try:
                import toml
                with open(".streamlit/secrets.toml", "r") as f:
                    secrets = toml.load(f)
                
                self.tenant_id = secrets.get("microsoft_graph_tenant_id")
                self.client_id = secrets.get("microsoft_graph_client_id") 
                self.client_secret = secrets.get("microsoft_graph_client_secret")
                self.from_email = secrets.get("microsoft_graph_from_email")
            except:
                # Manual TOML parsing fallback
                self._parse_secrets_file()
        
        # Validate configuration
        required_fields = [self.tenant_id, self.client_id, self.client_secret, self.from_email]
        self.configured = all(field and field.strip() for field in required_fields)
        
        if self.configured:
            logger.info(f"Microsoft Graph configured for {self.from_email}")
        else:
            logger.warning("Microsoft Graph configuration incomplete")
    
    def _parse_secrets_file(self) -> None:
        """Manually parse secrets.toml when toml library unavailable."""
        try:
            with open(".streamlit/secrets.toml", "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        if key == "microsoft_graph_tenant_id":
                            self.tenant_id = value
                        elif key == "microsoft_graph_client_id":
                            self.client_id = value
                        elif key == "microsoft_graph_client_secret":
                            self.client_secret = value
                        elif key == "microsoft_graph_from_email":
                            self.from_email = value
        except Exception as e:
            logger.error(f"Failed to parse secrets file: {e}")
    
    def _get_access_token(self) -> Optional[str]:
        """Obtain or refresh Microsoft Graph access token."""
        if not self.configured:
            logger.error("Microsoft Graph not configured")
            return None
        
        # Check if current token is still valid
        if self.access_token and self.token_expires:
            if datetime.now() < self.token_expires - timedelta(minutes=5):
                return self.access_token
        
        # Request new token
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        token_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default"
        }
        
        try:
            response = requests.post(token_url, data=token_data, timeout=30)
            response.raise_for_status()
            
            token_response = response.json()
            self.access_token = token_response["access_token"]
            expires_in = token_response.get("expires_in", 3600)
            self.token_expires = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("Microsoft Graph access token obtained")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to obtain access token: {e}")
            return None
    
    def send_email(
        self, 
        to: str, 
        subject: str, 
        body: str, 
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send email via Microsoft Graph API."""
        if not self.configured:
            logger.error("Microsoft Graph not configured - cannot send email")
            return False
        
        access_token = self._get_access_token()
        if not access_token:
            logger.error("Could not obtain access token")
            return False
        
        # Build email message
        message = self._build_email_message(to, subject, body, body_html, attachments)
        
        # Send email via Graph API
        return self._send_via_graph_api(message, access_token)
    
    def _build_email_message(
        self,
        to: str,
        subject: str, 
        body: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Build email message structure for Graph API."""
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if body_html else "Text",
                    "content": body_html or body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to
                        }
                    }
                ],
                "from": {
                    "emailAddress": {
                        "address": self.from_email
                    }
                }
            }
        }
        
        # Add attachments if provided
        if attachments:
            message["message"]["attachments"] = []
            for attachment in attachments:
                graph_attachment = self._convert_attachment_to_graph_format(attachment)
                if graph_attachment:
                    message["message"]["attachments"].append(graph_attachment)
        
        return message
    
    def _convert_attachment_to_graph_format(self, attachment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert attachment to Microsoft Graph format."""
        try:
            content = attachment.get("content")
            if isinstance(content, bytes):
                encoded_content = base64.b64encode(content).decode('utf-8')
            else:
                logger.warning(f"Invalid attachment content type: {type(content)}")
                return None
            
            return {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": attachment.get("filename", "attachment.pdf"),
                "contentType": attachment.get("content_type", "application/pdf"),
                "contentBytes": encoded_content
            }
        except Exception as e:
            logger.error(f"Failed to convert attachment: {e}")
            return None
    
    def _send_via_graph_api(self, message: Dict[str, Any], access_token: str) -> bool:
        """Send email message via Microsoft Graph API."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        graph_url = f"https://graph.microsoft.com/v1.0/users/{self.from_email}/sendMail"
        
        try:
            response = requests.post(graph_url, json=message, headers=headers, timeout=60)
            
            if response.status_code == 202:
                logger.info(f"Email sent successfully to {message['message']['toRecipients'][0]['emailAddress']['address']}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email via Graph API: {e}")
            return False
    
    def send_email_with_package(self, email_package: Dict[str, Any]) -> bool:
        """Send email using prepared email package."""
        try:
            recipient = email_package.get("recipient") or email_package.get("client_email")
            subject = email_package.get("subject", "Broiler Analysis Report")
            body_text = email_package.get("body_text", "")
            body_html = email_package.get("body_html")
            attachments = email_package.get("attachments", [])
            
            if not recipient:
                logger.error("No recipient specified in email package")
                return False
            
            return self.send_email(recipient, subject, body_text, body_html, attachments)
            
        except Exception as e:
            logger.error(f"Failed to send email with package: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test Microsoft Graph connection."""
        if not self.configured:
            return False
        
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        # Test API call to verify connection
        headers = {"Authorization": f"Bearer {access_token}"}
        test_url = f"https://graph.microsoft.com/v1.0/users/{self.from_email}"
        
        try:
            response = requests.get(test_url, headers=headers, timeout=30)
            return response.status_code == 200
        except:
            return False


def send_email(to: str, subject: str, body: str) -> bool:
    """Convenience function for sending simple emails."""
    sender = MicrosoftGraphSender()
    return sender.send_email(to, subject, body)