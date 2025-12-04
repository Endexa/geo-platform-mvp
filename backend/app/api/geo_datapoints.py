"""
GEO Data Points API Endpoints

FastAPI routes for triggering GEO data points analysis and querying results.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field, validator
from uuid import UUID
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add geo_data_points to path
geo_data_points_path = Path(__file__).parent.parent.parent.parent / "geo_data_points"
sys.path.append(str(geo_data_points_path))

from app.core.database import get_db
from app.core.rate_limiter import standard_rate_limit, analysis_rate_limit
from app.core.validators import SecureBaseModel
from loguru import logger

# Import GEO data points components
try:
    from db import Analysis as GeoAnalysis, DataPointResult, get_db_session
    from orchestrator import GeoOrchestrator
except ImportError as e:
    logger.warning(f"Could not import GEO data points modules: {e}")
    GeoAnalysis = None
    DataPointResult = None
    GeoOrchestrator = None


router = APIRouter()


class RunGeoAnalysisRequest(SecureBaseModel):
    """Request to run GEO data points analysis"""
    url: str = Field(..., min_length=8, max_length=500)

    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            v = f"https://{v}"
        return v


@router.post("/run", dependencies=[Depends(analysis_rate_limit)])
async def run_geo_analysis(
    request: RunGeoAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger GEO data points analysis for a URL.

    **Security Features:**
    - Rate limited: 5 analyses per 5 minutes
    - Input validation: URL sanitized
    - Background execution: Doesn't block response

    **Response:**
    Returns analysis_id immediately, analysis runs in background.
    Use GET /geo-datapoints/{analysis_id} to check status and results.
    """
    if not GeoOrchestrator:
        raise HTTPException(
            status_code=500,
            detail="GEO data points system not available. Check installation."
        )

    logger.info(f"GEO analysis requested for: {request.url}")

    # Create orchestrator and start analysis in background
    def run_analysis_task(url: str):
        try:
            orchestrator = GeoOrchestrator(url)
            analysis_id = orchestrator.run_all()
            logger.info(f"GEO analysis completed: {analysis_id}")
        except Exception as e:
            logger.error(f"GEO analysis failed for {url}: {str(e)}", exc_info=True)

    # Get analysis ID upfront
    try:
        orchestrator = GeoOrchestrator(request.url)
        analysis_id = orchestrator.analysis_id

        # Initialize database and create pending record
        from db import init_database
        init_database()

        with get_db_session() as db:
            analysis = GeoAnalysis(
                id=analysis_id,
                site_url=request.url,
                status="pending",
                total_data_points=0
            )
            db.add(analysis)
            db.commit()

        # Start background task
        background_tasks.add_task(run_analysis_task, request.url)

        logger.info(f"GEO analysis started with ID: {analysis_id}")

        return {
            "analysis_id": str(analysis_id),
            "status": "pending",
            "message": "GEO analysis started. Use analysis_id to check status."
        }

    except Exception as e:
        logger.error(f"Failed to start GEO analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start analysis")


@router.get("/{analysis_id}", dependencies=[Depends(standard_rate_limit)])
async def get_geo_analysis(analysis_id: UUID):
    """
    Get GEO analysis results by ID.

    **Security Features:**
    - Rate limited: 100 requests per minute

    **Response:**
    Returns analysis status and all data point results if completed.
    """
    if not GeoAnalysis or not DataPointResult:
        raise HTTPException(
            status_code=500,
            detail="GEO data points system not available"
        )

    try:
        with get_db_session() as db:
            # Get analysis
            analysis = db.query(GeoAnalysis).filter(GeoAnalysis.id == analysis_id).first()

            if not analysis:
                raise HTTPException(status_code=404, detail="Analysis not found")

            # Get results
            results = db.query(DataPointResult).filter(
                DataPointResult.analysis_id == analysis_id
            ).all()

            # Convert to dict
            results_list = [
                {
                    'id': str(r.id),
                    'data_point_name': r.data_point_name,
                    'module': r.module,
                    'priority': r.priority,
                    'score': r.score,
                    'comment': r.comment,
                    'measurement_method': r.measurement_method,
                    'automation_level': r.automation_level,
                    'execution_time_ms': r.execution_time_ms,
                    'error_message': r.error_message,
                    'created_at': r.created_at.isoformat() if r.created_at else None
                }
                for r in results
            ]

            return {
                'analysis_id': str(analysis.id),
                'site_url': analysis.site_url,
                'status': analysis.status,
                'timestamp': analysis.timestamp.isoformat() if analysis.timestamp else None,
                'completed_at': analysis.completed_at.isoformat() if analysis.completed_at else None,
                'total_data_points': analysis.total_data_points,
                'successful_measurements': analysis.successful_measurements,
                'failed_measurements': analysis.failed_measurements,
                'average_score': analysis.average_score,
                'results': results_list
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching GEO analysis {analysis_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch analysis")


@router.get("/{analysis_id}/summary", dependencies=[Depends(standard_rate_limit)])
async def get_geo_analysis_summary(analysis_id: UUID):
    """
    Get GEO analysis summary with aggregated scores by module.

    **Security Features:**
    - Rate limited: 100 requests per minute

    **Response:**
    Returns aggregated scores per module (WI, CNT, BV, SEO, UX, COMP, LEG).
    """
    if not GeoAnalysis or not DataPointResult:
        raise HTTPException(
            status_code=500,
            detail="GEO data points system not available"
        )

    try:
        with get_db_session() as db:
            # Get analysis
            analysis = db.query(GeoAnalysis).filter(GeoAnalysis.id == analysis_id).first()

            if not analysis:
                raise HTTPException(status_code=404, detail="Analysis not found")

            # Aggregate scores by module
            module_scores = db.query(
                DataPointResult.module,
                func.avg(DataPointResult.score).label('average_score'),
                func.count(DataPointResult.id).label('count'),
                func.min(DataPointResult.score).label('min_score'),
                func.max(DataPointResult.score).label('max_score')
            ).filter(
                DataPointResult.analysis_id == analysis_id
            ).group_by(
                DataPointResult.module
            ).all()

            # Aggregate by priority
            priority_scores = db.query(
                DataPointResult.priority,
                func.avg(DataPointResult.score).label('average_score'),
                func.count(DataPointResult.id).label('count')
            ).filter(
                DataPointResult.analysis_id == analysis_id
            ).group_by(
                DataPointResult.priority
            ).all()

            # Format results
            modules = {
                row.module: {
                    'average_score': round(float(row.average_score), 2),
                    'count': row.count,
                    'min_score': round(float(row.min_score), 2),
                    'max_score': round(float(row.max_score), 2)
                }
                for row in module_scores
            }

            priorities = {
                row.priority: {
                    'average_score': round(float(row.average_score), 2),
                    'count': row.count
                }
                for row in priority_scores
            }

            return {
                'analysis_id': str(analysis.id),
                'site_url': analysis.site_url,
                'status': analysis.status,
                'overall_score': analysis.average_score,
                'total_data_points': analysis.total_data_points,
                'module_scores': modules,
                'priority_scores': priorities,
                'timestamp': analysis.timestamp.isoformat() if analysis.timestamp else None
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching GEO summary {analysis_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch summary")


@router.get("/{analysis_id}/module/{module}", dependencies=[Depends(standard_rate_limit)])
async def get_geo_analysis_by_module(analysis_id: UUID, module: str):
    """
    Get GEO analysis results filtered by module.

    **Modules:**
    - WI: Web Infrastructure
    - CNT: Content
    - BV: Brand Visibility
    - SEO: Search Engine Optimization
    - UX: User Experience
    - COMP: Competitive
    - LEG: Legal

    **Security Features:**
    - Rate limited: 100 requests per minute
    """
    valid_modules = ['WI', 'CNT', 'BV', 'SEO', 'UX', 'COMP', 'LEG']
    if module.upper() not in valid_modules:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid module. Must be one of: {', '.join(valid_modules)}"
        )

    if not DataPointResult:
        raise HTTPException(
            status_code=500,
            detail="GEO data points system not available"
        )

    try:
        with get_db_session() as db:
            results = db.query(DataPointResult).filter(
                DataPointResult.analysis_id == analysis_id,
                DataPointResult.module == module.upper()
            ).all()

            if not results:
                raise HTTPException(
                    status_code=404,
                    detail=f"No results found for module {module}"
                )

            results_list = [
                {
                    'id': str(r.id),
                    'data_point_name': r.data_point_name,
                    'priority': r.priority,
                    'score': r.score,
                    'comment': r.comment,
                    'execution_time_ms': r.execution_time_ms
                }
                for r in results
            ]

            # Calculate module average
            avg_score = sum(r['score'] for r in results_list) / len(results_list)

            return {
                'analysis_id': str(analysis_id),
                'module': module.upper(),
                'average_score': round(avg_score, 2),
                'count': len(results_list),
                'results': results_list
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching module results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch module results")
