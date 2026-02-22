"""Recommendation API endpoints for CRUD, sentiment, content gaps, and export.

Provides GET recommendations with filtering, PATCH status updates,
GET per-engine sentiment summary, GET content gaps with mini briefs,
and GET Markdown fix plan export.

All endpoints require authentication and verify audit ownership.
"""

from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import Profile
from app.models.audit import Audit
from app.models.audit_recommendation import AuditRecommendation
from app.schemas.recommendation import (
    AuditRecommendationResponse,
    ContentGapListResponse,
    ContentGapResponse,
    RecommendationListResponse,
    RecommendationStatusUpdate,
    SentimentSummaryResponse,
)
from app.services.recommendation_engine import RecommendationEngine
from app.services.sentiment_service import SentimentService

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


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
        HTTPException 403 if audit not owned by user.
        HTTPException 404 if audit not found.
    """
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found",
        )
    if audit.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return audit


@router.get("/{audit_id}", response_model=RecommendationListResponse)
def get_recommendations(
    audit_id: str,
    page_url: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get recommendations for an audit with optional filtering.

    Supports filtering by page_url, priority (high/medium/low), and
    category (crawlability/content_structure/structured_data/authority/sentiment).

    Returns recommendations with summary statistics: by_priority counts and
    progress tracking (done/dismissed/open/total).
    """
    _verify_audit_ownership(audit_id, db, current_user)

    query = db.query(AuditRecommendation).filter(
        AuditRecommendation.audit_id == audit_id
    )

    if page_url:
        query = query.filter(AuditRecommendation.page_url == page_url)
    if priority:
        query = query.filter(AuditRecommendation.priority == priority)
    if category:
        query = query.filter(AuditRecommendation.category == category)

    recs = query.order_by(
        AuditRecommendation.priority,
        AuditRecommendation.gap_score.desc(),
    ).all()

    # Compute counts from all recommendations for this audit (unfiltered)
    all_recs = (
        db.query(AuditRecommendation)
        .filter(AuditRecommendation.audit_id == audit_id)
        .all()
    )

    by_priority = {"high": 0, "medium": 0, "low": 0}
    progress = {"done": 0, "dismissed": 0, "open": 0, "total": len(all_recs)}

    for rec in all_recs:
        by_priority[rec.priority] = by_priority.get(rec.priority, 0) + 1
        progress[rec.status] = progress.get(rec.status, 0) + 1

    return RecommendationListResponse(
        recommendations=[
            AuditRecommendationResponse.model_validate(r, from_attributes=True)
            for r in recs
        ],
        total=len(recs),
        by_priority=by_priority,
        progress=progress,
    )


@router.patch(
    "/{audit_id}/{recommendation_id}",
    response_model=AuditRecommendationResponse,
)
def update_recommendation_status(
    audit_id: str,
    recommendation_id: str,
    body: RecommendationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Update a recommendation's status to done, dismissed, or open.

    Verifies audit ownership and that the recommendation belongs to
    the specified audit.
    """
    _verify_audit_ownership(audit_id, db, current_user)

    rec = (
        db.query(AuditRecommendation)
        .filter(AuditRecommendation.id == recommendation_id)
        .filter(AuditRecommendation.audit_id == audit_id)
        .first()
    )
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )

    rec.status = body.status
    rec.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)

    logger.info(
        "Recommendation {} status updated to '{}' by user {}",
        recommendation_id,
        body.status,
        current_user.id,
    )

    return AuditRecommendationResponse.model_validate(rec, from_attributes=True)


@router.get(
    "/{audit_id}/sentiment",
    response_model=SentimentSummaryResponse,
)
def get_sentiment_summary(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get per-engine sentiment breakdown for an audit.

    Returns a dict of engine -> {positive, negative, neutral, total, dominant}
    computed from MentionSentiment records.
    """
    _verify_audit_ownership(audit_id, db, current_user)

    service = SentimentService(db)
    engine_sentiments = service.get_per_engine_summary(audit_id)

    return SentimentSummaryResponse(engine_sentiments=engine_sentiments)


@router.get(
    "/{audit_id}/content-gaps",
    response_model=ContentGapListResponse,
)
def get_content_gaps(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get content gaps for an audit.

    Content gaps are topics where competitors are mentioned in AI responses
    but the user brand is not. Each gap includes a mini content brief with
    suggested title and key points.

    Reads from the audit's content_gaps JSONB column (populated at audit
    completion).
    """
    _verify_audit_ownership(audit_id, db, current_user)

    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    gaps_data = audit.content_gaps or []

    gaps = [ContentGapResponse(**gap) for gap in gaps_data]

    return ContentGapListResponse(gaps=gaps, total=len(gaps))


@router.get("/{audit_id}/export/markdown")
def export_markdown(
    audit_id: str,
    page_url: str | None = None,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Export recommendations as a Markdown fix plan.

    Generates a structured Markdown document suitable for feeding into
    AI coding assistants (Claude Code, etc.) to auto-fix site issues.

    Supports two scopes:
    - Full site (no page_url param): all recommendations grouped by page
    - Single page (page_url param): recommendations for one page only

    Returns text/markdown with Content-Disposition attachment header.
    """
    audit = _verify_audit_ownership(audit_id, db, current_user)

    engine = RecommendationEngine(db)
    markdown_content = engine.export_markdown(audit_id, page_url)

    # Build filename
    domain_slug = audit.domain.replace(".", "-").replace(":", "")
    if page_url:
        parsed = urlparse(page_url)
        page_slug = (
            parsed.path.strip("/").replace("/", "-") or "homepage"
        )
        filename = f"fix-plan-{domain_slug}-{page_slug}.md"
    else:
        filename = f"fix-plan-{domain_slug}.md"

    return Response(
        content=markdown_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
