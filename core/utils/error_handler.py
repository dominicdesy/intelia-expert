#!/usr/bin/env python3
"""
Enhanced error handling and logging utilities with centralized logging.
"""

import logging
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
from functools import wraps

# Import centralized logging
try:
    from core.utils.logging_manager import get_logging_manager, LogCategory
    LOGGING_MANAGER_AVAILABLE = True
except ImportError:
    LOGGING_MANAGER_AVAILABLE = False

# Import translation manager
try:
    from core.notifications.translation_manager import get_translation_manager
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False

# Import constants
try:
    from core.config.constants import LOG_FILES, get_log_file_path, get_log_category
    CONSTANTS_AVAILABLE = True
except ImportError:
    CONSTANTS_AVAILABLE = False
    LOG_FILES = {'error': Path('logs/error.log')}
    
    def get_log_file_path(log_type: str) -> Path:
        return Path('logs') / f'{log_type}.log'


class BroilerErrorHandler:
    """Enhanced error handler with centralized logging and translation support."""
    
    def __init__(self, module_name: str, log_type: str = 'system'):
        """Initialize error handler for specific module."""
        self.module_name = module_name
        self.log_type = log_type
        self.translation_manager = get_translation_manager() if TRANSLATION_AVAILABLE else None
        
        if LOGGING_MANAGER_AVAILABLE:
            self.logging_manager = get_logging_manager()
            self.logger = self.logging_manager.get_logger(module_name, log_type)
        else:
            self.logger = self._create_fallback_logger(module_name, log_type)
    
    def _create_fallback_logger(self, module_name: str, log_type: str) -> logging.Logger:
        """Create fallback logger if logging manager is not available."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logger = logging.getLogger(module_name)
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # File handler
            log_file = get_log_file_path(log_type)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
            logger.setLevel(logging.DEBUG)
        
        return logger
    
    def log_error(self, 
                  message: str, 
                  exception: Optional[Exception] = None,
                  context: Optional[Dict[str, Any]] = None,
                  translate_key: Optional[str] = None,
                  language: str = 'en') -> None:
        """Log error with enhanced context and translation."""
        error_details = {
            'module': self.module_name,
            'timestamp': datetime.now().isoformat(),
            'message': message
        }
        
        if context:
            error_details.update(context)
        
        if exception:
            error_details.update({
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'traceback': traceback.format_exc()
            })
        
        # Use centralized logging if available
        if LOGGING_MANAGER_AVAILABLE:
            self.logging_manager.log_error(
                self.module_name, 
                message, 
                translate_key=translate_key,
                language=language,
                **error_details
            )
        else:
            self.logger.error(f"{message} | Context: {error_details}")
    
    def log_warning(self, 
                   message: str, 
                   context: Optional[Dict[str, Any]] = None,
                   translate_key: Optional[str] = None,
                   language: str = 'en') -> None:
        """Log warning with context."""
        warning_details = {
            'module': self.module_name,
            'timestamp': datetime.now().isoformat(),
            'message': message
        }
        
        if context:
            warning_details.update(context)
        
        if LOGGING_MANAGER_AVAILABLE:
            self.logging_manager.log_with_category(
                self.module_name, 
                'warning', 
                message, 
                LogCategory.ERROR_HANDLER,
                self.log_type,
                translate_key=translate_key,
                language=language,
                **warning_details
            )
        else:
            self.logger.warning(f"{message} | Context: {warning_details}")
    
    def log_info(self, 
                message: str, 
                category: Optional[str] = None,
                context: Optional[Dict[str, Any]] = None,
                translate_key: Optional[str] = None,
                language: str = 'en') -> None:
        """Log info with category and context."""
        info_details = {
            'module': self.module_name,
            'timestamp': datetime.now().isoformat(),
            'message': message
        }
        
        if context:
            info_details.update(context)
        
        if LOGGING_MANAGER_AVAILABLE:
            log_category = LogCategory.SYSTEM_EVENT
            if category:
                try:
                    log_category = LogCategory(get_log_category(category))
                except (ValueError, AttributeError):
                    pass
            
            self.logging_manager.log_with_category(
                self.module_name, 
                'info', 
                message, 
                log_category,
                self.log_type,
                translate_key=translate_key,
                language=language,
                **info_details
            )
        else:
            self.logger.info(f"{message} | Context: {info_details}")
    
    def log_debug(self, 
                 message: str, 
                 context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug information."""
        debug_details = {
            'module': self.module_name,
            'timestamp': datetime.now().isoformat(),
            'message': message
        }
        
        if context:
            debug_details.update(context)
        
        if LOGGING_MANAGER_AVAILABLE:
            self.logging_manager.log_debug(self.module_name, message, **debug_details)
        else:
            self.logger.debug(f"{message} | Context: {debug_details}")
    
    def handle_exception(self, 
                        exception: Exception, 
                        context: Optional[Dict[str, Any]] = None,
                        reraise: bool = True) -> None:
        """Handle exception with proper logging."""
        error_message = f"Exception in {self.module_name}: {str(exception)}"
        
        self.log_error(
            error_message, 
            exception, 
            context,
            translate_key='error.exception_occurred'
        )
        
        if reraise:
            raise exception


def error_handler_decorator(
    module_name: str, 
    log_type: str = 'system',
    reraise: bool = True,
    return_value: Any = None
):
    """Decorator for automatic error handling and logging."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = BroilerErrorHandler(module_name, log_type)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args)[:200] if args else None,
                    'kwargs': str(kwargs)[:200] if kwargs else None
                }
                
                handler.handle_exception(e, context, reraise=reraise)
                
                if not reraise:
                    return return_value
        
        return wrapper
    return decorator


def get_error_handler(module_name: str, log_type: str = 'system') -> BroilerErrorHandler:
    """Get error handler instance for module."""
    return BroilerErrorHandler(module_name, log_type)


# Legacy compatibility function
def get_error_handler_legacy(module_name: str):
    """Legacy compatibility function - deprecated."""
    return get_error_handler(module_name)


# Convenience functions for common logging operations
def log_system_startup(message: str, **kwargs) -> None:
    """Log system startup event."""
    if LOGGING_MANAGER_AVAILABLE:
        get_logging_manager().log_system_startup('system', message, **kwargs)
    else:
        logger = logging.getLogger('system')
        logger.info(f"SYSTEM_STARTUP | {message}")


def log_system_event(message: str, **kwargs) -> None:
    """Log system event."""
    if LOGGING_MANAGER_AVAILABLE:
        get_logging_manager().log_system_event('system', message, **kwargs)
    else:
        logger = logging.getLogger('system')
        logger.info(f"SYSTEM_EVENT | {message}")


def log_barn_validation(message: str, **kwargs) -> None:
    """Log barn validation event."""
    if LOGGING_MANAGER_AVAILABLE:
        get_logging_manager().log_barn_validation('daily_analysis', message, **kwargs)
    else:
        logger = logging.getLogger('daily_analysis')
        logger.info(f"BARN_VALIDATION | {message}")


def log_alert_evaluation(message: str, **kwargs) -> None:
    """Log alert evaluation event."""
    if LOGGING_MANAGER_AVAILABLE:
        get_logging_manager().log_alert_evaluation('alert_monitor', message, **kwargs)
    else:
        logger = logging.getLogger('alert_monitor')
        logger.info(f"ALERT_EVALUATION | {message}")


def log_api_operation(message: str, level: str = 'info', **kwargs) -> None:
    """Log API operation."""
    if LOGGING_MANAGER_AVAILABLE:
        get_logging_manager().log_api_operation('api_client', message, level, **kwargs)
    else:
        logger = logging.getLogger('api_client')
        getattr(logger, level)(f"API_OPERATION | {message}")


if __name__ == "__main__":
    # Test the enhanced error handler
    handler = get_error_handler('test_module', 'system')
    
    # Test various log types
    handler.log_info("Test info message", category='SYSTEM_EVENT')
    handler.log_warning("Test warning message")
    handler.log_debug("Test debug message")
    
    # Test error handling
    try:
        raise ValueError("Test exception")
    except ValueError as e:
        handler.log_error("Test error occurred", e, {'test_context': 'test_value'})
    
    # Test decorator
    @error_handler_decorator('test_module', 'system', reraise=False, return_value=None)
    def test_function():
        raise RuntimeError("Test decorator error")
    
    result = test_function()
    print(f"Function result: {result}")
