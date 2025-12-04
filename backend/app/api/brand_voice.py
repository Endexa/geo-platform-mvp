from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
from uuid import UUID
from typing import List
from app.core.database import get_db
from app.models import BrandVoiceConfig, VoiceVector, VoiceRule, Profile
from app.services.brand_voice import BrandVoiceService
from app.core.security import get_current_active_user
from app.core.rate_limiter import standard_rate_limit, upload_rate_limit
from app.core.validators import (
    SecureBaseModel,
    SecureBrandVoiceCheck,
    StringSanitizer,
    FileUploadValidator
)
from loguru import logger

router = APIRouter()


class CreateConfigRequest(SecureBaseModel):
    """Secure request for creating brand voice config"""
    name: str = Field(..., min_length=3, max_length=100)
    description: str | None = Field(None, max_length=500)

    @validator('name', 'description')
    def sanitize_text(cls, v):
        if v:
            return StringSanitizer.sanitize(v, max_length=500)
        return v


class AddRuleRequest(SecureBaseModel):
    """Secure request for adding brand voice rule"""
    config_id: UUID
    rule_type: str = Field(..., pattern=r'^(forbidden_word|required_phrase|tone_directive)$')
    value: str = Field(..., min_length=1, max_length=500)

    @validator('value')
    def sanitize_value(cls, v):
        return StringSanitizer.sanitize(v, max_length=500)


class CheckVoiceRequest(SecureBrandVoiceCheck):
    """Secure request for checking brand voice (inherits from SecureBrandVoiceCheck)"""
    pass


@router.post("/config", dependencies=[Depends(standard_rate_limit)])
async def create_config(
    request: CreateConfigRequest,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Create a new brand voice configuration.

    **Security Features:**
    - Rate limited: 100 requests per minute
    - Input validation: Name and description sanitized
    - Audit logged: All config creations logged

    **Authentication:** Currently optional for MVP.
    Uncomment dependencies to require authentication.
    """
    logger.info(f"Brand voice config creation requested: {request.name}")

    # For MVP, using a mock org_id
    # In production, this would come from authenticated user's organization
    mock_org_id = "00000000-0000-0000-0000-000000000000"

    config = BrandVoiceConfig(
        org_id=mock_org_id,
        name=request.name,
        description=request.description
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    logger.info(f"Brand voice config created: {config.id}")

    return {
        "config_id": str(config.id),
        "name": config.name,
        "message": "Brand voice config created"
    }


@router.post("/config/{config_id}/upload", dependencies=[Depends(upload_rate_limit)])
async def upload_knowledge_base(
    config_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Upload text/PDF to the Golden Knowledge Base.
    Creates vector embeddings for brand voice matching.

    **Security Features:**
    - Rate limited: 5 uploads per hour
    - File validation: Type and size validated
    - Audit logged: All uploads logged

    **Allowed file types:** .txt, .pdf, .doc, .docx
    **Max file size:** 10MB
    """
    logger.info(f"Knowledge base upload requested for config: {config_id}, file: {file.filename}")

    # Validate file
    try:
        file_size = 0
        content_chunks = []
        async for chunk in file.stream():
            file_size += len(chunk)
            content_chunks.append(chunk)
            if file_size > FileUploadValidator.MAX_FILE_SIZE:
                logger.warning(f"File too large: {file.filename} ({file_size} bytes)")
                raise HTTPException(status_code=413, detail="File too large")

        FileUploadValidator.validate(file.filename, file_size)
    except ValueError as e:
        logger.warning(f"File validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    config = db.query(BrandVoiceConfig).filter(BrandVoiceConfig.id == config_id).first()

    if not config:
        logger.warning(f"Config not found: {config_id}")
        raise HTTPException(status_code=404, detail="Config not found")

    # Read file content
    content = b''.join(content_chunks)
    try:
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        logger.warning(f"Invalid file encoding: {file.filename}")
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    # Process and store vectors
    brand_voice_service = BrandVoiceService(db)
    vector_count = await brand_voice_service.process_knowledge_base(
        config_id,
        text_content
    )

    logger.info(f"Knowledge base processed: {config_id}, vectors created: {vector_count}")

    return {
        "message": "Knowledge base uploaded and processed",
        "vectors_created": vector_count
    }


@router.post("/config/{config_id}/rule", dependencies=[Depends(standard_rate_limit)])
async def add_rule(
    config_id: UUID,
    request: AddRuleRequest,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Add a rule to the brand voice config.

    **Security Features:**
    - Rate limited: 100 requests per minute
    - Input validation: Rule type and value sanitized
    - Audit logged: All rule additions logged
    """
    logger.info(f"Adding rule to config {config_id}: type={request.rule_type}")

    config = db.query(BrandVoiceConfig).filter(BrandVoiceConfig.id == config_id).first()

    if not config:
        logger.warning(f"Config not found: {config_id}")
        raise HTTPException(status_code=404, detail="Config not found")

    rule = VoiceRule(
        config_id=config_id,
        rule_type=request.rule_type,
        value=request.value
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    logger.info(f"Rule added successfully: {rule.id}")

    return {
        "rule_id": str(rule.id),
        "message": "Rule added successfully"
    }


@router.post("/check", dependencies=[Depends(standard_rate_limit)])
async def check_voice(
    request: CheckVoiceRequest,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Check content against brand voice.
    Returns hybrid score (vector + rule-based).

    **Security Features:**
    - Rate limited: 100 requests per minute
    - Input validation: Text sanitized, XSS/SQL injection prevented
    - Audit logged: All checks logged
    """
    logger.info(f"Brand voice check requested for config: {request.config_id}")

    config = db.query(BrandVoiceConfig).filter(BrandVoiceConfig.id == request.config_id).first()

    if not config:
        logger.warning(f"Config not found: {request.config_id}")
        raise HTTPException(status_code=404, detail="Config not found")

    brand_voice_service = BrandVoiceService(db)
    result = await brand_voice_service.check_voice(
        request.text,
        request.config_id
    )

    logger.info(f"Brand voice check completed: config={request.config_id}, score={result['hybrid_score']}")

    return {
        "config_id": str(request.config_id),
        "overall_score": result["hybrid_score"],
        "vector_score": result["vector_score"],
        "rule_score": result["rule_score"],
        "violations": result["violations"],
        "suggestions": result["suggestions"]
    }


@router.get("/config/{config_id}", dependencies=[Depends(standard_rate_limit)])
async def get_config(
    config_id: UUID,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Get brand voice configuration details.

    **Security Features:**
    - Rate limited: 100 requests per minute
    """
    config = db.query(BrandVoiceConfig).filter(BrandVoiceConfig.id == config_id).first()

    if not config:
        logger.warning(f"Config not found: {config_id}")
        raise HTTPException(status_code=404, detail="Config not found")

    vector_count = db.query(VoiceVector).filter(VoiceVector.config_id == config_id).count()
    rule_count = db.query(VoiceRule).filter(VoiceRule.config_id == config_id).count()

    return {
        "id": str(config.id),
        "name": config.name,
        "description": config.description,
        "vector_count": vector_count,
        "rule_count": rule_count
    }
