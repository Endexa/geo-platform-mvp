from typing import Optional

from pydantic import BaseModel, ConfigDict


class AIBotAccess(BaseModel):
    """Robots.txt directives for AI bot user-agents.

    True = allowed, False = blocked, None = no directive found.
    """

    gptbot: Optional[bool] = None
    chatgpt_user: Optional[bool] = None
    claudebot: Optional[bool] = None
    claude_searchbot: Optional[bool] = None
    perplexitybot: Optional[bool] = None
    google_extended: Optional[bool] = None
    applebot_extended: Optional[bool] = None
    ccbot: Optional[bool] = None


class CrawlResult(BaseModel):
    """Structured output from crawling a URL for AI-readiness signals."""

    model_config = ConfigDict(from_attributes=True)

    url: str
    domain: str
    title: str
    meta_description: str
    main_content: str
    headings: dict[str, list[str]]  # {"h1": [...], "h2": [...], "h3": [...]}
    schema_org: list[dict]  # JSON-LD structured data from extruct
    open_graph: dict[str, str]  # OG tags
    microdata: list[dict]  # microdata from extruct
    ai_bot_access: AIBotAccess
    word_count: int
    content_keywords: list[str]
    industry_signals: list[str]
    authority_markers: dict  # E-E-A-T signals
