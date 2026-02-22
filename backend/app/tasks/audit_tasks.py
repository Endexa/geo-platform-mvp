"""Celery task for the audit pipeline: crawl URL -> generate queries -> dispatch -> complete.

Orchestrates the complete audit pipeline as a background task triggered by the audit API.
Updates audit status at each stage and handles errors gracefully.

Pipeline stages:
    1. CRAWLING — Fetch URL, extract structured data and AI-readiness signals
    2. GENERATING_QUERIES — Extract brand name, call LLM to generate 10-15 queries
    3. DISPATCHING — Dispatch queries to AI engines (OpenAI, Anthropic, Perplexity)
    4. COMPLETED — All stages finished successfully
"""

import asyncio
from datetime import datetime, timezone

from loguru import logger

from app.core.database import SessionLocal
from app.models.audit import Audit, AuditStatus
from app.models.audit_query import AuditQuery
from app.models.engine_response import EngineResponse
from app.services.crawler_service import CrawlerService
from app.services.dispatch_service import DispatchService
from app.services.query_generator import QueryGeneratorService
from app.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.audit.run_crawl_and_generate",
    max_retries=1,
    default_retry_delay=30,
)
def run_crawl_and_generate(self, audit_id: str, url: str):
    """Crawl a URL, extract brand signals, generate queries, dispatch to AI engines.

    Pipeline stages:
        1. CRAWLING: Fetch URL, extract structured data and AI-readiness signals
        2. GENERATING_QUERIES: Extract brand name, call LLM to generate 10-15 queries
        3. DISPATCHING: Dispatch queries to AI engines (OpenAI, Anthropic, Perplexity)
        4. COMPLETED: All stages finished successfully

    Args:
        audit_id: UUID string of the Audit record to process.
        url: The URL to crawl and analyze.

    Raises:
        Exception: Re-raises any exception after setting audit status to FAILED.
    """
    db = SessionLocal()
    try:
        # Fetch the audit record
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            logger.error("Audit {} not found in database", audit_id)
            return

        # Stage 1: Crawl the URL
        logger.info("Audit {}: starting crawl for {}", audit_id, url)
        audit.status = AuditStatus.CRAWLING.value
        db.commit()

        crawler = CrawlerService()
        crawl_result = asyncio.run(crawler.crawl(url))
        audit.crawl_data = crawl_result.model_dump()
        db.commit()
        logger.info(
            "Audit {}: crawl complete, {} words extracted",
            audit_id,
            crawl_result.word_count,
        )

        # Stage 2: Generate queries
        audit.status = AuditStatus.GENERATING_QUERIES.value
        db.commit()

        query_gen = QueryGeneratorService()
        brand_name = query_gen.extract_brand_name(audit.crawl_data)
        logger.info("Audit {}: extracted brand name '{}'", audit_id, brand_name)

        query_set = query_gen.generate(audit.crawl_data, brand_name)

        # Store queries
        for i, q in enumerate(query_set.queries):
            audit_query = AuditQuery(
                audit_id=audit_id,
                category=q.category,
                query_text=q.query_text,
                sort_order=i,
            )
            db.add(audit_query)
        db.commit()
        logger.info(
            "Audit {}: stored {} queries", audit_id, len(query_set.queries)
        )

        # Stage 3: Dispatch to AI engines
        logger.info("Audit {}: starting dispatch to AI engines", audit_id)
        audit.status = AuditStatus.DISPATCHING.value
        db.commit()

        # Reload queries from DB to get their IDs (needed for FK in engine_responses)
        queries = db.query(AuditQuery).filter(AuditQuery.audit_id == audit_id).all()

        dispatcher = DispatchService(db)
        dispatch_result = dispatcher.dispatch_all_queries(
            audit_id=audit_id,
            queries=queries,
        )
        logger.info(
            "Audit {}: dispatched {} queries, {} responses, {} failures, budget_exceeded={}",
            audit_id,
            dispatch_result.total_queries,
            dispatch_result.total_responses,
            dispatch_result.total_failures,
            dispatch_result.budget_exceeded,
        )

        # Stage 4: Mark as completed
        audit.status = AuditStatus.COMPLETED.value
        audit.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Audit {}: pipeline complete", audit_id)

    except Exception as e:
        logger.error("Audit {} failed: {}", audit_id, str(e))
        try:
            audit = db.query(Audit).filter(Audit.id == audit_id).first()
            if audit:
                audit.status = AuditStatus.FAILED.value
                audit.error_message = str(e)[:1000]  # Truncate long error messages
                db.commit()
        except Exception:
            logger.error("Failed to update audit {} status to FAILED", audit_id)
        raise
    finally:
        db.close()
