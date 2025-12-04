"""
Base Measurement Class

All GEO data point measurements inherit from this base class.
Provides consistent interface and metadata structure.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class BaseMeasurement(ABC):
    """
    Abstract base class for all GEO measurements.

    All measurements must implement the measure() method and provide
    metadata about the measurement (code, name, description, category, weight).
    """

    def __init__(
        self,
        code: str,
        name: str,
        description: str,
        category: str,
        weight: float = 1.0
    ):
        """
        Initialize measurement with metadata.

        Args:
            code: Unique measurement code (e.g., "WI-001", "CNT-002")
            name: Human-readable measurement name
            description: Detailed description of what this measures
            category: Category (Web Infrastructure, Content, Brand Visibility, SEO, UX, Competitive, Legal)
            weight: Importance weight (0.0-1.0), default 1.0
        """
        self.code = code
        self.name = name
        self.description = description
        self.category = category
        self.weight = weight
        self.version = "1.0.0"

    @abstractmethod
    async def measure(
        self,
        url: str,
        html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform the measurement.

        Args:
            url: Target URL to analyze
            html: HTML content (optional, some measurements fetch it themselves)
            metadata: Additional metadata (e.g., brand_name, domain_age, etc.)

        Returns:
            Dict with required keys:
                - score: int (0-100) - The measurement score
                - comment: str - Detailed, actionable comment explaining the score

            Optional keys:
                - raw_value: Any - Raw measurement value before scoring
                - sub_scores: Dict[str, int] - Breakdown of score components
                - metadata: Dict[str, Any] - Additional measurement metadata
                - recommendations: List[str] - Specific improvement recommendations
                - error: str - Error message if measurement partially failed
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get measurement metadata.

        Returns:
            Dict with measurement metadata
        """
        return {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'weight': self.weight,
            'version': self.version
        }

    async def execute(
        self,
        url: str,
        html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute measurement with error handling and metadata wrapping.

        This method wraps the measure() method with:
        - Execution timing
        - Error handling
        - Result validation
        - Metadata attachment

        Args:
            url: Target URL
            html: HTML content (optional)
            metadata: Additional metadata (optional)

        Returns:
            Dict with measurement result including metadata
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Execute measurement
            result = await self.measure(url, html, metadata)

            # Validate result structure
            if 'score' not in result:
                raise ValueError("Measurement result must include 'score' key")
            if 'comment' not in result:
                raise ValueError("Measurement result must include 'comment' key")

            # Validate score range
            if not isinstance(result['score'], (int, float)):
                raise ValueError(f"Score must be numeric, got {type(result['score'])}")
            if not (0 <= result['score'] <= 100):
                raise ValueError(f"Score must be between 0 and 100, got {result['score']}")

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Build full result with metadata
            full_result = {
                'measurement': self.get_metadata(),
                'execution': {
                    'id': execution_id,
                    'timestamp': start_time.isoformat(),
                    'execution_time_ms': execution_time_ms,
                    'success': True
                },
                'result': result,
                'url': url
            }

            return full_result

        except Exception as e:
            # Handle execution errors
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            error_result = {
                'measurement': self.get_metadata(),
                'execution': {
                    'id': execution_id,
                    'timestamp': start_time.isoformat(),
                    'execution_time_ms': execution_time_ms,
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                },
                'result': {
                    'score': 0,
                    'comment': f'Measurement failed: {str(e)}'
                },
                'url': url
            }

            return error_result

    def __str__(self) -> str:
        """String representation of measurement."""
        return f"{self.code}: {self.name}"

    def __repr__(self) -> str:
        """Detailed representation of measurement."""
        return f"<{self.__class__.__name__} code='{self.code}' category='{self.category}' weight={self.weight}>"
