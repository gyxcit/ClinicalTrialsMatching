"""
Beautiful and informative logger for the clinical trials agent.
Provides colored, formatted logging with different levels and contexts.
"""
import sys
from datetime import datetime
from pathlib import Path
from loguru import logger


# Remove default logger
logger.remove()

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Console handler with beautiful formatting
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
    level="DEBUG",
    colorize=True,
)

# File handler for all logs
logger.add(
    LOGS_DIR / "agent_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="00:00",  # Rotate at midnight
    retention="30 days",  # Keep logs for 30 days
    compression="zip",  # Compress old logs
)

# Error file handler
logger.add(
    LOGS_DIR / "agent_errors_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{extra}",
    level="ERROR",
    rotation="1 week",
    retention="60 days",
    backtrace=True,
    diagnose=True,
)


def log_api_call(service: str, endpoint: str, status: str = "started"):
    """Log API calls with consistent formatting."""
    logger.info(f"🌐 API Call [{service}] - {endpoint} - Status: {status}")


def log_agent_action(action: str, details: str = ""):
    """Log agent actions with emoji indicators."""
    logger.info(f"🤖 Agent Action: {action} {f'- {details}' if details else ''}")


def log_data_processing(step: str, count: int = None):
    """Log data processing steps."""
    count_str = f"({count} items)" if count is not None else ""
    logger.info(f"⚙️  Processing: {step} {count_str}")


def log_success(message: str):
    """Log success messages."""
    logger.success(f"✅ {message}")


def log_warning(message: str):
    """Log warning messages."""
    logger.warning(f"⚠️  {message}")


def log_error(message: str, exception: Exception = None):
    """Log error messages with optional exception details."""
    if exception:
        logger.error(f"❌ {message}: {str(exception)}")
        logger.exception(exception)
    else:
        logger.error(f"❌ {message}")


def log_llm_interaction(model: str, prompt_length: int, response_length: int = None):
    """Log LLM interactions."""
    if response_length:
        logger.info(f"🧠 LLM [{model}] - Prompt: {prompt_length} chars → Response: {response_length} chars")
    else:
        logger.info(f"🧠 LLM [{model}] - Prompt: {prompt_length} chars - Processing...")


def log_trial_match(trial_id: str, score: float = None):
    """Log clinical trial matching results."""
    score_str = f"(Score: {score:.2f})" if score is not None else ""
    logger.info(f"🔬 Trial Match: {trial_id} {score_str}")


# Export the logger instance
__all__ = [
    "logger",
    "log_api_call",
    "log_agent_action", 
    "log_data_processing",
    "log_success",
    "log_warning",
    "log_error",
    "log_llm_interaction",
    "log_trial_match",
]