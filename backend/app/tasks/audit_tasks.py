"""Celery task for the audit pipeline: crawl URL -> generate queries -> store results.

Orchestrates the complete Phase 2 pipeline as a background task triggered by the audit API.
Updates audit status at each stage and handles errors gracefully.
"""

import asyncio
from datetime import datetime, timezone

from loguru import logger

from app.core.database import SessionLocal
from app.models.audit import Audit, AuditStatus
from app.models.audit_query import AuditQuery
from app.services.crawler_service import CrawlerService
from app.services.query_generator import QueryGeneratorService
from app.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.audit.run_crawl_and_generate",
    max_retries=1,
    default_retry_delay=30,
)
def run_crawl_and_generate(self, audit_id: str, url: str):
    """Crawl a URL, extract brand signals, generate categorized queries, and store results.

    Pipeline stages:
        1. CRAWLING: Fetch URL, extract structured data and AI-readiness signals
        2. GENERATING_QUERIES: Extract brand name, call LLM to generate 10-15 queries
        3. COMPLETED: Store generated queries as AuditQuery records

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

        # Stage 3: Store queries
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

        # Mark as completed
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
