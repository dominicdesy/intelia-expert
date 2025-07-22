print("🚀🚀🚀 NOUVEAU ORCHESTRATOR LOADED - VERSION 2.0 🚀🚀🚀")
"""Multi-client report orchestrator with automated email delivery."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import logging

logger = logging.getLogger(__name__)

# Component availability flags
BARN_LIST_PARSER_AVAILABLE = False
AI_CLIENT_AVAILABLE = False
PDF_GENERATOR_AVAILABLE = False
EMAIL_TEMPLATES_AVAILABLE = False
ANALYZER_AVAILABLE = False
BARN_DIAGNOSTICS_AVAILABLE = False
RAG_AI_BRIDGE_AVAILABLE = False
MICROSOFT_GRAPH_AVAILABLE = False

def try_import_with_fallbacks():
    """Import modules with fallback handling."""
    global BARN_LIST_PARSER_AVAILABLE, AI_CLIENT_AVAILABLE, PDF_GENERATOR_AVAILABLE
    global EMAIL_TEMPLATES_AVAILABLE, ANALYZER_AVAILABLE, BARN_DIAGNOSTICS_AVAILABLE
    global RAG_AI_BRIDGE_AVAILABLE, MICROSOFT_GRAPH_AVAILABLE
    global BarnClient, get_clients_for_barn, RAGPoweredAIAnalyzer, EnhancedAnalysisResult
    global generate_pdf_for_client, prepare_email_package_for_client
    global BroilerAnalyzer, get_status_system, BarnDiagnostics, RAGAIBridge, MicrosoftGraphSender
    
    # Import barn list parser
    try:
        try:
            from .barn_list_parser import BarnClient, get_clients_for_barn
        except ImportError:
            from core.data.barn_list_parser import BarnClient, get_clients_for_barn
        BARN_LIST_PARSER_AVAILABLE = True
        logger.info("BarnListParser imported")
    except ImportError as e:
        logger.warning(f"BarnListParser import failed: {e}")
        @dataclass
        class BarnClient:
            barn_id: str
            language: str
            email: str
        
        def get_clients_for_barn(barn_id):
            return [BarnClient(barn_id, "en", "test@example.com")]
    
    # Import AI client
    try:
        try:
            from .ai_client import RAGPoweredAIAnalyzer, EnhancedAnalysisResult
        except ImportError:
            from core.ai.ai_client import RAGPoweredAIAnalyzer, EnhancedAnalysisResult
        AI_CLIENT_AVAILABLE = True
        logger.info("AIClient imported")
    except ImportError as e:
        logger.warning(f"AIClient import failed: {e}")
        @dataclass
        class EnhancedAnalysisResult:
            client_email: str
            language: str
            analysis_text: str
            success: bool
            rag_context_used: bool = False
        
        class RAGPoweredAIAnalyzer:
            def __init__(self, *args, **kwargs):
                logger.warning("Using fallback RAGPoweredAIAnalyzer")
            
            def get_expert_analysis_for_client(self, *args, **kwargs):
                return "Fallback analysis - AI system not available"
            
            def get_system_statistics(self):
                return {"system_availability": {"rag_bridge": False}}
    
    # Import PDF generator
    try:
        try:
            from .pdf_generator import generate_pdf_for_client
        except ImportError:
            from core.notifications.pdf_generator import generate_pdf_for_client
        PDF_GENERATOR_AVAILABLE = True
        logger.info("PDFGenerator imported")
    except ImportError as e:
        logger.warning(f"PDFGenerator import failed: {e}")
        def generate_pdf_for_client(*args, **kwargs):
            return {"status": "error", "error": "PDF generation not available"}
    
    # Import email templates
    try:
        try:
            from .email_templates import prepare_email_package_for_client
        except ImportError:
            from core.notifications.email_templates import prepare_email_package_for_client
        EMAIL_TEMPLATES_AVAILABLE = True
        logger.info("EmailTemplates imported")
    except ImportError as e:
        logger.warning(f"EmailTemplates import failed: {e}")
        def prepare_email_package_for_client(*args, **kwargs):
            return {"status": "error", "error": "Email templates not available"}
    
    # Import Microsoft Graph sender
    try:
        try:
            from .microsoft_graph_sender import MicrosoftGraphSender
        except ImportError:
            from core.notifications.microsoft_graph_sender import MicrosoftGraphSender
        MICROSOFT_GRAPH_AVAILABLE = True
        logger.info("MicrosoftGraphSender imported")
    except ImportError as e:
        logger.warning(f"MicrosoftGraphSender import failed: {e}")
        class MicrosoftGraphSender:
            def __init__(self):
                self.configured = False
            def send_email_with_package(self, package):
                return False
            def test_connection(self):
                return False
    
    # Import analyzer
    try:
        try:
            from .analyzer import BroilerAnalyzer, get_status_system
        except ImportError:
            from core.analysis.analyzer import BroilerAnalyzer, get_status_system
        ANALYZER_AVAILABLE = True
        logger.info("Analyzer imported")
    except ImportError as e:
        logger.warning(f"Analyzer import failed: {e}")
        class BroilerAnalyzer:
            def __init__(self, *args, **kwargs):
                logger.warning("Using fallback BroilerAnalyzer")
            def analyze_barn(self, barn_id):
                return None
        def get_status_system():
            return None
    
    # Import barn diagnostics
    try:
        try:
            from core.analysis.barn_diagnostics import BarnDiagnostics
        except ImportError:
            from core.analysis.barn_diagnostics import BarnDiagnostics
        BARN_DIAGNOSTICS_AVAILABLE = True
        logger.info("BarnDiagnostics imported")
    except ImportError as e:
        logger.warning(f"BarnDiagnostics import failed: {e}")
        class BarnDiagnostics:
            def __init__(self, *args, **kwargs):
                logger.warning("Using fallback BarnDiagnostics")
            def run_diagnostics(self, barn_id):
                return {"status": "unavailable", "overall_score": 75.0}
    
    # Import RAG AI bridge
    try:
        try:
            from core.ai.rag_ai_bridge import RAGAIBridge
        except ImportError:
            from core.ai.rag_ai_bridge import RAGAIBridge
        RAG_AI_BRIDGE_AVAILABLE = True
        logger.info("RAGAIBridge imported")
    except ImportError as e:
        logger.warning(f"RAGAIBridge import failed: {e}")
        class RAGAIBridge:
            def __init__(self, *args, **kwargs):
                logger.warning("Using fallback RAGAIBridge")
                self.rag_available = False
            def is_available(self):
                return False
            def get_debug_info(self):
                return {"error": "RAG Bridge not available"}

try_import_with_fallbacks()


@dataclass
class EnhancedClientReportResult:
    """Result for each client report with metadata."""
    client: BarnClient
    status: str  # "success", "failed", "warning"
    ai_analysis: Optional[str] = None
    pdf_bytes: Optional[bytes] = None
    pdf_filename: Optional[str] = None
    email_package: Optional[Dict] = None
    email_sent: bool = False
    error_message: Optional[str] = None
    processing_time: float = 0.0
    language: str = "en"
    
    # Analytics metadata
    rag_context_used: bool = False
    weather_integrated: bool = False
    expert_sources_count: int = 0
    analysis_confidence: float = 0.0
    analysis_mode: str = "standard"
    source_documents: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "client_email": self.client.email,
            "language": self.language,
            "status": self.status,
            "has_ai_analysis": bool(self.ai_analysis),
            "has_pdf": bool(self.pdf_bytes),
            "has_email_package": bool(self.email_package),
            "email_sent": self.email_sent,
            "error_message": self.error_message,
            "processing_time": self.processing_time,
            "pdf_filename": self.pdf_filename,
            "rag_context_used": self.rag_context_used,
            "weather_integrated": self.weather_integrated,
            "expert_sources_count": self.expert_sources_count,
            "analysis_confidence": self.analysis_confidence,
            "analysis_mode": self.analysis_mode,
            "analysis_quality": "expert" if self.rag_context_used else "standard",
            "has_expert_sources": len(self.source_documents) > 0
        }


@dataclass
class EnhancedOrchestrationResult:
    """Orchestration result with analytics."""
    barn_id: str
    total_clients: int
    successful_reports: int
    failed_reports: int
    emails_sent: int = 0
    client_results: List[EnhancedClientReportResult] = field(default_factory=list)
    total_processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Analytics
    barn_health_score: float = 0.0
    critical_issues: List[str] = field(default_factory=list)
    overall_status: str = "unknown"
    rag_system_available: bool = False
    weather_system_available: bool = False
    email_system_available: bool = False
    expert_analysis_count: int = 0
    average_confidence: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_clients == 0:
            return 0.0
        return (self.successful_reports / self.total_clients) * 100
    
    @property
    def email_delivery_rate(self) -> float:
        """Calculate email delivery rate percentage."""
        if self.total_clients == 0:
            return 0.0
        return (self.emails_sent / self.total_clients) * 100
    
    @property
    def expert_analysis_rate(self) -> float:
        """Calculate percentage of expert analyses."""
        if self.total_clients == 0:
            return 0.0
        return (self.expert_analysis_count / self.total_clients) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "barn_id": self.barn_id,
            "total_clients": self.total_clients,
            "successful_reports": self.successful_reports,
            "failed_reports": self.failed_reports,
            "emails_sent": self.emails_sent,
            "success_rate": self.success_rate,
            "email_delivery_rate": self.email_delivery_rate,
            "total_processing_time": self.total_processing_time,
            "client_results": [r.to_dict() for r in self.client_results],
            "errors": self.errors,
            "warnings": self.warnings,
            "barn_health_score": self.barn_health_score,
            "critical_issues": self.critical_issues,
            "overall_status": self.overall_status,
            "expert_analysis_rate": self.expert_analysis_rate,
            "average_confidence": self.average_confidence,
            "system_capabilities": {
                "rag_system_available": self.rag_system_available,
                "weather_system_available": self.weather_system_available,
                "email_system_available": self.email_system_available,
                "expert_analysis_count": self.expert_analysis_count
            }
        }


class RAGEnabledMultiClientOrchestrator:
    """Orchestrator with RAG analysis and automated email delivery."""
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        claude_api_key: Optional[str] = None,
        default_ai_model: str = "gpt-4o",
        max_concurrent_jobs: int = 5,
        timeout_per_client: int = 120,
        api_client=None
    ):
        """Initialize orchestrator."""
        self.openai_api_key = openai_api_key
        self.claude_api_key = claude_api_key
        self.default_ai_model = default_ai_model
        self.max_concurrent_jobs = max_concurrent_jobs
        self.timeout_per_client = timeout_per_client
        self.api_client = api_client
        
        self._initialize_components()
        
        logger.info(f"Multi-Client Orchestrator ready - Model: {default_ai_model}")
        logger.info(f"Components: RAG={self.rag_available}, AI={self.ai_available}, Email={self.email_available}")
    
    def _initialize_components(self):
        """Initialize all components."""
        # Initialize AI analyzer
        if AI_CLIENT_AVAILABLE:
            try:
                self.ai_analyzer = RAGPoweredAIAnalyzer(
                    openai_api_key=self.openai_api_key,
                    claude_api_key=self.claude_api_key,
                    default_model=self.default_ai_model
                )
                self.ai_available = True
                logger.info("AI analyzer initialized")
            except Exception as e:
                logger.error(f"Failed to initialize AI analyzer: {e}")
                self.ai_analyzer = RAGPoweredAIAnalyzer()
                self.ai_available = False
        else:
            logger.warning("AI Client not available")
            self.ai_analyzer = RAGPoweredAIAnalyzer()
            self.ai_available = False
        
        # Initialize broiler analyzer
        if ANALYZER_AVAILABLE:
            try:
                self.broiler_analyzer = BroilerAnalyzer(self.api_client)
                self.status_system = get_status_system()
                logger.info("Broiler analyzer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize broiler analyzer: {e}")
                self.broiler_analyzer = BroilerAnalyzer()
                self.status_system = None
        else:
            logger.warning("Analyzer not available")
            self.broiler_analyzer = BroilerAnalyzer()
            self.status_system = None
        
        # Initialize barn diagnostics
        if BARN_DIAGNOSTICS_AVAILABLE:
            try:
                self.barn_diagnostics = BarnDiagnostics(self.api_client)
                logger.info("Barn diagnostics initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize barn diagnostics: {e}")
                self.barn_diagnostics = BarnDiagnostics()
        else:
            logger.warning("Barn Diagnostics not available")
            self.barn_diagnostics = BarnDiagnostics()
        
        # Initialize RAG bridge
        if RAG_AI_BRIDGE_AVAILABLE and self.openai_api_key:
            try:
                self.rag_bridge = RAGAIBridge(self.openai_api_key)
                self.rag_available = self.rag_bridge.is_available()
                logger.info("RAG bridge initialized")
            except Exception as e:
                logger.warning(f"RAG bridge failed: {e}")
                self.rag_bridge = RAGAIBridge()
                self.rag_available = False
        else:
            logger.warning("RAG Bridge not available")
            self.rag_bridge = RAGAIBridge()
            self.rag_available = False
        
        # Initialize Microsoft Graph email sender
        if MICROSOFT_GRAPH_AVAILABLE:
            try:
                self.email_sender = MicrosoftGraphSender()
                self.email_available = self.email_sender.test_connection()
                if self.email_available:
                    logger.info("Microsoft Graph email sender ready")
                else:
                    logger.warning("Microsoft Graph configured but connection test failed")
            except Exception as e:
                logger.error(f"Failed to initialize email sender: {e}")
                self.email_sender = MicrosoftGraphSender()
                self.email_available = False
        else:
            logger.warning("Microsoft Graph sender not available")
            self.email_sender = MicrosoftGraphSender()
            self.email_available = False
    
    def generate_enhanced_reports_for_barn(
        self,
        barn_id: str,
        broiler_data: Optional[Dict[str, Any]] = None,
        analysis_result: Any = None,
        include_pdf: bool = True,
        include_email: bool = True,
        include_diagnostics: bool = True
    ) -> EnhancedOrchestrationResult:
        """Generate and deliver reports for all clients of a barn."""
        start_time = datetime.now()
        
        try:
            # Get clients for barn
            if BARN_LIST_PARSER_AVAILABLE:
                clients = get_clients_for_barn(barn_id)
            else:
                logger.warning(f"BarnListParser not available, using mock client for {barn_id}")
                clients = [BarnClient(barn_id, "en", "test@example.com")]
            
            if not clients:
                return EnhancedOrchestrationResult(
                    barn_id=barn_id,
                    total_clients=0,
                    successful_reports=0,
                    failed_reports=0,
                    errors=[f"No clients found for barn {barn_id}"]
                )
            
            logger.info(f"Processing barn {barn_id} with {len(clients)} clients")
            
            # Get barn analysis if not provided
            if not analysis_result and ANALYZER_AVAILABLE:
                logger.info("Performing barn analysis")
                try:
                    analysis_result = self.broiler_analyzer.analyze_barn(barn_id)
                    if analysis_result:
                        logger.info(f"Analysis completed: {analysis_result.deviation_level} status")
                        
                        # Extract broiler data from analysis result
                        if not broiler_data:
                            broiler_data = {
                                'age': analysis_result.age,
                                'breed': analysis_result.breed,
                                'observed_weight': analysis_result.observed_weight,
                                'expected_weight': analysis_result.expected_weight,
                                'gain_observed': analysis_result.observed_gain,
                                'gain_expected': analysis_result.expected_gain,
                                'gain_ratio': analysis_result.gain_ratio,
                                'temperature_avg': analysis_result.environmental_metrics.temperature_avg if analysis_result.environmental_metrics else 25,
                                'humidity_avg': analysis_result.environmental_metrics.humidity_avg if analysis_result.environmental_metrics else 60
                            }
                except Exception as e:
                    logger.warning(f"Barn analysis failed: {e}")
            
            # Use fallback data if needed
            if not broiler_data:
                broiler_data = {
                    'age': 35,
                    'breed': 'Ross 308',
                    'observed_weight': 2000,
                    'expected_weight': 2100,
                    'gain_observed': 85,
                    'gain_expected': 90,
                    'gain_ratio': 0.94,
                    'temperature_avg': 25,
                    'humidity_avg': 60
                }
                logger.info("Using fallback broiler data")
            
            # Get barn diagnostics
            barn_health_score = 75.0
            critical_issues = []
            overall_status = "unknown"
            
            if include_diagnostics and BARN_DIAGNOSTICS_AVAILABLE:
                try:
                    diagnostics_result = self.barn_diagnostics.run_diagnostics(barn_id)
                    barn_health_score = diagnostics_result.get('overall_score', 75.0)
                    critical_issues = diagnostics_result.get('issues', [])
                    overall_status = diagnostics_result.get('status', 'unknown')
                    logger.info(f"Barn diagnostics: {overall_status} (score: {barn_health_score:.1f})")
                except Exception as e:
                    logger.warning(f"Barn diagnostics failed: {e}")
            
            # Process clients
            client_results = self._process_clients_with_delivery(
                clients, barn_id, broiler_data, analysis_result, 
                include_pdf, include_email
            )
            
            # Calculate results
            successful = sum(1 for r in client_results if r.status == "success")
            failed = sum(1 for r in client_results if r.status == "failed")
            emails_sent = sum(1 for r in client_results if r.email_sent)
            expert_analysis_count = sum(1 for r in client_results if r.rag_context_used)
            
            # Calculate average confidence
            confidence_scores = [r.analysis_confidence for r in client_results if r.analysis_confidence > 0]
            average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            
            result = EnhancedOrchestrationResult(
                barn_id=barn_id,
                total_clients=len(clients),
                successful_reports=successful,
                failed_reports=failed,
                emails_sent=emails_sent,
                client_results=client_results,
                total_processing_time=total_time,
                barn_health_score=barn_health_score,
                critical_issues=critical_issues,
                overall_status=overall_status,
                rag_system_available=self.rag_available,
                weather_system_available=True,
                email_system_available=self.email_available,
                expert_analysis_count=expert_analysis_count,
                average_confidence=average_confidence
            )
            
            logger.info(f"Barn {barn_id} processing completed:")
            logger.info(f"Success: {successful}/{len(clients)}, Emails: {emails_sent}/{len(clients)}")
            logger.info(f"Expert analyses: {expert_analysis_count}, Health: {barn_health_score:.1f}")
            
            return result
        
        except Exception as e:
            logger.error(f"Orchestration failed for barn {barn_id}: {e}")
            return EnhancedOrchestrationResult(
                barn_id=barn_id,
                total_clients=0,
                successful_reports=0,
                failed_reports=1,
                errors=[f"Orchestration failed: {str(e)}"],
                overall_status="error"
            )
    
    def _process_clients_with_delivery(
        self,
        clients: List[BarnClient],
        barn_id: str,
        broiler_data: Dict[str, Any],
        analysis_result: Any,
        include_pdf: bool,
        include_email: bool
    ) -> List[EnhancedClientReportResult]:
        """Process multiple clients with AI analysis and email delivery."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent_jobs) as executor:
            # Submit client processing jobs
            future_to_client = {
                executor.submit(
                    self._process_single_client_with_delivery,
                    client, barn_id, broiler_data, analysis_result, include_pdf, include_email
                ): client
                for client in clients
            }
            
            # Collect results
            for future in as_completed(future_to_client, timeout=self.timeout_per_client * len(clients)):
                client = future_to_client[future]
                try:
                    result = future.result(timeout=self.timeout_per_client)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process client {client.email}: {e}")
                    results.append(EnhancedClientReportResult(
                        client=client,
                        status="failed",
                        error_message=str(e),
                        language=client.language,
                        analysis_mode="error"
                    ))
        
        return results
    
    def _process_single_client_with_delivery(
        self,
        client: BarnClient,
        barn_id: str,
        broiler_data: Dict[str, Any],
        analysis_result: Any,
        include_pdf: bool,
        include_email: bool
    ) -> EnhancedClientReportResult:
        """Process single client with analysis, PDF generation, and email delivery."""
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing client {client.email} (language: {client.language})")
            
            result = EnhancedClientReportResult(
                client=client,
                status="success",
                language=client.language
            )
            
            # Generate AI analysis
            if self.ai_available and AI_CLIENT_AVAILABLE:
                try:
                    logger.info(f"Generating AI analysis for {client.email}")
                    
                    ai_analysis = self.ai_analyzer.get_expert_analysis_for_client(
                        barn_id, client.email, broiler_data, client.language
                    )
                    
                    if ai_analysis:
                        result.ai_analysis = ai_analysis
                        
                        # Get analysis metadata
                        try:
                            system_stats = self.ai_analyzer.get_system_statistics()
                            
                            if system_stats.get("system_availability", {}).get("rag_bridge", False):
                                result.rag_context_used = True
                                result.analysis_mode = "expert"
                                result.analysis_confidence = 0.85
                            else:
                                result.analysis_mode = "standard"
                                result.analysis_confidence = 0.65
                        except Exception as e:
                            logger.debug(f"Could not get system stats: {e}")
                            result.analysis_mode = "standard"
                            result.analysis_confidence = 0.65
                        
                        logger.info(f"AI analysis completed for {client.email} (mode: {result.analysis_mode})")
                    else:
                        result.ai_analysis = "Analysis could not be generated."
                        result.analysis_mode = "fallback"
                        logger.warning(f"AI analysis failed for {client.email}")
                        
                except Exception as e:
                    logger.error(f"AI analysis failed for {client.email}: {e}")
                    result.ai_analysis = f"Analysis error: {str(e)}"
                    result.analysis_mode = "error"
            else:
                result.ai_analysis = "AI analysis not available."
                result.analysis_mode = "unavailable"
                logger.warning(f"AI analyzer not available for {client.email}")
            
            # Generate PDF
            if include_pdf and PDF_GENERATOR_AVAILABLE:
                try:
                    pdf_data = generate_pdf_for_client(
                        client, barn_id, broiler_data, analysis_result, result.ai_analysis
                    )
                    result.pdf_bytes = pdf_data.get("pdf_bytes")
                    result.pdf_filename = pdf_data.get("filename")
                    
                    if result.pdf_bytes:
                        logger.info(f"PDF generated for {client.email}: {len(result.pdf_bytes)} bytes")
                    
                except Exception as e:
                    logger.warning(f"PDF generation failed for {client.email}: {e}")
                    result.error_message = f"PDF generation failed: {str(e)}"
                    if result.status == "success":
                        result.status = "warning"
            elif include_pdf:
                logger.warning(f"PDF generation requested but not available for {client.email}")
                result.error_message = "PDF generation not available"
                if result.status == "success":
                    result.status = "warning"
            
            # Prepare and send email
            if include_email and EMAIL_TEMPLATES_AVAILABLE and self.email_available:
                try:
                    # Prepare email package
                    email_package = prepare_email_package_for_client(
                        client, barn_id, broiler_data, result.ai_analysis, result.pdf_bytes
                    )
                    result.email_package = email_package
                    
                    # Send email via Microsoft Graph
                    if email_package.get("status") == "success":
                        email_sent = self.email_sender.send_email_with_package(email_package)
                        result.email_sent = email_sent
                        
                        if email_sent:
                            logger.info(f"Email sent successfully to {client.email}")
                        else:
                            logger.error(f"Failed to send email to {client.email}")
                            if result.status == "success":
                                result.status = "warning"
                            result.error_message = "Email delivery failed"
                    else:
                        logger.error(f"Email package preparation failed for {client.email}")
                        if result.status == "success":
                            result.status = "warning"
                        result.error_message = "Email preparation failed"
                    
                except Exception as e:
                    logger.warning(f"Email processing failed for {client.email}: {e}")
                    if result.status == "success":
                        result.status = "warning"
                    result.error_message = f"Email processing failed: {str(e)}"
            elif include_email:
                if not EMAIL_TEMPLATES_AVAILABLE:
                    logger.warning(f"Email requested but templates not available for {client.email}")
                    result.error_message = "Email templates not available"
                elif not self.email_available:
                    logger.warning(f"Email requested but sender not available for {client.email}")
                    result.error_message = "Email sender not available"
                else:
                    logger.warning(f"Email requested but conditions not met for {client.email}")
                    result.error_message = "Email service not ready"
                
                if result.status == "success":
                    result.status = "warning"
            
            # Calculate processing time
            end_time = datetime.now()
            result.processing_time = (end_time - start_time).total_seconds()
            
            status_emoji = "✅" if result.email_sent else "📄" if result.pdf_bytes else "⚠️"
            logger.info(f"{status_emoji} Client {client.email} processed in {result.processing_time:.1f}s "
                       f"(RAG: {result.rag_context_used}, Email: {result.email_sent})")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to process client {client.email}: {e}")
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            return EnhancedClientReportResult(
                client=client,
                status="failed",
                error_message=str(e),
                processing_time=processing_time,
                language=client.language,
                analysis_mode="error"
            )
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """Get system health report."""
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        components = {
            "barn_list_parser": BARN_LIST_PARSER_AVAILABLE,
            "ai_client": AI_CLIENT_AVAILABLE,
            "pdf_generator": PDF_GENERATOR_AVAILABLE,
            "email_templates": EMAIL_TEMPLATES_AVAILABLE,
            "analyzer": ANALYZER_AVAILABLE,
            "barn_diagnostics": BARN_DIAGNOSTICS_AVAILABLE,
            "rag_ai_bridge": RAG_AI_BRIDGE_AVAILABLE,
            "microsoft_graph": MICROSOFT_GRAPH_AVAILABLE
        }
        
        for component, available in components.items():
            if available:
                health_report["components"][component] = {
                    "status": "healthy",
                    "details": f"{component} operational"
                }
            else:
                health_report["components"][component] = {
                    "status": "unavailable",
                    "details": f"{component} using fallback"
                }
                if health_report["overall_status"] == "healthy":
                    health_report["overall_status"] = "degraded"
        
        # Check systems
        health_report["components"]["rag_system"] = {
            "status": "healthy" if self.rag_available else "unavailable",
            "details": "RAG available" if self.rag_available else "RAG unavailable"
        }
        
        health_report["components"]["ai_system"] = {
            "status": "healthy" if self.ai_available else "unavailable",
            "details": f"AI {self.default_ai_model}" if self.ai_available else "AI unavailable"
        }
        
        health_report["components"]["email_system"] = {
            "status": "healthy" if self.email_available else "unavailable",
            "details": "Email delivery ready" if self.email_available else "Email delivery unavailable"
        }
        
        if not self.ai_available:
            health_report["overall_status"] = "critical"
        
        return health_report


class MultiClientReportOrchestrator(RAGEnabledMultiClientOrchestrator):
    """Backward compatibility wrapper."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("Using compatibility wrapper")
    
    def generate_reports_for_barn(self, *args, **kwargs):
        """Compatibility method."""
        return self.generate_enhanced_reports_for_barn(*args, **kwargs)


def generate_rag_enhanced_reports(
    barn_id: str,
    broiler_data: Optional[Dict[str, Any]] = None,
    analysis_result: Any = None,
    openai_api_key: Optional[str] = None,
    claude_api_key: Optional[str] = None,
    include_diagnostics: bool = True
) -> EnhancedOrchestrationResult:
    """Convenience function for generating reports."""
    orchestrator = RAGEnabledMultiClientOrchestrator(
        openai_api_key=openai_api_key,
        claude_api_key=claude_api_key
    )
    
    return orchestrator.generate_enhanced_reports_for_barn(
        barn_id, broiler_data, analysis_result, 
        include_diagnostics=include_diagnostics
    )


def validate_system_configuration() -> Dict[str, Any]:
    """Validate system configuration."""
    return {
        "status": "available" if EMAIL_TEMPLATES_AVAILABLE and MICROSOFT_GRAPH_AVAILABLE else "unavailable",
        "components": {
            "email_templates": EMAIL_TEMPLATES_AVAILABLE,
            "microsoft_graph": MICROSOFT_GRAPH_AVAILABLE,
            "ai_client": AI_CLIENT_AVAILABLE,
            "pdf_generator": PDF_GENERATOR_AVAILABLE
        }
    }