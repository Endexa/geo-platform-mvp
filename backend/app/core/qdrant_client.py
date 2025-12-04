"""
Qdrant Vector Database Client

Client for Qdrant Cloud with vector storage, similarity search,
and optimized for RAG (Retrieval-Augmented Generation).
"""

from qdrant_client import QdrantClient as QdrantSDK
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from typing import List, Dict, Any, Optional, Tuple
import os
import numpy as np
from datetime import datetime

from loguru import logger


class QdrantVectorClient:
    """
    Qdrant client for vector storage and similarity search.

    Features:
    - Automatic collection creation
    - Batch vector insertion
    - Similarity search with filtering
    - Optimized for billions of vectors
    """

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Get Qdrant config from environment
        self.qdrant_url = os.getenv('QDRANT_URL')
        self.qdrant_api_key = os.getenv('QDRANT_API_KEY')

        if not self.qdrant_url or not self.qdrant_api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY environment variables must be set")

        self.collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'geo_documents')
        self.vector_size = int(os.getenv('EMBEDDING_DIMENSION', '1536'))

        # Initialize connection
        self._connect()
        self._initialized = True

    def _connect(self):
        """Establish Qdrant connection."""
        try:
            self._client = QdrantSDK(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
                timeout=30
            )

            # Test connection
            collections = self._client.get_collections()
            logger.info(f"✓ Connected to Qdrant: {len(collections.collections)} collections")

            # Ensure collection exists
            self._ensure_collection()

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise

    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = self._client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")

                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    ),
                    # Optimized settings for production
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=20000
                    ),
                    hnsw_config=models.HnswConfigDiff(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000
                    )
                )

                logger.info(f"✓ Created collection: {self.collection_name}")
            else:
                logger.info(f"✓ Collection exists: {self.collection_name}")

        except Exception as e:
            logger.error(f"Collection creation error: {str(e)}")
            raise

    # ========== Vector Operations ==========

    def upsert_vector(self, vector_id: str, vector: List[float],
                      payload: Dict[str, Any]) -> bool:
        """
        Insert or update a single vector.

        Args:
            vector_id: Unique ID for vector
            vector: Embedding vector
            payload: Metadata payload

        Returns:
            True if successful
        """
        try:
            # Add timestamp to payload
            if 'indexed_at' not in payload:
                payload['indexed_at'] = datetime.utcnow().isoformat()

            self._client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=vector_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )

            return True

        except Exception as e:
            logger.error(f"Vector upsert error: {str(e)}")
            return False

    def upsert_vectors_batch(self, vectors: List[Tuple[str, List[float], Dict[str, Any]]]) -> int:
        """
        Batch insert/update vectors.

        Args:
            vectors: List of (id, vector, payload) tuples

        Returns:
            Number of vectors upserted
        """
        try:
            points = []
            for vector_id, vector, payload in vectors:
                # Add timestamp
                if 'indexed_at' not in payload:
                    payload['indexed_at'] = datetime.utcnow().isoformat()

                points.append(
                    models.PointStruct(
                        id=vector_id,
                        vector=vector,
                        payload=payload
                    )
                )

            # Batch upsert (Qdrant handles batching internally)
            self._client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            return len(points)

        except Exception as e:
            logger.error(f"Batch upsert error: {str(e)}")
            return 0

    def search_similar(self, query_vector: List[float], limit: int = 10,
                       score_threshold: Optional[float] = None,
                       filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Max results
            score_threshold: Minimum similarity score (0-1)
            filter_dict: Metadata filters

        Returns:
            List of results with score and payload
        """
        try:
            # Build filter if provided
            search_filter = None
            if filter_dict:
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )

                if conditions:
                    search_filter = models.Filter(must=conditions)

            # Search
            results = self._client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Vector search error: {str(e)}")
            return []

    def search_by_id(self, vector_id: str, limit: int = 10,
                     score_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Find similar vectors to a given vector ID.

        Args:
            vector_id: ID of the reference vector
            limit: Max results
            score_threshold: Minimum similarity score

        Returns:
            List of similar vectors
        """
        try:
            results = self._client.recommend(
                collection_name=self.collection_name,
                positive=[vector_id],
                limit=limit,
                score_threshold=score_threshold
            )

            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Recommend error: {str(e)}")
            return []

    def get_vector(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve vector by ID.

        Args:
            vector_id: Vector ID

        Returns:
            Vector data with payload
        """
        try:
            result = self._client.retrieve(
                collection_name=self.collection_name,
                ids=[vector_id],
                with_vectors=True,
                with_payload=True
            )

            if result:
                point = result[0]
                return {
                    'id': point.id,
                    'vector': point.vector,
                    'payload': point.payload
                }

            return None

        except Exception as e:
            logger.error(f"Vector retrieval error: {str(e)}")
            return None

    def delete_vector(self, vector_id: str) -> bool:
        """Delete vector by ID."""
        try:
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[vector_id]
                )
            )
            return True

        except Exception as e:
            logger.error(f"Vector deletion error: {str(e)}")
            return False

    def delete_vectors_by_filter(self, filter_dict: Dict[str, Any]) -> bool:
        """
        Delete vectors matching filter.

        Args:
            filter_dict: Metadata filters

        Returns:
            True if successful
        """
        try:
            conditions = []
            for key, value in filter_dict.items():
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                )

            self._client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=conditions)
                )
            )

            return True

        except Exception as e:
            logger.error(f"Filtered deletion error: {str(e)}")
            return False

    # ========== Collection Management ==========

    def count_vectors(self) -> int:
        """Get total number of vectors in collection."""
        try:
            info = self._client.get_collection(self.collection_name)
            return info.points_count
        except Exception as e:
            logger.error(f"Count error: {str(e)}")
            return 0

    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            info = self._client.get_collection(self.collection_name)

            return {
                'name': self.collection_name,
                'vectors_count': info.points_count,
                'indexed_vectors_count': info.indexed_vectors_count,
                'vector_size': info.config.params.vectors.size,
                'distance': info.config.params.vectors.distance.value,
                'status': info.status.value
            }

        except Exception as e:
            logger.error(f"Collection info error: {str(e)}")
            return {}

    def create_payload_index(self, field_name: str, field_type: str = 'keyword'):
        """
        Create index on payload field for faster filtering.

        Args:
            field_name: Payload field to index
            field_type: Field type ('keyword', 'integer', 'float', 'bool')
        """
        try:
            schema_map = {
                'keyword': models.PayloadSchemaType.KEYWORD,
                'integer': models.PayloadSchemaType.INTEGER,
                'float': models.PayloadSchemaType.FLOAT,
                'bool': models.PayloadSchemaType.BOOL
            }

            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=schema_map.get(field_type, models.PayloadSchemaType.KEYWORD)
            )

            logger.info(f"✓ Created payload index: {field_name} ({field_type})")

        except Exception as e:
            logger.error(f"Payload index creation error: {str(e)}")

    def ensure_payload_indexes(self):
        """Create all necessary payload indexes for GEO platform."""
        logger.info("Creating Qdrant payload indexes...")

        # Common filters
        self.create_payload_index('url', 'keyword')
        self.create_payload_index('domain', 'keyword')
        self.create_payload_index('content_type', 'keyword')
        self.create_payload_index('created_at', 'keyword')

        logger.info("✓ Qdrant payload indexes created")

    # ========== Health Check ==========

    def health_check(self) -> Dict[str, Any]:
        """
        Check Qdrant connection health.

        Returns:
            Health status dictionary
        """
        try:
            collections = self._client.get_collections()
            collection_info = self.get_collection_info()

            return {
                'status': 'healthy',
                'total_collections': len(collections.collections),
                'collection': collection_info
            }

        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# ========== Global Instance ==========

_qdrant_client = None


def get_qdrant_client() -> QdrantVectorClient:
    """Get global Qdrant client instance."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantVectorClient()
    return _qdrant_client
