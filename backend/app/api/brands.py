"""Brand CRUD API endpoints for multi-brand management.

Provides POST (create), GET (list/detail), PUT (update), DELETE, and
GET brand audits. All endpoints require authentication and enforce
user ownership.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import Profile
from app.models.audit import Audit
from app.models.visibility_score import VisibilityScore
from app.schemas.brand import (
    BrandCreate,
    BrandListResponse,
    BrandResponse,
    BrandUpdate,
    MultiBrandOverviewResponse,
)
from app.services.brand_service import BrandService

router = APIRouter(prefix="/api/v1/brands", tags=["brands"])


def _brand_to_response(brand, audit_count: int) -> BrandResponse:
    """Convert a Brand ORM object to a BrandResponse with audit count."""
    return BrandResponse(
        id=brand.id,
        name=brand.name,
        url=brand.url,
        domain=brand.domain,
        description=brand.description,
        created_at=brand.created_at,
        updated_at=brand.updated_at,
        audit_count=audit_count,
    )


@router.post("/", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
def create_brand(
    request: BrandCreate,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Create a new brand and retroactively associate matching audits.

    Returns 201 on success, 409 if a brand with the same domain already
    exists for this user.
    """
    service = BrandService(db)
    try:
        brand = service.create_brand(str(current_user.id), request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    audit_count = service.get_brand_audit_count(str(brand.id))
    logger.info(
        "Brand {} created for user {} (domain: {}, {} audits associated)",
        brand.id,
        current_user.id,
        brand.domain,
        audit_count,
    )
    return _brand_to_response(brand, audit_count)


@router.get("/", response_model=BrandListResponse)
def list_brands(
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """List all brands for the current user."""
    service = BrandService(db)
    brands = service.list_brands(str(current_user.id))

    brand_responses = []
    for brand in brands:
        audit_count = service.get_brand_audit_count(str(brand.id))
        brand_responses.append(_brand_to_response(brand, audit_count))

    return BrandListResponse(brands=brand_responses, total=len(brand_responses))


@router.get("/overview", response_model=MultiBrandOverviewResponse)
def get_multi_brand_overview(
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get a multi-brand overview with aggregated metrics for all user brands.

    Returns lightweight per-brand metrics including combined GEO score,
    visibility, optimization, mention count, issues count, audit count,
    and last audited date. Avoids N+1 by querying directly per brand.
    """
    service = BrandService(db)
    entries = service.get_multi_brand_overview(str(current_user.id))

    return MultiBrandOverviewResponse(
        brands=entries,
        total_brands=len(entries),
    )


@router.get("/{brand_id}", response_model=BrandResponse)
def get_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get a single brand detail. Returns 404 if not found or not owned."""
    service = BrandService(db)
    try:
        brand = service.get_brand(brand_id, str(current_user.id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found",
        )

    audit_count = service.get_brand_audit_count(str(brand.id))
    return _brand_to_response(brand, audit_count)


@router.put("/{brand_id}", response_model=BrandResponse)
def update_brand(
    brand_id: str,
    request: BrandUpdate,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Update a brand. Returns 404 if not found or not owned."""
    service = BrandService(db)
    try:
        brand = service.update_brand(brand_id, str(current_user.id), request)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand not found",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_msg,
        )

    audit_count = service.get_brand_audit_count(str(brand.id))
    logger.info("Brand {} updated by user {}", brand.id, current_user.id)
    return _brand_to_response(brand, audit_count)


@router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Delete a brand. Unlinks audits (sets brand_id=NULL). Returns 204 on success."""
    service = BrandService(db)
    try:
        service.delete_brand(brand_id, str(current_user.id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found",
        )

    logger.info("Brand {} deleted by user {}", brand_id, current_user.id)


@router.get("/{brand_id}/audits")
def list_brand_audits(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
    limit: int = 20,
    offset: int = 0,
):
    """List audits associated with a specific brand.

    Returns audit summaries including id, url, status, created_at,
    optimization_score, and visibility_score if available.
    """
    service = BrandService(db)
    try:
        brand = service.get_brand(brand_id, str(current_user.id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found",
        )

    audits = (
        db.query(Audit)
        .filter(Audit.brand_id == brand.id, Audit.user_id == current_user.id)
        .order_by(Audit.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    total = (
        db.query(func.count(Audit.id))
        .filter(Audit.brand_id == brand.id, Audit.user_id == current_user.id)
        .scalar()
    )

    results = []
    for audit in audits:
        # Get visibility score if it exists
        vs = (
            db.query(VisibilityScore)
            .filter(VisibilityScore.audit_id == audit.id)
            .first()
        )
        visibility_score = vs.overall_score if vs else None

        results.append(
            {
                "id": str(audit.id),
                "url": audit.url,
                "domain": audit.domain,
                "status": audit.status,
                "created_at": audit.created_at.isoformat() if audit.created_at else None,
                "optimization_score": audit.optimization_score,
                "visibility_score": visibility_score,
            }
        )

    return {"audits": results, "total": total}
