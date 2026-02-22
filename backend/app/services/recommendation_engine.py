"""Deterministic gap analysis engine for generating evidence-backed recommendations.

Compares per-criterion user scores against competitor category averages and
research-backed benchmarks. Produces prioritized AuditRecommendation records
with evidence, competitor comparison data, and code snippets.

Also provides content gap identification (queries where competitors are mentioned
but user is not) and Markdown fix plan export.

Not LLM-based: all gap analysis logic is deterministic. Only sentiment
classification (separate service) uses LLM calls.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy.orm import Session

from app.models.audit import Audit
from app.models.audit_query import AuditQuery
from app.models.audit_recommendation import AuditRecommendation
from app.models.brand_mention import BrandMention
from app.models.competitor import CompetitorAudit, DiscoveredCompetitor
from app.models.criterion_result import CriterionResult
from app.models.engine_response import EngineResponse
from app.models.mention_sentiment import MentionSentiment
from app.models.page_score import PageScore


# ---------------------------------------------------------------------------
# Research benchmarks -- hard-coded from Princeton GEO, BrightEdge, Surfer SEO,
# Frase.io, Ahrefs 75K study, Otterly.ai, and industry research.
# ---------------------------------------------------------------------------
CRITERION_RESEARCH_MAP: dict[str, dict] = {
    "SD3": {
        "impact_pct": 320,
        "impact_label": "3.2x citation rate",
        "evidence_source": "BrightEdge + Frase.io",
        "priority_base": "high",
        "threshold": 60,
    },
    "SD1": {
        "impact_pct": 240,
        "impact_label": "2.3-2.5x in AI Overviews",
        "evidence_source": "BrightEdge",
        "priority_base": "high",
        "threshold": 60,
    },
    "SD7": {
        "impact_pct": 240,
        "impact_label": "2.3-2.5x in AI Overviews",
        "evidence_source": "BrightEdge",
        "priority_base": "high",
        "threshold": 60,
    },
    "CS2": {
        "impact_pct": 140,
        "impact_label": "+40% citations",
        "evidence_source": "Princeton GEO paper",
        "priority_base": "high",
        "threshold": 50,
    },
    "CS10": {
        "impact_pct": 140,
        "impact_label": "+40% visibility",
        "evidence_source": "Princeton GEO paper",
        "priority_base": "high",
        "threshold": 50,
    },
    "CS4": {
        "impact_pct": 410,
        "impact_label": "4.1x AI citations",
        "evidence_source": "Surfer SEO 46M analysis",
        "priority_base": "high",
        "threshold": 40,
    },
    "CS11": {
        "impact_pct": 120,
        "impact_label": "+15-25% boost",
        "evidence_source": "Princeton GEO paper",
        "priority_base": "medium",
        "threshold": 40,
    },
    "CS9": {
        "impact_pct": 320,
        "impact_label": "3.2x more citations",
        "evidence_source": "Industry benchmark",
        "priority_base": "medium",
        "threshold": 50,
    },
    "CS8": {
        "impact_pct": 125,
        "impact_label": "+20-30% visibility",
        "evidence_source": "Princeton GEO paper",
        "priority_base": "medium",
        "threshold": 40,
    },
    "CS1": {
        "impact_pct": 280,
        "impact_label": "2.8x citation rate",
        "evidence_source": "Industry research",
        "priority_base": "high",
        "threshold": 50,
    },
    "C9": {
        "impact_pct": 300,
        "impact_label": "Critical for AI bot access",
        "evidence_source": "Otterly.ai",
        "priority_base": "high",
        "threshold": 40,
    },
    "S8": {
        "impact_pct": 270,
        "impact_label": "2.7x citation probability",
        "evidence_source": "Content cluster research",
        "priority_base": "high",
        "threshold": 40,
    },
    "A3": {
        "impact_pct": 280,
        "impact_label": "2.8x citation likelihood",
        "evidence_source": "Ahrefs 75K study",
        "priority_base": "high",
        "threshold": 30,
    },
}

DEFAULT_BENCHMARK: dict = {
    "impact_pct": 105,
    "impact_label": "+5% improvement",
    "evidence_source": "Industry standard",
    "priority_base": "low",
    "threshold": 60,
}


# ---------------------------------------------------------------------------
# Code snippet templates for highest-impact criteria
# ---------------------------------------------------------------------------
CRITERION_SNIPPETS: dict[str, Optional[str]] = {
    "SD3": """{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Your most-asked question here?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Provide a clear, concise answer with supporting data."
      }
    },
    {
      "@type": "Question",
      "name": "Second frequently asked question?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Another detailed answer. Include statistics when possible."
      }
    }
  ]
}""",
    "SD1": """{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Your Brand Name",
  "url": "https://yourdomain.com",
  "logo": "https://yourdomain.com/logo.png",
  "sameAs": [
    "https://twitter.com/yourbrand",
    "https://linkedin.com/company/yourbrand",
    "https://github.com/yourbrand"
  ],
  "description": "One-sentence description of what your organization does."
}""",
    "SD7": """{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "Page Title",
  "description": "Page description",
  "mainEntity": {
    "@type": "Article",
    "headline": "Article Headline",
    "author": {
      "@type": "Person",
      "name": "Author Name"
    },
    "datePublished": "2024-01-01",
    "dateModified": "2024-06-01"
  }
}""",
    "C9": """# SSR Configuration Notes
# AI crawlers (GPTBot, ClaudeBot, PerplexityBot) do NOT execute JavaScript.
# Ensure your site serves fully-rendered HTML via SSR or SSG.

# Next.js: Use getServerSideProps or generateStaticParams
# Nuxt 3: Use server routes and universal rendering (ssr: true)
# SvelteKit: Use +page.server.ts for server-side data loading

# Verify: curl -s https://yourdomain.com | grep '<main>'
# If <main> is empty, your content is client-rendered and invisible to AI.""",
    "CS5": """<!-- FAQ Section Template -->
<section id="faq">
  <h2>Frequently Asked Questions</h2>

  <details>
    <summary>What is [your product/service]?</summary>
    <p>Clear, concise answer with supporting data and statistics.</p>
  </details>

  <details>
    <summary>How does [your product] compare to alternatives?</summary>
    <p>Honest comparison with specific metrics and differentiators.</p>
  </details>

  <details>
    <summary>What are the pricing options?</summary>
    <p>Transparent pricing information with comparison table.</p>
  </details>
</section>""",
    "SD12": """# llms.txt - AI-Readable Site Summary
# Place at: https://yourdomain.com/llms.txt

# Company
> Your Brand Name - One-line description of what you do.

## Products/Services
- Product A: Brief description with key differentiator
- Product B: Brief description with key differentiator

## Key Facts
- Founded: Year
- Headquarters: Location
- Customers: Notable customer names or count

## Links
- Pricing: /pricing
- Documentation: /docs
- Blog: /blog""",
    "CS4": """<!-- Data Table Template for AI Citation Optimization -->
<table>
  <caption>Comparison of [Topic] - Updated [Month Year]</caption>
  <thead>
    <tr>
      <th>Feature</th>
      <th>Your Product</th>
      <th>Competitor A</th>
      <th>Competitor B</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Key Metric 1</td>
      <td>Your value (with source)</td>
      <td>Their value</td>
      <td>Their value</td>
    </tr>
  </tbody>
</table>""",
    "CS2": """<!-- Answer-First Content Pattern -->
<!-- Lead with a direct answer in the first paragraph -->
<article>
  <h1>What is [Topic]?</h1>

  <!-- Direct answer (first 2-3 sentences) -->
  <p><strong>[Topic] is [clear definition].</strong> It works by [brief mechanism].
  According to [source], it achieves [specific metric].</p>

  <!-- Then expand with details, evidence, examples -->
  <h2>How It Works</h2>
  <p>Detailed explanation with statistics...</p>
</article>""",
    "CS10": """<!-- Statistics Integration Pattern -->
<!-- AI engines strongly prefer content with specific data points -->

<!-- Instead of: "Our product is fast" -->
<!-- Write: "Our product processes 10,000 requests/second (benchmarked Jan 2024)" -->

<!-- Include:
  1. Specific numbers (not "many" or "most")
  2. Sources or methodology
  3. Dates for time-sensitive data
  4. Comparisons to known benchmarks
-->""",
    "A3": """<!-- Knowledge Graph Optimization -->
<!-- To increase Knowledge Graph presence: -->

<!-- 1. Claim your Google Knowledge Panel -->
<!-- 2. Ensure Wikipedia/Wikidata entries are accurate -->
<!-- 3. Add Organization schema with sameAs links -->
<!-- 4. Maintain consistent NAP across directories -->

<!-- Verify: Search "your brand name" on Google -->
<!-- If no Knowledge Panel appears, create/update Wikidata entity -->""",
}


def _compute_rec_hash(criterion_id: str, page_url: str) -> str:
    """Stable hash for recommendation identity across re-audits.

    Normalizes URL (lowercase scheme+host, strip trailing slash) and combines
    with criterion_id to produce a 16-char hex digest.
    """
    if page_url:
        parsed = urlparse(page_url.lower())
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    else:
        normalized = "_site_wide_"
    key = f"{criterion_id}|{normalized}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class RecommendationEngine:
    """Deterministic gap analysis engine.

    Reads CriterionResult records per page, compares against CompetitorAudit
    category averages and research benchmarks, and produces prioritized
    AuditRecommendation records.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_recommendations(
        self, audit_id: str, user_id: str
    ) -> list[AuditRecommendation]:
        """Generate page-specific recommendations from scoring data.

        Steps:
            1. Load completed CompetitorAudit records
            2. Compute competitor category averages
            3. Load all scored PageScore records
            4. For each page, generate recommendations from criterion gaps
            5. Generate sentiment-based recommendations for negative mentions
            6. Sort by priority then gap_score descending
            7. Persist and return
        """
        # Load competitor category averages (may be empty)
        comp_audits = (
            self.db.query(CompetitorAudit)
            .filter(CompetitorAudit.parent_audit_id == audit_id)
            .filter(CompetitorAudit.status == "completed")
            .all()
        )
        comp_avgs = self._compute_competitor_averages(comp_audits)
        logger.debug(
            "Audit {}: competitor averages = {}", audit_id, comp_avgs
        )

        # Load all scored pages
        page_scores = (
            self.db.query(PageScore)
            .filter(PageScore.audit_id == audit_id)
            .filter(PageScore.was_scored.is_(True))
            .all()
        )

        recs: list[AuditRecommendation] = []
        for page_score in page_scores:
            page_recs = self._generate_page_recommendations(
                audit_id, user_id, page_score, comp_avgs
            )
            recs.extend(page_recs)

        # Generate negative sentiment recommendations
        sentiment_recs = self._generate_sentiment_recommendations(
            audit_id, user_id
        )
        recs.extend(sentiment_recs)

        # Sort by priority then gap_score descending
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recs.sort(
            key=lambda r: (priority_order.get(r.priority, 2), -r.gap_score)
        )

        for rec in recs:
            self.db.add(rec)
        self.db.flush()

        logger.info(
            "Audit {}: generated {} recommendations ({} high, {} medium, {} low)",
            audit_id,
            len(recs),
            sum(1 for r in recs if r.priority == "high"),
            sum(1 for r in recs if r.priority == "medium"),
            sum(1 for r in recs if r.priority == "low"),
        )
        return recs

    def _compute_competitor_averages(
        self, comp_audits: list[CompetitorAudit]
    ) -> dict[str, Optional[float]]:
        """Average per-category scores across all completed competitor audits."""
        categories = [
            "crawlability",
            "content_structure",
            "structured_data",
            "authority",
        ]
        avgs: dict[str, Optional[float]] = {}
        for cat in categories:
            attr = f"{cat}_avg"
            scores = [
                getattr(ca, attr)
                for ca in comp_audits
                if getattr(ca, attr, None) is not None
            ]
            avgs[cat] = sum(scores) / len(scores) if scores else None
        return avgs

    def _generate_page_recommendations(
        self,
        audit_id: str,
        user_id: str,
        page_score: PageScore,
        comp_avgs: dict[str, Optional[float]],
    ) -> list[AuditRecommendation]:
        """Generate recommendations for a single page based on criterion gaps."""
        criteria = (
            self.db.query(CriterionResult)
            .filter(CriterionResult.page_score_id == page_score.id)
            .filter(CriterionResult.checked.is_(True))
            .all()
        )

        if not criteria:
            logger.debug(
                "Audit {}: no checked criteria for page {}, skipping",
                audit_id,
                page_score.page_url,
            )
            return []

        recs: list[AuditRecommendation] = []
        for criterion in criteria:
            benchmark = CRITERION_RESEARCH_MAP.get(
                criterion.criterion_id, DEFAULT_BENCHMARK
            )
            threshold = benchmark["threshold"]

            # Skip if already above threshold
            if criterion.score >= threshold:
                continue

            # Compute gap score
            comp_avg = comp_avgs.get(criterion.category)
            if comp_avg is not None:
                gap_score = round(comp_avg - criterion.score)
            else:
                gap_score = round(threshold - criterion.score)

            # Skip if gap too small
            if gap_score < 10:
                continue

            priority = self._classify_priority(
                benchmark["impact_pct"], gap_score
            )
            rec_hash = _compute_rec_hash(
                criterion.criterion_id, page_score.page_url
            )

            # Carry over prior done/dismissed status
            status = self._lookup_prior_status(rec_hash, user_id) or "open"

            summary = self._build_summary(
                criterion, benchmark, comp_avg, page_score.page_url
            )
            action_steps = self._build_action_steps(criterion, benchmark)
            code_snippet = CRITERION_SNIPPETS.get(criterion.criterion_id)

            rec = AuditRecommendation(
                audit_id=audit_id,
                page_url=page_score.page_url,
                criterion_id=criterion.criterion_id,
                criterion_name=criterion.criterion_name,
                category=criterion.category,
                priority=priority,
                impact_label=benchmark["impact_label"],
                impact_pct=benchmark["impact_pct"],
                user_score=criterion.score,
                competitor_avg=round(comp_avg) if comp_avg is not None else None,
                gap_score=gap_score,
                summary=summary,
                action_steps=action_steps,
                code_snippet=code_snippet,
                evidence_source=benchmark["evidence_source"],
                recommendation_hash=rec_hash,
                status=status,
            )
            recs.append(rec)

        return recs

    def _generate_sentiment_recommendations(
        self, audit_id: str, user_id: str
    ) -> list[AuditRecommendation]:
        """Create recommendations for negative sentiment mentions."""
        negative_sentiments = (
            self.db.query(MentionSentiment)
            .filter(MentionSentiment.audit_id == audit_id)
            .filter(MentionSentiment.sentiment == "negative")
            .all()
        )

        recs: list[AuditRecommendation] = []
        for sentiment in negative_sentiments:
            rec_hash = _compute_rec_hash(
                f"SENTIMENT_{sentiment.engine}",
                sentiment.context_quote[:50],
            )
            status = self._lookup_prior_status(rec_hash, user_id) or "open"

            # Truncate quote for summary
            quote_preview = sentiment.context_quote[:120]
            if len(sentiment.context_quote) > 120:
                quote_preview += "..."

            summary = (
                f"Negative mention on {sentiment.engine}: "
                f'"{quote_preview}" -- Address the concern raised in this AI response.'
            )
            action_steps = [
                f"Review the AI response context: \"{sentiment.context_quote}\"",
                "Identify the specific concern or criticism mentioned",
                "Update the relevant page content to address the issue",
                "Add supporting data or evidence to counter the negative perception",
                "Re-run audit to verify the mention sentiment has improved",
            ]

            rec = AuditRecommendation(
                audit_id=audit_id,
                page_url=None,  # Site-wide, not page-specific
                criterion_id="SENTIMENT",
                criterion_name="Negative AI Mention",
                category="sentiment",
                priority="high",
                impact_label="Address negative AI perception",
                impact_pct=None,
                user_score=0,
                competitor_avg=None,
                gap_score=100,  # Max gap for negative sentiment
                summary=summary,
                action_steps=action_steps,
                code_snippet=None,
                evidence_source=f"AI engine: {sentiment.engine}",
                recommendation_hash=rec_hash,
                status=status,
            )
            recs.append(rec)

        return recs

    def _classify_priority(self, impact_pct: int, gap_score: int) -> str:
        """Classify recommendation priority.

        HIGH: gap_score >= 50 OR (impact_pct >= 200 AND gap_score >= 30)
        MEDIUM: impact_pct >= 120 AND gap_score >= 20
        LOW: everything else
        """
        if gap_score >= 50 or (impact_pct >= 200 and gap_score >= 30):
            return "high"
        if impact_pct >= 120 and gap_score >= 20:
            return "medium"
        return "low"

    def _lookup_prior_status(
        self, rec_hash: str, user_id: str
    ) -> Optional[str]:
        """Look up previous done/dismissed status for this recommendation hash."""
        result = (
            self.db.query(AuditRecommendation.status)
            .join(Audit, AuditRecommendation.audit_id == Audit.id)
            .filter(Audit.user_id == user_id)
            .filter(AuditRecommendation.recommendation_hash == rec_hash)
            .filter(AuditRecommendation.status.in_(["done", "dismissed"]))
            .order_by(AuditRecommendation.created_at.desc())
            .first()
        )
        return result[0] if result else None

    def _build_summary(
        self,
        criterion: CriterionResult,
        benchmark: dict,
        comp_avg: Optional[float],
        page_url: str,
    ) -> str:
        """Build user-facing one-liner summary for a recommendation."""
        # Extract path from URL for display
        parsed = urlparse(page_url)
        path = parsed.path or "/"

        parts = [f"{criterion.criterion_name} -- {path}: {criterion.human_summary}"]

        if comp_avg is not None:
            parts.append(
                f"Your score: {criterion.score}, competitor avg: {round(comp_avg)}"
            )

        parts.append(
            f"{benchmark['impact_label']} ({benchmark['evidence_source']})"
        )

        return ". ".join(parts)

    def _build_action_steps(
        self, criterion: CriterionResult, benchmark: dict
    ) -> list[str]:
        """Build list of action step strings from criterion data."""
        steps = []

        # Start with the technical detail from criterion
        if criterion.technical_detail:
            steps.append(criterion.technical_detail)

        # Add research-specific guidance
        steps.append(
            f"Target impact: {benchmark['impact_label']} "
            f"(source: {benchmark['evidence_source']})"
        )

        # Add validation step
        steps.append(
            "Re-run audit after implementing changes to verify improvement"
        )

        return steps

    # ------------------------------------------------------------------
    # Content gap identification
    # ------------------------------------------------------------------

    def identify_content_gaps(self, audit_id: str) -> list[dict]:
        """Find queries where competitors appear in AI responses but user does not.

        Algorithm:
            1. Load all AuditQuery records for this audit
            2. Find queries where user brand was mentioned (BrandMention join chain)
            3. Load DiscoveredCompetitor records (non-user-brand)
            4. Build query_id -> [competitor names] index from queries_mentioned_in
            5. Gap = queries where competitor appears but user does not
            6. Generate template-based mini brief per gap

        Returns:
            list of dicts with query_id, query_text, competitors_mentioned, brief
        """
        # 1. All queries for this audit
        all_queries = {
            str(q.id): q.query_text
            for q in self.db.query(AuditQuery)
            .filter(AuditQuery.audit_id == audit_id)
            .all()
        }

        if not all_queries:
            return []

        # 2. Queries where user brand was mentioned
        user_mentioned_rows = (
            self.db.query(AuditQuery.id)
            .join(EngineResponse, EngineResponse.audit_query_id == AuditQuery.id)
            .join(BrandMention, BrandMention.engine_response_id == EngineResponse.id)
            .filter(AuditQuery.audit_id == audit_id)
            .distinct()
            .all()
        )
        user_mentioned_query_ids = {str(row[0]) for row in user_mentioned_rows}

        # 3. Load non-user-brand competitors
        competitors = (
            self.db.query(DiscoveredCompetitor)
            .filter(DiscoveredCompetitor.audit_id == audit_id)
            .filter(DiscoveredCompetitor.is_user_brand.is_(False))
            .all()
        )

        # 4. Build query_id -> [competitor names] index
        query_to_competitors: dict[str, list[str]] = {}
        for comp in competitors:
            for qid in comp.queries_mentioned_in or []:
                query_to_competitors.setdefault(str(qid), []).append(
                    comp.entity_name
                )

        # 5. Find gaps: competitor mentioned, user not mentioned
        gaps: list[dict] = []
        for query_id, query_text in all_queries.items():
            if (
                query_id not in user_mentioned_query_ids
                and query_id in query_to_competitors
            ):
                competitors_mentioned = query_to_competitors[query_id]
                brief = self._template_brief(query_text, competitors_mentioned)
                gaps.append(
                    {
                        "query_id": query_id,
                        "query_text": query_text,
                        "competitors_mentioned": competitors_mentioned,
                        "brief": brief,
                    }
                )

        logger.info(
            "Audit {}: identified {} content gaps from {} queries",
            audit_id,
            len(gaps),
            len(all_queries),
        )
        return gaps

    def save_content_gaps(self, audit_id: str, gaps: list[dict]) -> None:
        """Persist content gaps to the Audit record's JSONB column."""
        audit = self.db.query(Audit).filter(Audit.id == audit_id).first()
        if audit:
            audit.content_gaps = gaps
            self.db.flush()

    def _template_brief(
        self, query_text: str, competitors: list[str]
    ) -> dict:
        """Generate a template-based mini content brief for a content gap.

        Returns:
            dict with title, key_points, and target_queries
        """
        return {
            "title": f"Complete Guide: {query_text.rstrip('?').capitalize()}",
            "key_points": [
                f"Answer the question: {query_text}",
                "Include statistics and data tables to support claims "
                "(+40% visibility, 4.1x citations)",
                "Add FAQPage schema with the most common related questions "
                "(+28% AI citations)",
                "Cite authoritative sources for E-E-A-T signals",
                f"Address what {', '.join(competitors[:3])} cover that you "
                "currently miss",
            ],
            "target_queries": [query_text],
        }

    # ------------------------------------------------------------------
    # Markdown fix plan export
    # ------------------------------------------------------------------

    def export_markdown(
        self, audit_id: str, page_url: str | None = None
    ) -> str:
        """Generate a structured Markdown fix plan from audit recommendations.

        The format is inspired by GSD PLAN.md structure: clear tasks, evidence,
        code changes, and acceptance criteria.

        Args:
            audit_id: The audit UUID.
            page_url: Optional filter for single-page export.

        Returns:
            Complete Markdown string.
        """
        # Load audit for domain name
        audit = self.db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            return "# Error: Audit not found"

        # Load recommendations
        query = self.db.query(AuditRecommendation).filter(
            AuditRecommendation.audit_id == audit_id
        )
        if page_url:
            query = query.filter(AuditRecommendation.page_url == page_url)

        recs = query.order_by(
            AuditRecommendation.priority,
            AuditRecommendation.gap_score.desc(),
        ).all()

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        domain = audit.domain

        # Count by priority
        high_count = sum(1 for r in recs if r.priority == "high")
        medium_count = sum(1 for r in recs if r.priority == "medium")
        low_count = sum(1 for r in recs if r.priority == "low")

        lines: list[str] = []

        # Header
        if page_url:
            parsed = urlparse(page_url)
            path_display = parsed.path or "/"
            lines.append(f"# GEO Fix Plan: {domain} ({path_display}) - {today}")
        else:
            lines.append(f"# GEO Fix Plan: {domain} - {today}")

        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(
            f"{high_count} high-priority fixes | "
            f"{medium_count} medium | {low_count} low"
        )
        if recs:
            max_impact_recs = [
                r for r in recs if r.impact_pct is not None
            ]
            if max_impact_recs:
                max_impact = max(r.impact_pct for r in max_impact_recs)
                lines.append(
                    f"Addressing these fixes is estimated to improve "
                    f"your AI citation rate by up to {max_impact}%."
                )
        lines.append("")

        if not recs:
            lines.append("No recommendations found for this audit.")
            return "\n".join(lines)

        # Group by priority if full site, or by page then priority
        if page_url:
            # Single page: group by priority
            self._append_priority_groups(lines, recs)
        else:
            # Full site: group by page then priority
            pages: dict[str | None, list[AuditRecommendation]] = {}
            for rec in recs:
                pages.setdefault(rec.page_url, []).append(rec)

            for page, page_recs in pages.items():
                if page:
                    parsed = urlparse(page)
                    lines.append(f"## Page: {parsed.path or '/'}")
                else:
                    lines.append("## Site-wide Recommendations")
                lines.append("")
                self._append_priority_groups(lines, page_recs)

        # Content gaps section
        content_gaps = audit.content_gaps
        if content_gaps:
            lines.append("## Content Gaps")
            lines.append("")
            lines.append(
                "Topics where competitors are mentioned but you are not:"
            )
            lines.append("")

            for gap in content_gaps:
                query_text = gap.get("query_text", "Unknown topic")
                competitors_mentioned = gap.get("competitors_mentioned", [])
                brief = gap.get("brief", {})

                lines.append(f"### {query_text}")
                lines.append(
                    f"**Competitors mentioned:** "
                    f"{', '.join(competitors_mentioned)}"
                )
                if brief:
                    lines.append(
                        f"**Suggested content:** {brief.get('title', 'N/A')}"
                    )
                    key_points = brief.get("key_points", [])
                    if key_points:
                        lines.append("**Key points to cover:**")
                        for point in key_points:
                            lines.append(f"- {point}")
                lines.append("")

        return "\n".join(lines)

    def _append_priority_groups(
        self,
        lines: list[str],
        recs: list[AuditRecommendation],
    ) -> None:
        """Append recommendations grouped by priority to the lines list."""
        priority_labels = {
            "high": "High Priority Fixes",
            "medium": "Medium Priority Fixes",
            "low": "Low Priority Fixes",
        }

        fix_num = 1
        for priority in ("high", "medium", "low"):
            priority_recs = [r for r in recs if r.priority == priority]
            if not priority_recs:
                continue

            lines.append(f"### {priority_labels[priority]}")
            lines.append("")

            for rec in priority_recs:
                page_display = rec.page_url or "Site-wide"
                if rec.page_url:
                    parsed = urlparse(rec.page_url)
                    page_display = parsed.path or "/"

                lines.append(
                    f"#### Fix {fix_num}: {rec.criterion_name} "
                    f"-- {page_display}"
                )
                lines.append(
                    f"**Evidence:** {rec.impact_label} "
                    f"({rec.evidence_source})"
                )

                comp_avg_display = (
                    f"{rec.competitor_avg}" if rec.competitor_avg is not None
                    else "N/A"
                )
                lines.append(
                    f"**Your score:** {rec.user_score}/100 | "
                    f"**Competitor avg:** {comp_avg_display}/100 | "
                    f"**Gap:** {rec.gap_score} points"
                )
                lines.append(f"**Status:** {rec.status}")
                lines.append("")

                # Action steps
                if rec.action_steps:
                    lines.append("**Steps:**")
                    for i, step in enumerate(rec.action_steps, 1):
                        lines.append(f"{i}. {step}")
                    lines.append("")

                # Code snippet
                if rec.code_snippet:
                    lines.append("```")
                    lines.append(rec.code_snippet)
                    lines.append("```")
                    lines.append("")

                # Acceptance criteria
                threshold = CRITERION_RESEARCH_MAP.get(
                    rec.criterion_id, DEFAULT_BENCHMARK
                ).get("threshold", 60)
                lines.append("**Acceptance criteria:**")
                lines.append("- [ ] Re-run audit to verify improvement")
                lines.append(
                    f"- [ ] {rec.criterion_name} score > {threshold}"
                )
                lines.append("")
                lines.append("---")
                lines.append("")

                fix_num += 1
