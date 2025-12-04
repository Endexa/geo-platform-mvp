"""
Base Measurement Class

Abstract base class for all GEO data point measurements.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils import get_logger, get_config, validate_url, normalize_url


class BaseMeasurement(ABC):
    """
    Abstract base class for GEO data point measurements.

    All measurement scripts must inherit from this class and implement
    the measure() method.

    Returns a standardized result dictionary:
    {
        'score': float (0-100),
        'comment': str (explanation of the score),
        'metadata': dict (optional additional data)
    }
    """

    def __init__(self, url: str):
        """
        Initialize measurement.

        Args:
            url: Target URL to measure
        """
        self.url = normalize_url(url)
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()

        if not validate_url(self.url):
            raise ValueError(f"Invalid URL: {url}")

    @abstractmethod
    def measure(self) -> Dict[str, Any]:
        """
        Perform measurement and return result.

        Must be implemented by subclasses.

        Returns:
            dict: {
                'score': float (0-100),
                'comment': str (explanation),
                'metadata': dict (optional)
            }

        Raises:
            Exception: On measurement failure
        """
        pass

    def run(self) -> Dict[str, Any]:
        """
        Run measurement with timing and error handling.

        Returns:
            dict: Measurement result with timing information
        """
        start_time = time.time()
        self.logger.measurement_start(self.__class__.__name__, self.url)

        try:
            result = self.measure()

            # Validate result format
            if not isinstance(result, dict):
                raise ValueError("measure() must return a dictionary")

            if 'score' not in result:
                raise ValueError("Result must contain 'score' key")

            if 'comment' not in result:
                raise ValueError("Result must contain 'comment' key")

            # Validate score range
            score = result['score']
            if not isinstance(score, (int, float)):
                raise ValueError(f"Score must be numeric, got {type(score)}")

            if not 0 <= score <= 100:
                raise ValueError(f"Score must be between 0 and 100, got {score}")

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Add timing metadata
            result['execution_time_ms'] = round(duration_ms, 2)
            result['timestamp'] = datetime.utcnow().isoformat()
            result['success'] = True
            result['error_message'] = None

            self.logger.measurement_complete(self.__class__.__name__, score, duration_ms)

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_message = f"{type(e).__name__}: {str(e)}"

            self.logger.measurement_error(self.__class__.__name__, error_message)

            # Return error result
            return {
                'score': 0.0,
                'comment': f"Measurement failed: {error_message}",
                'metadata': {},
                'execution_time_ms': round(duration_ms, 2),
                'timestamp': datetime.utcnow().isoformat(),
                'success': False,
                'error_message': error_message
            }

    def _default_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Generate default error result.

        Args:
            error_message: Error description

        Returns:
            dict: Error result with score 0
        """
        return {
            'score': 0.0,
            'comment': f"Error: {error_message}",
            'metadata': {},
            'success': False,
            'error_message': error_message
        }

    def _clamp_score(self, score: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
        """
        Clamp score to valid range.

        Args:
            score: Score value
            min_val: Minimum value (default 0)
            max_val: Maximum value (default 100)

        Returns:
            float: Clamped score
        """
        return max(min_val, min(max_val, score))


# Example implementation for reference
class ExampleMeasurement(BaseMeasurement):
    """
    Example measurement implementation.

    This demonstrates the structure all measurements should follow.
    """

    def measure(self) -> Dict[str, Any]:
        """
        Example measurement that always returns 100.

        In real implementations, this would fetch data and calculate scores.
        """
        return {
            'score': 100.0,
            'comment': 'This is an example measurement that always passes.',
            'metadata': {
                'url': self.url,
                'example_metric': 'some_value'
            }
        }


if __name__ == "__main__":
    # Test the base class with example
    test_url = "https://example.com"
    measurement = ExampleMeasurement(test_url)
    result = measurement.run()
    print(f"Result: {result}")
