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
from app.schemas.audit import (
    AuditCreate,
    AuditDetailResponse,
    AuditResponse,
    DispatchSummary,
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
    """Get audit details including generated queries and engine responses.

    Only returns audits owned by the authenticated user.
    Eager-loads associated AuditQuery records and their EngineResponse records
    to avoid N+1 query issues. Computes a dispatch summary when available.
    """
    audit = (
        db.query(Audit)
        .options(
            joinedload(Audit.queries).joinedload(AuditQuery.engine_responses)
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
    if audit.status in (AuditStatus.COMPLETED.value, AuditStatus.DISPATCHING.value):
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

    # Build response with dispatch summary
    response = AuditDetailResponse.model_validate(audit)
    response.dispatch_summary = dispatch_summary
    return response
