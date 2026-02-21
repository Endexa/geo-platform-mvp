"""Base measurement class for simple measurement scripts."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseMeasurement(ABC):
    """Simple base class for measurements that just need async measure()."""

    @abstractmethod
    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Measure a single aspect of the URL/HTML.

        Args:
            url: The URL being measured
            html: The HTML content
            metadata: Optional pre-calculated metadata

        Returns:
            Dict with keys: score (0-100), comment, metadata, recommendations
        """
        pass


__all__ = ['BaseMeasurement']
