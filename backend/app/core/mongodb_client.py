"""
MongoDB Client

Client for MongoDB Atlas with connection pooling, error handling,
and optimized queries for document storage.
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure, DuplicateKeyError
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from contextlib import contextmanager

from loguru import logger


class MongoDBClient:
    """
    MongoDB client with connection pooling and error handling.

    Features:
    - Connection pooling for high throughput
    - Automatic reconnection
    - Query optimization
    - Index management
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

        # Get MongoDB URI from environment
        self.mongo_uri = os.getenv('MONGO_URI')
        if not self.mongo_uri:
            raise ValueError("MONGO_URI environment variable not set")

        self.db_name = os.getenv('MONGO_DB_NAME', 'geo_platform')

        # Initialize connection
        self._connect()
        self._initialized = True

    def _connect(self):
        """Establish MongoDB connection with retries."""
        try:
            # Connection pool settings for high throughput
            self._client = MongoClient(
                self.mongo_uri,
                maxPoolSize=100,
                minPoolSize=10,
                maxIdleTimeMS=60000,
                connectTimeoutMS=10000,
                serverSelectionTimeoutMS=10000
            )

            # Test connection
            self._client.admin.command('ping')

            self.db = self._client[self.db_name]

            logger.info(f"✓ Connected to MongoDB: {self.db_name}")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def get_collection(self, collection_name: str):
        """Get collection instance."""
        return self.db[collection_name]

    # ========== Document Operations ==========

    def insert_document(self, collection: str, document: Dict[str, Any]) -> str:
        """
        Insert a document.

        Args:
            collection: Collection name
            document: Document to insert

        Returns:
            Inserted document ID as string
        """
        try:
            # Add timestamp if not present
            if 'created_at' not in document:
                document['created_at'] = datetime.utcnow()

            result = self.db[collection].insert_one(document)
            return str(result.inserted_id)

        except DuplicateKeyError:
            logger.warning(f"Duplicate key error in {collection}")
            raise
        except Exception as e:
            logger.error(f"Insert error in {collection}: {str(e)}")
            raise

    def insert_many(self, collection: str, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple documents.

        Args:
            collection: Collection name
            documents: List of documents

        Returns:
            List of inserted IDs
        """
        try:
            # Add timestamps
            for doc in documents:
                if 'created_at' not in doc:
                    doc['created_at'] = datetime.utcnow()

            result = self.db[collection].insert_many(documents)
            return [str(id) for id in result.inserted_ids]

        except Exception as e:
            logger.error(f"Bulk insert error in {collection}: {str(e)}")
            raise

    def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find single document.

        Args:
            collection: Collection name
            query: Query filter

        Returns:
            Document or None
        """
        try:
            return self.db[collection].find_one(query)
        except Exception as e:
            logger.error(f"Find error in {collection}: {str(e)}")
            return None

    def find_many(self, collection: str, query: Dict[str, Any] = None,
                  limit: int = 0, skip: int = 0,
                  sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        """
        Find multiple documents.

        Args:
            collection: Collection name
            query: Query filter
            limit: Max results (0 = no limit)
            skip: Skip first N results
            sort: Sort order [(field, direction)]

        Returns:
            List of documents
        """
        try:
            query = query or {}
            cursor = self.db[collection].find(query)

            if sort:
                cursor = cursor.sort(sort)

            if skip > 0:
                cursor = cursor.skip(skip)

            if limit > 0:
                cursor = cursor.limit(limit)

            return list(cursor)

        except Exception as e:
            logger.error(f"Find many error in {collection}: {str(e)}")
            return []

    def update_one(self, collection: str, query: Dict[str, Any],
                   update: Dict[str, Any], upsert: bool = False) -> bool:
        """
        Update single document.

        Args:
            collection: Collection name
            query: Query filter
            update: Update operations
            upsert: Create if not exists

        Returns:
            True if updated
        """
        try:
            # Add updated_at timestamp
            if '$set' in update:
                update['$set']['updated_at'] = datetime.utcnow()
            else:
                update['$set'] = {'updated_at': datetime.utcnow()}

            result = self.db[collection].update_one(query, update, upsert=upsert)
            return result.modified_count > 0 or result.upserted_id is not None

        except Exception as e:
            logger.error(f"Update error in {collection}: {str(e)}")
            return False

    def update_many(self, collection: str, query: Dict[str, Any],
                    update: Dict[str, Any]) -> int:
        """
        Update multiple documents.

        Returns:
            Number of documents modified
        """
        try:
            if '$set' in update:
                update['$set']['updated_at'] = datetime.utcnow()
            else:
                update['$set'] = {'updated_at': datetime.utcnow()}

            result = self.db[collection].update_many(query, update)
            return result.modified_count

        except Exception as e:
            logger.error(f"Update many error in {collection}: {str(e)}")
            return 0

    def delete_one(self, collection: str, query: Dict[str, Any]) -> bool:
        """Delete single document."""
        try:
            result = self.db[collection].delete_one(query)
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Delete error in {collection}: {str(e)}")
            return False

    def delete_many(self, collection: str, query: Dict[str, Any]) -> int:
        """
        Delete multiple documents.

        Returns:
            Number of documents deleted
        """
        try:
            result = self.db[collection].delete_many(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Delete many error in {collection}: {str(e)}")
            return 0

    def count_documents(self, collection: str, query: Dict[str, Any] = None) -> int:
        """Count documents matching query."""
        try:
            query = query or {}
            return self.db[collection].count_documents(query)
        except Exception as e:
            logger.error(f"Count error in {collection}: {str(e)}")
            return 0

    # ========== Aggregation ==========

    def aggregate(self, collection: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run aggregation pipeline.

        Args:
            collection: Collection name
            pipeline: Aggregation pipeline

        Returns:
            Aggregation results
        """
        try:
            return list(self.db[collection].aggregate(pipeline))
        except Exception as e:
            logger.error(f"Aggregation error in {collection}: {str(e)}")
            return []

    # ========== Index Management ==========

    def create_index(self, collection: str, keys: List[tuple], unique: bool = False):
        """
        Create index on collection.

        Args:
            collection: Collection name
            keys: List of (field, direction) tuples
            unique: Unique index

        Example:
            create_index('users', [('email', ASCENDING)], unique=True)
        """
        try:
            self.db[collection].create_index(keys, unique=unique)
            logger.info(f"✓ Created index on {collection}: {keys}")
        except Exception as e:
            logger.error(f"Index creation error: {str(e)}")

    def ensure_indexes(self):
        """Create all required indexes for GEO platform."""
        logger.info("Creating MongoDB indexes...")

        # Documents collection
        self.create_index('documents', [('url', ASCENDING)], unique=True)
        self.create_index('documents', [('content_hash', ASCENDING)])
        self.create_index('documents', [('created_at', DESCENDING)])

        # Analyses collection
        self.create_index('analyses', [('site_url', ASCENDING)])
        self.create_index('analyses', [('status', ASCENDING)])
        self.create_index('analyses', [('created_at', DESCENDING)])

        # Data point results
        self.create_index('data_point_results', [('analysis_id', ASCENDING)])
        self.create_index('data_point_results', [('module', ASCENDING)])
        self.create_index('data_point_results', [('priority', ASCENDING)])

        # Organizations
        self.create_index('organizations', [('name', ASCENDING)], unique=True)

        # Users
        self.create_index('users', [('email', ASCENDING)], unique=True)

        logger.info("✓ MongoDB indexes created")

    # ========== Health Check ==========

    def health_check(self) -> Dict[str, Any]:
        """
        Check MongoDB connection health.

        Returns:
            Health status dictionary
        """
        try:
            # Ping server
            self._client.admin.command('ping')

            # Get server info
            server_info = self._client.server_info()

            return {
                'status': 'healthy',
                'database': self.db_name,
                'version': server_info.get('version'),
                'collections': self.db.list_collection_names()
            }

        except Exception as e:
            logger.error(f"MongoDB health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")


# ========== Global Instance ==========

_mongodb_client = None


def get_mongodb_client() -> MongoDBClient:
    """Get global MongoDB client instance."""
    global _mongodb_client
    if _mongodb_client is None:
        _mongodb_client = MongoDBClient()
    return _mongodb_client


@contextmanager
def mongodb_session():
    """
    Context manager for MongoDB operations.

    Usage:
        with mongodb_session() as db:
            db.insert_document('users', {'name': 'John'})
    """
    client = get_mongodb_client()
    try:
        yield client
    except Exception as e:
        logger.error(f"MongoDB session error: {str(e)}")
        raise
