#!/usr/bin/env python3
"""
Centralized Logging Manager for Broiler Analysis System
Manages all system logging with proper paths, formatting, and translation support.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass

# Import translation manager with fallback
try:
    from core.notifications.translation_manager import get_translation_manager
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    def get_translation_manager():
        return None


class LogCategory(Enum):
    """Log categories for better organization."""
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_EVENT = "system_event"
    BARN_VALIDATION = "barn_validation"
    BARN_CLIENTS_LOADED = "barn_clients_loaded"
    ORCHESTRATION_RESULT = "orchestration_result"
    CLIENT_REPORT_SUCCESS = "client_report_success"
    BATCH_COMPLETE = "batch_complete"
    PRODUCTION_CHECK = "production_check"
    DATA_QUALITY = "data_quality"
    ANALYSIS_SUCCESS = "analysis_success"
    EMAIL_OPERATION = "email_operation"
    API_OPERATION = "api_operation"
    ALERT_EVALUATION = "alert_evaluation"
    MONITORING_CYCLE = "monitoring_cycle"
    CONFIG_LOADED = "config_loaded"
    ERROR_HANDLER = "error_handler"
    DEBUG_INFO = "debug_info"


@dataclass
class LogConfig:
    """Configuration for logging setup."""
    logs_dir: Path
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    log_format: str = "%(asctime)s | %(levelname)-8s | %(category)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    encoding: str = "utf-8"
    
    def __post_init__(self):
        """Ensure logs directory exists."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)


class CustomLogFormatter(logging.Formatter):
    """Custom formatter with category support and translation."""
    
    def __init__(self, fmt: str, datefmt: str = None, translation_manager=None):
        super().__init__(fmt, datefmt)
        self.translation_manager = translation_manager
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with category and translation support."""
        # Add category if not present
        if not hasattr(record, 'category'):
            record.category = LogCategory.SYSTEM_EVENT.value.upper()
        
        # Translate message if translation manager is available
        if self.translation_manager and hasattr(record, 'translate_key'):
            try:
                translated = self.translation_manager.get(
                    record.translate_key, 
                    getattr(record, 'language', 'en')
                )
                if translated != record.translate_key:
                    record.msg = translated
            except Exception:
                pass  # Use original message if translation fails
        
        return super().format(record)


class BroilerLoggingManager:
    """Centralized logging manager for the broiler analysis system."""
    
    def __init__(self, config: Optional[LogConfig] = None):
        """Initialize logging manager."""
        self.project_root = Path.cwd()
        self.logs_dir = self.project_root / "logs"
        
        if config:
            self.config = config
        else:
            self.config = LogConfig(logs_dir=self.logs_dir)
        
        self.translation_manager = get_translation_manager() if TRANSLATION_AVAILABLE else None
        self.loggers: Dict[str, logging.Logger] = {}
        
        # Ensure logs directory exists
        self.config.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file mappings
        self.log_files = {
            'daily_analysis': self.config.logs_dir / 'broiler_auto.log',
            'alert_monitor': self.config.logs_dir / 'alert_monitor.log',
            'api_client': self.config.logs_dir / 'core.api_client.log',
            'system': self.config.logs_dir / 'system.log',
            'error': self.config.logs_dir / 'error.log',
            'debug': self.config.logs_dir / 'debug.log'
        }
    
    def get_logger(self, name: str, log_type: str = 'system') -> logging.Logger:
        """Get or create a logger with proper configuration."""
        logger_key = f"{name}_{log_type}"
        
        if logger_key not in self.loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            
            # Clear existing handlers to avoid duplicates
            logger.handlers.clear()
            
            # Create formatter
            formatter = CustomLogFormatter(
                fmt=self.config.log_format,
                datefmt=self.config.date_format,
                translation_manager=self.translation_manager
            )
            
            # File handler with rotation
            log_file = self.log_files.get(log_type, self.log_files['system'])
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
                encoding=self.config.encoding
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # Console handler for INFO and above
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # Prevent propagation to avoid duplicate logs
            logger.propagate = False
            
            self.loggers[logger_key] = logger
        
        return self.loggers[logger_key]
    
    def log_with_category(self, 
                         logger_name: str, 
                         level: str, 
                         message: str, 
                         category: LogCategory = LogCategory.SYSTEM_EVENT,
                         log_type: str = 'system',
                         translate_key: Optional[str] = None,
                         language: str = 'en',
                         **kwargs) -> None:
        """Log message with category and translation support."""
        logger = self.get_logger(logger_name, log_type)
        
        # Create log record
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Add extra fields
        extra = {
            'category': category.value.upper(),
            **kwargs
        }
        
        if translate_key:
            extra['translate_key'] = translate_key
            extra['language'] = language
        
        logger.log(log_level, message, extra=extra)
    
    def log_system_startup(self, logger_name: str, message: str, **kwargs) -> None:
        """Log system startup event."""
        self.log_with_category(
            logger_name, 'info', message, 
            LogCategory.SYSTEM_STARTUP, 'system', **kwargs
        )
    
    def log_system_event(self, logger_name: str, message: str, **kwargs) -> None:
        """Log system event."""
        self.log_with_category(
            logger_name, 'info', message, 
            LogCategory.SYSTEM_EVENT, 'system', **kwargs
        )
    
    def log_barn_validation(self, logger_name: str, message: str, **kwargs) -> None:
        """Log barn validation event."""
        self.log_with_category(
            logger_name, 'info', message, 
            LogCategory.BARN_VALIDATION, 'daily_analysis', **kwargs
        )
    
    def log_alert_evaluation(self, logger_name: str, message: str, **kwargs) -> None:
        """Log alert evaluation event."""
        self.log_with_category(
            logger_name, 'info', message, 
            LogCategory.ALERT_EVALUATION, 'alert_monitor', **kwargs
        )
    
    def log_api_operation(self, logger_name: str, message: str, level: str = 'info', **kwargs) -> None:
        """Log API operation."""
        self.log_with_category(
            logger_name, level, message, 
            LogCategory.API_OPERATION, 'api_client', **kwargs
        )
    
    def log_error(self, logger_name: str, message: str, **kwargs) -> None:
        """Log error with proper categorization."""
        self.log_with_category(
            logger_name, 'error', message, 
            LogCategory.ERROR_HANDLER, 'error', **kwargs
        )
    
    def log_debug(self, logger_name: str, message: str, **kwargs) -> None:
        """Log debug information."""
        self.log_with_category(
            logger_name, 'debug', message, 
            LogCategory.DEBUG_INFO, 'debug', **kwargs
        )
    
    def migrate_existing_logs(self) -> Dict[str, str]:
        """Migrate existing logs from data/ to logs/ directory."""
        migration_results = {}
        
        # Define migration mappings
        migrations = {
            'data/broiler_auto.log': 'logs/broiler_auto.log',
            'data/alert_monitor.log': 'logs/alert_monitor.log'
        }
        
        for source, target in migrations.items():
            source_path = self.project_root / source
            target_path = self.project_root / target
            
            try:
                if source_path.exists():
                    # Ensure target directory exists
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Move file
                    source_path.rename(target_path)
                    migration_results[source] = f"Migrated to {target}"
                else:
                    migration_results[source] = "Source file not found"
                    
            except Exception as e:
                migration_results[source] = f"Migration failed: {str(e)}"
        
        return migration_results
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        stats = {
            'logs_directory': str(self.config.logs_dir),
            'translation_available': TRANSLATION_AVAILABLE,
            'active_loggers': len(self.loggers),
            'log_files': {}
        }
        
        for log_type, log_file in self.log_files.items():
            if log_file.exists():
                stats['log_files'][log_type] = {
                    'path': str(log_file),
                    'size_mb': log_file.stat().st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                }
            else:
                stats['log_files'][log_type] = {
                    'path': str(log_file),
                    'exists': False
                }
        
        return stats
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """Clean up old log files."""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleanup_results = {'cleaned_files': [], 'errors': []}
        
        for log_file in self.config.logs_dir.rglob('*.log*'):
            try:
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    cleanup_results['cleaned_files'].append({
                        'file': str(log_file),
                        'size_mb': file_size / (1024 * 1024)
                    })
            except Exception as e:
                cleanup_results['errors'].append({
                    'file': str(log_file),
                    'error': str(e)
                })
        
        return cleanup_results


# Global logging manager instance
_logging_manager = None

def get_logging_manager() -> BroilerLoggingManager:
    """Get global logging manager instance."""
    global _logging_manager
    if _logging_manager is None:
        _logging_manager = BroilerLoggingManager()
    return _logging_manager


def get_logger(name: str, log_type: str = 'system') -> logging.Logger:
    """Get configured logger instance."""
    return get_logging_manager().get_logger(name, log_type)


def log_system_startup(message: str, **kwargs) -> None:
    """Convenience function for system startup logging."""
    get_logging_manager().log_system_startup('system', message, **kwargs)


def log_system_event(message: str, **kwargs) -> None:
    """Convenience function for system event logging."""
    get_logging_manager().log_system_event('system', message, **kwargs)


def log_barn_validation(message: str, **kwargs) -> None:
    """Convenience function for barn validation logging."""
    get_logging_manager().log_barn_validation('daily_analysis', message, **kwargs)


def log_alert_evaluation(message: str, **kwargs) -> None:
    """Convenience function for alert evaluation logging."""
    get_logging_manager().log_alert_evaluation('alert_monitor', message, **kwargs)


def log_api_operation(message: str, level: str = 'info', **kwargs) -> None:
    """Convenience function for API operation logging."""
    get_logging_manager().log_api_operation('api_client', message, level, **kwargs)


def migrate_logs() -> Dict[str, str]:
    """Migrate existing logs to proper directory."""
    return get_logging_manager().migrate_existing_logs()


if __name__ == "__main__":
    # Test the logging manager
    manager = get_logging_manager()
    
    # Test various log types
    log_system_startup("Logging Manager Test Started")
    log_system_event("System configuration loaded")
    log_barn_validation("Barn 712 validated successfully")
    log_alert_evaluation("Temperature alert evaluated")
    log_api_operation("API request completed", level='info')
    
    # Test migration
    migration_results = migrate_logs()
    print("Migration results:", migration_results)
    
    # Show stats
    stats = manager.get_log_stats()
    print("Logging stats:", stats)
