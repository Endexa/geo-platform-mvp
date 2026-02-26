"""Pydantic v2 schemas for the code analysis feature.

Covers request schemas, prompt response schemas, LLM structured output
schemas (used as response_format for litellm), and API response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CodeUploadRequest(BaseModel):
    """Body for JSON upload of AI tool output text."""

    output: str
    categories_used: list[str] = []


# ---------------------------------------------------------------------------
# Prompt schemas
# ---------------------------------------------------------------------------


class GeneratedPrompt(BaseModel):
    """A single diagnostic prompt for one failing category."""

    category: str
    title: str
    prompt_text: str
    priority: str  # high, medium, low
    target_count: int  # number of failing criteria this addresses


class PromptsResponse(BaseModel):
    """Full response from the prompts endpoint."""

    audit_id: str
    domain: str
    generated_at: str
    prompts: list[GeneratedPrompt]
    markdown_bundle: str  # Full downloadable Markdown text


# ---------------------------------------------------------------------------
# LLM structured output schemas (also used as response_format for litellm)
# ---------------------------------------------------------------------------


class CodeFinding(BaseModel):
    """A single finding extracted from AI tool output by the LLM parser."""

    criterion_id: str | None = None
    category: str  # crawlability, content_structure, structured_data, authority
    severity: str  # high, medium, low
    finding: str
    location: str | None = None
    suggestion: str
    evidence: str


class CodeAnalysisResult(BaseModel):
    """Structured extraction from uploaded AI tool output (LLM response_format)."""

    detected_framework: str | None = None
    findings: list[CodeFinding]
    summary: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class CodeAnalysisResponse(BaseModel):
    """API response for GET /code-analysis/{audit_id} status poll."""

    id: str
    audit_id: str
    status: str
    detected_framework: str | None = None
    parsed_findings: dict | None = None
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


class CodeRecommendationResponse(BaseModel):
    """API response for a single code recommendation."""

    id: str
    code_analysis_id: str
    criterion_id: str | None = None
    category: str
    severity: str
    finding: str
    file_path: str | None = None
    suggestion: str
    code_snippet: str | None = None
    evidence: str | None = None
    status: str
    created_at: str


class CodeRecommendationUpdateRequest(BaseModel):
    """Request body for PATCH /recommendations/{rec_id}."""

    status: str  # open, done, dismissed
