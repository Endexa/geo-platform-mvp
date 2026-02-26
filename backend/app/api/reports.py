"""Report download API endpoints with tier-gated access.

Provides PDF, HTML, and CSV download endpoints for completed audit
reports. All endpoints require PRO subscription tier and verify
audit ownership.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import SubscriptionTier, require_tier
from app.core.security import get_current_active_user
from app.models.audit import Audit
from app.models.profile import Profile
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


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
        HTTPException 404 if audit not found.
        HTTPException 403 if audit not owned by user.
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


@router.get(
    "/{audit_id}/pdf",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
)
def download_pdf_report(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Download a PDF audit report.

    Renders the full audit report (executive summary, dual scores,
    category breakdown, recommendations, competitors) as a PDF file.

    Requires PRO subscription tier.
    """
    audit = _verify_audit_ownership(audit_id, db, current_user)
    service = ReportService(db)
    pdf_bytes = service.render_pdf(audit_id)

    domain_slug = audit.domain.replace(".", "-")
    filename = f"endexa-report-{domain_slug}.pdf"

    logger.info(
        "PDF report downloaded for audit {} by user {}",
        audit_id,
        current_user.id,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/{audit_id}/html",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
)
def download_html_report(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Download an HTML audit report.

    Renders the full audit report as an HTML file suitable for
    viewing in a browser.

    Requires PRO subscription tier.
    """
    audit = _verify_audit_ownership(audit_id, db, current_user)
    service = ReportService(db)
    html_string = service.render_html(audit_id)

    domain_slug = audit.domain.replace(".", "-")
    filename = f"endexa-report-{domain_slug}.html"

    logger.info(
        "HTML report downloaded for audit {} by user {}",
        audit_id,
        current_user.id,
    )

    return Response(
        content=html_string,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/{audit_id}/csv",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
)
def download_csv_export(
    audit_id: str,
    grouping: str = "category",
    epic_link: str | None = None,
    fields: str | None = None,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Export recommendations as a Jira-compatible CSV file.

    Query parameters:
    - grouping: Sort order -- "category" (default), "priority", or "page"
    - epic_link: Optional Jira epic key to include in every row
    - fields: Optional comma-separated list of CSV column names

    Requires PRO subscription tier.
    """
    audit = _verify_audit_ownership(audit_id, db, current_user)
    service = ReportService(db)

    # Parse fields if provided
    parsed_fields = None
    if fields:
        parsed_fields = [f.strip() for f in fields.split(",") if f.strip()]

    csv_string = service.export_csv(
        audit_id,
        fields=parsed_fields,
        grouping=grouping,
        epic_link=epic_link,
    )

    domain_slug = audit.domain.replace(".", "-")
    filename = f"endexa-recommendations-{domain_slug}.csv"

    logger.info(
        "CSV export downloaded for audit {} by user {}",
        audit_id,
        current_user.id,
    )

    return Response(
        content=csv_string,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
