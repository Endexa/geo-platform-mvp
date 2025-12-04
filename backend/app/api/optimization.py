from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from uuid import UUID
from app.core.database import get_db
from app.models import Analysis, Recommendation, Profile
from app.services.optimizer import OptimizerService
from app.core.security import get_current_active_user
from app.core.rate_limiter import standard_rate_limit, optimization_rate_limit
from app.core.validators import SecureBaseModel
from loguru import logger

router = APIRouter()


class GenerateRecommendationsRequest(SecureBaseModel):
    """Secure request for generating recommendations"""
    analysis_id: UUID = Field(..., description="ID of the completed analysis")


@router.post("/generate", dependencies=[Depends(optimization_rate_limit)])
async def generate_recommendations(
    request: GenerateRecommendationsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Generate AI-powered recommendations for an analysis.
    Uses RAG to provide actionable insights.

    **Security Features:**
    - Rate limited: 10 optimizations per minute
    - Input validation: UUID format validated
    - Audit logged: All requests logged

    **Authentication:** Currently optional for MVP.
    Uncomment dependencies to require authentication.
    """
    logger.info(f"Recommendation generation requested for analysis: {request.analysis_id}")

    analysis = db.query(Analysis).filter(Analysis.id == request.analysis_id).first()

    if not analysis:
        logger.warning(f"Analysis not found: {request.analysis_id}")
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.status != "completed":
        logger.warning(f"Attempted recommendation generation on incomplete analysis: {request.analysis_id}")
        raise HTTPException(status_code=400, detail="Analysis must be completed first")

    # Check if recommendations already exist
    existing_recs = db.query(Recommendation).filter(
        Recommendation.analysis_id == request.analysis_id
    ).count()

    if existing_recs > 0:
        logger.info(f"Recommendations already exist for analysis: {request.analysis_id}")
        return {
            "message": "Recommendations already exist",
            "count": existing_recs
        }

    # Trigger background recommendation generation
    optimizer_service = OptimizerService(db)
    background_tasks.add_task(
        optimizer_service.generate_recommendations,
        analysis.id
    )

    logger.info(f"Recommendation generation started for analysis: {analysis.id}")

    return {
        "message": "Recommendation generation started",
        "analysis_id": str(analysis.id)
    }


@router.post("/optimize-content", dependencies=[Depends(optimization_rate_limit)])
async def optimize_content(
    recommendation_id: UUID,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Get optimized content for a specific recommendation.
    Shows the "Writing..." animation effect.

    **Security Features:**
    - Rate limited: 10 optimizations per minute
    - Audit logged: All optimizations logged
    """
    logger.info(f"Content optimization requested for recommendation: {recommendation_id}")

    recommendation = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id
    ).first()

    if not recommendation:
        logger.warning(f"Recommendation not found: {recommendation_id}")
        raise HTTPException(status_code=404, detail="Recommendation not found")

    optimizer_service = OptimizerService(db)
    optimized_text = await optimizer_service.optimize_content(recommendation)

    logger.info(f"Content optimization completed for recommendation: {recommendation_id}")

    return {
        "recommendation_id": str(recommendation_id),
        "optimized_content": optimized_text,
        "status": "completed"
    }


@router.patch("/{recommendation_id}/implement", dependencies=[Depends(standard_rate_limit)])
async def mark_as_implemented(
    recommendation_id: UUID,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Mark a recommendation as implemented.

    **Security Features:**
    - Rate limited: 100 requests per minute
    - Audit logged: Implementation status changes logged
    """
    logger.info(f"Marking recommendation as implemented: {recommendation_id}")

    recommendation = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id
    ).first()

    if not recommendation:
        logger.warning(f"Recommendation not found: {recommendation_id}")
        raise HTTPException(status_code=404, detail="Recommendation not found")

    recommendation.implemented = True
    db.commit()

    logger.info(f"Recommendation marked as implemented: {recommendation_id}")

    return {
        "message": "Recommendation marked as implemented",
        "id": str(recommendation_id)
    }
