"""
GEO Data Points Configuration

Loads environment variables and provides configuration settings.
"""

import os
from pathlib import Path
from typing import Optional


class GeoConfig:
    """
    Configuration manager for GEO data points system.

    Loads settings from environment variables with sensible defaults.
    """

    def __init__(self):
        # Database
        self.DATABASE_URL = os.getenv(
            "GEO_DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/geo_platform"
        )

        # API Keys
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.AHREFS_API_KEY = os.getenv("AHREFS_API_KEY", "")
        self.SEMRUSH_API_KEY = os.getenv("SEMRUSH_API_KEY", "")
        self.GOOGLE_PAGESPEED_API_KEY = os.getenv("GOOGLE_PAGESPEED_API_KEY", "")

        # HTTP Settings
        self.REQUEST_TIMEOUT = int(os.getenv("GEO_REQUEST_TIMEOUT", "10"))  # seconds
        self.MAX_RETRIES = int(os.getenv("GEO_MAX_RETRIES", "3"))
        self.USER_AGENT = os.getenv(
            "GEO_USER_AGENT",
            "Mozilla/5.0 (compatible; GeoBot/1.0; +https://geoplatform.com/bot)"
        )

        # Measurement Settings
        self.ENABLE_EXTERNAL_APIS = os.getenv("GEO_ENABLE_EXTERNAL_APIS", "false").lower() == "true"
        self.PARALLEL_EXECUTION = os.getenv("GEO_PARALLEL_EXECUTION", "true").lower() == "true"
        self.MAX_WORKERS = int(os.getenv("GEO_MAX_WORKERS", "4"))

        # Paths
        self.PROJECT_ROOT = Path(__file__).parent.parent
        self.DATA_POINTS_JSON = self.PROJECT_ROOT / "data_points.json"
        self.SCRIPTS_DIR = self.PROJECT_ROOT / "scripts"
        self.LOGS_DIR = self.PROJECT_ROOT / "logs"

        # Ensure directories exist
        self.LOGS_DIR.mkdir(exist_ok=True)

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        errors = []

        # Check data_points.json exists
        if not self.DATA_POINTS_JSON.exists():
            errors.append(f"data_points.json not found at {self.DATA_POINTS_JSON}")

        # Check scripts directory exists
        if not self.SCRIPTS_DIR.exists():
            errors.append(f"Scripts directory not found at {self.SCRIPTS_DIR}")

        # Warn about missing API keys (non-fatal)
        if not self.OPENAI_API_KEY and self.ENABLE_EXTERNAL_APIS:
            print(f"⚠ Warning: OPENAI_API_KEY not set")

        if not self.AHREFS_API_KEY and self.ENABLE_EXTERNAL_APIS:
            print(f"⚠ Warning: AHREFS_API_KEY not set")

        if errors:
            for error in errors:
                print(f"✗ Configuration error: {error}")
            return False

        return True

    def __repr__(self):
        return (
            f"<GeoConfig database={self.DATABASE_URL[:30]}... "
            f"external_apis={self.ENABLE_EXTERNAL_APIS} "
            f"parallel={self.PARALLEL_EXECUTION}>"
        )


# Global config instance
_config_instance: Optional[GeoConfig] = None


def get_config() -> GeoConfig:
    """
    Get or create global configuration instance.

    Returns:
        GeoConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = GeoConfig()
    return _config_instance
