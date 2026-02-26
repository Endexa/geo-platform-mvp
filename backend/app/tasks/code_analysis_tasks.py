"""Celery task for asynchronous code analysis processing.

Pipeline: pending -> parsing -> recommending -> completed (or failed).
Triggered by the upload endpoint after creating the CodeAnalysis DB record.
"""

import asyncio
from datetime import datetime, timezone

from loguru import logger

from app.core.config import settings  # noqa: F401  (imported for settings access in task)
from app.core.database import SessionLocal
from app.models.code_analysis import CodeAnalysis
from app.services.code_analysis_service import CodeAnalysisService
from app.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.code_analysis.process_upload",
    max_retries=1,
    default_retry_delay=60,
)
def process_code_analysis(self, code_analysis_id: str):
    """Parse uploaded AI tool output and generate enriched code recommendations.

    Status lifecycle: pending -> parsing -> recommending -> completed / failed.

    Args:
        code_analysis_id: UUID string of the CodeAnalysis record to process.
    """
    db = SessionLocal()
    ca = None
    try:
        ca = db.query(CodeAnalysis).filter(CodeAnalysis.id == code_analysis_id).first()
        if not ca:
            logger.error("CodeAnalysis %s not found", code_analysis_id)
            return

        service = CodeAnalysisService()

        # Stage 1: Parse uploaded text with LLM structured output
        ca.status = "parsing"
        db.commit()

        result = asyncio.run(service.parse_output(ca.raw_output))

        ca.parsed_findings = result.model_dump()
        ca.detected_framework = result.detected_framework
        ca.model_used = settings.CODE_ANALYSIS_MODEL
        ca.status = "recommending"
        db.commit()

        # Stage 2: Generate code recommendations from parsed findings
        service.generate_code_recommendations(ca, result, db)

        ca.status = "completed"
        ca.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Code analysis %s completed with %d findings",
            code_analysis_id,
            len(result.findings),
        )

    except Exception as e:
        logger.error("Code analysis %s failed: %s", code_analysis_id, str(e))
        if ca:
            ca.status = "failed"
            ca.error_message = str(e)[:1000]
            db.commit()
    finally:
        db.close()
