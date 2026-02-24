"""Dashboard API endpoints for overview, history, and report export.

Provides GET dashboard overview (aggregated scores, issues, competitors),
GET audit history (trend data), and GET export as PDF or CSV.

Completely replaces the legacy dashboard that used the obsolete Analysis model.
All endpoints require authentication and verify audit ownership.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import Profile
from app.schemas.dashboard import AuditHistoryResponse, DashboardOverviewResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/overview/{audit_id}", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get single-screen dashboard overview for an audit.

    Returns combined GEO score, visibility/optimization scores,
    per-engine breakdown, top 5 issues, competitive position,
    and recommendation progress in a single response.
    """
    service = DashboardService(db)
    try:
        data = service.get_overview(audit_id, str(current_user.id))
    except ValueError as e:
        msg = str(e)
        if "denied" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found",
        )

    logger.info(
        "Dashboard overview served for audit {} by user {}",
        audit_id,
        current_user.id,
    )
    return DashboardOverviewResponse(**data)


@router.get("/history", response_model=AuditHistoryResponse)
def get_audit_history(
    domain: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get audit history for a domain for trend visualization.

    Returns time-series data for all completed audits of the given domain
    owned by the current user. Filters by domain AND user_id.
    """
    service = DashboardService(db)
    data = service.get_audit_history(domain, str(current_user.id))

    logger.info(
        "Audit history served for domain '{}': {} entries",
        domain,
        data["total"],
    )
    return AuditHistoryResponse(**data)


@router.get("/{audit_id}/export/pdf")
def export_pdf(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Export complete audit report as PDF.

    Uses WeasyPrint to render an HTML template to PDF. This is a sync
    endpoint so FastAPI auto-runs it in a threadpool, preventing
    event loop blocking during PDF generation.
    """
    service = DashboardService(db)
    try:
        pdf_bytes, domain = service.export_pdf(audit_id, str(current_user.id))
    except ValueError as e:
        msg = str(e)
        if "denied" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found",
        )

    logger.info("PDF export served for audit {}", audit_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="geo-audit-{domain}.pdf"'
        },
    )


@router.get("/{audit_id}/export/csv")
def export_csv(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Export complete audit report as CSV.

    Generates a CSV with sections: scores, per-engine breakdown, category
    scores, recommendations, content gaps, and competitors.
    """
    service = DashboardService(db)
    try:
        content, domain = service.export_csv(audit_id, str(current_user.id))
    except ValueError as e:
        msg = str(e)
        if "denied" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found",
        )

    logger.info("CSV export served for audit {}", audit_id)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="geo-audit-{domain}.csv"'
        },
    )
