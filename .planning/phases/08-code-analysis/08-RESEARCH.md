# Phase 8: Code Analysis - Research

**Researched:** 2026-02-26
**Domain:** LLM prompt generation, code analysis output ingestion, recommendation enrichment
**Confidence:** HIGH

## Summary

Phase 8 adds a two-step code analysis flow to the Endexa platform: (1) Endexa generates tailored analysis prompts based on audit scoring gaps, (2) the user runs those prompts with their own AI tools (Claude, Copilot, ChatGPT, etc.), then (3) uploads the output back to Endexa, which (4) produces enriched code-specific recommendations. This is a unique differentiator -- no competitor offers this "bring-your-own-AI" code analysis bridge.

The feature operates entirely within the existing stack (FastAPI + Celery + Supabase + LiteLLM + Nuxt 3). Prompt generation is a deterministic template-fill operation (sync, no LLM needed). Output parsing and recommendation enrichment use LiteLLM with structured output (Pydantic response_format) via Celery background tasks. The upload endpoint accepts plain text (UploadFile or raw text body) since AI tool output is inherently unstructured text.

**Primary recommendation:** Build prompt generation as a synchronous, template-based service (no LLM calls). Build output ingestion as a Celery task using LiteLLM structured output with Pydantic models to extract findings from free-text uploads. Map findings back to existing criterion_ids for enriched recommendations.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CODE-01 | Endexa generates analysis prompts users can run on their codebase with their AI tools | PromptGeneratorService reads failing CriterionResult records, selects from category-specific prompt templates, fills in context from audit data. Downloadable as Markdown bundle. |
| CODE-02 | User can upload AI tool output back to Endexa for deeper analysis | CodeAnalysisUpload API endpoint accepts text/plain or multipart file upload. Creates CodeAnalysis DB record. Triggers Celery task for LLM parsing. |
| CODE-03 | Endexa produces additional recommendations based on code analysis output | CodeAnalysisService uses LiteLLM with Pydantic structured output to extract findings, then creates CodeRecommendation records linked to existing criterion_ids. |
| CODE-04 | Prompts are useful but not self-revealing (users still need Endexa for interpretation) | Prompts ask diagnostic questions ("find all meta tags and list them") but never reveal scoring weights, thresholds, or the recommendation logic. The interpretation layer is server-side only. |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | API endpoints for prompt download + output upload | Already the project backend |
| SQLAlchemy | existing | CodeAnalysis + CodeRecommendation models | Already the ORM |
| Celery + Redis | existing | Background processing of uploaded output | Already the task queue |
| LiteLLM | existing | Parse uploaded AI output into structured findings | Already used for chat + dispatch |
| Pydantic v2 | existing | Structured output schemas for LLM parsing | Already used for all schemas |
| Alembic | existing | Migration for new tables | Already the migration tool |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | existing | UploadFile parsing in FastAPI | File upload endpoint |
| loguru | existing | Logging throughout services | All service code |

### No New Dependencies Needed
This phase requires zero new pip packages. Everything is built on the existing stack.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/
│   └── code_analysis.py          # API router: generate prompts, upload output, get results
├── models/
│   └── code_analysis.py          # CodeAnalysis + CodeRecommendation SQLAlchemy models
├── schemas/
│   └── code_analysis.py          # Pydantic request/response schemas
├── services/
│   └── code_analysis_service.py  # PromptGenerator + OutputParser + RecommendationEnricher
└── tasks/
    └── audit_tasks.py            # Add code_analysis_task (or new file)

frontend/
├── pages/
│   └── audit.vue                 # Add "Code Analysis" section (download prompts + upload output)
├── components/
│   ├── CodeAnalysisPrompts.vue   # Prompt download UI
│   └── CodeAnalysisUpload.vue    # Upload + results display
└── composables/
    └── useCodeAnalysis.ts        # API composable
```

### Pattern 1: Template-Based Prompt Generation (No LLM)
**What:** Prompts are generated deterministically from audit data using pre-written templates. No LLM call needed at generation time.
**When to use:** Always for CODE-01. Prompt generation must be instant and free.
**Why:** Prompt generation is a mapping operation: take failing criteria, select relevant templates, fill in context (URL, detected framework, specific issues). This is deterministic and should return in <100ms.

```python
# Source: Codebase pattern from recommendation_engine.py
class PromptGeneratorService:
    """Generates code analysis prompts from audit scoring gaps."""

    # Category -> list of prompt templates
    CATEGORY_TEMPLATES: dict[str, list[PromptTemplate]] = {
        "crawlability": [...],
        "content_structure": [...],
        "structured_data": [...],
        "authority": [...],
    }

    def generate_prompts(
        self, audit_id: str, db: Session
    ) -> list[GeneratedPrompt]:
        """Generate prompts from failing criteria.

        Steps:
        1. Load CriterionResult records where score < threshold
        2. Group by category
        3. Select matching prompt templates
        4. Fill template variables (url, domain, detected_framework, etc.)
        5. Return list of GeneratedPrompt objects
        """
        # Load failing criteria (score below threshold)
        failing = self._load_failing_criteria(audit_id, db)

        prompts = []
        for criterion in failing:
            template = self._select_template(criterion)
            if template:
                prompt = template.render(
                    url=audit.url,
                    domain=audit.domain,
                    criterion_name=criterion.criterion_name,
                    current_score=criterion.score,
                    technical_detail=criterion.technical_detail,
                )
                prompts.append(prompt)
        return prompts
```

### Pattern 2: LLM Structured Output for Output Parsing
**What:** Use LiteLLM with Pydantic `response_format` to parse free-text AI tool output into structured findings.
**When to use:** For CODE-03. The uploaded text is unstructured -- an LLM is the best parser.
**Why:** AI tool output will vary wildly in format. Regex/rule-based parsing would be brittle. LLM structured output with Pydantic validation gives reliable extraction.

```python
# Source: LiteLLM docs (https://docs.litellm.ai/docs/completion/json_mode)
from pydantic import BaseModel
import litellm

class CodeFinding(BaseModel):
    """A single finding from code analysis output."""
    criterion_id: str | None  # Map to existing criterion if possible
    category: str  # crawlability, content_structure, structured_data, authority
    severity: str  # high, medium, low
    finding: str  # What was found
    location: str | None  # File path or code location
    suggestion: str  # What to fix
    evidence: str  # Supporting detail from the AI output

class CodeAnalysisResult(BaseModel):
    """Structured extraction from uploaded AI tool output."""
    detected_framework: str | None  # e.g., "Next.js", "WordPress", "Django"
    findings: list[CodeFinding]
    summary: str  # One-paragraph summary

# In CodeAnalysisService:
response = await litellm.acompletion(
    model=settings.CODE_ANALYSIS_MODEL,  # gemini/gemini-2.5-flash
    messages=[
        {"role": "system", "content": PARSING_SYSTEM_PROMPT},
        {"role": "user", "content": uploaded_text},
    ],
    response_format=CodeAnalysisResult,
    api_key=api_key,
)
result = CodeAnalysisResult.model_validate_json(
    response.choices[0].message.content
)
```

### Pattern 3: Two-Phase Async Processing (Upload -> Parse -> Recommend)
**What:** Upload creates a record immediately (status=pending), then a Celery task processes asynchronously.
**When to use:** For CODE-02/CODE-03. Parsing + recommendation generation may take 5-15 seconds.
**Why:** Follows the exact same pattern as the main audit pipeline. User gets instant feedback (upload accepted) and polls for results.

```python
# Same pattern as run_crawl_and_generate in audit_tasks.py
@celery_app.task(bind=True, name="app.tasks.code_analysis.process_upload")
def process_code_analysis(self, code_analysis_id: str):
    """Parse uploaded output and generate enriched recommendations."""
    db = SessionLocal()
    try:
        ca = db.query(CodeAnalysis).filter(CodeAnalysis.id == code_analysis_id).first()
        ca.status = "parsing"
        db.commit()

        # Step 1: Parse with LLM
        result = asyncio.run(service.parse_output(ca.raw_output))
        ca.parsed_findings = result.model_dump()
        ca.detected_framework = result.detected_framework
        db.commit()

        # Step 2: Generate enriched recommendations
        ca.status = "recommending"
        db.commit()
        recs = service.generate_code_recommendations(ca, result, db)

        ca.status = "completed"
        db.commit()
    except Exception as e:
        ca.status = "failed"
        ca.error_message = str(e)[:1000]
        db.commit()
    finally:
        db.close()
```

### Pattern 4: Prompt IP Protection (CODE-04)
**What:** Prompts ask diagnostic questions but never reveal scoring logic.
**When to use:** Always. This is a core business requirement.
**Design principles:**
1. **Ask, don't tell:** Prompts say "Find all JSON-LD blocks and list their @type values" not "Your structured data score is 30/100 because you're missing FAQPage schema."
2. **No thresholds:** Never include scoring thresholds or weights in prompts.
3. **No category mapping:** Don't tell the user which criterion each prompt maps to.
4. **Diagnostic framing:** Frame as "analyze your codebase for AI readiness" not "fix these specific scoring criteria."
5. **Output format guidance:** Tell the user's AI tool what format to output (sections, lists) to make parsing easier, but don't reveal why that format matters.

### Anti-Patterns to Avoid
- **LLM for prompt generation:** Don't use an LLM to generate the prompts. Templates are faster, cheaper, deterministic, and don't risk leaking scoring logic.
- **Strict JSON upload requirement:** Don't require users to upload structured JSON. AI tool output is free-text. Accept it as-is and use LLM to parse.
- **Blocking upload endpoint:** Don't parse synchronously in the upload endpoint. Use Celery -- parsing takes 5-15 seconds.
- **Direct code access:** Don't ask users to give Endexa access to their code repository. The prompt-based approach is privacy-preserving and works with any AI tool.
- **One giant prompt:** Don't generate a single massive prompt. Generate multiple focused prompts grouped by scoring category so users can run them incrementally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Free-text parsing to structured data | Regex-based parser for AI output | LiteLLM structured output (Pydantic response_format) | AI output format varies wildly between tools and runs; LLM parsing with schema validation handles all formats |
| File upload handling | Custom multipart parser | FastAPI UploadFile | Built-in, handles streaming, size limits already configured (10MB) |
| Background task processing | Custom async queue | Celery task (existing) | Already running, tested, with error handling patterns |
| Prompt template rendering | Custom string formatting | Jinja2 (already in project for reports) | Already used in ReportService, handles conditionals and loops |
| Tier gating | Custom auth check | `require_tier(SubscriptionTier.PRO)` dependency | Already built and tested in Phase 4 |

**Key insight:** This entire feature fits within existing patterns. The prompt generation mirrors the recommendation engine (deterministic, template-based). The upload/parse flow mirrors the audit pipeline (create record, Celery task, poll for status). The LLM call mirrors chat service (LiteLLM with explicit api_key). No new infrastructure needed.

## Common Pitfalls

### Pitfall 1: Leaking Scoring Logic in Prompts
**What goes wrong:** Generated prompts reveal Endexa's proprietary scoring weights, thresholds, or criteria mapping. Users realize they can skip Endexa entirely and just use the prompts.
**Why it happens:** Developer writes prompts that say "Your SD3 (FAQPage schema) criterion scored 20/100, threshold is 60. Fix this." The user now knows the exact criterion ID, score, and threshold.
**How to avoid:** Prompts must be phrased as diagnostic questions: "Search your codebase for FAQ-related schema markup (JSON-LD with @type: FAQPage). List all instances found, their locations, and whether they contain mainEntity with Question/Answer pairs." Never include scores, thresholds, criterion IDs, or category weights.
**Warning signs:** Prompt text contains numbers from the scoring system, criterion IDs (C1, SD3, CS2), or phrases like "your score" or "threshold."

### Pitfall 2: Brittle Output Parsing
**What goes wrong:** The parser expects a specific format from the uploaded AI output but different AI tools (Claude, ChatGPT, Copilot) produce very different output formats.
**Why it happens:** Developer tests with only one AI tool's output format and builds a parser around it.
**How to avoid:** Use LLM structured output for parsing. The LLM can handle any reasonable text format and extract findings into a consistent Pydantic schema. Add test cases with output samples from at least 3 different AI tools.
**Warning signs:** Parser uses regex patterns that match Claude's markdown format but not ChatGPT's.

### Pitfall 3: Prompt Explosion
**What goes wrong:** An audit with 30 failing criteria generates 30 separate prompts. Users are overwhelmed and don't run any of them.
**Why it happens:** Generating one prompt per failing criterion without aggregation.
**How to avoid:** Group prompts by category (max 4 categories). Each category prompt covers all failing criteria in that category. Cap at 4-6 prompts total per audit. Prioritize by gap_score so the most impactful prompts come first.
**Warning signs:** More than 8 prompts generated for a single audit. Prompts that overlap or repeat instructions.

### Pitfall 4: Cost Overrun on Output Parsing
**What goes wrong:** Users upload huge AI outputs (50KB+ of text) and parsing via LLM costs more than expected.
**Why it happens:** No size limit on uploads. Using expensive models for parsing. No budget tracking.
**How to avoid:** Cap upload size at 100KB of text (plenty for any reasonable analysis output). Use the cheap model (gemini/gemini-2.5-flash) for parsing. Track cost via existing AuditCostLedger. Truncate input to 50K tokens max before sending to LLM.
**Warning signs:** Single parsing call costs >$0.05. Upload sizes routinely exceed 100KB.

### Pitfall 5: Orphaned Code Analysis Records
**What goes wrong:** User starts code analysis but never uploads output. Records pile up in "pending" or "prompts_generated" state.
**Why it happens:** No lifecycle management for code analysis records.
**How to avoid:** Code analysis records should be created only when output is uploaded, not when prompts are generated. Prompt generation is stateless (no DB record needed). Only the upload creates a CodeAnalysis record.

## DB Schema Design

### New Tables

```sql
-- Code analysis sessions: one per upload per audit
CREATE TABLE code_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID NOT NULL REFERENCES audits(id),
    user_id UUID NOT NULL REFERENCES profiles(id),
    status VARCHAR NOT NULL DEFAULT 'pending',
        -- pending -> parsing -> recommending -> completed / failed
    raw_output TEXT NOT NULL,             -- Uploaded AI tool output (plain text)
    raw_output_size_bytes INTEGER NOT NULL,
    detected_framework VARCHAR,           -- e.g., "nextjs", "wordpress", "django"
    parsed_findings JSONB,                -- Structured extraction from LLM
    prompt_categories_used JSONB,         -- Which category prompts were run
    model_used VARCHAR,                   -- LLM model used for parsing
    error_message VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX idx_code_analyses_audit_id ON code_analyses(audit_id);
CREATE INDEX idx_code_analyses_user_id ON code_analyses(user_id);

-- Code-specific recommendations: linked to code analysis + optionally to existing criteria
CREATE TABLE code_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code_analysis_id UUID NOT NULL REFERENCES code_analyses(id),
    audit_id UUID NOT NULL REFERENCES audits(id),
    criterion_id VARCHAR,                 -- Links to existing criterion if applicable (e.g., "SD3")
    category VARCHAR NOT NULL,            -- crawlability, content_structure, structured_data, authority
    severity VARCHAR NOT NULL,            -- high, medium, low
    finding TEXT NOT NULL,                -- What was found in the code
    file_path VARCHAR,                    -- Where in the codebase
    suggestion TEXT NOT NULL,             -- How to fix it
    code_snippet TEXT,                    -- Example fix code
    evidence TEXT,                        -- Supporting detail
    status VARCHAR NOT NULL DEFAULT 'open', -- open, done, dismissed
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_code_recs_code_analysis_id ON code_recommendations(code_analysis_id);
CREATE INDEX idx_code_recs_audit_id ON code_recommendations(audit_id);
```

### Key Design Decisions

1. **code_analyses links to audit_id** -- Code analysis is always associated with a specific audit. This means the prompts are generated from that audit's failing criteria.
2. **raw_output stored as TEXT** -- The uploaded AI tool output is plain text. Storing it allows re-processing if the parsing model improves.
3. **parsed_findings as JSONB** -- The structured LLM extraction. Stored as JSONB for flexibility and queryability.
4. **code_recommendations links to both code_analysis_id and audit_id** -- This allows querying all recommendations (audit + code) for a given audit.
5. **criterion_id is nullable** -- Some code findings may not map to existing scoring criteria. Those are still valuable but won't have a criterion_id link.
6. **No separate table for prompts** -- Prompts are generated on-the-fly from audit data and served directly. No need to persist them.

## API Endpoints Design

```
POST   /api/v1/code-analysis/{audit_id}/prompts      -- Generate and download analysis prompts (Pro tier)
POST   /api/v1/code-analysis/{audit_id}/upload        -- Upload AI tool output (Pro tier)
GET    /api/v1/code-analysis/{audit_id}               -- Get code analysis status and results (Pro tier)
GET    /api/v1/code-analysis/{audit_id}/recommendations -- Get code-specific recommendations (Pro tier)
PATCH  /api/v1/code-analysis/{audit_id}/recommendations/{id} -- Update code rec status
```

### Prompt Generation Endpoint (Sync)
- **Method:** POST (generates fresh prompts based on current audit data)
- **Auth:** JWT + require_tier(PRO)
- **Response:** JSON with prompts array, or downloadable Markdown file (Accept header negotiation)
- **Performance:** <200ms (no LLM calls, pure template fill)
- **Returns:** Array of {category, title, prompt_text, priority, target_criteria_count}

### Upload Endpoint
- **Method:** POST multipart/form-data OR application/json with text body
- **Auth:** JWT + require_tier(PRO)
- **Body:** UploadFile (text/plain, text/markdown, application/json) OR JSON {output: string, categories: string[]}
- **Size limit:** 100KB max (validated server-side)
- **Response:** {id, status: "pending"} -- immediate return, processing via Celery
- **Idempotency:** Multiple uploads per audit allowed (each creates a new CodeAnalysis record)

## Prompt Template Architecture

### Category: Crawlability (C1-C12)
Focus: AI bot access, SSR detection, server configuration
```markdown
## AI Bot Access Analysis

Analyze the project's web server configuration and deployment setup:

1. **robots.txt**: Find the robots.txt file or configuration. List all User-agent
   directives and any Disallow rules. Pay special attention to rules targeting
   these user agents: GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot,
   Claude-SearchBot, Bingbot, CCBot, Google-Extended.

2. **Server-Side Rendering**: Identify the rendering strategy:
   - Is this a static site (SSG), server-rendered (SSR), or client-side only (CSR)?
   - If using a framework (Next.js, Nuxt, SvelteKit, etc.), what rendering mode
     is configured?
   - Are there pages that load content purely via JavaScript after initial page load?

3. **Response Headers**: Check for any middleware or server configuration that sets
   custom headers. Look for: X-Robots-Tag, Cache-Control, Content-Type headers.

4. **Performance Configuration**: Identify any CDN, caching, or compression
   configuration that affects page load time.

For each finding, provide: the file path, the relevant code/config snippet,
and a brief description of what it does.
```

### Category: Content Structure (CS1-CS13)
Focus: Heading hierarchy, content organization, FAQ patterns
```markdown
## Content Structure Analysis

Examine the codebase for content structure patterns:

1. **Heading Hierarchy**: Find all components or templates that render headings
   (h1-h6). For each:
   - What determines the heading level?
   - Are headings hardcoded or dynamic?
   - Is there a consistent hierarchy (h1 > h2 > h3)?

2. **FAQ Sections**: Search for any FAQ-related components, templates, or content:
   - Are there <details>/<summary> elements?
   - Any accordion or collapsible components?
   - Any structured Q&A content patterns?

3. **Content Freshness**: Look for date/timestamp patterns:
   - Are published dates or "last updated" dates displayed?
   - Are they hardcoded or dynamically generated?
   - What format are they in?

4. **Data Tables**: Find any table components or HTML tables:
   - Do tables have captions?
   - Are they accessible (th, scope attributes)?
   - Are they data-rich or presentational?

5. **Content Length & Structure**: For key pages (homepage, main product/service pages):
   - Approximately how much content is on each?
   - Are there bulleted/numbered lists?
   - Is content organized with clear sections?

For each finding, provide: the file path, relevant code snippet, and description.
```

### Category: Structured Data (SD1-SD13)
Focus: JSON-LD, schema.org, llms.txt
```markdown
## Structured Data Analysis

Search the codebase for structured data implementation:

1. **JSON-LD Blocks**: Find all JSON-LD script tags or components:
   - List every @type found across the codebase
   - For each, list the fields populated
   - Note any dynamic vs hardcoded values
   - Check if schemas are validated against schema.org specs

2. **Schema.org Types**: Specifically check for these schema types:
   - Organization (with name, url, logo, sameAs)
   - WebSite (with searchAction)
   - FAQPage (with mainEntity containing Question/Answer pairs)
   - Article/BlogPosting (with headline, author, datePublished, dateModified)
   - BreadcrumbList
   - Product/Offer (if applicable)
   - HowTo (if applicable)

3. **llms.txt**: Check if there is an llms.txt or llms-full.txt file at the
   site root. If found, list its contents and structure.

4. **Sitemap**: Find the sitemap.xml configuration:
   - Is it auto-generated or manual?
   - What pages are included/excluded?
   - Is lastmod populated and accurate?

For each finding, provide: the file path, the complete code snippet, and assessment.
```

### Category: Authority (A1-A8, S1-S15)
Focus: E-E-A-T signals, SEO fundamentals, meta tags
```markdown
## Authority & SEO Fundamentals Analysis

Examine the codebase for authority signals and SEO implementation:

1. **Meta Tags**: Find where meta tags are set for each page:
   - title tag: How is it generated? Is it unique per page?
   - meta description: Is it present? Dynamic or static?
   - canonical URL: Is it set? Is it correct?
   - Open Graph tags (og:title, og:description, og:image)
   - Twitter Card tags

2. **Author Information**: Search for author-related patterns:
   - Are author names displayed on content pages?
   - Are there author bio sections or "about" pages?
   - Is author structured data (Person schema) present?

3. **Internal Linking**: Analyze the navigation and linking structure:
   - How does the main navigation work?
   - Are there breadcrumbs?
   - Are related content links present?
   - Estimate the average internal links per page

4. **Image Optimization**: Check image handling:
   - Do images have alt text?
   - Is it descriptive or generic (e.g., "image1.jpg")?
   - Are images optimized (lazy loading, srcset, WebP)?

5. **SSL & Security**: Check for HTTPS configuration, HSTS headers,
   Content-Security-Policy setup.

For each finding, provide: the file path, the relevant code, and description.
```

### Framework Detection Heuristic
Before generating prompts, detect the tech stack from crawl_data to customize prompt language:
```python
FRAMEWORK_HINTS: dict[str, list[str]] = {
    "nextjs": ["next/", "_next/", "Next.js", "__next"],
    "nuxt": ["nuxt", "_nuxt/", "Nuxt"],
    "wordpress": ["wp-content", "wp-includes", "WordPress"],
    "react_spa": ["react", "bundle.js", "root"],
    "django": ["csrfmiddlewaretoken", "django"],
    "rails": ["rails", "turbolinks"],
    "angular": ["ng-", "angular"],
    "svelte": ["svelte", "__svelte"],
    "gatsby": ["gatsby", "__gatsby"],
    "hugo": ["hugo"],
    "jekyll": ["jekyll"],
}

def detect_framework(crawl_data: dict) -> str | None:
    """Detect framework from crawl_data HTML and headers."""
    html = crawl_data.get("html", "").lower()
    headers = str(crawl_data.get("headers", {})).lower()
    combined = html + headers

    for framework, hints in FRAMEWORK_HINTS.items():
        if any(hint.lower() in combined for hint in hints):
            return framework
    return None
```

## LLM Parsing System Prompt

The system prompt for parsing uploaded AI output back into structured findings:

```
You are an expert at analyzing code review output and extracting structured findings.

You will receive the output from an AI tool (Claude, ChatGPT, Copilot, etc.) that
analyzed a website's codebase for AI-readiness issues.

Extract each distinct finding into the structured format. For each finding:

1. Determine the category:
   - "crawlability" -- AI bot access, robots.txt, SSR, response times, server config
   - "content_structure" -- headings, content organization, FAQs, data tables, freshness
   - "structured_data" -- JSON-LD, schema.org, llms.txt, sitemaps
   - "authority" -- meta tags, author info, E-E-A-T signals, SEO fundamentals, images

2. Map to a criterion_id if clearly applicable (use null if unsure):
   - C1-C12: Crawlability criteria
   - CS1-CS13: Content Structure criteria
   - SD1-SD13: Structured Data criteria
   - A1-A8: Authority (E-E-A-T) criteria
   - S1-S15: SEO fundamental criteria

3. Assess severity:
   - "high" -- Missing or broken, significant negative impact
   - "medium" -- Present but incomplete or suboptimal
   - "low" -- Minor improvement opportunity

4. Extract the finding, file location (if mentioned), and a specific suggestion.

Be thorough. Extract EVERY actionable finding. Do not summarize or skip findings.
If the text is unclear or garbled, extract what you can and note uncertainty.
```

## Prompt Download Format

Prompts should be downloadable as a single Markdown file, structured for easy copy-paste into AI tools:

```markdown
# Endexa Code Analysis Prompts
# Site: example.com
# Generated: 2026-02-26
# Audit ID: abc123

---

## Prompt 1: Crawlability Analysis (Priority: High)

[Paste the following prompt into your AI tool (Claude, ChatGPT, Copilot, etc.)
and provide access to your codebase.]

<prompt>
[Full prompt text here]
</prompt>

---

## Prompt 2: Structured Data Analysis (Priority: High)

<prompt>
[Full prompt text here]
</prompt>

---

[... more prompts ...]

---

## After Running These Prompts

1. Copy the output from your AI tool
2. Go to your Endexa audit results page
3. Click "Upload Analysis Results"
4. Paste or upload the output
5. Endexa will analyze the results and generate code-specific recommendations
```

## Frontend Integration Points

### Audit Page (audit.vue) -- New Section
Add a "Code Analysis" section between the Download & Export section and the Competitor Preview:

```
Download & Export section (existing)
    [PDF] [HTML] [CSV] [Chat with AI]

Code Analysis section (NEW) -- Pro tier only
    "Get deeper code-level recommendations"
    [Download Analysis Prompts] -- triggers POST /prompts
    [Upload Analysis Results] -- triggers file picker + POST /upload

    If code analysis exists:
        Status badge (pending/parsing/completed)
        Code recommendations list (when completed)

Competitor Preview (existing)
Recommendation Preview (existing)
```

### UI Components
- **CodeAnalysisPrompts.vue:** Button to download prompts. Shows category pills for which prompts will be generated. Instructions for using them.
- **CodeAnalysisUpload.vue:** File upload or paste textarea. Category checkboxes (which prompts did you run?). Upload progress and status polling. Results display when complete.

### Polling Pattern
Same pattern as audit polling (useIntervalFn, 3-second interval, stop on completion):
```typescript
const { pause, resume } = useIntervalFn(async () => {
  const data = await useApiFetch<CodeAnalysisResponse>(
    `/code-analysis/${auditId}/`
  )
  codeAnalysis.value = data
  if (data.status === 'completed' || data.status === 'failed') {
    pause()
    if (data.status === 'completed') {
      loadCodeRecommendations(auditId)
    }
  }
}, 3000, { immediate: false })
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ask users for repo access | Generate prompts users run with their own AI tools | 2024-2025 | Privacy-preserving, works with any codebase, no security risk |
| Regex-based code parsing | LLM structured output with Pydantic schemas | 2024-2025 | Handles any format, no brittle regex patterns |
| One-shot analysis | Iterative: audit scores -> prompts -> upload -> enriched recs | Endexa innovation | Users progressively deepen their analysis |
| Generic code review prompts | Audit-gap-targeted prompts | Endexa innovation | Prompts focus on what actually scored poorly, not generic advice |

## Open Questions

1. **Should prompts include framework-specific hints?**
   - What we know: We can detect the framework from crawl_data (Next.js, WordPress, etc.)
   - What's unclear: How much framework-specific language to include in prompts vs keeping them generic
   - Recommendation: Include light framework hints (e.g., "If using Next.js, check next.config.js for...") when framework is detected. Keep prompts useful for any stack when not detected.

2. **Multiple uploads per audit?**
   - What we know: Users might run prompts one category at a time
   - What's unclear: Should each upload create a new CodeAnalysis or update an existing one?
   - Recommendation: Allow multiple uploads, each creates a new CodeAnalysis record. The UI shows all code analyses for an audit, with the most recent first. Recommendations from all uploads are aggregated.

3. **Should code recommendations integrate into the main recommendations list?**
   - What we know: The main recommendations list (AuditRecommendation) is well-established
   - What's unclear: Whether code recommendations should appear alongside or separately
   - Recommendation: Keep them in a separate table (code_recommendations) but display them in a combined view on the frontend. This preserves the clean audit recommendation pipeline while adding code-level depth.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: recommendation_engine.py, chat_service.py, audit_tasks.py, scoring_orchestrator.py, base_scorer.py, all 4 scorers
- LiteLLM structured output docs: https://docs.litellm.ai/docs/completion/json_mode
- Existing REQUIREMENTS.md and ROADMAP.md in .planning/

### Secondary (MEDIUM confidence)
- FastAPI file upload patterns: https://fastapi.tiangolo.com/tutorial/request-forms-and-files/
- LiteLLM Pydantic integration: https://python.useinstructor.com/integrations/litellm/

### Tertiary (LOW confidence -- for context only)
- AI prompts for code review patterns: https://5ly.co/blog/ai-prompts-for-code-review/
- Claude SEO workflows: https://www.the-ai-corner.com/p/claude-seo-cowork-prompts-free-agency

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all patterns from existing codebase
- Architecture: HIGH -- directly mirrors existing patterns (recommendation engine, audit pipeline, chat service)
- DB Schema: HIGH -- follows existing conventions (UUID PKs, JSONB, status columns, audit linkage)
- Prompt templates: MEDIUM -- templates need real-world testing with multiple AI tools
- LLM parsing accuracy: MEDIUM -- structured output works well but needs validation with diverse AI output formats
- Pitfalls: HIGH -- grounded in existing project-specific pitfalls research and codebase patterns

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable patterns, no fast-moving dependencies)
