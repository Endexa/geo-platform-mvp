"""
GEO Data Points Logging Utility

Provides structured logging with timestamps, levels, and file output.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class GeoLogger:
    """
    Structured logger for GEO data points measurements.

    Features:
    - Console output with colors (INFO, WARNING, ERROR)
    - File output with rotation
    - Timestamp prefixes
    - Module/script identification
    """

    def __init__(self, name: str = "geo_datapoints", log_file: Optional[str] = None):
        """
        Initialize logger.

        Args:
            name: Logger name (typically module or script name)
            log_file: Optional log file path (defaults to logs/geo_datapoints_YYYYMMDD.log)
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Avoid duplicate handlers
        if self.logger.handlers:
            return

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler with daily rotation
        if log_file is None:
            today = datetime.now().strftime("%Y%m%d")
            log_file = LOGS_DIR / f"geo_datapoints_{today}.log"

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def info(self, message: str):
        """Log INFO level message."""
        self.logger.info(message)

    def warning(self, message: str):
        """Log WARNING level message."""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """Log ERROR level message with optional exception traceback."""
        self.logger.error(message, exc_info=exc_info)

    def debug(self, message: str):
        """Log DEBUG level message (file only)."""
        self.logger.debug(message)

    def success(self, message: str):
        """Log success message (INFO level with prefix)."""
        self.logger.info(f"✓ {message}")

    def measurement_start(self, data_point_name: str, url: str):
        """Log measurement start."""
        self.info(f"▶ Starting measurement: {data_point_name} for {url}")

    def measurement_complete(self, data_point_name: str, score: float, duration_ms: float):
        """Log measurement completion."""
        self.success(f"Completed: {data_point_name} - Score: {score:.2f} ({duration_ms:.0f}ms)")

    def measurement_error(self, data_point_name: str, error: str):
        """Log measurement error."""
        self.error(f"✗ Failed: {data_point_name} - {error}")


# Global logger instance
_default_logger = None


def get_logger(name: str = "geo_datapoints") -> GeoLogger:
    """
    Get or create logger instance.

    Args:
        name: Logger name (defaults to 'geo_datapoints')

    Returns:
        GeoLogger instance
    """
    global _default_logger
    if _default_logger is None or _default_logger.name != name:
        _default_logger = GeoLogger(name)
    return _default_logger
