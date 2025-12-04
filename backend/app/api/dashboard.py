from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models import Analysis, Website, Profile
from app.core.security import get_current_active_user
from app.core.rate_limiter import standard_rate_limit
from loguru import logger

router = APIRouter()


@router.get("/stats", dependencies=[Depends(standard_rate_limit)])
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Get aggregated statistics for dashboard.

    **Security Features:**
    - Rate limited: 100 requests per minute
    - Read-only operation (safe for public access in MVP)

    **Authentication:** Currently optional for MVP.
    In production, this would filter data by organization.
    """
    logger.info("Dashboard stats requested")

    # Total analyses
    total_analyses = db.query(func.count(Analysis.id)).scalar()

    # Average GEO score
    avg_geo_score = db.query(func.avg(Analysis.geo_score)).filter(
        Analysis.status == "completed"
    ).scalar() or 0

    # Recent analyses (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_analyses = db.query(Analysis).filter(
        Analysis.created_at >= thirty_days_ago,
        Analysis.status == "completed"
    ).order_by(Analysis.created_at.desc()).all()

    # Calculate trend data
    trend_data = []
    for analysis in recent_analyses[:30]:  # Last 30 analyses
        trend_data.append({
            "date": analysis.created_at.isoformat(),
            "geo_score": analysis.geo_score,
            "visibility_score": analysis.visibility_score,
            "readability_score": analysis.readability_score,
            "authority_score": analysis.authority_score
        })

    # Recent audits
    recent_audits = db.query(Analysis).order_by(
        Analysis.created_at.desc()
    ).limit(5).all()

    logger.info(f"Dashboard stats retrieved: {total_analyses} total analyses")

    return {
        "total_analyses": total_analyses,
        "avg_geo_score": round(avg_geo_score, 2),
        "trend_data": trend_data,
        "recent_audits": [
            {
                "id": str(audit.id),
                "website": audit.website.domain,
                "geo_score": audit.geo_score,
                "status": audit.status,
                "created_at": audit.created_at.isoformat()
            }
            for audit in recent_audits
        ]
    }


@router.get("/history", dependencies=[Depends(standard_rate_limit)])
async def get_analysis_history(
    days: int = 30,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Get analysis history for charts.

    **Security Features:**
    - Rate limited: 100 requests per minute
    - Input validation: Days parameter validated
    - Read-only operation (safe for public access in MVP)

    **Authentication:** Currently optional for MVP.
    In production, this would filter data by organization.
    """
    # Validate days parameter
    if days < 1 or days > 365:
        logger.warning(f"Invalid days parameter: {days}")
        days = 30  # Default to 30 days if invalid

    logger.info(f"Analysis history requested: last {days} days")

    start_date = datetime.utcnow() - timedelta(days=days)

    analyses = db.query(Analysis).filter(
        Analysis.created_at >= start_date,
        Analysis.status == "completed"
    ).order_by(Analysis.created_at).all()

    logger.info(f"Analysis history retrieved: {len(analyses)} analyses")

    return {
        "period": f"last_{days}_days",
        "data": [
            {
                "date": analysis.created_at.date().isoformat(),
                "geo_score": analysis.geo_score,
                "visibility_score": analysis.visibility_score,
                "readability_score": analysis.readability_score,
                "authority_score": analysis.authority_score
            }
            for analysis in analyses
        ]
    }
