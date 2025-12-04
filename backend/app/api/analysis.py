from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, HttpUrl
from uuid import UUID
from app.core.database import get_db
from app.models import Analysis, Website, Profile
from app.services.analyzer import AnalyzerService
from app.core.security import get_current_active_user, OrganizationChecker
from app.core.rate_limiter import analysis_rate_limit, standard_rate_limit
from app.core.validators import SecureAnalyzeRequest
from loguru import logger

router = APIRouter()


# Pydantic schemas (using secure validator)
class AnalyzeRequest(SecureAnalyzeRequest):
    pass


class AnalysisResponse(BaseModel):
    id: UUID
    status: str
    geo_score: int | None = None
    visibility_score: int | None = None
    readability_score: int | None = None
    authority_score: int | None = None
    created_at: str

    class Config:
        from_attributes = True


@router.post("/analyze", response_model=dict, dependencies=[Depends(analysis_rate_limit)])
async def create_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user),
    # org: Organization = Depends(OrganizationChecker())
):
    """
    Initiate a new website analysis.

    **Security Features:**
    - Rate limited: 3 analyses per 5 minutes
    - Input validation: URL and keywords sanitized
    - Audit logged: All requests logged

    **Authentication:** Currently optional for MVP.
    Uncomment dependencies to require authentication.

    Returns analysis_id for polling.
    """

    # Log analysis request
    logger.info(f"Analysis requested for URL: {request.url}")

    # Create or get website
    domain = str(request.url).split("//")[1].split("/")[0]
    website = db.query(Website).filter(Website.domain == domain).first()

    if not website:
        # For MVP, create website without org_id
        # In production with auth: website = Website(domain=domain, org_id=org.id)
        website = Website(domain=domain)
        db.add(website)
        db.commit()
        db.refresh(website)

    # Create analysis record
    analysis = Analysis(
        website_id=website.id,
        status="pending"
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Log successful creation
    logger.info(f"Analysis created with ID: {analysis.id}")

    # Trigger background analysis
    analyzer_service = AnalyzerService(db)
    background_tasks.add_task(
        analyzer_service.run_analysis,
        analysis.id,
        str(request.url),
        request.keywords
    )

    return {
        "analysis_id": str(analysis.id),
        "status": "pending",
        "message": "Analysis started. Poll /analysis/{id} for results."
    }


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get analysis status and results.
    Polling endpoint for frontend.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisResponse(
        id=analysis.id,
        status=analysis.status,
        geo_score=analysis.geo_score,
        visibility_score=analysis.visibility_score,
        readability_score=analysis.readability_score,
        authority_score=analysis.authority_score,
        created_at=analysis.created_at.isoformat()
    )


@router.get("/{analysis_id}/recommendations")
async def get_recommendations(
    analysis_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get AI-generated recommendations for an analysis.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.status != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed yet")

    recommendations = analysis.recommendations

    return {
        "analysis_id": str(analysis_id),
        "recommendations": [
            {
                "id": str(rec.id),
                "category": rec.category,
                "severity": rec.severity,
                "issue": rec.issue,
                "action_plan": rec.action_plan,
                "impact_score": rec.impact_score,
                "implemented": rec.implemented
            }
            for rec in recommendations
        ]
    }
