"""
RAG API Endpoints

FastAPI routes for document ingestion, vector search, and RAG responses.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.core.rag_system import get_rag_system
from app.core.rate_limiter import standard_rate_limit
from app.core.validators import SecureBaseModel
from loguru import logger


router = APIRouter()


# ========== Request/Response Models ==========

class AddDocumentRequest(SecureBaseModel):
    """Request to add a document."""
    url: str = Field(..., min_length=8, max_length=2048)
    content: str = Field(..., min_length=10, max_length=1000000)
    metadata: Optional[Dict[str, Any]] = None
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)


class AddDocumentsBatchRequest(SecureBaseModel):
    """Request to add multiple documents."""
    documents: List[Dict[str, Any]] = Field(..., min_items=1, max_items=100)


class SearchDocumentsRequest(SecureBaseModel):
    """Request to search documents."""
    query: str = Field(..., min_length=3, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata_filter: Optional[Dict[str, Any]] = None


class RAGQueryRequest(SecureBaseModel):
    """Request for RAG-enhanced LLM response."""
    query: str = Field(..., min_length=3, max_length=1000)
    system_prompt: str = Field(
        default="You are a helpful assistant. Answer based on the provided context.",
        max_length=2000
    )
    max_chunks: int = Field(default=3, ge=1, le=10)


# ========== Endpoints ==========

@router.post("/documents/add", dependencies=[Depends(standard_rate_limit)])
async def add_document(request: AddDocumentRequest):
    """
    Add a document to RAG system.

    **Workflow:**
    1. Chunk content
    2. Generate embeddings
    3. Store in MongoDB
    4. Index vectors in Qdrant

    **Returns:**
    - document_id
    - chunks_created
    - vectors_indexed
    """
    try:
        rag_system = get_rag_system()

        result = rag_system.add_document(
            url=request.url,
            content=request.content,
            metadata=request.metadata,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result.get('error'))

        return result

    except Exception as e:
        logger.error(f"Add document error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/batch", dependencies=[Depends(standard_rate_limit)])
async def add_documents_batch(request: AddDocumentsBatchRequest):
    """
    Add multiple documents in batch.

    **Batch Processing:**
    - Processes documents sequentially
    - Returns aggregated results
    - Continues on individual failures

    **Returns:**
    - total: Total documents
    - successful: Successfully added
    - failed: Failed to add
    - already_exists: Duplicates skipped
    """
    try:
        rag_system = get_rag_system()

        result = rag_system.add_documents_batch(request.documents)

        return result

    except Exception as e:
        logger.error(f"Batch add error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", dependencies=[Depends(standard_rate_limit)])
async def search_documents(request: SearchDocumentsRequest):
    """
    Search for relevant documents using semantic similarity.

    **Process:**
    1. Generate query embedding
    2. Search in Qdrant vector database
    3. Return top-K most similar chunks

    **Returns:**
    List of document chunks with:
    - chunk_text
    - similarity_score
    - url
    - metadata
    """
    try:
        rag_system = get_rag_system()

        results = rag_system.search_documents(
            query=request.query,
            limit=request.limit,
            score_threshold=request.score_threshold,
            metadata_filter=request.metadata_filter
        )

        return {
            'query': request.query,
            'results_count': len(results),
            'results': results
        }

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/query", dependencies=[Depends(standard_rate_limit)])
async def rag_query(request: RAGQueryRequest):
    """
    Generate LLM response with RAG context.

    **RAG Process:**
    1. Search for relevant documents
    2. Prepare context from top results
    3. Generate LLM response with context
    4. Return response + sources

    **Returns:**
    - response: LLM-generated answer
    - sources: Retrieved documents
    - tokens_used: API token usage
    """
    try:
        rag_system = get_rag_system()

        result = rag_system.generate_rag_response(
            query=request.query,
            system_prompt=request.system_prompt,
            max_chunks=request.max_chunks
        )

        return result

    except Exception as e:
        logger.error(f"RAG query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}", dependencies=[Depends(standard_rate_limit)])
async def get_document(document_id: str):
    """
    Retrieve document by ID.

    **Returns:**
    Complete document data including:
    - url
    - content
    - metadata
    - chunk_count
    """
    try:
        rag_system = get_rag_system()

        document = rag_system.get_document_by_id(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Convert ObjectId to string for JSON serialization
        document['_id'] = str(document['_id'])

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}", dependencies=[Depends(standard_rate_limit)])
async def delete_document(document_id: str):
    """
    Delete document and all its vectors.

    **Process:**
    1. Delete from MongoDB
    2. Delete vectors from Qdrant
    3. Return confirmation
    """
    try:
        rag_system = get_rag_system()

        success = rag_system.delete_document(document_id)

        if not success:
            raise HTTPException(status_code=404, detail="Document not found or deletion failed")

        return {
            'document_id': document_id,
            'status': 'deleted'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", dependencies=[Depends(standard_rate_limit)])
async def get_statistics():
    """
    Get RAG system statistics.

    **Returns:**
    - MongoDB: Document counts, collections
    - Qdrant: Vector counts, collection info
    """
    try:
        rag_system = get_rag_system()

        stats = rag_system.get_statistics()

        return stats

    except Exception as e:
        logger.error(f"Statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", dependencies=[Depends(standard_rate_limit)])
async def health_check():
    """
    Health check for RAG system.

    **Checks:**
    - MongoDB connection
    - Qdrant connection
    - OpenAI API availability
    """
    try:
        rag_system = get_rag_system()

        mongodb_health = rag_system.mongodb.health_check()
        qdrant_health = rag_system.qdrant.health_check()

        return {
            'status': 'healthy' if (
                mongodb_health['status'] == 'healthy' and
                qdrant_health['status'] == 'healthy'
            ) else 'degraded',
            'mongodb': mongodb_health,
            'qdrant': qdrant_health
        }

    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
