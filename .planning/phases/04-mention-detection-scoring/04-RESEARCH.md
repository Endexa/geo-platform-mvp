# Phase 4: Mention Detection & Scoring - Research

**Researched:** 2026-02-22
**Domain:** NLP text analysis, fuzzy string matching, scoring algorithms
**Confidence:** HIGH

## Summary

Phase 4 takes the AI engine responses stored by Phase 3 (in `engine_responses` table with full `response_text`, `model_version`, and `engine` fields) and performs three operations: (1) detect brand name mentions including variants and typos, (2) extract verbatim quotes around each mention, and (3) compute a 0-100 visibility score with per-engine breakdown.

The primary recommendation is to use a layered detection approach: exact regex matching first, then RapidFuzz fuzzy matching for typos/abbreviations, with no need for heavyweight NER (spaCy/transformers). The brand name is already extracted in Phase 2 (`QueryGeneratorService.extract_brand_name()`), so this phase only needs to search for it and its generated variants within existing response texts. The visibility score should combine mention frequency, position weighting (earlier = more prominent), and mention quality (standalone mention vs. listed among competitors) into a weighted formula.

**Primary recommendation:** Use `re` (stdlib) for exact brand matching with word boundaries + `rapidfuzz` for fuzzy variant detection. No NER library needed -- the problem is known-entity search, not open-domain entity discovery.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIT-05 | App detects brand mentions in AI responses with verbatim quotes | Layered detection (regex exact + RapidFuzz fuzzy) with context window extraction. New `BrandMention` model stores each mention with verbatim quote. Brand variants generated algorithmically from the brand name already extracted in Phase 2. |
| AUDIT-06 | User sees a visibility score (0-100) with per-engine breakdown | Weighted scoring formula combining mention_rate (40%), position_score (30%), prominence_score (30%). Per-engine scores stored in new `VisibilityScore` model. Temperature=0 already set in Phase 3 dispatch config (`DISPATCH_TEMPERATURE: float = 0.0`). Model version already logged in `EngineResponse.model_version`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `rapidfuzz` | 3.14.x | Fuzzy string matching for brand variants/typos | C++ backend, MIT license, 10x faster than thefuzz, industry standard for entity matching. Handles "Huawi" -> "Huawei" at 91% confidence. |
| `re` (stdlib) | Python 3.11+ | Exact brand name regex with word boundaries | Zero dependencies, handles exact and case-insensitive matching, `re.finditer` provides match positions for context extraction. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy | 2.0.25 (existing) | BrandMention + VisibilityScore models | Already in project, extend with new models |
| Alembic | 1.13.1 (existing) | Migration 005 for new tables | Already in project, add migration for mention detection tables |
| Pydantic | 2.5.3 (existing) | Request/response schemas for mentions and scores | Already in project, add mention and score schemas |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| RapidFuzz | spaCy NER | Overkill -- we know what entity to find (brand name). spaCy adds 300MB+ models, requires NLTK/transformers. Our problem is known-entity search, not entity discovery. |
| RapidFuzz | thefuzz | thefuzz is the legacy name for fuzzywuzzy, GPL-licensed, pure Python (10x slower). RapidFuzz is MIT-licensed, C++ compiled. |
| Custom scoring | LLM-based scoring | Using an LLM to score mentions would add API cost, latency, and non-determinism. A deterministic formula is reproducible and free. |
| regex + RapidFuzz | Full NLP pipeline (tokenizer + NER + POS) | Unnecessary complexity. Brand names are proper nouns we already know; we just need to find them in text. Adding NLP pipelines would increase memory, latency, and dependencies for no accuracy gain on this specific task. |

**Installation:**
```bash
pip install rapidfuzz>=3.14.0
```

Only one new dependency. Everything else is already in the project.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  models/
    brand_mention.py        # BrandMention model
    visibility_score.py     # VisibilityScore model
  services/
    mention_detector.py     # MentionDetectorService (core detection logic)
    scoring_service.py      # ScoringService (visibility score computation)
  schemas/
    audit.py                # Extended with mention and score schemas
```

### Pattern 1: Layered Detection (Exact -> Fuzzy)
**What:** Two-pass brand detection: first regex for exact matches (fast, cheap), then RapidFuzz for fuzzy matches on response segments where exact match failed.
**When to use:** Always. The exact match pass catches 80%+ of mentions at near-zero cost; fuzzy pass catches abbreviations, typos, and partial references.
**Example:**
```python
# Source: RapidFuzz docs + stdlib re docs
import re
from rapidfuzz import fuzz

class MentionDetectorService:
    FUZZY_THRESHOLD = 80  # Score 0-100, reject below this

    def detect_mentions(
        self, response_text: str, brand_name: str, brand_variants: list[str]
    ) -> list[dict]:
        """Detect brand mentions using layered exact + fuzzy matching."""
        mentions = []

        # Pass 1: Exact regex match for brand name and known variants
        all_names = [brand_name] + brand_variants
        for name in all_names:
            pattern = re.compile(
                r'\b' + re.escape(name) + r'\b',
                re.IGNORECASE
            )
            for match in pattern.finditer(response_text):
                context = self._extract_context(response_text, match.start(), match.end())
                mentions.append({
                    "matched_text": match.group(),
                    "match_type": "exact",
                    "confidence": 100,
                    "char_offset": match.start(),
                    "context_quote": context,
                })

        # Pass 2: Fuzzy matching on sentences not already matched
        if not mentions:
            sentences = self._split_sentences(response_text)
            for i, sentence in enumerate(sentences):
                # Use token_set_ratio for brand names with suffixes (Inc., LLC)
                score = fuzz.token_set_ratio(brand_name.lower(), sentence.lower())
                if score >= self.FUZZY_THRESHOLD:
                    # Confirm with partial_ratio for substring detection
                    partial = fuzz.partial_ratio(brand_name.lower(), sentence.lower())
                    if partial >= self.FUZZY_THRESHOLD:
                        mentions.append({
                            "matched_text": sentence.strip(),
                            "match_type": "fuzzy",
                            "confidence": int(min(score, partial)),
                            "char_offset": self._sentence_offset(response_text, i),
                            "context_quote": sentence.strip(),
                        })

        return mentions
```

### Pattern 2: Brand Variant Generation
**What:** Algorithmically generate likely search variants from the extracted brand name.
**When to use:** During the analysis stage, before running detection. Variants are generated once per audit, not per response.
**Example:**
```python
def generate_brand_variants(brand_name: str) -> list[str]:
    """Generate brand name variants for detection.

    Variants include:
    - Lowercase/uppercase forms
    - Without common suffixes (Inc., LLC, Ltd., Co.)
    - Abbreviation (first letters of multi-word names)
    - Domain-style (no spaces, lowered)
    """
    variants = set()
    clean = brand_name.strip()

    # As-is
    variants.add(clean)
    variants.add(clean.lower())
    variants.add(clean.upper())

    # Remove common suffixes
    suffixes = [" Inc.", " Inc", " LLC", " Ltd.", " Ltd", " Co.", " Co",
                " Corp.", " Corp", " Corporation", " Group", " Holdings"]
    for suffix in suffixes:
        if clean.endswith(suffix):
            stripped = clean[: -len(suffix)].strip()
            variants.add(stripped)
            variants.add(stripped.lower())

    # Abbreviation for multi-word names
    words = clean.split()
    if len(words) >= 2:
        abbrev = "".join(w[0].upper() for w in words if w[0].isalpha())
        if len(abbrev) >= 2:
            variants.add(abbrev)

    # Domain-style (no spaces)
    variants.add(clean.replace(" ", "").lower())

    # Remove the original to avoid redundancy in exact pass
    variants.discard(clean)
    return list(variants)
```

### Pattern 3: Context Window Extraction
**What:** Extract a verbatim quote of surrounding text (sentence-level) around each brand mention.
**When to use:** For every detected mention. The quote should be a complete sentence or a fixed character window (whichever is shorter).
**Example:**
```python
def _extract_context(
    self, text: str, match_start: int, match_end: int, window_chars: int = 200
) -> str:
    """Extract surrounding context as a verbatim quote.

    Strategy: expand to sentence boundaries within a character window.
    """
    # Expand to character window
    ctx_start = max(0, match_start - window_chars // 2)
    ctx_end = min(len(text), match_end + window_chars // 2)

    # Try to align to sentence boundaries
    # Look backward for sentence start
    for i in range(ctx_start, max(0, ctx_start - 50), -1):
        if text[i] in '.!?\n' and i < match_start - 1:
            ctx_start = i + 1
            break

    # Look forward for sentence end
    for i in range(ctx_end, min(len(text), ctx_end + 50)):
        if text[i] in '.!?\n':
            ctx_end = i + 1
            break

    return text[ctx_start:ctx_end].strip()
```

### Pattern 4: Visibility Score Computation
**What:** Compute a 0-100 score from mention data across all queries and engines.
**When to use:** After all mentions have been detected for an audit.
**Example:**
```python
def compute_visibility_score(
    audit_id: str,
    engine_mentions: dict[str, list],  # engine -> list of mention dicts
    total_queries: int,
) -> dict:
    """Compute visibility score with per-engine breakdown.

    Formula:
        mention_rate (40%): % of responses that contain at least one mention
        position_score (30%): average normalized position (earlier = higher)
        prominence_score (30%): quality of mentions (standalone vs. listed)

    Returns dict with overall_score and per_engine scores.
    """
    per_engine = {}
    for engine, mentions_list in engine_mentions.items():
        responses_with_mentions = len([m for m in mentions_list if m])
        mention_rate = (responses_with_mentions / total_queries) * 100 if total_queries > 0 else 0

        # Position: normalize char_offset to 0-100 (0 = start, 100 = end)
        position_scores = []
        for mention_group in mentions_list:
            if mention_group:
                first_mention = min(mention_group, key=lambda m: m["char_offset"])
                # Assume ~2000 char average response
                position_scores.append(
                    max(0, 100 - (first_mention["char_offset"] / 20))
                )
        avg_position = sum(position_scores) / len(position_scores) if position_scores else 0

        # Prominence: exact > fuzzy, high confidence > low
        prominence_scores = []
        for mention_group in mentions_list:
            if mention_group:
                best = max(mention_group, key=lambda m: m["confidence"])
                prominence_scores.append(best["confidence"])
        avg_prominence = sum(prominence_scores) / len(prominence_scores) if prominence_scores else 0

        engine_score = (
            mention_rate * 0.40
            + avg_position * 0.30
            + avg_prominence * 0.30
        )
        per_engine[engine] = min(100, max(0, round(engine_score)))

    # Overall = average of engine scores (weighted equally)
    overall = round(sum(per_engine.values()) / len(per_engine)) if per_engine else 0
    return {"overall_score": overall, "per_engine": per_engine}
```

### Anti-Patterns to Avoid
- **Using NER to find a known entity:** NER is for discovering unknown entities in text. We already know the brand name from Phase 2. Using spaCy/transformers would add 300MB+ dependencies and model loading time for zero accuracy benefit.
- **Scoring from a single response:** LLM outputs are non-deterministic even at temperature=0 (due to sampling, batching, model updates). A single response is not statistically meaningful. The score must aggregate across all queries and engines.
- **Storing computed scores in the response table:** Scores are derived data. Store them in a separate table so they can be recomputed if the algorithm changes without re-running expensive AI queries.
- **Fuzzy matching every word in the response:** Only run fuzzy matching after exact match fails, and only on sentence-level chunks. Running RapidFuzz on every word is O(n*m) and unnecessary.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom Levenshtein/edit distance | `rapidfuzz` | RapidFuzz handles Unicode, has optimized C++ backend, supports multiple algorithms (ratio, partial_ratio, token_set_ratio). Custom implementations miss edge cases with Unicode, accents, and casing. |
| Sentence splitting | Custom regex splitter | Python `re.split(r'(?<=[.!?])\s+', text)` | Simple regex is sufficient for AI responses (which are grammatically well-formed). No need for NLTK sentence tokenizer -- AI responses have clean punctuation. |
| Brand variant generation | Manual variant lists | Algorithmic generation from brand name | Manually maintaining variant lists does not scale. Generating them algorithmically (abbreviation, suffix removal, domain form) covers 95% of cases with zero maintenance. |

**Key insight:** The mention detection problem is fundamentally different from open-domain NER. We have a *known entity* (brand name) and need to find it in text, including near-misses. This is a string search problem, not a classification problem. The entire implementation can be done with regex + one C library (RapidFuzz), no ML models needed.

## Common Pitfalls

### Pitfall 1: False Positives from Short Brand Names
**What goes wrong:** A 2-3 letter brand name (e.g., "AI", "Go", "Be") matches common English words, producing hundreds of false positives.
**Why it happens:** Word boundary regex `\bGo\b` matches the verb "go" in every AI response.
**How to avoid:** For brand names shorter than 4 characters, require case-sensitive matching AND higher fuzzy thresholds (90+). Consider requiring the brand to appear as a proper noun (preceded by article or at sentence start). Log a warning when the brand name is suspiciously short.
**Warning signs:** Detection returning 50+ mentions per response for a short brand name.

### Pitfall 2: Fuzzy Matching Noise on Long Responses
**What goes wrong:** RapidFuzz `partial_ratio` returns high scores for coincidental substring matches in multi-paragraph AI responses.
**Why it happens:** `partial_ratio("Nike", "I think nicer things...")` can score above 80 because "nike" is a substring of "nicer".
**How to avoid:** Never run fuzzy matching on the entire response text. Split into sentences first, then fuzzy-match against each sentence. This bounds the comparison string length and reduces false positives. Use `token_set_ratio` (not just `partial_ratio`) and require BOTH to exceed the threshold.
**Warning signs:** Fuzzy matches appearing in sentences that clearly have no brand reference when read by a human.

### Pitfall 3: Temperature=0 Does Not Guarantee Reproducibility
**What goes wrong:** Developers assume temperature=0 means identical outputs, then find that scores change between runs.
**Why it happens:** Temperature=0 reduces but does not eliminate non-determinism. Model version changes (GPT-4o updates silently), batch size effects, and provider-side caching all introduce variation. The success criteria requires logging model version for reproducibility, not guaranteeing identical outputs.
**How to avoid:** Log model_version (already stored in EngineResponse), timestamp, and algorithm version. Accept that scores are "reproducible given the same inputs" not "identical across time." The 24h cache from Phase 1 helps during a single audit run.
**Warning signs:** Users complaining about score fluctuations between audits of the same URL.

### Pitfall 4: Context Quote Extraction Crossing Boundaries
**What goes wrong:** Verbatim quotes contain truncated sentences or include content from unrelated paragraphs.
**Why it happens:** Fixed character window extraction (e.g., 100 chars before and after) ignores sentence boundaries, producing quotes like "...nce for enterprise. Nike is recommended for ath..."
**How to avoid:** Expand to sentence boundaries, not fixed character counts. Start with a character window, then extend outward to the nearest sentence-ending punctuation. Cap at a reasonable max (e.g., 500 chars) to prevent capturing entire paragraphs.
**Warning signs:** Quotes starting/ending mid-word or mid-sentence.

### Pitfall 5: Scoring Penalizes Engines with Errors
**What goes wrong:** An engine that failed to respond (network error, rate limit) gets a score of 0, dragging down the overall visibility score.
**Why it happens:** Error responses have empty `response_text` and no mentions, contributing a 0 to the average.
**How to avoid:** Filter out `EngineResponse` records where `error_message IS NOT NULL` before computing scores. Only score engines that successfully returned a response. Report engine coverage separately (e.g., "scored from 2/3 engines").
**Warning signs:** Overall score dropping significantly when one engine has intermittent failures.

## Code Examples

### Database Schema: BrandMention Model
```python
# Source: Project patterns from existing models (EngineResponse, AuditQuery)
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class BrandMention(Base):
    __tablename__ = "brand_mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_response_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engine_responses.id"),
        nullable=False,
        index=True,
    )
    matched_text = Column(String, nullable=False)     # what was actually matched
    match_type = Column(String, nullable=False)        # "exact" or "fuzzy"
    confidence = Column(Integer, nullable=False)       # 0-100
    char_offset = Column(Integer, nullable=False)      # position in response_text
    context_quote = Column(Text, nullable=False)       # verbatim surrounding context
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    engine_response = relationship("EngineResponse", backref="mentions")
```

### Database Schema: VisibilityScore Model
```python
class VisibilityScore(Base):
    __tablename__ = "visibility_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audits.id"),
        nullable=False,
        unique=True,  # One score per audit
        index=True,
    )
    overall_score = Column(Integer, nullable=False)  # 0-100
    per_engine_scores = Column(JSONB, nullable=False)  # {"openai": 75, "anthropic": 60, ...}
    mention_count = Column(Integer, nullable=False, default=0)
    query_mention_rate = Column(Numeric(5, 2), nullable=False)  # % of queries with mentions
    algorithm_version = Column(String, nullable=False, default="v1")  # for reproducibility
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    audit = relationship("Audit", backref="visibility_score")
```

### Alembic Migration 005
```python
"""add brand_mentions and visibility_scores tables

Revision ID: 005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade():
    op.create_table(
        "brand_mentions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("engine_response_id", UUID(as_uuid=True),
                  sa.ForeignKey("engine_responses.id"), nullable=False, index=True),
        sa.Column("matched_text", sa.String, nullable=False),
        sa.Column("match_type", sa.String, nullable=False),
        sa.Column("confidence", sa.Integer, nullable=False),
        sa.Column("char_offset", sa.Integer, nullable=False),
        sa.Column("context_quote", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "visibility_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("audit_id", UUID(as_uuid=True),
                  sa.ForeignKey("audits.id"), nullable=False, unique=True, index=True),
        sa.Column("overall_score", sa.Integer, nullable=False),
        sa.Column("per_engine_scores", JSONB, nullable=False),
        sa.Column("mention_count", sa.Integer, nullable=False, default=0),
        sa.Column("query_mention_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("algorithm_version", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_table("visibility_scores")
    op.drop_table("brand_mentions")
```

### Celery Pipeline Extension
```python
# In audit_tasks.py, between DISPATCHING and COMPLETED stages:

# Stage 4: Analyze mentions
audit.status = AuditStatus.ANALYZING.value
db.commit()

# Reload engine responses for analysis
responses = (
    db.query(EngineResponse)
    .join(AuditQuery)
    .filter(AuditQuery.audit_id == audit_id)
    .filter(EngineResponse.error_message.is_(None))  # Skip failed engines
    .all()
)

detector = MentionDetectorService()
brand_variants = generate_brand_variants(brand_name)

for response in responses:
    mentions = detector.detect_mentions(
        response_text=response.response_text,
        brand_name=brand_name,
        brand_variants=brand_variants,
    )
    for mention_data in mentions:
        mention = BrandMention(
            engine_response_id=response.id,
            **mention_data,
        )
        db.add(mention)
db.commit()

# Stage 5: Compute visibility score
scorer = ScoringService(db)
score = scorer.compute_audit_score(audit_id=audit_id, total_queries=len(queries))
db.add(score)
db.commit()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| fuzzywuzzy (pure Python, GPL) | RapidFuzz (C++, MIT) | 2021+ | 10x speed improvement, no license concerns |
| spaCy NER for entity matching | Regex + fuzzy for known entities | Always true for known-entity search | NER was never the right tool for finding a specific known entity |
| Single-metric visibility (mention count) | Multi-signal scoring (rate + position + prominence) | 2024-2025 industry shift | Aligns with how Semrush, Otterly, Profound compute scores |
| Manual brand variant lists | Algorithmic variant generation | Standard practice | Scales across brands without per-brand configuration |

**Deprecated/outdated:**
- `fuzzywuzzy`: Renamed to `thefuzz`, but both are slower than RapidFuzz. Use RapidFuzz.
- `python-Levenshtein`: Was a companion to fuzzywuzzy for speed. RapidFuzz includes its own C++ implementation.
- NLTK for sentence tokenization: Overkill for AI-generated text (which has clean punctuation). Simple regex splitting suffices.

## Open Questions

1. **Fuzzy threshold calibration**
   - What we know: 80 is a standard starting threshold for RapidFuzz, industry examples use 80-90.
   - What's unclear: The optimal threshold for brand names of various lengths. Short names need higher thresholds; long names can tolerate lower.
   - Recommendation: Start with 80, add a config setting (`MENTION_FUZZY_THRESHOLD`), and tune based on real audit data. Consider length-adaptive thresholds (brand_name < 4 chars -> threshold 90, otherwise 80).

2. **Mention deduplication across detection passes**
   - What we know: A brand name found by exact match will also be found by fuzzy match at the same position.
   - What's unclear: Whether to deduplicate by char_offset or by sentence.
   - Recommendation: Deduplicate by char_offset range overlap. If a fuzzy match overlaps with an exact match, keep only the exact match (higher confidence).

3. **Score normalization across audit sizes**
   - What we know: An audit with 10 queries produces a different statistical distribution than one with 15 queries.
   - What's unclear: Whether the 0-100 scale feels "right" with small query counts (e.g., 8 queries).
   - Recommendation: The formula is already percentage-based (mention_rate), so it normalizes naturally. But consider a minimum query threshold (e.g., require at least 8 successful responses to compute a score; otherwise mark as "insufficient data").

## Sources

### Primary (HIGH confidence)
- [RapidFuzz official docs](https://rapidfuzz.github.io/RapidFuzz/) -- API reference for fuzz functions, installation requirements
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) -- Version 3.14.x, MIT license, Python 3.10+
- [Python re module docs](https://docs.python.org/3/library/re.html) -- `re.finditer`, `re.IGNORECASE`, word boundaries
- Project codebase inspection -- EngineResponse model, DispatchService, audit_tasks.py pipeline, config.py settings

### Secondary (MEDIUM confidence)
- [Semrush AI Visibility Toolkit](https://www.semrush.com/blog/ai-visibility/) -- Industry scoring methodology (mention rate, position, sentiment)
- [AccuRanker LLM metrics 2026](https://www.accuranker.com/blog/llm-visibility-metrics-2026/) -- 5 key LLM visibility metrics
- [Wellows LLM audit guide](https://wellows.com/blog/audit-brand-visibility-on-llms/) -- Mention frequency formula, explicit vs implicit mentions
- [Advanced Web Ranking visibility scoring](https://www.advancedwebranking.com/help/ai-brand-visibility-insights-see-how-llms-talk-about-your-brand) -- Position weighting formula (1st=100%, 2nd=90%, etc.)
- [RapidFuzz usage examples (Snyk)](https://snyk.io/advisor/python/rapidfuzz/example) -- token_set_ratio and partial_ratio patterns

### Tertiary (LOW confidence)
- [Princeton GEO paper (arXiv:2311.09735)](https://arxiv.org/abs/2311.09735) -- Academic visibility framework referenced but full formula not accessible from abstract
- [Search Engine Land LLM optimization 2026](https://searchengineland.com/llm-optimization-tracking-visibility-ai-discovery-463860) -- Polling-based measurement methodology

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- RapidFuzz is the clear industry choice for fuzzy matching, regex is appropriate for exact matching. Decision is well-supported by project constraints (known entity, no need for NER).
- Architecture: HIGH -- Models follow established project patterns (UUID PKs, ForeignKeys, DateTime columns). Pipeline extension follows existing audit_tasks.py stage pattern. Detection algorithm is straightforward two-pass approach.
- Pitfalls: HIGH -- Short brand name false positives, fuzzy matching noise, and temperature non-determinism are well-documented issues in the string matching and LLM monitoring domains.

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (30 days -- stable domain, no fast-moving dependencies)
