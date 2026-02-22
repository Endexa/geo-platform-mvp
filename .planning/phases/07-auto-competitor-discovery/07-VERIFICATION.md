---
phase: 07-auto-competitor-discovery
verified: 2026-02-22T22:15:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Run a full audit against a real URL and confirm DiscoveredCompetitor rows appear in the database with non-zero mention counts and share_of_voice values"
    expected: "At least 2-3 competitor entities extracted from AI responses, each with mention_count >= 2"
    why_human: "Requires live AI engine responses and a running database to confirm spaCy NER pipeline actually produces output end-to-end"
  - test: "Navigate to /competitors after a completed audit and verify the leaderboard renders rows with SOV bars and engine badges"
    expected: "Table shows ranked brands with colored SOV bars and per-engine badges (GPT/Claude/Pplx/Gemini)"
    why_human: "Visual rendering and API data shape cannot be confirmed without a browser and live backend"
  - test: "On the audit page, add a custom query and confirm it appears in the query list with amber dashed border, then delete it"
    expected: "New query appears with 'Custom' badge and amber styling; DELETE removes it; UI refreshes automatically"
    why_human: "Interactive UI flow requires a browser session with an authenticated user"
  - test: "Trigger competitor crawl from /competitors page with uncrawled entities present"
    expected: "Loading spinner appears, crawl completes within ~60s, CompetitorComparison table populates with per-category scores"
    why_human: "Requires live external HTTP requests to competitor sites and functioning scorer pipeline"
---

# Phase 7: Auto-Competitor Discovery Verification Report

**Phase Goal:** The system automatically discovers competitors from AI engine responses (who AI mentions instead of you), crawls their sites, and compares their technical setup against the user's site.
**Verified:** 2026-02-22T22:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All brand/entity names are extracted from AI engine responses using NER and pattern matching | VERIFIED | `entity_extractor.py` implements `extract_entities_from_response()` using spaCy NER (ORG/PRODUCT labels) + `extract_citations()` using regex patterns. `discover_competitors_for_audit()` orchestrates the full pipeline. |
| 2 | Discovered entities are ranked by mention frequency across all queries and engines, with share-of-voice percentages | VERIFIED | `deduplicate_entities()` tracks per-engine and per-query counts; `compute_share_of_voice()` computes SOV = `(entity_mentions / total_mentions) * 100`. `DiscoveredCompetitor` model stores `mention_count`, `share_of_voice`, `engines_mentioned_in`. |
| 3 | User sees a competitor leaderboard showing which brands AI mentions most for their industry queries | VERIFIED | `CompetitorLeaderboard.vue` renders ranked table with SOV percentage bars, entity type badges, engine badges (GPT/Claude/Pplx/Gemini), and crawl status. `GET /api/v1/competitors/{audit_id}/leaderboard` endpoint returns `CompetitorLeaderboardResponse`. |
| 4 | Top 3-5 competitors by mention frequency are auto-crawled using the same crawl + scoring pipeline as the user's site | VERIFIED | `CompetitorService.crawl_top_competitors()` queries top competitors by `mention_count DESC`, resolves URLs via 3-layer strategy, then calls `crawl_and_score_competitor()` which reuses `CrawlerService` and all 4 Phase 6 category scorers. `audit_tasks.py` Stage 6 triggers `crawl_top_competitors()` non-fatally after entity extraction. |
| 5 | User sees a comparison of their scores vs competitor scores per category | VERIFIED | `CompetitorComparison.vue` renders side-by-side table for Crawlability, Content Structure, Structured Data, Authority, and Overall score. Includes directional arrows and "Score Gaps" summary sorted by deficit size. |
| 6 | User can add, edit, or remove custom queries alongside auto-generated ones before or after an audit runs | VERIFIED | Four CRUD endpoints in `audit.py`: `GET/POST/PUT/DELETE /{audit_id}/queries`. `QueryEditor.vue` implements full inline add/edit/delete with amber styling, category dropdown, delete confirmation dialog, and API calls to all endpoints. |
| 7 | For AI responses that cite sources, the system extracts and displays which URLs/sources each engine references | VERIFIED | `dispatch_service.py` captures Perplexity citations from `response.citations` / `_hidden_params`, and inline URL regex for all engines. `EngineResponse.citations` JSONB column stores them. `SourceCitations.vue` renders per-engine citation lists with domain extraction, cross-engine frequency summary, and URL regex fallback. |

**Score: 7/7 truths verified**

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/competitor.py` | DiscoveredCompetitor and CompetitorAudit SQLAlchemy models | VERIFIED | Contains both classes with all required columns: `share_of_voice`, `engines_mentioned_in`, `is_user_brand`, `competitor_audit_id`, per-category averages. |
| `backend/app/services/entity_extractor.py` | EntityExtractorService with NER, citation extraction, deduplication, SOV | VERIFIED | 345 lines, fully implemented: `extract_entities_from_response()`, `extract_citations()`, `extract_all_entities_for_audit()`, `deduplicate_entities()`, `compute_share_of_voice()`, `discover_competitors_for_audit()`. Generic blocklist and corporate suffix stripping present. |
| `backend/alembic/versions/007_add_competitors_and_citations.py` | Migration creating competitor tables and adding columns | VERIFIED | Creates `competitor_audits` (first, for FK), then `discovered_competitors` with indices. Adds `citations` JSONB to `engine_responses`. Adds `is_custom`, `is_editable` Boolean columns to `audit_queries`. `downgrade()` reverses all operations. |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/competitor_service.py` | CompetitorService with URL resolution, crawl+score, leaderboard | VERIFIED | 572 lines, fully implemented: `resolve_competitor_url()` (3-layer: citation/heuristic/KG), `crawl_and_score_competitor()`, `crawl_top_competitors()`, `get_leaderboard()`. Reuses all 4 Phase 6 scorers via `_build_scorers()`. |
| `backend/app/api/competitors.py` | 3 competitor API endpoints | VERIFIED | Contains `router`, 3 endpoints: `GET /{audit_id}/leaderboard`, `POST /{audit_id}/crawl`, `GET /{audit_id}/competitor/{competitor_audit_id}`. All auth-protected with ownership verification. |
| `backend/app/schemas/competitor.py` | Pydantic schemas for competitor responses | VERIFIED | `CompetitorLeaderboardEntry`, `CompetitorAuditSummary`, `CompetitorLeaderboardResponse` — all with correct field types and `from_attributes=True`. |

### Plan 03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/api/audit.py` | CRUD endpoints for custom queries | VERIFIED | Contains `GET`, `POST`, `PUT`, `DELETE` for `/{audit_id}/queries`. `POST` creates with `is_custom=True`. `PUT`/`DELETE` enforce `is_custom=True` guard (403 if not custom). `DELETE` checks for engine responses (409 if dispatched). |
| `frontend/components/QueryEditor.vue` | Vue component for custom query add/edit/delete | VERIFIED | 383 lines. Full implementation: add form with category dropdown, inline editing mode, delete confirmation dialog, sorting (custom first), API calls to all 3 endpoints, emit events (`query-added`, `query-updated`, `query-deleted`). |

### Plan 04 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/pages/competitors.vue` | Competitors page with leaderboard and comparison | VERIFIED | Full page with `CompetitorLeaderboard`, `CompetitorComparison`, crawl trigger button, loading/error states, no-audit redirect, parallel API fetch via `Promise.all`. |
| `frontend/components/CompetitorLeaderboard.vue` | Ranked table with SOV percentages | VERIFIED | Contains `share_of_voice` rendering with dynamic bar width, engine badges with colors, entity type badges, status badges (Scored/Pending/No URL), user brand highlighting. |
| `frontend/components/CompetitorComparison.vue` | Side-by-side score comparison | VERIFIED | Contains `CompetitorComparison` class definition. Renders per-category rows (crawlability, content_structure, structured_data, authority, overall), directional arrows, Score Gaps summary sorted by deficit. |
| `frontend/components/SourceCitations.vue` | Source citation display grouped by engine | VERIFIED | Contains `citations` field handling. Accordion-style per-engine URL lists, regex fallback for non-citation engines, domain frequency summary, expandable sections via `ChevronDownIcon`. |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `audit_tasks.py` | `entity_extractor.py` | `EntityExtractorService` called in Stage 6 | WIRED | Lines 243-258: `from app.services.entity_extractor import EntityExtractorService; extractor = EntityExtractorService(); competitors = extractor.discover_competitors_for_audit(db=db, audit_id=audit_id, user_brand_name=brand_name)` |
| `dispatch_service.py` | `engine_response.py` | Perplexity citations captured in `citations` column | WIRED | Lines 258-330: citation extraction from `response.citations` and `_hidden_params`, inline URL regex for all engines, `citations=citations_list` set on `EngineResponse` object in both cached and non-cached paths. |
| `entity_extractor.py` | `competitor.py` | `DiscoveredCompetitor` records created | WIRED | Lines 321-334: `DiscoveredCompetitor(audit_id=..., entity_name=..., mention_count=..., share_of_voice=..., ...)` created for each ranked entity, `db.add(competitor)`, `db.flush()`. |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `audit_tasks.py` | `competitor_service.py` | `CompetitorService.crawl_top_competitors()` in Stage 6 | WIRED | Lines 262-283: `from app.services.competitor_service import CompetitorService; competitor_svc = CompetitorService(db); loop.run_until_complete(competitor_svc.crawl_top_competitors(audit_id))`. Wrapped in try/except (non-fatal). |
| `competitor_service.py` | `scoring_orchestrator.py` | `ScoringOrchestrator` reused for page discovery | WIRED | Lines 218-235: `from app.services.scoring.scoring_orchestrator import ScoringOrchestrator; temp_orch = ScoringOrchestrator(self.db); discovered_links = temp_orch._discover_internal_links(...)`. Also calls individual scorers via `_build_scorers()`. |
| `competitors.py` (API) | `competitor.py` (model) | Queries `DiscoveredCompetitor` and `CompetitorAudit` models | WIRED | Lines 19, 44, 69-72, 145-150: imports and queries both models. `CompetitorService(db).get_leaderboard(audit_id)` returns full data. |

### Plan 03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `QueryEditor.vue` | `audit.py` API | `useApiFetch` to `/audit/{id}/queries` endpoints | WIRED | Lines 288, 333, 364: `useApiFetch('/audit/${props.auditId}/queries', {method: 'POST', ...})`, `PUT`, and `DELETE` calls. Emits events consumed by `audit.vue`. |
| `audit.py` API | `audit_query.py` model | Creates/updates/deletes `AuditQuery` records with `is_custom=True` | WIRED | Lines 287-293: `AuditQuery(audit_id=..., is_custom=True, ...)`. Lines 328, 375: `is_custom` guard enforcement. |

### Plan 04 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `competitors.vue` | `competitors.py` API | `useApiFetch` to `GET /api/v1/competitors/{audit_id}/leaderboard` | WIRED | Line 188: `useApiFetch('/competitors/${targetAuditId}/leaderboard')`. Pattern `competitors.*leaderboard` confirmed. |
| `CompetitorComparison.vue` | `competitor.py` schemas | Renders `crawlability_avg`, `content_structure_avg`, `structured_data_avg`, `authority_avg` | WIRED | Lines 135-166: `categoryRows` computed property maps all 4 category averages from `userScores` props. Competitor score rendering on lines 50-69. |
| `SourceCitations.vue` | `audit.py` API | Reads `citations` field from `engineResponses` prop | WIRED | Lines 145-158: `if (resp.citations && resp.citations.length > 0)` branch with URL regex fallback. The `audit.vue` passes all engine responses via `allEngineResponses` computed property. |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| COMP-01 | Plan 01 | Extract brand/entity names from AI responses using NER and pattern matching | SATISFIED | `EntityExtractorService.extract_entities_from_response()` uses spaCy ORG/PRODUCT NER. `extract_citations()` uses regex patterns. `discover_competitors_for_audit()` called in audit pipeline Stage 6. |
| COMP-02 | Plan 01 | Rank discovered entities by mention frequency with share-of-voice percentages | SATISFIED | `deduplicate_entities()` counts per-engine/per-query appearances. `compute_share_of_voice()` computes SOV percentages. `DiscoveredCompetitor.share_of_voice` and `mention_count` stored in DB. |
| COMP-03 | Plan 02 | User sees competitor leaderboard with share-of-voice percentages | SATISFIED | `CompetitorLeaderboard.vue` renders SOV bars, engine badges, status. `GET /api/v1/competitors/{id}/leaderboard` endpoint returns `CompetitorLeaderboardResponse`. Router registered in `main.py`. |
| COMP-04 | Plan 02 | Crawl top 3-5 competitor sites using the same pipeline | SATISFIED | `CompetitorService.crawl_top_competitors()` + `crawl_and_score_competitor()` reuses `CrawlerService` and all 4 category scorers. `COMPETITOR_MAX_COUNT=5` config. Wired into audit pipeline Stage 6 (non-fatal). |
| COMP-05 | Plan 04 | Compare competitor technical setup against user's site per category | SATISFIED | `CompetitorComparison.vue` shows per-category scores (crawlability, content structure, structured data, authority) for user vs each competitor. Score Gaps summary highlights deficits. |
| COMP-06 | Plan 03 | User can add/edit/remove custom queries alongside auto-generated ones | SATISFIED | Full CRUD: `POST/PUT/DELETE/GET /{audit_id}/queries` in `audit.py`. `QueryEditor.vue` with inline add/edit, delete confirmation, amber styling for custom queries. `is_custom=True` field on `AuditQuery` model. |
| COMP-07 | Plan 04 | For AI responses that cite sources, extract and display URLs | SATISFIED | `dispatch_service.py` captures Perplexity citations from API and inline URL regex for all engines. `EngineResponse.citations` JSONB column. `SourceCitations.vue` renders per-engine groups with cross-engine domain frequency. |

All 7 requirements verified. No orphaned requirements found.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned: `entity_extractor.py`, `competitor_service.py`, `competitors.py`, `CompetitorLeaderboard.vue`, `CompetitorComparison.vue`, `SourceCitations.vue`, `QueryEditor.vue`, `competitors.vue`, `audit.vue`, `audit_tasks.py`, `dispatch_service.py`. No TODO/FIXME/placeholder patterns, no empty handler stubs, no return-null implementations detected in Phase 7 code.

**Note:** `entity_extractor.py` lines 181, 308, 315 contain `return []` but these are correct early-return guards (empty input → empty output), not stubs.

---

## Human Verification Required

### 1. End-to-End Entity Extraction

**Test:** Run a full audit against a real URL (e.g., `https://stripe.com`) and inspect the `discovered_competitors` table after the audit reaches COMPLETED status.
**Expected:** At least 2-3 competitor entities (e.g., PayPal, Square, Braintree) with `mention_count >= 2` and valid `share_of_voice` values summing to ~100%.
**Why human:** Requires live AI engine responses, a running PostgreSQL instance, spaCy `en_core_web_sm` model installed, and actual NER processing end-to-end.

### 2. Competitor Leaderboard Visual Rendering

**Test:** Navigate to `/competitors?audit_id={id}` after a completed audit with discovered competitors.
**Expected:** Table shows ranked brands with SOV percentage bars, colored engine badges (GPT=green, Claude=purple, Pplx=blue, Gemini=amber), Scored/Pending/No URL status badges.
**Why human:** Visual rendering and API data shape cannot be confirmed without a browser and live backend serving real data.

### 3. Custom Query CRUD Workflow

**Test:** On the audit page with a completed audit, click "Add Custom Query", enter a query, save it. Then edit the text, save. Then delete it.
**Expected:** New query appears with amber dashed border and "Custom" badge. Edit updates text. Delete shows confirmation dialog, then removes the row. Each action triggers a data refresh.
**Why human:** Interactive UI flow requires browser session with authenticated user.

### 4. Competitor Crawl Trigger

**Test:** On `/competitors` with uncrawled competitors having resolved URLs, click "Score Competitors".
**Expected:** Loading spinner appears for up to 60 seconds, then `CompetitorComparison` table populates with per-category scores for each crawled competitor, with directional arrows and Score Gaps summary.
**Why human:** Requires live external HTTP requests to competitor sites, working scorer pipeline, and database persistence.

---

## Gaps Summary

No gaps found. All 7 truths verified, all 10 key artifacts confirmed substantive and wired, all 7 requirements satisfied, zero blocking anti-patterns detected.

**Architecture observations (not gaps):**

1. **spaCy model download:** `entity_extractor.py` uses `spacy.load("en_core_web_sm")` with lazy loading. The model must be downloaded at Docker build time or before first use. This is documented in `requirements.txt` (comment on line 47) but is a deployment prerequisite, not a code gap.

2. **`httpx` version pinned twice:** `requirements.txt` lists `httpx==0.26.0` on lines 55 and 67 (duplicate entry). Minor hygiene issue, no functional impact.

3. **`allEngineResponses` in audit.vue missing `citations` field:** The `audit.vue` interface for engine responses (lines 108-122) does not include the `citations?: string[]` field, while `SourceCitations.vue` expects it. The data will be present in the API response (since `EngineResponse.citations` is serialized), but TypeScript will not have type-safety for it. `SourceCitations.vue` handles this gracefully with the regex fallback. Not a blocker.

---

_Verified: 2026-02-22T22:15:00Z_
_Verifier: Claude (gsd-verifier)_
