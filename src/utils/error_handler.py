"""Error handling and feedback system for agents"""
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import traceback
from ..logger import logger


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackType(Enum):
    """Types of feedback"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


@dataclass
class ErrorContext:
    """Context information for an error"""
    timestamp: str
    error_type: str
    message: str
    severity: ErrorSeverity
    agent_name: Optional[str] = None
    operation: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Feedback:
    """Feedback entry"""
    timestamp: str
    feedback_type: FeedbackType
    message: str
    agent_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ErrorHandler:
    """Handles errors and provides feedback"""
    
    def __init__(self):
        self.error_history: List[ErrorContext] = []
        self.feedback_history: List[Feedback] = []
        self.error_callbacks: Dict[str, List[Callable]] = {}
        
    def handle_error(
        self,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        agent_name: Optional[str] = None,
        operation: Optional[str] = None,
        **metadata
    ) -> ErrorContext:
        """
        Handle an error and create context
        
        Args:
            error: The exception that occurred
            severity: Error severity level
            agent_name: Agent that encountered the error
            operation: Operation being performed
            **metadata: Additional context
            
        Returns:
            ErrorContext object
        """
        error_context = ErrorContext(
            timestamp=datetime.now().isoformat(),
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            agent_name=agent_name,
            operation=operation,
            stack_trace=traceback.format_exc(),
            metadata=metadata
        )
        
        # Store in history
        self.error_history.append(error_context)
        
        # Log based on severity
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error(f"[{agent_name or 'Unknown'}] {operation or 'Operation'} failed: {str(error)}")
        else:
            logger.warning(f"[{agent_name or 'Unknown'}] {operation or 'Operation'} warning: {str(error)}")
        
        # Execute callbacks
        self._execute_callbacks(error_context)
        
        return error_context
    
    def add_feedback(
        self,
        feedback_type: FeedbackType,
        message: str,
        agent_name: Optional[str] = None,
        **metadata
    ) -> Feedback:
        """
        Add feedback entry
        
        Args:
            feedback_type: Type of feedback
            message: Feedback message
            agent_name: Related agent
            **metadata: Additional data
            
        Returns:
            Feedback object
        """
        feedback = Feedback(
            timestamp=datetime.now().isoformat(),
            feedback_type=feedback_type,
            message=message,
            agent_name=agent_name,
            metadata=metadata
        )
        
        self.feedback_history.append(feedback)
        
        # Log feedback
        logger.info(f"💬 Feedback [{feedback_type.value}] - {message}")
        
        return feedback
    
    def register_error_callback(self, error_type: str, callback: Callable) -> None:
        """
        Register callback for specific error type
        
        Args:
            error_type: Type of error to handle
            callback: Function to call when error occurs
        """
        if error_type not in self.error_callbacks:
            self.error_callbacks[error_type] = []
        self.error_callbacks[error_type].append(callback)
    
    def _execute_callbacks(self, error_context: ErrorContext) -> None:
        """Execute registered callbacks for error"""
        callbacks = self.error_callbacks.get(error_context.error_type, [])
        for callback in callbacks:
            try:
                callback(error_context)
            except Exception as e:
                logger.error(f"Error executing callback: {e}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors"""
        return {
            'total_errors': len(self.error_history),
            'by_severity': {
                severity.value: len([e for e in self.error_history if e.severity == severity])
                for severity in ErrorSeverity
            },
            'by_type': self._count_by_field('error_type'),
            'by_agent': self._count_by_field('agent_name'),
            'recent_errors': [
                {
                    'timestamp': e.timestamp,
                    'type': e.error_type,
                    'message': e.message,
                    'severity': e.severity.value
                }
                for e in self.error_history[-10:]
            ]
        }
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """Get summary of feedback"""
        return {
            'total_feedback': len(self.feedback_history),
            'by_type': {
                fb_type.value: len([f for f in self.feedback_history if f.feedback_type == fb_type])
                for fb_type in FeedbackType
            },
            'by_agent': self._count_by_field('agent_name', self.feedback_history),
            'recent_feedback': [
                {
                    'timestamp': f.timestamp,
                    'type': f.feedback_type.value,
                    'message': f.message
                }
                for f in self.feedback_history[-10:]
            ]
        }
    
    def _count_by_field(self, field: str, items: Optional[List] = None) -> Dict[str, int]:
        """Count items by field value"""
        items = items or self.error_history
        counts = {}
        for item in items:
            value = getattr(item, field, None)
            if value:
                counts[str(value)] = counts.get(str(value), 0) + 1
        return counts
    
    def clear_history(self, agent_name: Optional[str] = None) -> None:
        """Clear error and feedback history"""
        if agent_name:
            self.error_history = [e for e in self.error_history if e.agent_name != agent_name]
            self.feedback_history = [f for f in self.feedback_history if f.agent_name != agent_name]
        else:
            self.error_history.clear()
            self.feedback_history.clear()
