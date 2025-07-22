# Ajout à constants.py - Configuration des logs centralisée

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

from pathlib import Path

# Logging directories and files
LOGS_DIR = Path("logs")
DATA_DIR = Path("logs")
REPORTS_DIR = Path("reports")
TEMPLATES_DIR = Path("templates")
CONFIG_DIR = Path("config")

# Log file mappings
LOG_FILES = {
    'daily_analysis': LOGS_DIR / 'broiler_auto.log',
    'alert_monitor': LOGS_DIR / 'alert_monitor.log',
    'api_client': LOGS_DIR / 'core.api_client.log',
    'system': LOGS_DIR / 'system.log',
    'error': LOGS_DIR / 'error.log',
    'debug': LOGS_DIR / 'debug.log',
    'prefect': LOGS_DIR / 'prefect.log',
    'orchestrator': LOGS_DIR / 'orchestrator.log',
    'weather': LOGS_DIR / 'weather.log',
    'translation': LOGS_DIR / 'translation.log'
}

# Logging configuration
LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s | %(levelname)-8s | %(category)s | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s | %(levelname)-8s | %(name)s | %(category)s | %(funcName)s:%(lineno)d | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "category": "%(category)s", "message": "%(message)s"}',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file_system': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': str(LOG_FILES['system']),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf-8'
        },
        'file_error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': str(LOG_FILES['error']),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf-8'
        }
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console', 'file_system', 'file_error'],
            'level': 'DEBUG',
            'propagate': False
        },
        'core.api_client': {
            'handlers': ['console', 'file_system'],
            'level': 'INFO',
            'propagate': False
        },
        'apps.daily_analysis': {
            'handlers': ['console', 'file_system'],
            'level': 'INFO',
            'propagate': False
        },
        'apps.alert_monitor': {
            'handlers': ['console', 'file_system'],
            'level': 'INFO',
            'propagate': False
        }
    }
}

# Log categories for better organization
LOG_CATEGORIES = {
    'SYSTEM_STARTUP': 'system_startup',
    'SYSTEM_EVENT': 'system_event',
    'BARN_VALIDATION': 'barn_validation',
    'BARN_CLIENTS_LOADED': 'barn_clients_loaded',
    'ORCHESTRATION_RESULT': 'orchestration_result',
    'CLIENT_REPORT_SUCCESS': 'client_report_success',
    'BATCH_COMPLETE': 'batch_complete',
    'PRODUCTION_CHECK': 'production_check',
    'DATA_QUALITY': 'data_quality',
    'ANALYSIS_SUCCESS': 'analysis_success',
    'EMAIL_OPERATION': 'email_operation',
    'API_OPERATION': 'api_operation',
    'ALERT_EVALUATION': 'alert_evaluation',
    'MONITORING_CYCLE': 'monitoring_cycle',
    'CONFIG_LOADED': 'config_loaded',
    'ERROR_HANDLER': 'error_handler',
    'DEBUG_INFO': 'debug_info'
}

# Log retention settings
LOG_RETENTION = {
    'daily_analysis': 30,  # days
    'alert_monitor': 30,   # days
    'api_client': 14,      # days
    'system': 30,          # days
    'error': 90,           # days
    'debug': 7             # days
}

# Log file size limits (in MB)
LOG_SIZE_LIMITS = {
    'daily_analysis': 50,   # MB
    'alert_monitor': 50,    # MB
    'api_client': 20,       # MB
    'system': 100,          # MB
    'error': 100,           # MB
    'debug': 20             # MB
}

# Translation keys for logging messages
LOG_TRANSLATION_KEYS = {
    'system.startup': 'log.system.startup',
    'system.shutdown': 'log.system.shutdown',
    'system.config_loaded': 'log.system.config_loaded',
    'barn.validation_success': 'log.barn.validation_success',
    'barn.validation_failed': 'log.barn.validation_failed',
    'alert.evaluation_completed': 'log.alert.evaluation_completed',
    'alert.sent_successfully': 'log.alert.sent_successfully',
    'api.request_completed': 'log.api.request_completed',
    'api.request_failed': 'log.api.request_failed',
    'email.sent_successfully': 'log.email.sent_successfully',
    'email.send_failed': 'log.email.send_failed',
    'error.exception_occurred': 'log.error.exception_occurred',
    'debug.info_message': 'log.debug.info_message'
}

def get_log_file_path(log_type: str) -> Path:
    """Get log file path for specified type."""
    return LOG_FILES.get(log_type, LOG_FILES['system'])

def get_log_category(category_key: str) -> str:
    """Get log category string."""
    return LOG_CATEGORIES.get(category_key, 'system_event')

def get_log_translation_key(message_key: str) -> str:
    """Get translation key for log message."""
    return LOG_TRANSLATION_KEYS.get(message_key, message_key)
