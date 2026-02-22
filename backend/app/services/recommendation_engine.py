"""Deterministic gap analysis engine for generating evidence-backed recommendations.

Compares per-criterion user scores against competitor category averages and
research-backed benchmarks. Produces prioritized AuditRecommendation records
with evidence, competitor comparison data, and code snippets.

Not LLM-based: all gap analysis logic is deterministic. Only sentiment
classification (separate service) uses LLM calls.
"""

import hashlib
from typing import Optional
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy.orm import Session

from app.models.audit import Audit
from app.models.audit_recommendation import AuditRecommendation
from app.models.competitor import CompetitorAudit
from app.models.criterion_result import CriterionResult
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
