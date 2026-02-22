---
phase: 08-actionable-recommendations
verified: 2026-02-23T12:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 11/13
  gaps_closed:
    - "Content gaps are populated in the DB and returned by the API — identify_content_gaps() and save_content_gaps() are now called in the RECOMMENDING stage (audit_tasks.py lines 319-320)"
    - "API returns content gaps showing topics where competitors are mentioned but user is not — pipeline now writes to audit.content_gaps JSONB column before db.commit(), so the GET /content-gaps endpoint returns real data"
  gaps_remaining: []
  regressions: []
---

# Phase 8: Actionable Recommendations Verification Report

**Phase Goal:** The system generates page-specific, evidence-based recommendations by comparing user site scores against competitor scores and research-backed best practices, with each recommendation showing the evidence, the gap, and the estimated impact
**Verified:** 2026-02-23
**Status:** passed — all 13 truths verified, both previously-failing gaps closed, no regressions
**Re-verification:** Yes — after gap closure

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After an audit completes, AuditRecommendation records exist in the DB with page-specific gap analysis data | VERIFIED | generate_recommendations() called in RECOMMENDING stage (audit_tasks.py:308-311), reads CriterionResult per page, writes AuditRecommendation records |
| 2 | Each recommendation has evidence_source, impact_label, priority, competitor_avg, and gap_score populated | VERIFIED | All fields set in _generate_page_recommendations() (recommendation_engine.py:476-494), CRITERION_RESEARCH_MAP provides research-backed values for 13 criteria |
| 3 | MentionSentiment records exist for all brand mentions with positive/negative/neutral classification | VERIFIED | analyze_audit_sentiments() called before generate_recommendations() in RECOMMENDING stage (audit_tasks.py:298-304), uses gemini-2.5-flash with explicit api_key |
| 4 | Recommendations carry over done/dismissed status from previous audits via recommendation_hash | VERIFIED | _lookup_prior_status() (recommendation_engine.py:571-584) queries prior recommendations by rec_hash and user_id; _compute_rec_hash() produces stable 16-char SHA-256 digest |
| 5 | The Celery pipeline includes a RECOMMENDING stage between DISCOVERING_COMPETITORS and COMPLETED | VERIFIED | AuditStatus.RECOMMENDING added to audit.py; Stage 7 in audit_tasks.py:287-327 sets status, calls both services and content gap methods; Stage 8 marks COMPLETED |
| 6 | API returns paginated recommendations for an audit with priority, evidence, and competitor comparison data | VERIFIED | GET /{audit_id} endpoint (recommendations.py:67-124) with page_url/priority/category filters, returns RecommendationListResponse with by_priority and progress counts |
| 7 | User can PATCH a recommendation's status to done or dismissed | VERIFIED | PATCH /{audit_id}/{recommendation_id} endpoint (recommendations.py:127-169) with Literal["open","done","dismissed"] validation; frontend emits update-status and calls PATCH (recommendations.vue:426) |
| 8 | API returns per-engine sentiment breakdown for an audit | VERIFIED | GET /{audit_id}/sentiment (recommendations.py:172-191) calls SentimentService.get_per_engine_summary() which uses GROUP BY engine+sentiment aggregation |
| 9 | Content gaps are populated in the DB and returned by the API | VERIFIED | identify_content_gaps() and save_content_gaps() now called in RECOMMENDING stage (audit_tasks.py:319-320); db.commit() on line 327 persists the data; GET /content-gaps endpoint reads audit.content_gaps correctly |
| 10 | Markdown fix plan can be exported for a single page or full site | VERIFIED | GET /{audit_id}/export/markdown (recommendations.py:222-262) calls export_markdown() which generates structured Markdown with evidence, steps, code snippets, and acceptance criteria |
| 11 | Content gaps include mini briefs with suggested title and key points | VERIFIED | _template_brief() (recommendation_engine.py:723-744) returns dict with title, key_points, and target_queries; now reachable because identify_content_gaps() is called from the pipeline |
| 12 | User can view a dedicated recommendations page with all recommendations organized by priority | VERIFIED | /recommendations page (recommendations.vue) has 4 tabs: By Priority, By Page, Content Gaps, Sentiment; RecommendationCard components rendered per priority level |
| 13 | Recommendations page is accessible from sidebar navigation | VERIFIED | frontend/layouts/dashboard.vue line 102: { path: '/recommendations', label: 'Recommendations', icon: LightBulbIcon } |

**Score:** 13/13 truths verified

---

## Re-verification: Gap Closure Details

### Gap 1 (CLOSED): Content gaps not computed in pipeline

**Previous state:** `identify_content_gaps()` and `save_content_gaps()` existed in `RecommendationEngine` but were never called from `audit_tasks.py`. The `content_gaps` JSONB column on `Audit` was always NULL.

**Fix applied:** Three lines added to the RECOMMENDING stage in `audit_tasks.py` (lines 318-325):

```python
# Identify content gaps (topics where competitors mentioned but user is not)
gaps = rec_engine.identify_content_gaps(audit_id=audit_id)
rec_engine.save_content_gaps(audit_id=audit_id, gaps=gaps)
logger.info(
    "Audit {}: identified {} content gaps",
    audit_id,
    len(gaps),
)
```

The `db.commit()` on line 327 persists all three operations (recommendations, content gaps, sentiments) atomically.

**Verification:** `save_content_gaps()` uses `db.flush()` internally (recommendation_engine.py:721), and the outer `db.commit()` in audit_tasks.py:327 commits the transaction. The GET `/content-gaps` endpoint reads `audit.content_gaps or []` (recommendations.py:215), which will now return real data.

### Gap 2 (CLOSED): API always returning empty content gaps

**Previous state:** Directly caused by Gap 1. The endpoint logic was correct, but the column was always NULL.

**Fix applied:** Same as Gap 1. No changes to the API endpoint were needed — the fix was purely in the pipeline.

---

## Regression Check (Previously Passing Items)

All 11 previously-verified truths confirmed as still passing:

| Item | Regression Check | Result |
|------|-----------------|--------|
| generate_recommendations() in RECOMMENDING stage | grep confirms lines 308-311 in audit_tasks.py | No regression |
| analyze_audit_sentiments() in RECOMMENDING stage | grep confirms lines 298-304 in audit_tasks.py | No regression |
| recommendations.router mounted in main.py | main.py line 150: app.include_router(recommendations.router) | No regression |
| layouts/dashboard.vue nav item | layouts/dashboard.vue line 102: /recommendations with LightBulbIcon | No regression |
| All 4 key Phase 8 components present | RecommendationCard.vue, RecommendationProgress.vue, SentimentBreakdown.vue, ContentGapCard.vue all in frontend/components/ | No regression |
| recommendations.vue page present | frontend/pages/recommendations.vue exists | No regression |
| AuditRecommendation model | backend/app/models/audit_recommendation.py class AuditRecommendation | No regression |
| MentionSentiment model | backend/app/models/mention_sentiment.py class MentionSentiment | No regression |
| SentimentService | backend/app/services/sentiment_service.py: SENTIMENT_MODEL, analyze_audit_sentiments(), get_per_engine_summary() | No regression |
| export_markdown() | recommendations.py line 243 calls export_markdown() | No regression |
| _template_brief() | recommendation_engine.py lines 723-744 — now reachable from pipeline | No regression |

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/models/audit_recommendation.py` | VERIFIED | Class AuditRecommendation with all 16 required fields. Relationship to Audit. |
| `backend/app/models/mention_sentiment.py` | VERIFIED | Class MentionSentiment with all required fields. brand_mention_id unique=True. Relationship to Audit. |
| `backend/app/services/recommendation_engine.py` | VERIFIED | Class RecommendationEngine with CRITERION_RESEARCH_MAP (13 criteria), CRITERION_SNIPPETS (10 code templates), generate_recommendations(), identify_content_gaps(), save_content_gaps(), export_markdown(), _classify_priority(), _compute_rec_hash(), _lookup_prior_status(), _template_brief(). All methods now wired into the pipeline. |
| `backend/app/services/sentiment_service.py` | VERIFIED | Class SentimentService, SENTIMENT_MODEL = "gemini/gemini-2.5-flash", classify_mention_sentiment() with explicit api_key=settings.GEMINI_API_KEY, analyze_audit_sentiments(), get_per_engine_summary(). |
| `backend/alembic/versions/008_add_recommendations_sentiments_content_gaps.py` | VERIFIED | Creates audit_recommendations table, mention_sentiments table, adds content_gaps JSONB to audits. Both indexes created. Downgrade reverses all. |

### Plan 02 Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/api/recommendations.py` | VERIFIED | router = APIRouter; 5 endpoints: GET list, PATCH status, GET sentiment, GET content-gaps, GET export/markdown. _verify_audit_ownership() returns 403/404. |
| `backend/app/schemas/recommendation.py` | VERIFIED | 6 Pydantic schemas: AuditRecommendationResponse, RecommendationStatusUpdate (Literal validation), RecommendationListResponse, SentimentSummaryResponse, ContentGapResponse, ContentGapListResponse. ConfigDict(from_attributes=True). |

### Plan 03 Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/components/RecommendationCard.vue` | VERIFIED | Two-tier card (summary + expandable steps/code). Priority badges. Done/Dismiss/Undo buttons. Status-driven card background. |
| `frontend/components/RecommendationProgress.vue` | VERIFIED | Animated progress bar. Per-priority remaining counts via byPriority prop. |
| `frontend/components/SentimentBreakdown.vue` | VERIFIED | Per-engine mini bars. Engine display names. Dominant sentiment badge. |
| `frontend/components/ContentGapCard.vue` | VERIFIED | border-amber-200 bg-amber-50 styling. Toggle Show/Hide Brief. Key points as bullet list. |
| `frontend/pages/recommendations.vue` | VERIFIED | 4 tabs (priority/page/gaps/sentiment). Parallel API loading with .catch(() => null) for supplementary data. Optimistic status updates with rollback. Export fix plan button. |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| audit_tasks.py | recommendation_engine.py | RecommendationEngine(db).generate_recommendations() | WIRED | Lines 308-311 |
| audit_tasks.py | sentiment_service.py | SentimentService(db).analyze_audit_sentiments() | WIRED | Lines 298-304 |
| recommendation_engine.py | criterion_result.py | Reads CriterionResult records per page | WIRED | db.query(CriterionResult).filter(CriterionResult.page_score_id == page_score.id) |
| audit_tasks.py | recommendation_engine.py | identify_content_gaps() + save_content_gaps() | WIRED | Lines 319-320; db.commit() on line 327 persists data |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| recommendations.py | recommendation_engine.py | export_markdown() called for Markdown export | WIRED | Line 243 |
| recommendations.py | sentiment_service.py | get_per_engine_summary() for sentiment endpoint | WIRED | Lines 188-189 |
| main.py | recommendations.py | Router included in FastAPI app | WIRED | main.py line 150: app.include_router(recommendations.router) |

### Plan 03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| recommendations.vue | /api/v1/recommendations/{audit_id} | useApiFetch composable | WIRED | Line 391 |
| RecommendationCard.vue | /api/v1/recommendations/{audit_id}/{id} | PATCH call for status update | WIRED | recommendations.vue:426 makes PATCH call on update-status emit |
| layouts/dashboard.vue | recommendations.vue | Sidebar navigation item | WIRED | layouts/dashboard.vue line 102: { path: '/recommendations', label: 'Recommendations', icon: LightBulbIcon } |

---

## Requirements Coverage

| Requirement | Plans | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| REC-01 | 01, 02, 03 | Page-specific recommendations comparing user scores against competitor scores and research best practices | SATISFIED | generate_recommendations() reads CriterionResult per page, compares against CompetitorAudit category averages and CRITERION_RESEARCH_MAP benchmarks; 13 research-backed criteria with impact data |
| REC-02 | 01, 02, 03 | Each recommendation includes evidence, competitor comparison, and exact gap | SATISFIED | All AuditRecommendation records include evidence_source, impact_label, competitor_avg, gap_score, summary; AuditRecommendationResponse exposes all fields to the API |
| REC-03 | 01, 02, 03 | Recommendations prioritized by estimated impact (High/Medium/Low) | SATISFIED | _classify_priority() formula: HIGH if gap>=50 OR (impact>=200 AND gap>=30), MEDIUM if impact>=120 AND gap>=20; by_priority counts in API response |
| REC-04 | 01, 02, 03 | Classify sentiment of AI mentions and surface patterns per engine | SATISFIED | SentimentService uses gemini-2.5-flash; analyze_audit_sentiments() creates MentionSentiment records; get_per_engine_summary() returns {positive,negative,neutral,total,dominant} per engine; SentimentBreakdown.vue renders per-engine grid |
| REC-05 | 01, 02, 03 | Identify content gaps: topics where competitors mentioned but user is not | SATISFIED | identify_content_gaps() and save_content_gaps() now called in RECOMMENDING stage (audit_tasks.py:319-320); _template_brief() generates mini briefs with title and key_points; GET /content-gaps endpoint reads real data; ContentGapCard.vue renders the results |

**Orphaned requirements:** None. All 5 REC requirements appear in at least one plan's `requirements` field and are satisfied.

---

## Anti-Patterns Found

None. The blocker identified in the previous verification (content gap methods not called in pipeline) has been resolved. No new anti-patterns detected.

---

## Human Verification Required

None — all critical paths are verifiable programmatically. The two previously-failing items are now confirmed fixed by source code inspection.

---

## Summary

Phase 8 is fully complete. The single root-cause gap from the initial verification — `identify_content_gaps()` and `save_content_gaps()` not wired into the Celery pipeline — has been fixed by adding 3 lines to the RECOMMENDING stage in `audit_tasks.py` (lines 318-325). The `db.commit()` that follows (line 327) persists the content gaps atomically with recommendations and sentiment records.

All 13 truths are now VERIFIED:
- Recommendation engine: 13 research-backed criteria, deterministic gap analysis, competitor comparison, priority classification, hash-based status carry-over
- Content gaps: fully wired — pipeline identifies gaps, saves to JSONB column, API reads and returns real data, ContentGapCard.vue renders mini briefs with title and key points
- Sentiment service: gemini-2.5-flash with explicit api_key, per-engine aggregation
- API: 5 endpoints, auth-protected with 403/404 ownership verification, Literal status validation
- Frontend: Two-tier cards, progress bar, per-engine sentiment grid, content gap cards (now with data), Markdown export, sidebar navigation, audit page preview

---

_Verified: 2026-02-23_
_Verifier: Claude (gsd-verifier)_
