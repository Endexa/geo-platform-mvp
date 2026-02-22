"""Celery task for the audit pipeline: crawl -> generate -> dispatch -> analyze -> score -> discover -> complete.

Orchestrates the complete audit pipeline as a background task triggered by the audit API.
Updates audit status at each stage and handles errors gracefully.

Pipeline stages:
    1. CRAWLING — Fetch URL, extract structured data and AI-readiness signals
    2. GENERATING_QUERIES — Extract brand name, call LLM to generate 10-15 queries
    3. DISPATCHING — Dispatch queries to AI engines (OpenAI, Anthropic, Perplexity, Gemini)
    4. ANALYZING — Detect brand mentions in responses and compute visibility score
    5. SCORING — Multi-page crawl, per-page scoring, weakest-link aggregation
    6. DISCOVERING_COMPETITORS — Extract entities from AI responses, compute share-of-voice
    7. COMPLETED — All stages finished successfully
"""

import asyncio
from datetime import datetime, timezone

from loguru import logger

from app.core.database import SessionLocal
from app.models.audit import Audit, AuditStatus
from app.models.audit_query import AuditQuery
from app.models.brand_mention import BrandMention
from app.models.engine_response import EngineResponse
from app.services.crawler_service import CrawlerService
from app.services.dispatch_service import DispatchService
from app.services.mention_detector import MentionDetectorService
from app.services.query_generator import QueryGeneratorService
from app.services.scoring_service import ScoringService
from app.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.audit.run_crawl_and_generate",
    max_retries=1,
    default_retry_delay=30,
)
def run_crawl_and_generate(self, audit_id: str, url: str):
    """Crawl a URL, extract brand signals, generate queries, dispatch, analyze, score, discover competitors.

    Pipeline stages:
        1. CRAWLING: Fetch URL, extract structured data and AI-readiness signals
        2. GENERATING_QUERIES: Extract brand name, call LLM to generate 10-15 queries
        3. DISPATCHING: Dispatch queries to AI engines (OpenAI, Anthropic, Perplexity, Gemini)
        4. ANALYZING: Detect brand mentions in responses and compute visibility score
        5. SCORING: Multi-page crawl, per-page scoring, weakest-link aggregation
        6. DISCOVERING_COMPETITORS: Extract entities from AI responses, compute share-of-voice
        7. COMPLETED: All stages finished successfully

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

        # Stage 4: Analyze mentions and compute visibility score
        logger.info("Audit {}: starting mention analysis", audit_id)
        audit.status = AuditStatus.ANALYZING.value
        db.commit()

        # Extract brand name from crawl data (same extraction used in Stage 2)
        query_gen_for_brand = QueryGeneratorService()
        brand_name = query_gen_for_brand.extract_brand_name(audit.crawl_data)

        # Generate brand variants
        detector = MentionDetectorService()
        brand_variants = detector.generate_brand_variants(brand_name)
        logger.info(
            "Audit {}: analyzing mentions for brand '{}' ({} variants)",
            audit_id,
            brand_name,
            len(brand_variants),
        )

        # Load successful engine responses for analysis
        responses = (
            db.query(EngineResponse)
            .join(AuditQuery)
            .filter(AuditQuery.audit_id == audit_id)
            .filter(EngineResponse.error_message.is_(None))
            .all()
        )

        # Detect mentions in each response
        total_mentions = 0
        for response in responses:
            mentions = detector.detect_mentions(
                response_text=response.response_text,
                brand_name=brand_name,
                brand_variants=brand_variants,
            )
            for mention_data in mentions:
                mention = BrandMention(
                    engine_response_id=response.id,
                    **mention_data,
                )
                db.add(mention)
                total_mentions += 1
        db.commit()
        logger.info(
            "Audit {}: detected {} mentions across {} responses",
            audit_id,
            total_mentions,
            len(responses),
        )

        # Compute visibility score
        scorer = ScoringService(db)
        score = scorer.compute_audit_score(
            audit_id=audit_id, total_queries=len(queries)
        )
        db.add(score)
        db.commit()
        logger.info(
            "Audit {}: visibility score = {}/100", audit_id, score.overall_score
        )

        # Stage 5: SCORING -- multi-page crawl, per-page scoring, aggregation
        logger.info("Audit {}: starting scoring stage", audit_id)
        audit.status = AuditStatus.SCORING.value
        db.commit()

        from app.services.scoring.scoring_orchestrator import ScoringOrchestrator

        orchestrator = ScoringOrchestrator(db)

        # Register all available scorers -- conditional imports allow
        # the pipeline to work as scorers are built incrementally
        try:
            from app.services.scoring.crawlability_scorer import CrawlabilityScorer
            orchestrator.register_scorer("crawlability", CrawlabilityScorer())
        except ImportError:
            logger.warning("CrawlabilityScorer not yet available, skipping")
        try:
            from app.services.scoring.content_structure_scorer import ContentStructureScorer
            orchestrator.register_scorer("content_structure", ContentStructureScorer())
        except ImportError:
            logger.warning("ContentStructureScorer not yet available, skipping")
        try:
            from app.services.scoring.structured_data_scorer import StructuredDataScorer
            orchestrator.register_scorer("structured_data", StructuredDataScorer())
        except ImportError:
            logger.warning("StructuredDataScorer not yet available, skipping")
        try:
            from app.services.scoring.authority_scorer import AuthorityScorer
            orchestrator.register_scorer("authority", AuthorityScorer())
        except ImportError:
            logger.warning("AuthorityScorer not yet available, skipping")

        visibility_score_value = score.overall_score if score else 0
        scoring_result = asyncio.run(
            orchestrator.score_audit(audit_id, audit.crawl_data, visibility_score_value)
        )

        # Persist the optimization score on the Audit row
        audit.optimization_score = scoring_result["optimization_score"]
        db.commit()
        logger.info(
            "Audit {}: optimization_score={}, pages_scored={}, pages_discovered={}",
            audit_id,
            scoring_result["optimization_score"],
            scoring_result["pages_scored"],
            scoring_result["pages_discovered"],
        )

        # Stage 6: Discover competitors from AI responses
        logger.info("Audit {}: starting competitor discovery", audit_id)
        audit.status = AuditStatus.DISCOVERING_COMPETITORS.value
        db.commit()

        from app.services.entity_extractor import EntityExtractorService

        extractor = EntityExtractorService()
        query_gen_for_brand2 = QueryGeneratorService()
        brand_name = query_gen_for_brand2.extract_brand_name(audit.crawl_data)

        competitors = extractor.discover_competitors_for_audit(
            db=db, audit_id=audit_id, user_brand_name=brand_name
        )
        db.commit()
        logger.info(
            "Audit {}: discovered {} competitor entities, {} non-brand",
            audit_id,
            len(competitors),
            sum(1 for c in competitors if not c.is_user_brand),
        )

        # After entity extraction: resolve URLs and crawl top competitors
        # Non-fatal: competitor crawl failure should not fail the audit
        try:
            from app.services.competitor_service import CompetitorService

            competitor_svc = CompetitorService(db)
            loop = asyncio.new_event_loop()
            try:
                competitor_audits = loop.run_until_complete(
                    competitor_svc.crawl_top_competitors(audit_id)
                )
                logger.info(
                    "Audit {}: crawled {} competitor sites",
                    audit_id,
                    len(competitor_audits),
                )
            finally:
                loop.close()
        except Exception as e:
            logger.error(
                "Audit {}: competitor crawling failed: {}",
                audit_id,
                str(e),
            )

        # Stage 7: Mark as completed
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
