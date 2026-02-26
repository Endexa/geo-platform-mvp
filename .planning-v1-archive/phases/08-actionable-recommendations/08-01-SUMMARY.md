---
phase: 08-actionable-recommendations
plan: 01
subsystem: backend, pipeline
tags: [recommendation-engine, sentiment-analysis, gap-analysis, litellm, gemini, celery, sqlalchemy]

# Dependency graph
requires:
  - phase: 06-site-ai-readiness-scoring
    provides: CriterionResult and PageScore records per page for gap analysis
  - phase: 07-auto-competitor-discovery
    provides: CompetitorAudit category averages for competitor comparison
provides:
  - AuditRecommendation model and table for page-specific gap analysis recommendations
  - MentionSentiment model and table for per-mention sentiment classification
  - RecommendationEngine service with 13 research-backed criteria benchmarks
  - SentimentService using gemini-2.5-flash for LLM sentiment classification
  - RECOMMENDING pipeline stage between DISCOVERING_COMPETITORS and COMPLETED
  - content_gaps JSONB column on Audit model
  - Recommendation hash system for cross-audit status carry-over
affects: [08-02, 08-03, 09-dashboard-reporting]

# Tech tracking
tech-stack:
  added: []
  patterns: [deterministic-gap-analysis, research-benchmark-map, recommendation-hash-carry-over, non-fatal-pipeline-stage]

key-files:
  created:
    - backend/app/models/audit_recommendation.py
    - backend/app/models/mention_sentiment.py
    - backend/app/services/recommendation_engine.py
    - backend/app/services/sentiment_service.py
    - backend/alembic/versions/008_add_recommendations_sentiments_content_gaps.py
  modified:
    - backend/app/models/audit.py
    - backend/app/models/__init__.py
    - backend/alembic/env.py
    - backend/app/tasks/audit_tasks.py
    - frontend/components/AuditProgress.vue

key-decisions:
  - "13 research-backed criteria in CRITERION_RESEARCH_MAP covering Princeton GEO, BrightEdge, Surfer SEO, Frase.io, Ahrefs 75K, Otterly.ai"
  - "Code snippet templates for top 10 highest-impact criteria (SD3, SD1, SD7, C9, CS5, SD12, CS4, CS2, CS10, A3)"
  - "Negative sentiments generate site-wide recommendations with criterion_id=SENTIMENT"
  - "RECOMMENDING stage is non-fatal (try/except) matching competitor discovery pattern"
  - "Sentiment fallback: neutral/50 if no GEMINI_API_KEY"

patterns-established:
  - "Deterministic gap analysis: compare criterion scores against competitor averages and research thresholds"
  - "Priority classification: HIGH if gap>=50 OR (impact>=200 AND gap>=30), MEDIUM if impact>=120 AND gap>=20"
  - "Recommendation hash: SHA-256 of criterion_id|normalized_url truncated to 16 chars for cross-audit tracking"
  - "Non-fatal pipeline stage: wrap in try/except, log error, continue to COMPLETED"

requirements-completed: [REC-01, REC-02, REC-03, REC-04]

# Metrics
duration: 5min
completed: 2026-02-23
---

# Phase 8 Plan 01: Recommendation Engine Backend Summary

**Deterministic gap analysis engine with 13 research-backed criteria, LLM sentiment classification via gemini-2.5-flash, and RECOMMENDING Celery pipeline stage**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-22T22:55:01Z
- **Completed:** 2026-02-22T23:00:22Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- AuditRecommendation and MentionSentiment models with migration 008 creating both tables and content_gaps column
- RecommendationEngine with CRITERION_RESEARCH_MAP (13 criteria), CRITERION_SNIPPETS (10 code templates), priority classification, and recommendation hash carry-over
- SentimentService using gemini-2.5-flash with explicit api_key pattern for LLM-based 3-class sentiment classification
- RECOMMENDING stage wired into Celery pipeline (non-fatal) between DISCOVERING_COMPETITORS and COMPLETED
- AuditProgress.vue updated to 8 pipeline steps including discovering_competitors and recommending

## Task Commits

Each task was committed atomically:

1. **Task 1: Create AuditRecommendation and MentionSentiment models with migration 008** - `62fa894b` (feat)
2. **Task 2: Implement RecommendationEngine, SentimentService, and wire RECOMMENDING Celery stage** - `4eb2bcbc` (feat)

## Files Created/Modified
- `backend/app/models/audit_recommendation.py` - AuditRecommendation SQLAlchemy model with gap analysis fields and recommendation_hash
- `backend/app/models/mention_sentiment.py` - MentionSentiment SQLAlchemy model for per-mention sentiment classification
- `backend/app/services/recommendation_engine.py` - RecommendationEngine with 13 research benchmarks, priority classification, code snippets
- `backend/app/services/sentiment_service.py` - SentimentService with gemini-2.5-flash LLM classification and per-engine aggregation
- `backend/alembic/versions/008_add_recommendations_sentiments_content_gaps.py` - Migration creating audit_recommendations, mention_sentiments tables and content_gaps column
- `backend/app/models/audit.py` - Added AuditStatus.RECOMMENDING and content_gaps JSONB column
- `backend/app/models/__init__.py` - Added AuditRecommendation and MentionSentiment imports
- `backend/alembic/env.py` - Added new model imports for Alembic metadata
- `backend/app/tasks/audit_tasks.py` - Added RECOMMENDING stage (Stage 7) with sentiment + recommendation generation
- `frontend/components/AuditProgress.vue` - Updated from 6 to 8 pipeline steps

## Decisions Made
- 13 criteria in CRITERION_RESEARCH_MAP with evidence from Princeton GEO paper, BrightEdge, Surfer SEO 46M analysis, Frase.io, Ahrefs 75K study, Otterly.ai, and industry research
- Code snippet templates provided for top 10 criteria (SD3/FAQPage, SD1/Organization, SD7/JSON-LD, C9/SSR, CS5/FAQ section, SD12/llms.txt, CS4/data tables, CS2/answer-first, CS10/statistics, A3/Knowledge Graph)
- Negative mention sentiments generate site-wide AuditRecommendation records with criterion_id="SENTIMENT" and page_url=None
- SentimentService returns neutral/50 fallback when GEMINI_API_KEY is not set (graceful degradation)
- RECOMMENDING stage wrapped in try/except to match competitor discovery non-fatal pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. GEMINI_API_KEY is already configured from Phase 3.

## Next Phase Readiness
- Recommendation engine backend is complete and ready for API layer (08-02)
- Models, services, and pipeline stage all verified importable
- Frontend progress stepper ready for the full 8-stage pipeline
- Content gap identification and Markdown export will be built in subsequent plans

---
*Phase: 08-actionable-recommendations*
*Completed: 2026-02-23*
