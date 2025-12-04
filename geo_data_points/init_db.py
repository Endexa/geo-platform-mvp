#!/usr/bin/env python3
"""
Initialize GEO Data Points Database

Creates the database tables for the GEO data points system.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from db import init_database
from utils import get_logger


logger = get_logger("init_db")


def main():
    """Initialize database tables."""
    try:
        logger.info("Initializing GEO Data Points database...")
        init_database()
        logger.success("Database initialized successfully!")
        print("\n✓ Database tables created:")
        print("  - geo_analyses")
        print("  - geo_data_point_results")

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
