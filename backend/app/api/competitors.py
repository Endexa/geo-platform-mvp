"""Competitor API endpoints for leaderboard, crawl trigger, competitor detail,
SOV trend, and score comparison.

Provides GET leaderboard (share-of-voice rankings), POST crawl trigger
(resolve URLs and score competitors), GET competitor detail, GET SOV trend
for a competitor brand across audits, and GET score comparison (site vs
competitors side-by-side).

All endpoints require authentication and verify audit ownership.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import Profile
from app.models.audit import Audit
from app.models.competitor import CompetitorAudit
from app.schemas.competitor import (
    CompetitorAuditSummary,
    CompetitorLeaderboardResponse,
)
from app.services.competitor_service import CompetitorService

router = APIRouter(prefix="/api/v1/competitors", tags=["competitors"])


def _verify_audit_ownership(
    audit_id: str, db: Session, current_user: Profile
) -> Audit:
    """Verify audit exists and belongs to current user.

    Args:
        audit_id: The audit UUID string.
        db: SQLAlchemy session.
        current_user: Authenticated user profile.

    Returns:
        The Audit ORM object.

    Raises:
        HTTPException 404 if audit not found or not owned by user.
    """
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit or audit.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found",
        )
    return audit


@router.get(
    "/{audit_id}/leaderboard",
    response_model=CompetitorLeaderboardResponse,
)
def get_leaderboard(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get the competitor leaderboard for an audit.

    Returns all discovered entities ranked by share-of-voice with
    competitor audit summaries for crawled competitors.
    """
    _verify_audit_ownership(audit_id, db, current_user)

    service = CompetitorService(db)
    data = service.get_leaderboard(audit_id)

    return CompetitorLeaderboardResponse(**data)


@router.post("/{audit_id}/crawl")
async def trigger_competitor_crawl(
    audit_id: str,
    max_competitors: int | None = None,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Trigger competitor URL resolution and crawl+score for an audit.

    Resolves brand names to URLs and crawls the top competitors.
    This is a synchronous endpoint (not a Celery task) since competitor
    crawling typically takes 30-60s for 3-5 competitors.

    Args:
        audit_id: The audit UUID.
        max_competitors: Optional override for COMPETITOR_MAX_COUNT.
    """
    _verify_audit_ownership(audit_id, db, current_user)

    service = CompetitorService(db)
    results = await service.crawl_top_competitors(audit_id, max_competitors)

    audit_summaries = []
    for ca in results:
        audit_summaries.append({
            "id": str(ca.id),
            "competitor_name": ca.competitor_name,
            "competitor_url": ca.competitor_url,
            "optimization_score": ca.optimization_score,
            "crawlability_avg": ca.crawlability_avg,
            "content_structure_avg": ca.content_structure_avg,
            "structured_data_avg": ca.structured_data_avg,
            "authority_avg": ca.authority_avg,
            "pages_scored": ca.pages_scored,
            "status": ca.status,
            "created_at": (
                ca.created_at.isoformat() if ca.created_at else ""
            ),
        })

    logger.info(
        "Audit {}: competitor crawl triggered by user {}, {} crawled",
        audit_id,
        current_user.id,
        len(results),
    )

    return {
        "status": "completed",
        "competitors_crawled": len(results),
        "competitor_audits": audit_summaries,
    }


@router.get(
    "/{audit_id}/competitor/{competitor_audit_id}",
    response_model=CompetitorAuditSummary,
)
def get_competitor_detail(
    audit_id: str,
    competitor_audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get detailed results for a specific competitor audit.

    Verifies the parent audit belongs to the current user.
    """
    _verify_audit_ownership(audit_id, db, current_user)

    comp_audit = (
        db.query(CompetitorAudit)
        .filter(CompetitorAudit.id == competitor_audit_id)
        .filter(CompetitorAudit.parent_audit_id == audit_id)
        .first()
    )

    if not comp_audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor audit not found",
        )

    return CompetitorAuditSummary(
        id=str(comp_audit.id),
        competitor_name=comp_audit.competitor_name,
        competitor_url=comp_audit.competitor_url,
        optimization_score=comp_audit.optimization_score,
        crawlability_avg=comp_audit.crawlability_avg,
        content_structure_avg=comp_audit.content_structure_avg,
        structured_data_avg=comp_audit.structured_data_avg,
        authority_avg=comp_audit.authority_avg,
        pages_scored=comp_audit.pages_scored,
        status=comp_audit.status,
        created_at=(
            comp_audit.created_at.isoformat() if comp_audit.created_at else ""
        ),
    )


@router.get("/brands/{brand_id}/sov-trend")
def get_sov_trend(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get share-of-voice trend data for a competitor brand across audits.

    Returns time-series data points ordered by audit date with SOV percentage
    and mention count at each point.
    """
    trend = CompetitorService.get_competitor_sov_trend(
        db, brand_id, str(current_user.id)
    )
    return trend
