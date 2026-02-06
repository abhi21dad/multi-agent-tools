"""
Centralized logging configuration for LangGraph Chatbot.

Provides structured JSON logging with:
- Automatic sensitive data redaction (API keys, tokens, emails)
- Different log levels per environment (development/production)
- Log rotation and file management
- Structured logging for easy parsing and monitoring
"""

import logging
import logging.handlers
import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from config import get_settings


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive information from log messages."""
    
    PATTERNS = [
        # API keys and tokens
        (re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{20,})'), r'\1***REDACTED***'),
        (re.compile(r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{20,})'), r'\1***REDACTED***'),
        (re.compile(r'(bearer\s+)([a-zA-Z0-9_-]{20,})', re.IGNORECASE), r'\1***REDACTED***'),
        
        # Email addresses
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), r'***EMAIL***'),
        
        # Passwords
        (re.compile(r'(password["\']?\s*[:=]\s*["\']?)([^"\'\s]+)', re.IGNORECASE), r'\1***REDACTED***'),
        
        # Authorization headers
        (re.compile(r'(authorization["\']?\s*[:=]\s*["\']?)([^"\'\s]+)', re.IGNORECASE), r'\1***REDACTED***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from log record."""
        # Redact message
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        
        # Redact arguments
        if record.args:
            if isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact_value(arg) for arg in record.args)
        
        return True
    
    def _redact_value(self, value: Any) -> Any:
        """Redact sensitive data from a single value."""
        if isinstance(value, str):
            for pattern, replacement in self.PATTERNS:
                value = pattern.sub(replacement, value)
        elif isinstance(value, dict):
            value = self._redact_dict(value)
        elif isinstance(value, (list, tuple)):
            value = type(value)(self._redact_value(v) for v in value)
        return value
    
    def _redact_dict(self, d: Dict) -> Dict:
        """Redact sensitive data from dictionary."""
        redacted = {}
        sensitive_keys = {'api_key', 'token', 'password', 'secret', 'authorization', 'auth'}
        
        for key, value in d.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                redacted[key] = '***REDACTED***'
            else:
                redacted[key] = self._redact_value(value)
        
        return redacted


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data['extra'] = record.extra
        
        return json.dumps(log_data)


def setup_logger(
    name: str,
    log_file: str = None,
    level: str = None,
    use_json: bool = None
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name (usually __name__ or service name)
        log_file: Optional specific log file path. If None, uses logs/{name}.log
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). If None, uses settings
        use_json: Use JSON formatter for production. If None, uses settings
    
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    # Determine log level
    if level is None:
        level = settings.app.log_level
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Determine if we should use JSON formatting
    if use_json is None:
        use_json = settings.app.environment == 'production'
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Add sensitive data filter
    logger.addFilter(SensitiveDataFilter())
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    if use_json:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
    
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file is None and settings.app.environment != 'test':
        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f'{name.replace(".", "_")}.log'
    
    if log_file:
        # Rotating file handler (10MB max, keep 5 backups)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        if use_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
        
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    # Check if logger already exists and is configured
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger = setup_logger(name)
    return logger


# Create a default logger for the module
logger = get_logger('langgraph_chatbot')


if __name__ == '__main__':
    """Test logging functionality."""
    
    # Test basic logging
    test_logger = setup_logger('test_logger', use_json=False)
    
    print("Testing logging with sensitive data redaction...")
    test_logger.info("Starting test")
    test_logger.debug("Debug message")
    test_logger.warning("API key is: sk-abc123def456")
    test_logger.info("User email: user@example.com")
    test_logger.error("Token: bearer abc123token456")
    
    try:
        raise ValueError("Test exception")
    except Exception:
        test_logger.exception("Exception occurred")
    
    print("\nTesting JSON logging...")
    json_logger = setup_logger('json_test', use_json=True)
    json_logger.info("This is JSON formatted", extra={'user_id': '123', 'action': 'test'})
    
    print("\nLogging test complete. Check logs/ directory for output files.")
