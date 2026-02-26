"""Code Analysis API router — 5 endpoints, all Pro-tier gated.

Endpoints:
  POST  /{audit_id}/prompts             Generate and download analysis prompts
  POST  /{audit_id}/upload              Upload AI tool output text (triggers Celery)
  GET   /{audit_id}                     Get latest code analysis status
  GET   /{audit_id}/recommendations     List code recommendations
  PATCH /{audit_id}/recommendations/{rec_id}  Update recommendation status
"""

from __future__ import annotations

import uuid as uuid_module

from fastapi import Body, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from fastapi.routing import APIRouter
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import SubscriptionTier, require_tier
from app.core.security import get_current_active_user
from app.models.audit import Audit
from app.models.code_analysis import CodeAnalysis, CodeRecommendation
from app.models.profile import Profile
from app.schemas.code_analysis import (
    CodeAnalysisResponse,
    CodeRecommendationResponse,
    CodeRecommendationUpdateRequest,
    CodeUploadRequest,
    PromptsResponse,
)
from app.services.code_analysis_service import (
    CodeAnalysisService,
    PromptGeneratorService,
)
from app.tasks.code_analysis_tasks import process_code_analysis

router = APIRouter(
    prefix=f"{settings.API_V1_PREFIX}/code-analysis",
    tags=["code-analysis"],
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _get_owned_audit(audit_id: str, current_user: Profile, db: Session) -> Audit:
    """Fetch audit by ID, verify ownership, raise 404 if not found/not owned."""
    try:
        audit_uuid = uuid_module.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = (
        db.query(Audit)
        .filter(Audit.id == audit_uuid, Audit.user_id == current_user.id)
        .first()
    )
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


def _require_completed_audit(audit: Audit) -> None:
    """Raise 400 if the audit has not completed yet."""
    if audit.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Audit is not completed yet (status: {audit.status}). "
            "Run code analysis only on completed audits.",
        )


# ---------------------------------------------------------------------------
# POST /{audit_id}/prompts — Generate analysis prompts
# ---------------------------------------------------------------------------


@router.post(
    "/{audit_id}/prompts",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
    response_model=PromptsResponse,
)
async def generate_prompts(
    audit_id: str,
    request=None,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Generate diagnostic code analysis prompts based on audit scoring gaps.

    Returns JSON by default. Sends a downloadable Markdown file when the
    Accept header includes 'text/markdown' or 'text/plain'.
    """
    audit = _get_owned_audit(audit_id, current_user, db)
    _require_completed_audit(audit)

    svc = PromptGeneratorService()
    response = svc.generate_prompts(audit_id, db, audit)
    return response


# ---------------------------------------------------------------------------
# POST /{audit_id}/prompts — with content negotiation (Markdown download)
# ---------------------------------------------------------------------------


@router.post(
    "/{audit_id}/prompts/download",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
)
async def download_prompts(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Download analysis prompts as a Markdown file."""
    audit = _get_owned_audit(audit_id, current_user, db)
    _require_completed_audit(audit)

    svc = PromptGeneratorService()
    response = svc.generate_prompts(audit_id, db, audit)
    return PlainTextResponse(
        content=response.markdown_bundle,
        media_type="text/markdown",
        headers={
            "Content-Disposition": (
                f"attachment; filename=endexa-analysis-prompts-{audit.domain}.md"
            )
        },
    )


# ---------------------------------------------------------------------------
# POST /{audit_id}/upload — Upload AI tool output
# ---------------------------------------------------------------------------


@router.post(
    "/{audit_id}/upload",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
    status_code=202,
)
async def upload_code_output(
    audit_id: str,
    file: UploadFile | None = File(None),
    body: CodeUploadRequest | None = Body(None),
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Upload AI tool output text for async parsing.

    Accepts either:
    - multipart file upload (text/plain, text/markdown, application/json)
    - JSON body with {"output": "...", "categories_used": [...]}

    Returns 202 immediately. Processing happens via Celery background task.
    """
    audit = _get_owned_audit(audit_id, current_user, db)
    _require_completed_audit(audit)

    # Resolve raw text from file or JSON body
    raw_text: str | None = None
    categories_used: list[str] = []

    if file is not None:
        raw_bytes = await file.read()
        if len(raw_bytes) > settings.CODE_ANALYSIS_MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Upload exceeds 100KB limit",
            )
        raw_text = raw_bytes.decode("utf-8", errors="replace")
    elif body is not None:
        raw_text = body.output
        categories_used = body.categories_used
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either a file upload or a JSON body with 'output' field",
        )

    # Validate byte size for JSON body path
    if len(raw_text.encode("utf-8")) > settings.CODE_ANALYSIS_MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Upload exceeds 100KB limit",
        )

    # Create CodeAnalysis record
    code_analysis = CodeAnalysis(
        audit_id=audit.id,
        user_id=current_user.id,
        status="pending",
        raw_output=raw_text,
        raw_output_size_bytes=len(raw_text.encode("utf-8")),
        prompt_categories_used=categories_used if categories_used else None,
    )
    db.add(code_analysis)
    db.commit()
    db.refresh(code_analysis)

    # Trigger Celery task
    process_code_analysis.delay(str(code_analysis.id))
    logger.info(
        "Code analysis %s queued for audit %s", code_analysis.id, audit_id
    )

    return {
        "id": str(code_analysis.id),
        "status": "pending",
        "message": "Upload received. Processing in background.",
    }


# ---------------------------------------------------------------------------
# GET /{audit_id} — Get latest code analysis status
# ---------------------------------------------------------------------------


@router.get(
    "/{audit_id}",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
    response_model=CodeAnalysisResponse,
)
async def get_code_analysis(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Return the most recent code analysis status for an audit."""
    audit = _get_owned_audit(audit_id, current_user, db)

    ca = (
        db.query(CodeAnalysis)
        .filter(
            CodeAnalysis.audit_id == audit.id,
            CodeAnalysis.user_id == current_user.id,
        )
        .order_by(CodeAnalysis.created_at.desc())
        .first()
    )
    if not ca:
        raise HTTPException(
            status_code=404,
            detail="No code analysis found for this audit. Upload AI tool output first.",
        )

    return CodeAnalysisResponse(
        id=str(ca.id),
        audit_id=str(ca.audit_id),
        status=ca.status,
        detected_framework=ca.detected_framework,
        parsed_findings=ca.parsed_findings,
        error_message=ca.error_message,
        created_at=ca.created_at.isoformat(),
        completed_at=ca.completed_at.isoformat() if ca.completed_at else None,
    )


# ---------------------------------------------------------------------------
# GET /{audit_id}/recommendations — List code recommendations
# ---------------------------------------------------------------------------


@router.get(
    "/{audit_id}/recommendations",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
    response_model=list[CodeRecommendationResponse],
)
async def get_code_recommendations(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Return all code recommendations for an audit (ordered: high severity first)."""
    audit = _get_owned_audit(audit_id, current_user, db)

    recs = (
        db.query(CodeRecommendation)
        .join(CodeAnalysis)
        .filter(
            CodeRecommendation.audit_id == audit.id,
            CodeAnalysis.user_id == current_user.id,
        )
        .order_by(CodeRecommendation.created_at.asc())
        .all()
    )

    # Sort by severity priority (high -> medium -> low)
    recs.sort(key=lambda r: SEVERITY_ORDER.get(r.severity, 99))

    return [
        CodeRecommendationResponse(
            id=str(r.id),
            code_analysis_id=str(r.code_analysis_id),
            criterion_id=r.criterion_id,
            category=r.category,
            severity=r.severity,
            finding=r.finding,
            file_path=r.file_path,
            suggestion=r.suggestion,
            code_snippet=r.code_snippet,
            evidence=r.evidence,
            status=r.status,
            created_at=r.created_at.isoformat(),
        )
        for r in recs
    ]


# ---------------------------------------------------------------------------
# PATCH /{audit_id}/recommendations/{rec_id} — Update recommendation status
# ---------------------------------------------------------------------------


@router.patch(
    "/{audit_id}/recommendations/{rec_id}",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
    response_model=CodeRecommendationResponse,
)
async def update_recommendation_status(
    audit_id: str,
    rec_id: str,
    payload: CodeRecommendationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Update the status of a code recommendation (open, done, dismissed)."""
    audit = _get_owned_audit(audit_id, current_user, db)

    if payload.status not in {"open", "done", "dismissed"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be one of: open, done, dismissed",
        )

    try:
        rec_uuid = uuid_module.UUID(rec_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec = (
        db.query(CodeRecommendation)
        .join(CodeAnalysis)
        .filter(
            CodeRecommendation.id == rec_uuid,
            CodeRecommendation.audit_id == audit.id,
            CodeAnalysis.user_id == current_user.id,
        )
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.status = payload.status
    db.commit()
    db.refresh(rec)

    return CodeRecommendationResponse(
        id=str(rec.id),
        code_analysis_id=str(rec.code_analysis_id),
        criterion_id=rec.criterion_id,
        category=rec.category,
        severity=rec.severity,
        finding=rec.finding,
        file_path=rec.file_path,
        suggestion=rec.suggestion,
        code_snippet=rec.code_snippet,
        evidence=rec.evidence,
        status=rec.status,
        created_at=rec.created_at.isoformat(),
    )
