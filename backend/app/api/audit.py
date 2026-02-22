"""Audit API endpoints for creating and retrieving AI brand visibility audits.

Provides POST to trigger a new audit (crawl + query generation pipeline),
GET to retrieve audit details with generated queries, and GET to list user audits.
"""

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import Profile
from app.models.audit import Audit, AuditStatus
from app.models.audit_query import AuditQuery
from app.models.engine_response import EngineResponse
from app.models.page_score import PageScore
from app.schemas.audit import (
    AuditCreate,
    AuditDetailResponse,
    AuditResponse,
    DispatchSummary,
    OptimizationScoreSchema,
    VisibilityScoreSchema,
)
from app.tasks.audit_tasks import run_crawl_and_generate

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/", response_model=AuditResponse, status_code=status.HTTP_202_ACCEPTED)
def create_audit(
    request: AuditCreate,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Create and trigger a new AI brand visibility audit.

    Validates the URL, creates an Audit record, and dispatches the
    crawl + query generation pipeline as a Celery background task.

    Returns 202 Accepted since processing is asynchronous.
    """
    # Validate URL
    parsed = urlparse(request.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL must use http or https scheme",
        )
    if not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL must have a valid domain",
        )

    domain = parsed.netloc

    # Create audit record
    audit = Audit(
        user_id=current_user.id,
        url=request.url,
        domain=domain,
        status=AuditStatus.PENDING.value,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # Dispatch Celery task
    run_crawl_and_generate.delay(str(audit.id), request.url)
    logger.info(
        "Audit {} created for URL {} by user {}",
        audit.id,
        request.url,
        current_user.id,
    )

    return audit


@router.get("/", response_model=list[AuditResponse])
def list_audits(
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
    limit: int = 20,
    offset: int = 0,
):
    """List the current user's audits with pagination.

    Returns audits ordered by creation date (newest first).
    Does not include crawl_data for efficiency.
    """
    audits = (
        db.query(Audit)
        .filter(Audit.user_id == current_user.id)
        .order_by(Audit.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return audits


@router.get("/{audit_id}", response_model=AuditDetailResponse)
def get_audit(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get audit details including queries, engine responses, mentions, visibility score, optimization score, and page scores.

    Only returns audits owned by the authenticated user.
    Eager-loads associated AuditQuery records, their EngineResponse records with
    BrandMention data, VisibilityScore, and PageScore with CriterionResult data
    to avoid N+1 query issues.
    Computes dispatch summary and optimization score breakdown when available.
    """
    audit = (
        db.query(Audit)
        .options(
            joinedload(Audit.queries)
            .joinedload(AuditQuery.engine_responses)
            .joinedload(EngineResponse.mentions),
            joinedload(Audit.visibility_score),
            joinedload(Audit.page_scores).joinedload(
                PageScore.criterion_results
            ),
        )
        .filter(Audit.id == audit_id)
        .first()
    )

    if not audit or audit.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found",
        )

    # Compute dispatch summary if audit has engine responses
    dispatch_summary = None
    if audit.status in (
        AuditStatus.COMPLETED.value,
        AuditStatus.DISPATCHING.value,
        AuditStatus.ANALYZING.value,
        AuditStatus.SCORING.value,
    ):
        all_responses = []
        for q in audit.queries:
            all_responses.extend(q.engine_responses)
        if all_responses:
            engines_used = list(set(r.engine for r in all_responses))
            failures = sum(1 for r in all_responses if r.error_message is not None)
            dispatch_summary = DispatchSummary(
                total_queries=len(audit.queries),
                total_responses=len(all_responses) - failures,
                total_failures=failures,
                engines_used=sorted(engines_used),
            )

    # Build optimization score schema from page_scores
    optimization_score_schema = None
    page_scores_list = audit.page_scores if audit.page_scores else []
    if audit.optimization_score is not None and page_scores_list:
        scored_pages = [ps for ps in page_scores_list if ps.was_scored]
        discovered_pages = page_scores_list

        # Compute per-category averages across scored pages
        category_sums: dict[str, list[int]] = {
            "crawlability": [],
            "content_structure": [],
            "structured_data": [],
            "authority": [],
        }
        for ps in scored_pages:
            if ps.crawlability_score is not None:
                category_sums["crawlability"].append(ps.crawlability_score)
            if ps.content_structure_score is not None:
                category_sums["content_structure"].append(ps.content_structure_score)
            if ps.structured_data_score is not None:
                category_sums["structured_data"].append(ps.structured_data_score)
            if ps.authority_score is not None:
                category_sums["authority"].append(ps.authority_score)

        def _avg(scores: list[int]) -> int:
            return round(sum(scores) / len(scores)) if scores else 0

        optimization_score_schema = OptimizationScoreSchema(
            overall_score=audit.optimization_score,
            crawlability_avg=_avg(category_sums["crawlability"]),
            content_structure_avg=_avg(category_sums["content_structure"]),
            structured_data_avg=_avg(category_sums["structured_data"]),
            authority_avg=_avg(category_sums["authority"]),
            pages_scored=len(scored_pages),
            pages_discovered=len(discovered_pages),
        )

    # Build response — exclude visibility_score from auto-serialization
    # because the SQLAlchemy relationship returns InstrumentedList, not a single object
    response_data = {
        "id": audit.id,
        "url": audit.url,
        "domain": audit.domain,
        "status": audit.status,
        "created_at": audit.created_at,
        "completed_at": audit.completed_at,
        "error_message": audit.error_message,
        "crawl_data": audit.crawl_data,
        "queries": audit.queries,
        "dispatch_summary": dispatch_summary,
        "visibility_score": None,
        "optimization_score": optimization_score_schema,
        "page_scores": page_scores_list,
    }

    # Attach visibility score (backref returns a list)
    vs = audit.visibility_score
    if vs:
        score_obj = vs[0] if isinstance(vs, list) else vs
        response_data["visibility_score"] = score_obj

    return AuditDetailResponse.model_validate(response_data, from_attributes=True)
