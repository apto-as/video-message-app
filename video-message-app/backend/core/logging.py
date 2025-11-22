"""
Structured logging configuration for production environment

Security Features:
- Sensitive data filtering (passwords, API keys, tokens)
- PII masking (emails, phone numbers, credit cards)
- Regex-based log scrubbing
"""

import logging
import sys
import json
import re
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path
import structlog
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    # python-json-loggerパッケージの正しいインポート
    from python_json_logger import jsonlogger

# Log levels
CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG

class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive data from logs"""

    SENSITIVE_KEYS = {
        'password', 'token', 'secret', 'api_key', 'd_id_api_key',
        'authorization', 'cookie', 'session', 'credit_card',
        'ssn', 'email', 'phone', 'api_secret'
    }

    # Regex patterns for PII detection
    PII_PATTERNS = {
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'),  # US format
        'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'api_key': re.compile(r'\b(sk|pk|AKIA)[_-]?[a-zA-Z0-9]{24,}\b'),
        'bearer_token': re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE),
    }

    def filter(self, record):
        """Filter sensitive data from log records"""
        # Scrub message content
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._scrub_message(record.msg)

        # Scrub dict-based logging
        if hasattr(record, 'msg_dict'):
            self._mask_dict(record.msg_dict)
        if hasattr(record, 'args'):
            if isinstance(record.args, dict):
                self._mask_dict(record.args)
            elif isinstance(record.args, tuple):
                # Scrub tuple args (for % formatting)
                record.args = tuple(
                    self._scrub_message(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True

    def _scrub_message(self, message: str) -> str:
        """Scrub PII and sensitive data from message content using regex"""
        scrubbed = message
        for pii_type, pattern in self.PII_PATTERNS.items():
            scrubbed = pattern.sub(f'***REDACTED_{pii_type.upper()}***', scrubbed)
        return scrubbed

    def _mask_dict(self, data: Dict[str, Any]):
        """Recursively mask sensitive data in dictionaries"""
        for key in list(data.keys()):
            lower_key = key.lower()
            if any(sensitive in lower_key for sensitive in self.SENSITIVE_KEYS):
                data[key] = "***REDACTED***"
            elif isinstance(data[key], dict):
                self._mask_dict(data[key])
            elif isinstance(data[key], str):
                # Also scrub string values for PII
                data[key] = self._scrub_message(data[key])
            elif isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, dict):
                        self._mask_dict(item)

class ProductionFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for production logs"""
    
    def add_fields(self, log_record, record, message_dict):
        super(ProductionFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add location info
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add process info
        log_record['process'] = record.process
        log_record['thread'] = record.thread
        
        # Add service info
        log_record['service'] = 'video-message-app'
        log_record['environment'] = 'production' if '/home/ec2-user' in str(Path.cwd()) else 'development'

def configure_structlog():
    """Configure structlog for structured logging"""
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = True
) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_format: Use JSON format for production
    
    Returns:
        Configured logger instance
    """
    
    # Configure structlog
    configure_structlog()
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Set formatter
    if json_format:
        formatter = ProductionFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        # Development formatter (human-readable)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)
    
    # Add console handler
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return root_logger

def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)

# Convenience functions for different log levels
def log_debug(message: str, **kwargs):
    """Log debug message with context"""
    logger = get_logger("app")
    logger.debug(message, **kwargs)

def log_info(message: str, **kwargs):
    """Log info message with context"""
    logger = get_logger("app")
    logger.info(message, **kwargs)

def log_warning(message: str, **kwargs):
    """Log warning message with context"""
    logger = get_logger("app")
    logger.warning(message, **kwargs)

def log_error(message: str, error: Optional[Exception] = None, **kwargs):
    """Log error message with context and exception"""
    logger = get_logger("app")
    if error:
        logger.error(message, exc_info=True, error=str(error), **kwargs)
    else:
        logger.error(message, **kwargs)

def log_critical(message: str, error: Optional[Exception] = None, **kwargs):
    """Log critical message with context and exception"""
    logger = get_logger("app")
    if error:
        logger.critical(message, exc_info=True, error=str(error), **kwargs)
    else:
        logger.critical(message, **kwargs)

# Performance logging
def log_performance(operation: str, duration: float, **kwargs):
    """Log performance metrics"""
    logger = get_logger("performance")
    logger.info(
        "Performance metric",
        operation=operation,
        duration_ms=round(duration * 1000, 2),
        **kwargs
    )

# API request logging
def log_api_request(method: str, path: str, status_code: int, duration: float, **kwargs):
    """Log API request details"""
    logger = get_logger("api")
    logger.info(
        "API request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration * 1000, 2),
        **kwargs
    )

# Service health logging
def log_health_check(service: str, status: str, **kwargs):
    """Log service health check"""
    logger = get_logger("health")
    logger.info(
        "Health check",
        service=service,
        status=status,
        **kwargs
    )