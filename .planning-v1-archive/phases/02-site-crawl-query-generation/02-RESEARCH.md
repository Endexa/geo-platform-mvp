# Phase 2: Site Crawl & Query Generation - Research

**Researched:** 2026-02-22
**Domain:** Web crawling, structured data extraction, LLM-driven query generation
**Confidence:** HIGH

## Summary

Phase 2 has two distinct subsystems: (1) a site crawler that extracts AI-readiness signals from any URL, and (2) an LLM-powered query generator that produces 10-15 categorized queries reflecting how real users would ask AI engines about that brand's domain.

The existing codebase provides substantial crawling infrastructure that can be reused. The `geo_data_points/utils/` directory contains a `SiteCrawler` class, an `HTMLAnalyzer` with JSON-LD extraction, a `ContentAnalyzer` for text metrics, and a robust `CachedSession` HTTP client. The existing `backend/app/services/analyzer.py` demonstrates the pattern of fetching and parsing HTML with BeautifulSoup. For structured data extraction beyond JSON-LD (microdata, RDFa, Open Graph), the `extruct` library is the standard tool. For query generation, LiteLLM is already installed (pinned at 1.17.0 in requirements.txt, though current is much newer) and supports structured Pydantic output via `response_format`, which is exactly what we need to produce categorized, typed query objects. This phase also creates the core `Audit` model -- the central entity for the entire pipeline -- and the `AuditQuery` model that Phase 3 will consume.

**Primary recommendation:** Build a new `CrawlerService` in `backend/app/services/` using httpx (async, already installed) + BeautifulSoup + extruct for structured data extraction, and a `QueryGeneratorService` that uses LiteLLM `completion()` with a Pydantic `response_format` to produce typed queries. Use Celery tasks for the crawl + generation pipeline. Create `Audit` and `AuditQuery` SQLAlchemy models with an Alembic migration (003).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIT-02 | App crawls the site and extracts AI-readiness signals (schema.org, robots.txt AI directives, structured data, content structure) | CrawlerService using httpx + BeautifulSoup + extruct for JSON-LD/microdata/RDFa/OG extraction, robots.txt parsing with `urllib.robotparser` for GPTBot/ClaudeBot/PerplexityBot/Google-Extended directives, HTMLAnalyzer reuse for content structure (headings, meta tags, main content), ContentAnalyzer for text metrics |
| AUDIT-03 | App auto-generates industry-relevant queries from crawled site content | QueryGeneratorService using LiteLLM `completion()` with Pydantic `response_format` to produce 10-15 categorized queries (industry, brand-direct, comparison, problem, recommendation) from crawled signals. Queries stored in `audit_queries` table with category, text, and audit_id FK |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.26.0 (installed) | Async HTTP client for crawling | Already in requirements.txt, async-first, HTTP/2 support, connection pooling |
| beautifulsoup4 | 4.12.2 (installed) | HTML parsing and content extraction | Already in requirements.txt, project uses it extensively |
| lxml | 5.1.0 (installed) | Fast HTML parser backend for BS4 | Already in requirements.txt, used as BS4 parser backend |
| extruct | 0.18.0 | Structured data extraction (JSON-LD, microdata, RDFa, OG, Dublin Core) | Standard library for HTML metadata extraction, handles all schema.org formats, maintained by Scrapinghub |
| litellm | 1.17.0 (installed, update recommended) | LLM API for query generation with structured output | Already in requirements.txt, supports `response_format=PydanticModel`, works with OpenAI/Anthropic/Perplexity |
| pydantic | 2.5.3 (installed) | Schema for crawl results and generated queries | Already in requirements.txt, LiteLLM structured output uses Pydantic BaseModel |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| w3lib | latest | URL normalization, base URL extraction | Used by extruct internally, useful for canonical URL handling |
| textstat | 0.7.3 (installed) | Readability scoring for crawled content | Already in requirements.txt, used by ContentAnalyzer |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| extruct | Manual BS4 JSON-LD extraction | extruct handles 6 metadata formats automatically; manual approach only covers JSON-LD (existing code does this). extruct is the clear win for completeness |
| httpx async | requests (sync, installed) | Existing crawler uses sync requests. httpx async is better for the backend's async FastAPI pattern and allows concurrent page fetches. However, the Celery worker is sync -- use httpx sync client inside Celery, or use `asyncio.run()` wrapper |
| LiteLLM structured output | Instructor library | Instructor adds a dependency; LiteLLM native `response_format` is sufficient for this use case |

**Installation:**
```bash
pip install extruct w3lib
```

Note: All other dependencies already installed. LiteLLM 1.17.0 is very old (Feb 2024). Consider updating to latest, but test compatibility first. The `response_format=PydanticModel` feature works in 1.17.0+.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── models/
│   ├── audit.py              # NEW: Audit model (central entity)
│   └── audit_query.py        # NEW: AuditQuery model (generated queries)
├── services/
│   ├── crawler_service.py    # NEW: Site crawl + signal extraction
│   └── query_generator.py    # NEW: LLM-powered query generation
├── schemas/
│   ├── audit.py              # NEW: Pydantic request/response schemas
│   └── crawl.py              # NEW: CrawlResult, AIReadinessSignals schemas
└── tasks/
    └── celery_app.py         # MODIFY: Add crawl + query gen tasks
```

### Pattern 1: Audit Model as Central Entity
**What:** The `Audit` model is the top-level entity for the entire pipeline. Every subsequent phase (dispatch, scoring, reporting) hangs off this record. The existing `AuditCostLedger` already has an `audit_id` column (plain UUID, no FK yet -- see Phase 1 decision `[01-02]`).
**When to use:** Always -- this is the primary data model for the entire application.
**Example:**
```python
# backend/app/models/audit.py
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime, timezone
from app.core.database import Base


class AuditStatus(str, enum.Enum):
    PENDING = "pending"
    CRAWLING = "crawling"
    GENERATING_QUERIES = "generating_queries"
    DISPATCHING = "dispatching"       # Phase 3
    ANALYZING = "analyzing"           # Phase 4
    COMPLETED = "completed"
    FAILED = "failed"


class Audit(Base):
    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    url = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    status = Column(String, default=AuditStatus.PENDING)
    crawl_data = Column(JSONB, nullable=True)       # Structured crawl results
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    queries = relationship("AuditQuery", back_populates="audit", cascade="all, delete-orphan")
    cost_entries = relationship("AuditCostLedger", backref="audit", foreign_keys="AuditCostLedger.audit_id")
```

### Pattern 2: AuditQuery Model with Categories
**What:** Each generated query is stored with its category, text, and association to an audit. Downstream phases (3, 4) consume these queries.
**When to use:** After query generation, before AI dispatch.
**Example:**
```python
# backend/app/models/audit_query.py
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.core.database import Base


class AuditQuery(Base):
    __tablename__ = "audit_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False, index=True)
    category = Column(String, nullable=False)  # industry, brand_direct, comparison, problem, recommendation
    query_text = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    audit = relationship("Audit", back_populates="queries")
    # Phase 3 will add: responses = relationship("AuditResponse", ...)
```

### Pattern 3: CrawlerService with Signal Extraction
**What:** A service that crawls a URL and returns a structured `CrawlResult` with all AI-readiness signals.
**When to use:** First step of the audit pipeline after record creation.
**Example:**
```python
# backend/app/services/crawler_service.py
import httpx
from bs4 import BeautifulSoup
import extruct
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from pydantic import BaseModel
from typing import Optional


class AIBotAccess(BaseModel):
    gptbot: Optional[bool] = None        # True=allowed, False=blocked, None=no directive
    claudebot: Optional[bool] = None
    perplexitybot: Optional[bool] = None
    google_extended: Optional[bool] = None


class CrawlResult(BaseModel):
    url: str
    domain: str
    title: str
    meta_description: str
    main_content: str                     # Extracted main text (truncated)
    headings: dict[str, list[str]]        # {"h1": [...], "h2": [...]}
    schema_org: list[dict]                # JSON-LD structured data
    open_graph: dict[str, str]            # OG tags
    ai_bot_access: AIBotAccess            # robots.txt directives for AI bots
    word_count: int
    content_keywords: list[str]           # Top extracted keywords
    industry_signals: list[str]           # Detected industry from schema/content
    authority_markers: dict               # E-E-A-T signals


class CrawlerService:
    AI_BOT_USER_AGENTS = [
        ("GPTBot", "gptbot"),
        ("ClaudeBot", "claudebot"),
        ("PerplexityBot", "perplexitybot"),
        ("Google-Extended", "google_extended"),
    ]

    async def crawl(self, url: str) -> CrawlResult:
        """Crawl URL and extract AI-readiness signals."""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "GEOBot/1.0"})
            response.raise_for_status()

        html = response.text
        soup = BeautifulSoup(html, "lxml")

        # Extract structured data with extruct
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        structured = extruct.extract(html, base_url=base_url, syntaxes=["json-ld", "opengraph", "microdata"])

        # Check robots.txt for AI bot access
        ai_bot_access = self._check_ai_bot_access(base_url, url)

        # ... build and return CrawlResult
```

### Pattern 4: LLM Query Generation with Structured Output
**What:** Use LiteLLM `completion()` with `response_format=PydanticModel` to generate typed, categorized queries from crawl data.
**When to use:** After successful crawl, as the second step of the audit pipeline.
**Example:**
```python
# backend/app/services/query_generator.py
from litellm import completion
from pydantic import BaseModel


class GeneratedQuery(BaseModel):
    category: str       # "industry" | "brand_direct" | "comparison" | "problem" | "recommendation"
    query_text: str     # The actual query a user would ask an AI engine
    intent: str         # Why this query matters for brand visibility


class GeneratedQuerySet(BaseModel):
    queries: list[GeneratedQuery]


class QueryGeneratorService:
    SYSTEM_PROMPT = """You are an AI brand visibility analyst. Given crawled website data,
generate 10-15 queries that real users would ask AI engines (ChatGPT, Claude, Perplexity)
about this brand's domain. Queries should test whether AI engines know about, recommend,
or mention this brand.

Categories:
- industry: General industry questions where the brand should appear ("best X in Y city")
- brand_direct: Direct questions about the brand ("what is [brand] known for")
- comparison: Competitive comparison queries ("X vs Y vs Z")
- problem: Problem-solving queries where the brand's products/services are solutions
- recommendation: Recommendation-seeking queries ("recommend a good X for Y")

Rules:
- Queries must sound like natural user questions, not keyword strings
- Include the brand name in brand_direct queries only
- Industry/comparison/problem/recommendation queries should be phrased so the brand
  COULD appear in the answer without being explicitly asked about
- Cover diverse aspects of the brand's offerings based on the crawled content
"""

    async def generate(self, crawl_result: dict, brand_name: str) -> GeneratedQuerySet:
        user_prompt = self._build_prompt(crawl_result, brand_name)

        response = completion(
            model="gpt-4o",       # or configurable
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=GeneratedQuerySet,
            temperature=0.7,      # Some creativity for diverse queries
        )

        return GeneratedQuerySet.model_validate_json(
            response.choices[0].message.content
        )
```

### Pattern 5: Celery Task Pipeline
**What:** A Celery task orchestrates the crawl-then-generate pipeline, updating audit status at each stage.
**When to use:** Triggered when a user initiates an audit.
**Example:**
```python
# backend/app/tasks/ (new task module)
from app.tasks.celery_app import celery_app
from app.services.crawler_service import CrawlerService
from app.services.query_generator import QueryGeneratorService

@celery_app.task(bind=True, queue="audit")
def run_crawl_and_generate(self, audit_id: str, url: str):
    """Crawl site, extract signals, generate queries."""
    db = get_db_session()
    try:
        audit = db.query(Audit).get(audit_id)
        audit.status = AuditStatus.CRAWLING
        db.commit()

        # Step 1: Crawl
        crawler = CrawlerService()
        crawl_result = asyncio.run(crawler.crawl(url))
        audit.crawl_data = crawl_result.model_dump()
        audit.status = AuditStatus.GENERATING_QUERIES
        db.commit()

        # Step 2: Generate queries
        generator = QueryGeneratorService()
        query_set = asyncio.run(generator.generate(
            crawl_result.model_dump(),
            brand_name=extract_brand_name(crawl_result)
        ))

        for i, q in enumerate(query_set.queries):
            db.add(AuditQuery(
                audit_id=audit_id,
                category=q.category,
                query_text=q.query_text,
                sort_order=i,
            ))
        db.commit()

        audit.status = AuditStatus.GENERATING_QUERIES  # Ready for Phase 3
        db.commit()

    except Exception as e:
        audit.status = AuditStatus.FAILED
        audit.error_message = str(e)
        db.commit()
        raise
```

### Anti-Patterns to Avoid
- **Full site crawl for MVP:** Do NOT crawl the entire site. Crawl only the target URL + robots.txt. Multi-page crawling is out of scope for Phase 2; the existing `SiteCrawler` class in `geo_data_points/utils/crawl_helpers.py` is for deep analysis and would be too slow for an audit trigger.
- **Hardcoded query templates:** Do NOT generate queries from templates. Use LLM with crawled context to generate relevant, natural queries. Template-based queries miss industry specifics and sound robotic.
- **Storing raw HTML in database:** Store extracted structured data (JSON) in `crawl_data` JSONB column, not the full HTML. Full HTML is large and not needed downstream.
- **Synchronous LLM calls in request handler:** Always use Celery for the crawl+generate pipeline. LLM calls are 2-5 seconds and must not block the API.
- **Single large prompt with all crawl data:** Trim the main content to ~2000 words before sending to LLM. Full page content wastes tokens and does not improve query quality.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON-LD/microdata/RDFa extraction | Manual BS4 JSON-LD parsing (exists in html_parser.py) | `extruct.extract()` | Handles 6 metadata formats, edge cases (nested schemas, arrays, malformed JSON-LD), maintained by Scrapinghub |
| robots.txt parsing | Custom regex parsing | `urllib.robotparser.RobotFileParser` (stdlib) | Handles wildcards, multiple user-agents, crawl-delay, standard compliance. Already used in existing `robots_txt_gptbot.py` |
| LLM structured output | Manual JSON parsing + validation of LLM response | LiteLLM `response_format=PydanticModel` | Handles provider-specific serialization, retries on malformed JSON, Pydantic validation built-in |
| URL normalization | Manual string manipulation | `urllib.parse.urlparse` + `w3lib.url.canonicalize_url` | Edge cases: trailing slashes, default ports, fragment removal, encoding |
| Content text extraction | Manual tag stripping | `BeautifulSoup.get_text()` with `readability-lxml` for main content | Main content detection is heuristic-heavy; the existing `HTMLAnalyzer.get_main_content()` already handles `<main>`, `<article>`, largest block fallback |

**Key insight:** The crawling subsystem is deceptively complex -- robots.txt edge cases, redirect chains, JavaScript-rendered content, structured data format variations, and encoding issues. Use proven libraries for each piece rather than building custom solutions.

## Common Pitfalls

### Pitfall 1: Crawling JavaScript-Rendered Sites
**What goes wrong:** httpx/requests only fetch raw HTML. Sites using client-side rendering (React SPAs, Angular) return empty `<div id="app">` with no content.
**Why it happens:** Many modern sites render content via JavaScript, not server-side HTML.
**How to avoid:** For MVP, use httpx (fast, simple). Document that JS-rendered sites will have limited extraction. Playwright (already in requirements.txt) can be added as a fallback in a future iteration, but adds significant complexity (browser process, memory, timeout management). Do NOT add Playwright in Phase 2.
**Warning signs:** Crawl returns very short content (<100 words) from a site that visibly has substantial content.

### Pitfall 2: robots.txt Parsing Failures
**What goes wrong:** `RobotFileParser` raises exceptions or returns incorrect results when robots.txt is malformed, returns non-200, or has encoding issues.
**Why it happens:** Many sites have broken robots.txt files. Some return HTML error pages for /robots.txt.
**How to avoid:** Wrap all robots.txt parsing in try/except. Treat any error as "no directive found" (None), not as "allowed" or "blocked". The existing `robots_txt_gptbot.py` script already follows this pattern (returns score 50 on error).
**Warning signs:** `RobotFileParser.read()` hangs (no timeout) or raises `UnicodeDecodeError`.

### Pitfall 3: LLM Query Generation Inconsistency
**What goes wrong:** LLM generates fewer than 10 queries, wrong categories, or irrelevant queries that do not relate to the crawled content.
**Why it happens:** Insufficient context in the prompt, or LLM hallucinates brand details not present in crawl data.
**How to avoid:** (1) Use `response_format=PydanticModel` for structured output with enum validation on categories. (2) Include specific crawl signals in the prompt (brand name, industry, products/services from schema.org, top keywords). (3) Validate query count and category distribution after generation -- if fewer than 10, log a warning but do not retry (costly). (4) Use temperature=0.7 for diversity while keeping output reasonable.
**Warning signs:** Generated queries are generic ("what is the best product") without industry or brand specificity.

### Pitfall 4: AuditCostLedger FK Migration
**What goes wrong:** The existing `AuditCostLedger` model has `audit_id` as a plain UUID column with no FK constraint (see Phase 1 decision `[01-02]`). When creating the `audits` table, the FK must be added to the existing `audit_cost_ledger` table.
**Why it happens:** Phase 1 created the cost ledger before the `audits` table existed.
**How to avoid:** The Alembic migration (003) must: (1) Create the `audits` table, (2) Create the `audit_queries` table, (3) Add FK constraint from `audit_cost_ledger.audit_id` to `audits.id`. This must be done carefully -- if orphan rows exist in `audit_cost_ledger`, the FK will fail. Either clean up orphans first or make the FK deferrable.
**Warning signs:** `alembic upgrade` fails with "insert or update on table violates foreign key constraint".

### Pitfall 5: Celery Async Mismatch
**What goes wrong:** Celery workers are synchronous by default. Calling `await` inside a Celery task raises `RuntimeError: no running event loop`.
**Why it happens:** The new crawler service uses httpx async, but Celery tasks run in sync context.
**How to avoid:** Use `asyncio.run()` to run async code inside Celery tasks, OR use `httpx.Client` (sync) instead of `httpx.AsyncClient` for the Celery path. The sync approach is simpler. LiteLLM `completion()` is synchronous by default, so no async issue there.
**Warning signs:** `RuntimeError: This event loop is already running` or `RuntimeError: no current event loop`.

### Pitfall 6: extruct + lxml Compatibility
**What goes wrong:** extruct uses lxml under the hood. Some systems have issues with lxml C extensions.
**Why it happens:** lxml requires C compilation; Docker images may lack build tools.
**How to avoid:** lxml 5.1.0 is already in requirements.txt and presumably works in the project's Docker image. Verify with `docker-compose run backend python -c "import extruct"` after adding extruct.
**Warning signs:** `ImportError: lxml is required` or build failures during `pip install extruct`.

## Code Examples

Verified patterns from official sources and existing codebase:

### Structured Data Extraction with extruct
```python
# Source: https://github.com/scrapinghub/extruct + existing codebase pattern
import extruct
import httpx
from w3lib.html import get_base_url

def extract_structured_data(html: str, url: str) -> dict:
    """Extract all structured data from HTML."""
    base_url = get_base_url(html, url)
    data = extruct.extract(
        html,
        base_url=base_url,
        syntaxes=["json-ld", "opengraph", "microdata"],
        uniform=True,  # Normalize output format across syntaxes
    )
    return data
    # Returns: {"json-ld": [...], "opengraph": [...], "microdata": [...]}
```

### robots.txt AI Bot Check
```python
# Source: existing geo_data_points/scripts/robots_txt_gptbot.py pattern
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from typing import Optional

AI_BOTS = {
    "GPTBot": "gptbot",
    "ChatGPT-User": "chatgpt_user",
    "ClaudeBot": "claudebot",
    "Claude-SearchBot": "claude_searchbot",
    "PerplexityBot": "perplexitybot",
    "Google-Extended": "google_extended",
    "Applebot-Extended": "applebot_extended",
    "CCBot": "ccbot",
}

def check_ai_bot_access(url: str) -> dict[str, Optional[bool]]:
    """Check robots.txt for AI bot directives.

    Returns dict: bot_name -> True (allowed), False (blocked), None (no directive/error).
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    results = {}

    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        for user_agent, key in AI_BOTS.items():
            try:
                results[key] = rp.can_fetch(user_agent, url)
            except Exception:
                results[key] = None
    except Exception:
        # robots.txt not found or parsing error -- all None
        results = {key: None for key in AI_BOTS.values()}

    return results
```

### LiteLLM Structured Output for Query Generation
```python
# Source: https://docs.litellm.ai/docs/completion/json_mode
from litellm import completion
from pydantic import BaseModel, Field
from typing import Literal


class GeneratedQuery(BaseModel):
    category: Literal["industry", "brand_direct", "comparison", "problem", "recommendation"]
    query_text: str = Field(description="Natural language query a user would ask an AI engine")
    intent: str = Field(description="What this query tests about brand visibility")


class GeneratedQuerySet(BaseModel):
    queries: list[GeneratedQuery] = Field(
        min_length=10,
        max_length=15,
        description="10-15 categorized queries for AI brand visibility audit"
    )


def generate_queries(crawl_summary: str, brand_name: str) -> GeneratedQuerySet:
    response = completion(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Brand: {brand_name}\n\nCrawl data:\n{crawl_summary}"},
        ],
        response_format=GeneratedQuerySet,
        temperature=0.7,
    )
    return GeneratedQuerySet.model_validate_json(response.choices[0].message.content)
```

### Alembic Migration Pattern (manual, following Phase 1 convention)
```python
# Source: existing backend/alembic/versions/002_add_audit_cost_ledger.py pattern
"""add audits and audit_queries tables

Revision ID: 003
Revises: 002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"

def upgrade():
    # 1. Create audits table
    op.create_table(
        "audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending"),
        sa.Column("crawl_data", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Create audit_queries table
    op.create_table(
        "audit_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audits.id"), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("query_text", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_queries_audit_id", "audit_queries", ["audit_id"])

    # 3. Add FK from existing audit_cost_ledger to audits
    # NOTE: May need to clean orphan rows first if any exist
    op.create_foreign_key(
        "fk_audit_cost_ledger_audit_id",
        "audit_cost_ledger", "audits",
        ["audit_id"], ["id"],
    )
```

### Brand Name Extraction from Crawl Data
```python
def extract_brand_name(crawl_result: dict) -> str:
    """Extract brand name from crawl data, prioritizing structured data."""
    # Priority 1: schema.org Organization name
    for schema in crawl_result.get("schema_org", []):
        if schema.get("@type") == "Organization" and schema.get("name"):
            return schema["name"]

    # Priority 2: og:site_name
    og = crawl_result.get("open_graph", {})
    if og.get("og:site_name"):
        return og["og:site_name"]

    # Priority 3: Title tag (first segment before separator)
    title = crawl_result.get("title", "")
    if title:
        for sep in [" | ", " - ", " :: ", " — "]:
            if sep in title:
                return title.split(sep)[0].strip()
        return title.strip()

    # Fallback: domain name
    return crawl_result.get("domain", "Unknown")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON-LD extraction with BS4 | extruct library handles all metadata formats | Stable (extruct 0.18.0, Nov 2024) | Eliminates custom parsing code for 6 metadata standards |
| Template-based query generation | LLM-generated queries from crawl context | 2024-2025 (GEO industry emergence) | Queries match actual user behavior; categories reflect GEO audit best practices |
| robots.txt only for Googlebot/Bingbot | Must check GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot, Applebot-Extended | 2023-2025 (AI crawler explosion) | 21% of top 1000 sites now have GPTBot rules; ClaudeBot grew from 2k to 30k+ sites in 4 months |
| Single AI engine testing | Multi-engine testing (ChatGPT, Claude, Perplexity) | 2024-2025 | Each engine has different citation patterns; comprehensive audit requires all three |

**Deprecated/outdated:**
- The existing `geo_data_points/` measurement system (108-point scoring) is being replaced by the AI brand visibility audit pipeline. However, the utilities in `geo_data_points/utils/` (HTMLAnalyzer, ContentAnalyzer, http_client) contain reusable patterns.
- The `AnalyzerService` in `backend/app/services/analyzer.py` uses sync `requests` library -- the new `CrawlerService` should use `httpx` for consistency with the async FastAPI backend.

## AI Bot User-Agents Reference

Critical for AUDIT-02. These are the AI crawler user-agents to check in robots.txt:

| Bot | Company | Purpose | First Seen (robots.txt) |
|-----|---------|---------|------------------------|
| GPTBot | OpenAI | Training data crawl | Mid 2023 |
| ChatGPT-User | OpenAI | Real-time browsing for ChatGPT | Late 2023 |
| ClaudeBot | Anthropic | Training data crawl | Dec 2023 |
| Claude-SearchBot | Anthropic | Search/retrieval | 2024 |
| PerplexityBot | Perplexity | Indexing for Perplexity search | Jan 2024 |
| Google-Extended | Google | Gemini training (separate from Googlebot) | Late 2023 |
| Applebot-Extended | Apple | Apple Intelligence training | 2024 |
| CCBot | Common Crawl | Open training data (used by many AI labs) | 2019+ |

## Query Category Framework

Based on GEO industry research, the five query categories for AUDIT-03:

| Category | Purpose | Example (for a coffee roaster) |
|----------|---------|-------------------------------|
| **industry** | General industry queries where brand should surface | "best specialty coffee roasters in Portland" |
| **brand_direct** | Direct questions about the brand | "what is Blue Bottle Coffee known for" |
| **comparison** | Head-to-head competitive queries | "Blue Bottle vs Stumptown vs Intelligentsia" |
| **problem** | Problem-solving queries where brand is a solution | "how to get freshly roasted coffee beans delivered" |
| **recommendation** | Recommendation-seeking queries | "recommend a good single-origin coffee subscription" |

Distribution target: ~2-3 industry, ~2-3 brand_direct, ~2-3 comparison, ~2-3 problem, ~2-3 recommendation = 10-15 total.

## Open Questions

1. **LiteLLM version pinning**
   - What we know: requirements.txt pins `litellm==1.17.0` (Feb 2024). Current is much newer (Feb 2026). Structured output via `response_format` works in both.
   - What's unclear: Whether updating LiteLLM would break other dependencies or change API behavior.
   - Recommendation: Keep 1.17.0 for now. The `response_format=PydanticModel` + `model_validate_json()` pattern works. Update in a separate maintenance task if needed.

2. **Query generation model choice**
   - What we know: GPT-4o works well for structured output. Claude also supports it via LiteLLM. Cost per generation is ~$0.01-0.03.
   - What's unclear: Whether to make the model configurable or hardcode gpt-4o.
   - Recommendation: Make configurable via settings (`QUERY_GEN_MODEL`), default to `gpt-4o`. This allows switching to cheaper models (gpt-4o-mini) or different providers later.

3. **Content truncation for LLM prompt**
   - What we know: Full page content can be 10k+ words. LLM context window is not the issue; cost and relevance are.
   - What's unclear: Optimal truncation length for query generation quality.
   - Recommendation: Truncate main content to ~2000 words. Include full structured data (schema.org, OG tags) since these are small and information-dense. Include top 20 keywords.

4. **Handling the existing Analysis/Website models**
   - What we know: The existing `Analysis` and `Website` models serve the old 108-point scoring system. The new `Audit` model is the replacement.
   - What's unclear: Whether to repurpose, deprecate, or leave them alongside the new models.
   - Recommendation: Leave existing models untouched. Create new `Audit` and `AuditQuery` models. The old models can be cleaned up in a future maintenance phase. No schema conflicts.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/services/analyzer.py`, `backend/app/models/audit_cost.py`, `backend/app/tasks/celery_app.py` -- established patterns for crawling, models, and task routing
- Existing codebase: `geo_data_points/utils/html_parser.py`, `geo_data_points/utils/crawl_helpers.py`, `geo_data_points/utils/content_analyzer.py` -- reusable extraction patterns
- Existing codebase: `geo_data_points/scripts/robots_txt_gptbot.py`, `geo_data_points/scripts/schema_org_organization.py` -- established patterns for robots.txt and schema.org checks
- [LiteLLM Structured Output Docs](https://docs.litellm.ai/docs/completion/json_mode) -- `response_format=PydanticModel` pattern verified
- [extruct GitHub](https://github.com/scrapinghub/extruct) -- v0.18.0, BSD license, extracts JSON-LD/microdata/RDFa/OG/Dublin Core

### Secondary (MEDIUM confidence)
- [AI Bots and Robots.txt - Paul Calvano](https://paulcalvano.com/2025-08-21-ai-bots-and-robots-txt/) -- AI bot user-agent names and adoption data
- [How to Allow AI Bots in robots.txt](https://www.adnanzameer.com/2025/09/how-to-allow-ai-bots-in-your-robotstxt.html) -- Comprehensive bot list with company attribution
- [Understanding AI Crawlers - Qwairy](https://www.qwairy.co/blog/understanding-ai-crawlers-complete-guide) -- AI bot compliance and blocking patterns
- [GEO Guide 2025 - Profound](https://www.tryprofound.com/resources/articles/generative-engine-optimization-geo-guide-2025) -- Query generation methodology, funnel-based categories
- [HTTPX Web Scraping - BrightData](https://brightdata.com/blog/web-data/web-scraping-with-httpx) -- httpx async patterns for crawling

### Tertiary (LOW confidence)
- LiteLLM version 1.17.0 behavior: confirmed via docs that `response_format` is supported, but exact error handling on malformed output needs testing
- extruct + Python 3.12 compatibility: PyPI lists support up to 3.12, but project uses 3.12 (from Docker) -- needs validation during install

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All core libraries already installed except extruct. LiteLLM structured output verified via official docs. Patterns derived from existing codebase.
- Architecture: HIGH - Models follow established SQLAlchemy patterns from Phase 1. Celery task routing already configured. Service pattern matches existing analyzer.py.
- Pitfalls: HIGH - Identified from existing codebase patterns (robots.txt error handling, Celery async mismatch, FK migration) and verified against official docs.

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable domain, libraries are mature)
