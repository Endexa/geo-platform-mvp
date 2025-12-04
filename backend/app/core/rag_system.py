"""
RAG (Retrieval-Augmented Generation) System

Complete RAG system integrating MongoDB (document storage),
Qdrant (vector search), and OpenAI embeddings.
"""

import hashlib
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from openai import OpenAI
from loguru import logger

from .mongodb_client import get_mongodb_client
from .qdrant_client import get_qdrant_client


class RAGSystem:
    """
    Complete RAG system for document storage and retrieval.

    Features:
    - Document chunking and embedding
    - Vector similarity search
    - Metadata filtering
    - Deduplication
    - LLM context preparation
    """

    def __init__(self):
        """Initialize RAG system."""
        self.mongodb = get_mongodb_client()
        self.qdrant = get_qdrant_client()

        # Initialize OpenAI client
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')

        logger.info("✓ RAG system initialized")

    # ========== Document Ingestion ==========

    def add_document(self, url: str, content: str, metadata: Optional[Dict[str, Any]] = None,
                     chunk_size: int = 1000, chunk_overlap: int = 200) -> Dict[str, Any]:
        """
        Add document to RAG system.

        Workflow:
        1. Create content hash for deduplication
        2. Check if document already exists
        3. Chunk content
        4. Generate embeddings
        5. Store document in MongoDB
        6. Store vectors in Qdrant

        Args:
            url: Document URL
            content: Document text content
            metadata: Additional metadata
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks

        Returns:
            {
                'document_id': str,
                'chunks_created': int,
                'vectors_indexed': int,
                'status': str
            }
        """
        try:
            # 1. Create content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # 2. Check if already exists
            existing = self.mongodb.find_one('documents', {'content_hash': content_hash})
            if existing:
                logger.info(f"Document already exists: {url}")
                return {
                    'document_id': str(existing['_id']),
                    'chunks_created': 0,
                    'vectors_indexed': 0,
                    'status': 'already_exists'
                }

            # 3. Chunk content
            chunks = self._chunk_text(content, chunk_size, chunk_overlap)
            logger.info(f"Created {len(chunks)} chunks for {url}")

            # 4. Generate embeddings
            embeddings = self._generate_embeddings(chunks)
            logger.info(f"Generated {len(embeddings)} embeddings")

            # 5. Store document in MongoDB
            document_id = str(uuid.uuid4())
            metadata = metadata or {}

            document = {
                '_id': document_id,
                'url': url,
                'content': content,
                'content_hash': content_hash,
                'chunk_count': len(chunks),
                'char_count': len(content),
                'metadata': metadata,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

            self.mongodb.insert_document('documents', document)
            logger.info(f"✓ Stored document in MongoDB: {document_id}")

            # 6. Store vectors in Qdrant
            vectors_data = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{document_id}_{i}"

                payload = {
                    'document_id': document_id,
                    'url': url,
                    'chunk_index': i,
                    'chunk_text': chunk,
                    'char_count': len(chunk),
                    **metadata
                }

                vectors_data.append((chunk_id, embedding, payload))

            vectors_indexed = self.qdrant.upsert_vectors_batch(vectors_data)
            logger.info(f"✓ Indexed {vectors_indexed} vectors in Qdrant")

            return {
                'document_id': document_id,
                'chunks_created': len(chunks),
                'vectors_indexed': vectors_indexed,
                'status': 'success'
            }

        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            return {
                'document_id': None,
                'chunks_created': 0,
                'vectors_indexed': 0,
                'status': 'error',
                'error': str(e)
            }

    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add multiple documents in batch.

        Args:
            documents: List of dicts with 'url', 'content', 'metadata'

        Returns:
            Batch processing results
        """
        results = {
            'total': len(documents),
            'successful': 0,
            'failed': 0,
            'already_exists': 0,
            'document_ids': []
        }

        for doc in documents:
            result = self.add_document(
                url=doc.get('url'),
                content=doc.get('content'),
                metadata=doc.get('metadata')
            )

            if result['status'] == 'success':
                results['successful'] += 1
                results['document_ids'].append(result['document_id'])
            elif result['status'] == 'already_exists':
                results['already_exists'] += 1
            else:
                results['failed'] += 1

        return results

    # ========== Document Retrieval ==========

    def search_documents(self, query: str, limit: int = 5,
                        score_threshold: float = 0.7,
                        metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using semantic similarity.

        Args:
            query: Search query text
            limit: Max results
            score_threshold: Minimum similarity score (0-1)
            metadata_filter: Filter by metadata

        Returns:
            List of relevant document chunks with scores
        """
        try:
            # 1. Generate query embedding
            query_embedding = self._generate_embedding(query)

            # 2. Search in Qdrant
            results = self.qdrant.search_similar(
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                filter_dict=metadata_filter
            )

            # 3. Format results for LLM context
            formatted_results = []
            for result in results:
                payload = result['payload']

                formatted_results.append({
                    'chunk_id': result['id'],
                    'document_id': payload.get('document_id'),
                    'url': payload.get('url'),
                    'chunk_text': payload.get('chunk_text'),
                    'chunk_index': payload.get('chunk_index'),
                    'similarity_score': result['score'],
                    'metadata': {k: v for k, v in payload.items()
                                if k not in ['document_id', 'url', 'chunk_text', 'chunk_index']}
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document data
        """
        return self.mongodb.find_one('documents', {'_id': document_id})

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.

        Args:
            document_id: Document ID

        Returns:
            List of chunks with vectors
        """
        results = self.qdrant.search_similar(
            query_vector=[0] * self.qdrant.vector_size,  # Dummy vector
            limit=1000,
            filter_dict={'document_id': document_id}
        )

        return results

    # ========== Prepare Context for LLM ==========

    def prepare_rag_context(self, query: str, max_chunks: int = 3,
                           metadata_filter: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare context string for LLM from retrieved documents.

        Args:
            query: User query
            max_chunks: Max chunks to include
            metadata_filter: Filter documents

        Returns:
            Formatted context string for LLM
        """
        results = self.search_documents(
            query=query,
            limit=max_chunks,
            metadata_filter=metadata_filter
        )

        if not results:
            return "No relevant context found."

        # Format context
        context_parts = ["Retrieved context:\n"]

        for i, result in enumerate(results, 1):
            context_parts.append(f"\n[Source {i}] {result['url']}")
            context_parts.append(f"Relevance: {result['similarity_score']:.2%}")
            context_parts.append(f"{result['chunk_text']}\n")

        return "\n".join(context_parts)

    def generate_rag_response(self, query: str, system_prompt: str,
                             max_chunks: int = 3) -> Dict[str, Any]:
        """
        Generate LLM response with RAG context.

        Args:
            query: User query
            system_prompt: System instructions
            max_chunks: Max context chunks

        Returns:
            {
                'response': str,
                'sources': List[Dict],
                'tokens_used': int
            }
        """
        try:
            # Retrieve relevant context
            sources = self.search_documents(query=query, limit=max_chunks)

            if not sources:
                logger.warning("No relevant sources found for RAG")

            # Build context
            context = self.prepare_rag_context(query, max_chunks)

            # Generate response with OpenAI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuery: {query}"}
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            return {
                'response': response.choices[0].message.content,
                'sources': sources,
                'tokens_used': response.usage.total_tokens
            }

        except Exception as e:
            logger.error(f"RAG response generation error: {str(e)}")
            return {
                'response': f"Error generating response: {str(e)}",
                'sources': [],
                'tokens_used': 0
            }

    # ========== Document Management ==========

    def delete_document(self, document_id: str) -> bool:
        """
        Delete document and all its vectors.

        Args:
            document_id: Document ID

        Returns:
            True if successful
        """
        try:
            # Delete from MongoDB
            mongo_deleted = self.mongodb.delete_one('documents', {'_id': document_id})

            # Delete vectors from Qdrant
            qdrant_deleted = self.qdrant.delete_vectors_by_filter({'document_id': document_id})

            if mongo_deleted and qdrant_deleted:
                logger.info(f"✓ Deleted document: {document_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Document deletion error: {str(e)}")
            return False

    def update_document(self, document_id: str, content: str,
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update document content and re-index.

        Args:
            document_id: Document ID
            content: New content
            metadata: Updated metadata

        Returns:
            Update result
        """
        try:
            # Delete old version
            self.delete_document(document_id)

            # Get original URL
            old_doc = self.get_document_by_id(document_id)
            url = old_doc['url'] if old_doc else "unknown"

            # Re-add with new content
            return self.add_document(url=url, content=content, metadata=metadata)

        except Exception as e:
            logger.error(f"Document update error: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    # ========== Utility Methods ==========

    def _chunk_text(self, text: str, chunk_size: int = 1000,
                    chunk_overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)

                if break_point > chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1

            chunks.append(chunk.strip())
            start = end - chunk_overlap

        return [c for c in chunks if c]  # Remove empty chunks

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Embedding generation error: {str(e)}")
            raise

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []

        # Batch API calls (OpenAI supports up to 2048 texts per request)
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=batch
                )

                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"Batch embedding error: {str(e)}")
                raise

        return embeddings

    # ========== Statistics ==========

    def get_statistics(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        try:
            return {
                'mongodb': {
                    'total_documents': self.mongodb.count_documents('documents'),
                    'collections': self.mongodb.db.list_collection_names()
                },
                'qdrant': {
                    'total_vectors': self.qdrant.count_vectors(),
                    'collection_info': self.qdrant.get_collection_info()
                }
            }

        except Exception as e:
            logger.error(f"Statistics error: {str(e)}")
            return {}


# ========== Global Instance ==========

_rag_system = None


def get_rag_system() -> RAGSystem:
    """Get global RAG system instance."""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem()
    return _rag_system
