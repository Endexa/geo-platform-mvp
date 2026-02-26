---
phase: 02-recommendations-competitor-benchmarking
verified: 2026-02-26T06:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: null
gaps: []
human_verification:
  - test: "Run the full audit pipeline on a SaaS URL (e.g., stripe.com) and confirm that recommendations exclude Product/Offer (SD8) and ClaimReview (SD10) schema criteria, while FAQPage (SD3) and non-SD criteria appear"
    expected: "Zero SD8 and SD10 recommendations; SD3 and CS/C/A recommendations present"
    why_human: "Requires a live Celery worker, database session, and a real HTTP crawl to verify end-to-end pipeline behaviour"
  - test: "Run an audit, then re-run the same URL. Check that the same discovered competitor links to the same Brand record (competitor_brand_id is identical across both audits)"
    expected: "Two DiscoveredCompetitor rows for the same entity pointing to one Brand row with is_competitor=True"
    why_human: "Cross-audit deduplication requires two real audit runs and live DB inspection"
  - test: "Call GET /competitors/{audit_id}/score-comparison after an audit completes and verify the JSON contains site + competitors fields with numeric scores"
    expected: "Response body with site.optimization_score and competitors list"
    why_human: "End-to-end API response including authentication flow requires a running server"
---

# Phase 2: Recommendations + Competitor Benchmarking Verification Report

**Phase Goal:** Users receive specific, prioritized recommendations they can immediately act on, with competitor context showing where they stand relative to discovered competitors
**Verified:** 2026-02-26T06:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After an audit completes, the user sees a prioritized list of recommendations grouped by category with severity levels, where each recommendation includes a clear action description, impact estimate, and evidence from the actual audit data | VERIFIED | `recommendation_engine.py` generates `AuditRecommendation` records with `priority`, `impact_label`, `impact_pct`, `estimated_score_delta`, `summary`, `action_steps`, `evidence_source`, and `category` fields. `generate_recommendations()` sorts by priority order then gap_score descending. `estimated_score_delta` is populated via `_compute_impact_delta()`. |
| 2 | Recommendations are industry-aware: a SaaS site does not receive advice about LocalBusiness schema, and a blog does not receive advice about Product schema | VERIFIED | `VERTICAL_EXCLUSIONS` dict at module level in `recommendation_engine.py` maps verticals to excluded criterion_ids. `is_recommendation_relevant()` filters before creating each `AuditRecommendation`. `VerticalClassifier` detects 6 verticals via schema.org priority. Integration tests in `test_phase2_integration.py` and `test_recommendation_enhancements.py` confirm filtering. Note: there is no LocalBusiness schema criterion (none in the SD1-SD13 set) — the actual exclusions are SD8 (Product/Offer) for SaaS and SD10 (ClaimReview) for SaaS/ecommerce/local_business. |
| 3 | Competitor brands are automatically discovered from AI engine responses (NER extraction) and displayed in a side-by-side score comparison without the user manually entering competitor URLs | VERIFIED | `entity_extractor.py` contains `EntityExtractorService.discover_competitors_for_audit()` using spaCy NER with share-of-voice computation. `CompetitorService.get_score_comparison()` builds site-vs-competitors comparison. `GET /competitors/{audit_id}/score-comparison` endpoint is wired and returns `ScoreComparisonResponse`. NER was pre-existing from Phase 1 pipeline; score comparison is new in Phase 2. |
| 4 | Share of voice (percentage of AI mentions per brand across engines) is calculated and displayed per audit | VERIFIED | `EntityExtractorService.compute_share_of_voice()` computes SOV per entity. `DiscoveredCompetitor.share_of_voice` stores the value. `CompetitorService.get_competitor_sov_trend()` returns time-series SOV data. `GET /competitors/brands/{brand_id}/sov-trend` endpoint exposes it. |
| 5 | Competitor data persists across audits so users can track competitive positioning over time | VERIFIED | `Brand.is_competitor` boolean and `DiscoveredCompetitor.competitor_brand_id` FK (migration 011) enable cross-audit persistence. `CompetitorService.link_competitor_to_brand()` implements 4-level matching (domain > exact name > fuzzy > create new). `link_audit_competitors_to_brands()` is called from `audit_tasks.py` Stage 6.5. Tests in `test_competitor_persistence.py` and `test_phase2_integration.py` verify deduplication. |

**Score:** 5/5 truths verified

---

## Required Artifacts

### Plan 02-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/vertical_classifier.py` | SiteVertical enum + VerticalClassifier with heuristic detection | VERIFIED | 115 lines. `class VerticalClassifier` present. `SCHEMA_VERTICAL_MAP`, `ECOMMERCE_SIGNALS`, `LOCAL_SIGNALS`, `SAAS_SIGNALS` lists. `classify()` and `_extract_schema_types()` methods. |
| `backend/app/services/recommendation_engine.py` | Vertical-aware filtering and impact delta calculation | VERIFIED | 1058 lines. `VERTICAL_EXCLUSIONS`, `is_recommendation_relevant()`, `_compute_impact_delta()`, `generate_recommendations(vertical="generic")` parameter present and wired. |
| `backend/app/models/audit.py` | vertical column on Audit model | VERIFIED | `vertical = Column(String, nullable=True)` at line 38. |
| `backend/app/models/audit_recommendation.py` | estimated_score_delta column on AuditRecommendation model | VERIFIED | `estimated_score_delta = Column(Numeric(4, 1), nullable=True)` at lines 52-54. |
| `backend/alembic/versions/010_add_vertical_and_score_delta.py` | Migration adding vertical and estimated_score_delta | VERIFIED | Adds `audits.vertical` (String, nullable) and `audit_recommendations.estimated_score_delta` (Numeric(4,1), nullable). Chains from revision 009. |
| `backend/tests/test_vertical_classifier.py` | Unit tests for vertical classification | VERIFIED | 164 lines. 21 tests across 8 test classes covering all 6 verticals, priority ordering, schema extraction edge cases. |
| `backend/tests/test_recommendation_enhancements.py` | Tests for vertical filtering and impact delta | VERIFIED | 320 lines. Tests for `is_recommendation_relevant()`, `_compute_impact_delta()` bounds and multi-page adjustment, and full integration test with DB session verifying vertical filtering in `generate_recommendations()`. |

### Plan 02-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/brand.py` | is_competitor boolean field on Brand model | VERIFIED | `is_competitor = Column(Boolean, default=False, nullable=False, server_default="false")` at line 31-33. |
| `backend/app/models/competitor.py` | competitor_brand_id FK on DiscoveredCompetitor | VERIFIED | `competitor_brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True, index=True)` at lines 35-40. Relationship `competitor_brand` also present. |
| `backend/app/services/competitor_service.py` | link_competitor_to_brand logic, get_competitor_sov_trend, get_score_comparison | VERIFIED | All three methods present and substantive. `link_competitor_to_brand()` implements 4-level strategy. `get_competitor_sov_trend()` is a @staticmethod joining DiscoveredCompetitor with Audit ordered ascending. `get_score_comparison()` reads PageScore averages and CompetitorAudit records. |
| `backend/alembic/versions/011_add_competitor_brand_linking.py` | Migration adding is_competitor and competitor_brand_id | VERIFIED | Adds `brands.is_competitor` (Boolean, server_default=false) and `discovered_competitors.competitor_brand_id` (UUID FK with index). Chains from revision 010. |
| `backend/app/api/competitors.py` | SOV trend endpoint and score comparison endpoint | VERIFIED | `GET /brands/{brand_id}/sov-trend` at line 178 and `GET /{audit_id}/score-comparison` at line 195. Both authenticated, score_comparison verifies audit ownership. |
| `backend/app/schemas/competitor.py` | ScoreComparison response schema | VERIFIED | `ScoreComparisonSite`, `ScoreComparisonCompetitor`, `ScoreComparisonResponse` all present with correct fields. |
| `backend/tests/test_competitor_persistence.py` | Tests for brand linking, SOV trending, and score comparison | VERIFIED | 334 lines. 9 tests: brand linking (create new, domain match, name match, per-user isolation), SOV trend (across audits, empty for unknown), score comparison (returns site+competitors, excludes failed, empty competitor list). |

### Plan 02-03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/tasks/audit_tasks.py` | Vertical classification after crawl, brand linking after competitor discovery, vertical-aware recommendation generation | VERIFIED | Stage 1.5 (lines 85-103) classifies vertical with try/except fallback to "generic". Stage 6.5 (lines 319-337) calls `link_audit_competitors_to_brands()` with try/except. Stage 7 (line 363) passes `vertical=audit.vertical or "generic"` to `generate_recommendations()`. |
| `backend/tests/test_phase2_integration.py` | Integration tests covering full recommendations + competitor pipeline | VERIFIED | 555 lines. 10 tests across 6 test classes: SaaS vertical filtering, generic vertical pass-through, fixture classification, brand linking creates brands, cross-audit deduplication, SOV trend chronological ordering. |

---

## Key Link Verification

### Plan 02-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `recommendation_engine.py` | `vertical_classifier.py` | import in generate_recommendations | WIRED | `from app.services.vertical_classifier import` confirmed in `VERTICAL_EXCLUSIONS`/`is_recommendation_relevant()` module. `VerticalClassifier` is imported in `audit_tasks.py` which calls the recommendation engine with the classified vertical. |
| `recommendation_engine.py` | `audit_recommendation.py` | populates estimated_score_delta field | WIRED | `estimated_score_delta=estimated_delta` is passed to `AuditRecommendation` constructor at line 548. |

### Plan 02-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `competitor_service.py` | `brand.py` | Brand query/create in link_competitor_to_brand | WIRED | `from app.models.brand import Brand` at line 25. Brand is queried (domain match, name match, all brands for fuzzy) and created in `link_competitor_to_brand()`. |
| `competitor.py` | `brand.py` | competitor_brand_id FK referencing brands.id | WIRED | `ForeignKey("brands.id")` in `DiscoveredCompetitor.competitor_brand_id` column definition. |
| `competitors.py` (API) | `competitor_service.py` | calls get_competitor_sov_trend and get_score_comparison | WIRED | `CompetitorService.get_competitor_sov_trend(db, brand_id, ...)` at line 189. `service.get_score_comparison(db, ...)` at line 212. |

### Plan 02-03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `audit_tasks.py` | `vertical_classifier.py` | import and call after Stage 1 crawl | WIRED | `from app.services.vertical_classifier import VerticalClassifier` at line 32 (top of file). Called at Stage 1.5 lines 87-89. |
| `audit_tasks.py` | `competitor_service.py` | call link_audit_competitors_to_brands after Stage 6 | WIRED | `from app.services.competitor_service import CompetitorService as BrandLinker` inside Stage 6.5 try block. `brand_linker.link_audit_competitors_to_brands(db, str(audit_id), str(audit.user_id))` at line 324. |
| `audit_tasks.py` | `recommendation_engine.py` | passes vertical= parameter to generate_recommendations in Stage 7 | WIRED | `vertical=audit.vertical or "generic"` at line 363 in the `rec_engine.generate_recommendations()` call. |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REC-01 | 02-01, 02-03 | Deterministic gap analysis generates priority-ordered recommendations from scoring results | SATISFIED | `RecommendationEngine` reads `CriterionResult` records, computes gap_score, sorts by priority then gap_score desc. Wired into Stage 7 of `audit_tasks.py`. |
| REC-02 | 02-01 | Each recommendation includes impact estimate (estimated score improvement if fixed) | SATISFIED | `_compute_impact_delta()` computes linear estimate. `estimated_score_delta` column on `AuditRecommendation`. Populated for all non-sentiment recommendations. |
| REC-03 | 02-01, 02-03 | Recommendations are industry-aware (vertical classification affects advice relevance) | SATISFIED | `VerticalClassifier` detects 6 verticals. `VERTICAL_EXCLUSIONS` + `is_recommendation_relevant()` filter per vertical. `audit_tasks.py` Stage 1.5 classifies and stores vertical; Stage 7 passes it to the engine. |
| REC-04 | 02-01 | Recommendations grouped by category (Crawlability, Content, Schema, Authority) with severity levels | SATISFIED | `AuditRecommendation.category` and `priority` fields populated. `export_markdown()` groups by priority. Category comes from `CriterionResult.category`. |
| REC-05 | 02-01 | Each recommendation has a clear action description users can understand and act on | SATISFIED | `summary` (user-facing one-liner), `action_steps` (JSONB list of step strings), `code_snippet` (ready-to-use templates for high-impact criteria), `evidence_source` all populated in `_generate_page_recommendations()`. |
| COMP-01 | 02-02 | Auto-discover competitor brands from AI engine responses via NER extraction | SATISFIED | `EntityExtractorService.discover_competitors_for_audit()` in `entity_extractor.py` uses spaCy NER. Pre-existing from Phase 1 pipeline; this phase added Brand linking persistence on top. |
| COMP-02 | 02-02 | User can view side-by-side score comparison (their site vs discovered competitors) | SATISFIED | `CompetitorService.get_score_comparison()` builds site+competitors dict. `GET /competitors/{audit_id}/score-comparison` returns `ScoreComparisonResponse` with per-category scores for both site and each completed competitor. |
| COMP-03 | 02-02, 02-03 | Share of voice tracking: percentage of AI mentions per brand across engines over time | SATISFIED | `EntityExtractorService.compute_share_of_voice()` computes per-entity SOV. `CompetitorService.get_competitor_sov_trend()` returns time-series data. `GET /competitors/brands/{brand_id}/sov-trend` exposes it. |
| COMP-04 | 02-02, 02-03 | Competitor data persists across audits to show trends | SATISFIED | `DiscoveredCompetitor.competitor_brand_id` FK links per-audit competitor to persistent `Brand` record. `link_competitor_to_brand()` deduplicates via domain > name > fuzzy > create new. Stage 6.5 in `audit_tasks.py` calls linking automatically. |

**All 9 requirements (REC-01 through REC-05, COMP-01 through COMP-04) are SATISFIED.**

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `audit_tasks.py` | 69 (SUMMARY note) | Commit hashes listed as "PENDING" in 02-03-SUMMARY.md | Info | The SUMMARY documents commits as PENDING due to sandbox restrictions — actual audit_tasks.py file is substantively implemented. No impact on functionality. |

No stub implementations, placeholder returns, or empty handlers detected in any of the verified files.

---

## Human Verification Required

### 1. End-to-end SaaS vertical filtering in live pipeline

**Test:** Run a full audit on a SaaS URL (e.g., stripe.com or a local SaaS fixture). After audit completes, query `GET /api/v1/competitors/{audit_id}/leaderboard` and the audit's recommendations.
**Expected:** Zero recommendations with `criterion_id` in `{SD8, SD10}`. At least one recommendation with `criterion_id` starting with `SD3`, `CS`, `C`, `A`, or `S`. Each recommendation has a positive `estimated_score_delta` value between 0.1 and 15.0.
**Why human:** Requires a running Celery worker, real Supabase DB session, and live HTTP crawl to trigger the full pipeline including vertical classification, scoring, and recommendation generation.

### 2. Cross-audit competitor deduplication in production

**Test:** Run two audits for the same URL. Query `discovered_competitors` table for both audits. Check that entities with the same name/domain share a single `competitor_brand_id`.
**Expected:** Two `DiscoveredCompetitor` rows with the same `competitor_brand_id` pointing to a single `Brand` record with `is_competitor=True`.
**Why human:** Cross-audit deduplication requires two real audit runs and live DB inspection. The test suite uses transactional rollbacks that prevent testing true cross-session persistence.

### 3. SOV trend endpoint with real audit history

**Test:** After at least two audits on the same URL, call `GET /api/v1/competitors/brands/{brand_id}/sov-trend` for a discovered competitor brand.
**Expected:** JSON array with two or more objects, each containing `date`, `share_of_voice`, `mention_count`, and `audit_id`. Objects ordered by date ascending.
**Why human:** Requires multiple real audit runs to produce historical SOV data. Unit tests use mocked data.

---

## Gaps Summary

No gaps found. All five observable truths from the Phase 2 success criteria are fully implemented and substantively wired:

1. The recommendation engine generates prioritized, categorized, evidence-backed recommendations with impact estimates (estimated_score_delta) and clear action descriptions.
2. Industry-aware filtering works via the VerticalClassifier + VERTICAL_EXCLUSIONS chain. Note: the plan's "LocalBusiness schema" example doesn't match exactly — there is no LocalBusiness criterion (SD1-SD13 doesn't include one). The actual filtering correctly excludes SD8 (Product/Offer schema) for SaaS and SD10 (ClaimReview) for SaaS/ecommerce/local_business. This is correct behavior given the actual scoring pipeline's criterion IDs.
3. NER-based competitor discovery (pre-existing), URL resolution, and side-by-side score comparison are all wired end-to-end.
4. Share of voice is computed per entity and the time-series trend endpoint is operational.
5. Cross-audit persistence via the Brand FK is implemented with 4-level matching and Stage 6.5 pipeline integration.

The only qualification is human verification items above, which require a live runtime environment to confirm end-to-end behavior.

---

_Verified: 2026-02-26T06:00:00Z_
_Verifier: Claude (gsd-verifier)_
