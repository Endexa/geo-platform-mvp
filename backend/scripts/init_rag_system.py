#!/usr/bin/env python3
"""
Initialize RAG System

Initialize MongoDB collections, Qdrant indexes, and verify connections.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.mongodb_client import get_mongodb_client
from app.core.qdrant_client import get_qdrant_client
from app.core.rag_system import get_rag_system

from loguru import logger


def main():
    """Initialize RAG system."""
    logger.info("=" * 60)
    logger.info("Initializing RAG System")
    logger.info("=" * 60)

    # Check environment variables
    required_vars = ['MONGO_URI', 'QDRANT_URL', 'QDRANT_API_KEY', 'OPENAI_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        logger.error("Please set these variables in .env file")
        sys.exit(1)

    try:
        # 1. Initialize MongoDB
        logger.info("\n[1/4] Initializing MongoDB...")
        mongodb = get_mongodb_client()

        # Health check
        health = mongodb.health_check()
        if health['status'] != 'healthy':
            logger.error(f"MongoDB unhealthy: {health}")
            sys.exit(1)

        logger.info(f"✓ MongoDB connected: {health['database']}")
        logger.info(f"  Version: {health['version']}")
        logger.info(f"  Collections: {len(health['collections'])}")

        # Create indexes
        logger.info("\n[2/4] Creating MongoDB indexes...")
        mongodb.ensure_indexes()

        # 2. Initialize Qdrant
        logger.info("\n[3/4] Initializing Qdrant...")
        qdrant = get_qdrant_client()

        # Health check
        qdrant_health = qdrant.health_check()
        if qdrant_health['status'] != 'healthy':
            logger.error(f"Qdrant unhealthy: {qdrant_health}")
            sys.exit(1)

        logger.info(f"✓ Qdrant connected")
        logger.info(f"  Collections: {qdrant_health['total_collections']}")
        logger.info(f"  Vectors: {qdrant_health['collection']['vectors_count']}")

        # Create payload indexes
        logger.info("\n[4/4] Creating Qdrant payload indexes...")
        qdrant.ensure_payload_indexes()

        # 3. Test RAG system
        logger.info("\n[Test] Verifying RAG system...")
        rag = get_rag_system()

        stats = rag.get_statistics()
        logger.info(f"✓ RAG system operational")
        logger.info(f"  MongoDB documents: {stats['mongodb']['total_documents']}")
        logger.info(f"  Qdrant vectors: {stats['qdrant']['total_vectors']}")

        logger.info("\n" + "=" * 60)
        logger.info("✓ RAG System initialized successfully!")
        logger.info("=" * 60)
        logger.info("\nYou can now:")
        logger.info("  - Add documents via API: POST /api/v1/rag/documents/add")
        logger.info("  - Search documents: POST /api/v1/rag/search")
        logger.info("  - Query with RAG: POST /api/v1/rag/rag/query")
        logger.info("\nAPI Documentation: http://localhost:8000/api/v1/docs")

    except Exception as e:
        logger.error(f"\n✗ Initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
