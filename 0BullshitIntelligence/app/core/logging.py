"""
Logging configuration for 0BullshitIntelligence microservice.
Provides structured logging, performance monitoring, and debug capabilities.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
import structlog
from pythonjsonlogger import jsonlogger

from .config import settings, features


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add service information
        log_record['service'] = settings.app_name
        log_record['version'] = settings.app_version
        log_record['environment'] = settings.environment
        
        # Add level name
        log_record['level'] = record.levelname
        
        # Add module information
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno


class PerformanceLogger:
    """Logger specifically for performance monitoring"""
    
    def __init__(self):
        self.logger = structlog.get_logger("performance")
    
    def log_ai_request(
        self, 
        system_name: str, 
        duration_ms: float, 
        token_count: Optional[int] = None,
        success: bool = True,
        **kwargs
    ) -> None:
        """Log AI system performance"""
        self.logger.info(
            "ai_request_completed",
            system=system_name,
            duration_ms=duration_ms,
            token_count=token_count,
            success=success,
            **kwargs
        )
    
    def log_search_request(
        self,
        search_type: str,
        duration_ms: float,
        results_count: int,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log search performance"""
        self.logger.info(
            "search_request_completed",
            search_type=search_type,
            duration_ms=duration_ms,
            results_count=results_count,
            filters=filters,
            **kwargs
        )
    
    def log_database_operation(
        self,
        operation: str,
        table: str,
        duration_ms: float,
        affected_rows: Optional[int] = None,
        **kwargs
    ) -> None:
        """Log database operation performance"""
        self.logger.info(
            "database_operation_completed",
            operation=operation,
            table=table,
            duration_ms=duration_ms,
            affected_rows=affected_rows,
            **kwargs
        )


class AIDecisionLogger:
    """Logger for AI decision transparency"""
    
    def __init__(self):
        self.logger = structlog.get_logger("ai_decisions")
    
    def log_judge_decision(
        self,
        user_message: str,
        decision: str,
        confidence: float,
        reasoning: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log judge system decisions"""
        self.logger.info(
            "judge_decision_made",
            user_message=user_message[:200],  # Truncate for privacy
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            user_id=user_id,
            project_id=project_id,
            **kwargs
        )
    
    def log_language_detection(
        self,
        text: str,
        detected_language: str,
        confidence: float,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log language detection results"""
        self.logger.info(
            "language_detected",
            text=text[:100],  # Truncate for privacy
            detected_language=detected_language,
            confidence=confidence,
            user_id=user_id,
            **kwargs
        )
    
    def log_spam_detection(
        self,
        message: str,
        is_spam: bool,
        spam_score: float,
        reason: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log spam detection results"""
        self.logger.info(
            "spam_detection_completed",
            message=message[:100],  # Truncate for privacy
            is_spam=is_spam,
            spam_score=spam_score,
            reason=reason,
            user_id=user_id,
            **kwargs
        )


def setup_logging() -> None:
    """Setup logging configuration for the application"""
    
    # Configure standard library logging
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create formatters
    if features.is_debug_mode():
        # Console formatter for development
        console_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        # JSON formatter for production
        console_formatter = CustomJSONFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if settings.log_file:
        log_file_path = Path(settings.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(CustomJSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Configure structlog
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
            structlog.processors.JSONRenderer() if not features.is_debug_mode() 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set log levels for specific modules
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Enable debug logging for our modules in debug mode
    if features.is_debug_mode():
        logging.getLogger("app").setLevel(logging.DEBUG)
        logging.getLogger("ai_systems").setLevel(logging.DEBUG)
        logging.getLogger("search").setLevel(logging.DEBUG)


# ==========================================
# LOGGER INSTANCES
# ==========================================

# Performance monitoring
performance_logger = PerformanceLogger()

# AI decision transparency
ai_decision_logger = AIDecisionLogger()

# Get main application logger
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance for the given name"""
    return structlog.get_logger(name)


# ==========================================
# DECORATORS FOR LOGGING
# ==========================================

import functools
import time
from typing import Callable, Any


def log_ai_performance(system_name: str):
    """Decorator to log AI system performance"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = True
            token_count = None
            
            try:
                result = await func(*args, **kwargs)
                
                # Try to extract token count if available
                if hasattr(result, 'usage_metadata'):
                    token_count = getattr(result.usage_metadata, 'total_token_count', None)
                
                return result
                
            except Exception as e:
                success = False
                raise
                
            finally:
                duration_ms = (time.time() - start_time) * 1000
                performance_logger.log_ai_request(
                    system_name=system_name,
                    duration_ms=duration_ms,
                    token_count=token_count,
                    success=success
                )
        
        return wrapper
    return decorator


def log_search_performance(search_type: str):
    """Decorator to log search performance"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            results_count = 0
            
            try:
                result = await func(*args, **kwargs)
                
                # Try to extract results count
                if isinstance(result, (list, tuple)):
                    results_count = len(result)
                elif hasattr(result, '__len__'):
                    results_count = len(result)
                
                return result
                
            finally:
                duration_ms = (time.time() - start_time) * 1000
                performance_logger.log_search_request(
                    search_type=search_type,
                    duration_ms=duration_ms,
                    results_count=results_count
                )
        
        return wrapper
    return decorator


def log_database_performance(operation: str, table: str):
    """Decorator to log database operation performance"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            affected_rows = None
            
            try:
                result = await func(*args, **kwargs)
                
                # Try to extract affected rows
                if hasattr(result, 'data') and isinstance(result.data, list):
                    affected_rows = len(result.data)
                
                return result
                
            finally:
                duration_ms = (time.time() - start_time) * 1000
                performance_logger.log_database_operation(
                    operation=operation,
                    table=table,
                    duration_ms=duration_ms,
                    affected_rows=affected_rows
                )
        
        return wrapper
    return decorator