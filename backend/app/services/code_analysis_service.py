"""Code Analysis Service — two classes for Phase 8.

PromptGeneratorService: deterministic template-based prompt generation from
failing audit criteria. Zero LLM calls, sub-200ms response.

CodeAnalysisService: LiteLLM structured output parsing of uploaded AI tool
text into CodeFinding records, then bulk CodeRecommendation persistence.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import litellm
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.code_analysis import CodeAnalysis, CodeRecommendation
from app.models.criterion_result import CriterionResult
from app.models.page_score import PageScore
from app.schemas.code_analysis import (
    CodeAnalysisResult,
    CodeFinding,
    GeneratedPrompt,
    PromptsResponse,
)


# ---------------------------------------------------------------------------
# Framework detection helpers (shared between both services)
# ---------------------------------------------------------------------------

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

# Ordered priority for prompt generation (high-priority categories first)
CATEGORY_ORDER = ["crawlability", "structured_data", "content_structure", "authority"]


# ---------------------------------------------------------------------------
# PromptGeneratorService
# ---------------------------------------------------------------------------


class PromptGeneratorService:
    """Generates audit-gap-targeted code analysis prompts.

    Prompts are deterministic template fills — no LLM call, no scores,
    no thresholds, no criterion IDs in the output text.
    """

    # ---------------------------------------------------------------------------
    # Category prompt templates (diagnostic language only, no scoring logic)
    # ---------------------------------------------------------------------------

    CATEGORY_TEMPLATES: dict[str, dict] = {
        "crawlability": {
            "title": "AI Bot Access Analysis",
            "priority": "high",
            "prompt_text": (
                "## AI Bot Access Analysis\n\n"
                "Analyze the project's web server configuration and deployment setup:\n\n"
                "1. **robots.txt**: Find the robots.txt file or configuration. List all User-agent "
                "directives and any Disallow rules. Pay special attention to rules targeting "
                "these user agents: GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, "
                "Claude-SearchBot, Bingbot, CCBot, Google-Extended.\n\n"
                "2. **Server-Side Rendering**: Identify the rendering strategy:\n"
                "   - Is this a static site (SSG), server-rendered (SSR), or client-side only (CSR)?\n"
                "   - If using a framework (Next.js, Nuxt, SvelteKit, etc.), what rendering mode "
                "is configured?\n"
                "   - Are there pages that load content purely via JavaScript after initial page load?\n\n"
                "3. **Response Headers**: Check for any middleware or server configuration that sets "
                "custom headers. Look for: X-Robots-Tag, Cache-Control, Content-Type headers.\n\n"
                "4. **Performance Configuration**: Identify any CDN, caching, or compression "
                "configuration that affects page load time.\n\n"
                "For each finding, provide: the file path, the relevant code/config snippet, "
                "and a brief description of what it does."
            ),
        },
        "content_structure": {
            "title": "Content Structure Analysis",
            "priority": "medium",
            "prompt_text": (
                "## Content Structure Analysis\n\n"
                "Examine the codebase for content structure patterns:\n\n"
                "1. **Heading Hierarchy**: Find all components or templates that render headings "
                "(h1-h6). For each:\n"
                "   - What determines the heading level?\n"
                "   - Are headings hardcoded or dynamic?\n"
                "   - Is there a consistent hierarchy (h1 > h2 > h3)?\n\n"
                "2. **FAQ Sections**: Search for any FAQ-related components, templates, or content:\n"
                "   - Are there <details>/<summary> elements?\n"
                "   - Any accordion or collapsible components?\n"
                "   - Any structured Q&A content patterns?\n\n"
                "3. **Content Freshness**: Look for date/timestamp patterns:\n"
                "   - Are published dates or \"last updated\" dates displayed?\n"
                "   - Are they hardcoded or dynamically generated?\n"
                "   - What format are they in?\n\n"
                "4. **Data Tables**: Find any table components or HTML tables:\n"
                "   - Do tables have captions?\n"
                "   - Are they accessible (th, scope attributes)?\n"
                "   - Are they data-rich or presentational?\n\n"
                "5. **Content Length & Structure**: For key pages (homepage, main product/service pages):\n"
                "   - Approximately how much content is on each?\n"
                "   - Are there bulleted/numbered lists?\n"
                "   - Is content organized with clear sections?\n\n"
                "For each finding, provide: the file path, relevant code snippet, and description."
            ),
        },
        "structured_data": {
            "title": "Structured Data Analysis",
            "priority": "high",
            "prompt_text": (
                "## Structured Data Analysis\n\n"
                "Search the codebase for structured data implementation:\n\n"
                "1. **JSON-LD Blocks**: Find all JSON-LD script tags or components:\n"
                "   - List every @type found across the codebase\n"
                "   - For each, list the fields populated\n"
                "   - Note any dynamic vs hardcoded values\n"
                "   - Check if schemas are validated against schema.org specs\n\n"
                "2. **Schema.org Types**: Specifically check for these schema types:\n"
                "   - Organization (with name, url, logo, sameAs)\n"
                "   - WebSite (with searchAction)\n"
                "   - FAQPage (with mainEntity containing Question/Answer pairs)\n"
                "   - Article/BlogPosting (with headline, author, datePublished, dateModified)\n"
                "   - BreadcrumbList\n"
                "   - Product/Offer (if applicable)\n"
                "   - HowTo (if applicable)\n\n"
                "3. **llms.txt**: Check if there is an llms.txt or llms-full.txt file at the "
                "site root. If found, list its contents and structure.\n\n"
                "4. **Sitemap**: Find the sitemap.xml configuration:\n"
                "   - Is it auto-generated or manual?\n"
                "   - What pages are included/excluded?\n"
                "   - Is lastmod populated and accurate?\n\n"
                "For each finding, provide: the file path, the complete code snippet, and assessment."
            ),
        },
        "authority": {
            "title": "Authority & SEO Fundamentals Analysis",
            "priority": "medium",
            "prompt_text": (
                "## Authority & SEO Fundamentals Analysis\n\n"
                "Examine the codebase for authority signals and SEO implementation:\n\n"
                "1. **Meta Tags**: Find where meta tags are set for each page:\n"
                "   - title tag: How is it generated? Is it unique per page?\n"
                "   - meta description: Is it present? Dynamic or static?\n"
                "   - canonical URL: Is it set? Is it correct?\n"
                "   - Open Graph tags (og:title, og:description, og:image)\n"
                "   - Twitter Card tags\n\n"
                "2. **Author Information**: Search for author-related patterns:\n"
                "   - Are author names displayed on content pages?\n"
                "   - Are there author bio sections or \"about\" pages?\n"
                "   - Is author structured data (Person schema) present?\n\n"
                "3. **Internal Linking**: Analyze the navigation and linking structure:\n"
                "   - How does the main navigation work?\n"
                "   - Are there breadcrumbs?\n"
                "   - Are related content links present?\n"
                "   - Estimate the average internal links per page\n\n"
                "4. **Image Optimization**: Check image handling:\n"
                "   - Do images have alt text?\n"
                "   - Is it descriptive or generic (e.g., \"image1.jpg\")?\n"
                "   - Are images optimized (lazy loading, srcset, WebP)?\n\n"
                "5. **SSL & Security**: Check for HTTPS configuration, HSTS headers, "
                "Content-Security-Policy setup.\n\n"
                "For each finding, provide: the file path, the relevant code, and description."
            ),
        },
    }

    def detect_framework(self, crawl_data: dict) -> str | None:
        """Detect framework from crawl_data HTML and headers (case-insensitive)."""
        html = crawl_data.get("html", "").lower()
        headers = str(crawl_data.get("headers", {})).lower()
        combined = html + headers

        for framework, hints in FRAMEWORK_HINTS.items():
            if any(hint.lower() in combined for hint in hints):
                return framework
        return None

    def _load_failing_categories(self, audit_id: str, db: Session) -> set[str]:
        """Return categories with at least one criterion scoring below 50.

        Joins CriterionResult -> PageScore to filter by audit_id.
        Falls back to all 4 categories if no CriterionResult records found.
        """
        rows = (
            db.query(CriterionResult.category)
            .join(PageScore)
            .filter(
                PageScore.audit_id == uuid.UUID(audit_id),
                CriterionResult.score < 50,
            )
            .distinct()
            .all()
        )
        if rows:
            return {row[0] for row in rows}
        # Fallback: all categories (shouldn't happen on completed audit)
        logger.warning(
            "No failing CriterionResult found for audit %s — falling back to all categories",
            audit_id,
        )
        return set(CATEGORY_ORDER)

    def _count_failing_criteria(
        self, audit_id: str, category: str, db: Session
    ) -> int:
        """Count failing criteria in a specific category for an audit."""
        return (
            db.query(CriterionResult)
            .join(PageScore)
            .filter(
                PageScore.audit_id == uuid.UUID(audit_id),
                CriterionResult.category == category,
                CriterionResult.score < 50,
            )
            .count()
        )

    def generate_prompts(self, audit_id: str, db: Session, audit) -> PromptsResponse:
        """Generate diagnostic prompts for each failing category.

        Returns a PromptsResponse with a markdown_bundle ready for download.
        Zero LLM calls — pure template fill.
        """
        failing_categories = self._load_failing_categories(audit_id, db)
        framework = self.detect_framework(audit.crawl_data or {})

        prompts: list[GeneratedPrompt] = []
        for category in CATEGORY_ORDER:
            if category not in failing_categories:
                continue
            template = self.CATEGORY_TEMPLATES[category]
            prompt_text = template["prompt_text"]

            # Append light framework-specific note when detected
            if framework:
                framework_notes = {
                    "nextjs": "next.config.js",
                    "nuxt": "nuxt.config.ts",
                    "wordpress": "functions.php or theme directory",
                    "react_spa": "src/ directory and public/ folder",
                    "django": "settings.py and templates/",
                    "rails": "config/ and app/views/",
                    "angular": "angular.json and src/",
                    "svelte": "svelte.config.js",
                    "gatsby": "gatsby-config.js",
                    "hugo": "config.toml or config.yaml",
                    "jekyll": "_config.yml",
                }
                config_file = framework_notes.get(framework, "your project config")
                prompt_text += (
                    f"\n\nNote: This project appears to use {framework}. "
                    f"Tailor your analysis accordingly (e.g., check {config_file} "
                    f"for {framework}-specific configuration)."
                )

            target_count = self._count_failing_criteria(audit_id, category, db)
            prompts.append(
                GeneratedPrompt(
                    category=category,
                    title=template["title"],
                    prompt_text=prompt_text,
                    priority=template["priority"],
                    target_count=target_count,
                )
            )

        # Build downloadable Markdown bundle
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        markdown_bundle = self._build_markdown_bundle(
            audit_id=audit_id,
            domain=audit.domain,
            generated_at=now_str,
            prompts=prompts,
        )

        return PromptsResponse(
            audit_id=audit_id,
            domain=audit.domain,
            generated_at=now_str,
            prompts=prompts,
            markdown_bundle=markdown_bundle,
        )

    def _build_markdown_bundle(
        self,
        audit_id: str,
        domain: str,
        generated_at: str,
        prompts: list[GeneratedPrompt],
    ) -> str:
        """Render the downloadable Markdown file for all prompts."""
        lines = [
            "# Endexa Code Analysis Prompts",
            f"# Site: {domain}",
            f"# Generated: {generated_at}",
            f"# Audit ID: {audit_id}",
            "",
            "---",
            "",
        ]
        for i, prompt in enumerate(prompts, 1):
            lines += [
                f"## Prompt {i}: {prompt.title} (Priority: {prompt.priority.capitalize()})",
                "",
                "[Paste the following prompt into your AI tool (Claude, ChatGPT, Copilot, etc.)",
                "and provide access to your codebase.]",
                "",
                "<prompt>",
                prompt.prompt_text,
                "</prompt>",
                "",
                "---",
                "",
            ]
        lines += [
            "## After Running These Prompts",
            "",
            "1. Copy the output from your AI tool",
            "2. Go to your Endexa audit results page",
            "3. Click \"Upload Analysis Results\"",
            "4. Paste or upload the output",
            "5. Endexa will analyze the results and generate code-specific recommendations",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CodeAnalysisService
# ---------------------------------------------------------------------------


class CodeAnalysisService:
    """Parses uploaded AI tool output and generates code recommendations.

    parse_output() calls LiteLLM with response_format=CodeAnalysisResult.
    generate_code_recommendations() bulk-inserts CodeRecommendation rows.
    """

    PARSING_SYSTEM_PROMPT: str = (
        "You are an expert at analyzing code review output and extracting structured findings.\n\n"
        "You will receive the output from an AI tool (Claude, ChatGPT, Copilot, etc.) that "
        "analyzed a website's codebase for AI-readiness issues.\n\n"
        "Extract each distinct finding into the structured format. For each finding:\n\n"
        "1. Determine the category:\n"
        "   - \"crawlability\" -- AI bot access, robots.txt, SSR, response times, server config\n"
        "   - \"content_structure\" -- headings, content organization, FAQs, data tables, freshness\n"
        "   - \"structured_data\" -- JSON-LD, schema.org, llms.txt, sitemaps\n"
        "   - \"authority\" -- meta tags, author info, E-E-A-T signals, SEO fundamentals, images\n\n"
        "2. Map to a criterion_id if clearly applicable (use null if unsure):\n"
        "   - C1-C12: Crawlability criteria\n"
        "   - CS1-CS13: Content Structure criteria\n"
        "   - SD1-SD13: Structured Data criteria\n"
        "   - A1-A8: Authority (E-E-A-T) criteria\n"
        "   - S1-S15: SEO fundamental criteria\n\n"
        "3. Assess severity:\n"
        "   - \"high\" -- Missing or broken, significant negative impact\n"
        "   - \"medium\" -- Present but incomplete or suboptimal\n"
        "   - \"low\" -- Minor improvement opportunity\n\n"
        "4. Extract the finding, file location (if mentioned), and a specific suggestion.\n\n"
        "Be thorough. Extract EVERY actionable finding. Do not summarize or skip findings.\n"
        "If the text is unclear or garbled, extract what you can and note uncertainty."
    )

    def _resolve_api_key(self, model: str) -> str:
        """Resolve the correct API key for the given model prefix.

        Same prefix-based logic as dispatch_service.py and chat_service.py.
        """
        if model.startswith("gemini/"):
            return settings.GEMINI_API_KEY
        elif model.startswith("anthropic/"):
            return settings.ANTHROPIC_API_KEY
        elif model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            return settings.OPENAI_API_KEY
        return settings.OPENAI_API_KEY  # fallback

    async def parse_output(self, raw_text: str) -> CodeAnalysisResult:
        """Parse free-text AI tool output into structured CodeAnalysisResult.

        Truncates input to CODE_ANALYSIS_MAX_TOKENS_INPUT chars (rough token estimate).
        Calls LiteLLM with response_format=CodeAnalysisResult and explicit api_key.
        """
        # Truncate to char-level limit (50K chars ~ 50K tokens for most text)
        if len(raw_text) > settings.CODE_ANALYSIS_MAX_TOKENS_INPUT:
            logger.warning(
                "Truncating uploaded text from %d to %d chars",
                len(raw_text),
                settings.CODE_ANALYSIS_MAX_TOKENS_INPUT,
            )
            raw_text = raw_text[: settings.CODE_ANALYSIS_MAX_TOKENS_INPUT]

        model = settings.CODE_ANALYSIS_MODEL
        api_key = self._resolve_api_key(model)

        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": self.PARSING_SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
            response_format=CodeAnalysisResult,
            api_key=api_key,
            temperature=0.1,
        )

        result = CodeAnalysisResult.model_validate_json(
            response.choices[0].message.content
        )
        logger.info(
            "Parsed %d findings from uploaded text (framework: %s)",
            len(result.findings),
            result.detected_framework,
        )
        return result

    def generate_code_recommendations(
        self,
        code_analysis: CodeAnalysis,
        result: CodeAnalysisResult,
        db: Session,
    ) -> list[CodeRecommendation]:
        """Create CodeRecommendation rows from parsed findings.

        Bulk inserts and commits all recommendations in a single transaction.
        """
        recs: list[CodeRecommendation] = []
        for finding in result.findings:
            rec = CodeRecommendation(
                code_analysis_id=code_analysis.id,
                audit_id=code_analysis.audit_id,
                criterion_id=finding.criterion_id,
                category=finding.category,
                severity=finding.severity,
                finding=finding.finding,
                file_path=finding.location,
                suggestion=finding.suggestion,
                code_snippet=None,  # Not extracted at parse time; future enhancement
                evidence=finding.evidence,
                status="open",
            )
            db.add(rec)
            recs.append(rec)
        db.commit()
        logger.info(
            "Created %d CodeRecommendation rows for code_analysis %s",
            len(recs),
            code_analysis.id,
        )
        return recs
