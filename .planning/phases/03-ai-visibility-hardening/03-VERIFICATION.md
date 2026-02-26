---
phase: 03-ai-visibility-hardening
status: passed
verified: 2026-02-26
updated: 2026-02-26
---

# Phase 3: AI Visibility Hardening - Verification

## Goal
Users can trust their AI Visibility Score because it is derived from statistical measurement across multiple queries and engines, not a single-shot check.

## Requirements Verified

| Requirement | Status | Evidence |
|-------------|--------|----------|
| VIS-01 | PASS | ScoringService v2 produces enriched per_engine_scores from real LLM queries with queries_sent, mention_rate, confidence_level per engine |
| VIS-02 | PASS | _compute_confidence_level thresholds (0=not_measured, 1-4=low, 5-9=medium, 10+=high) surfaced to users via per_engine_breakdown |
| VIS-03 | PASS | Per-engine breakdown for ChatGPT, Claude, Perplexity, Gemini with display names; frontend cards show individual scores |
| VIS-04 | PASS | Engines without API keys get skipped=true, skip_reason="No API key configured", engines_skipped tracked in model; frontend shows "Not configured" badge |

## Success Criteria Verification

### SC1: Multi-query scoring with confidence indicators
**Status:** PASS
- ScoringService.ALGORITHM_VERSION = "v2"
- Per-engine breakdown includes queries_sent, queries_with_mentions, mention_rate, avg_confidence, confidence_level
- Frontend displays confidence badges (high=green, medium=yellow, low=orange)
- Frontend shows "Mentioned in X of Y queries" stats

### SC2: Per-engine breakdown for each active engine
**Status:** PASS
- ENGINE_DISPLAY_NAMES maps openai->ChatGPT, anthropic->Claude, perplexity->Perplexity, gemini->Gemini
- PerEngineBreakdown Pydantic model with full statistical fields
- Frontend renders separate cards per engine with individual scores
- VisibilityScoreSchema includes per_engine_breakdown list

### SC3: Graceful skipping of engines without API keys
**Status:** PASS
- ScoringService iterates ENGINE_CONFIG and adds skipped entries for missing engines
- VisibilityScore model tracks engines_queried and engines_skipped columns
- Overall score uses only active engines (weighted-by-queries-sent)
- Frontend shows "Not configured" badge with "--" score for skipped engines

### SC4: Cache consistency within TTL
**Status:** PASS
- AICacheService (Phase 1) with Redis 24h TTL remains unchanged
- Phase 3 does not modify caching behavior
- Same queries within TTL return cached responses -> consistent scores

## Artifact Verification

| Artifact | Exists | Substantive | Wired |
|----------|--------|-------------|-------|
| backend/app/models/visibility_score.py | YES | 3 new columns (confidence_level, engines_queried, engines_skipped) | Used by ScoringService |
| backend/alembic/versions/012_add_visibility_confidence_fields.py | YES | Adds 3 columns with server_defaults | Chains after 011 |
| backend/app/services/scoring_service.py | YES | Enriched breakdown, weighted scoring, confidence levels | Imported in audit_tasks.py |
| backend/app/schemas/audit.py | YES | PerEngineBreakdown model, ENGINE_DISPLAY_NAMES, extended schema | Used by audit API |
| backend/app/api/audit.py | YES | _build_per_engine_breakdown helper, enriched serialization | API endpoint |
| frontend/components/AuditResults.vue | YES | Confidence badges, skipped display, mention stats | Rendered in analyze page |
| backend/tests/test_visibility_scoring.py | YES | 8 tests (confidence, enriched, backward compat, weighted) | Runs in pytest |

## Test Results

- **Visibility scoring tests:** 8/8 passing
- **Scoring pipeline tests:** 23/23 passing
- **Frontend build:** Successful (no TypeScript errors)
- **Total tests affected:** 31 passing, 0 regressions

## Must-Have Truths Verified

All truths from both plans checked:

1. ScoringService produces per-engine breakdown with queries_sent, queries_with_mentions, mention_rate, confidence_level, and skipped flag: **TRUE**
2. Overall visibility score uses weighted-by-queries-sent averaging: **TRUE**
3. Engines without API keys appear with skipped=true and skip_reason: **TRUE**
4. API response includes per_engine_breakdown list with display names: **TRUE**
5. Old audits with simple per_engine_scores format still render without errors: **TRUE** (verified by test_per_engine_breakdown_from_old_format)
6. Frontend per-engine cards show confidence badge and mention rate: **TRUE**
7. Frontend handles skipped engines with "Not configured" badge: **TRUE**
8. Tests verify confidence level thresholds correctly: **TRUE**

## Verdict

**PASSED** - All 4 success criteria met, all 4 requirements verified, all must-have truths confirmed, 31 tests passing, frontend builds cleanly.
