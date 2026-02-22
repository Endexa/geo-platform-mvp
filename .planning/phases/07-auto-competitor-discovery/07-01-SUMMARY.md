---
phase: 07-auto-competitor-discovery
plan: 01
subsystem: backend, ai, database
tags: [spacy, ner, entity-extraction, competitor-discovery, citations, rapidfuzz]

# Dependency graph
requires:
  - phase: 04-mention-detection-scoring
    provides: "EngineResponse model with AI response text for NER extraction"
  - phase: 06-site-ai-readiness-scoring
    provides: "Scoring pipeline stage that competitor discovery follows"
provides:
  - "DiscoveredCompetitor and CompetitorAudit SQLAlchemy models"
  - "EntityExtractorService with spaCy NER, citation extraction, deduplication, and SOV computation"
  - "Migration 007 creating competitors tables and adding citations/query flags columns"
  - "DISCOVERING_COMPETITORS pipeline stage between SCORING and COMPLETED"
  - "Perplexity citation capture and inline URL extraction in DispatchService"
affects: [07-02, 07-03, 07-04, 08-recommendations]

# Tech tracking
tech-stack:
  added: [spacy, en_core_web_sm]
  patterns: [lazy-loaded-nlp-model, fuzzy-entity-deduplication, share-of-voice-computation]

key-files:
  created:
    - backend/app/models/competitor.py
    - backend/app/services/entity_extractor.py
    - backend/alembic/versions/007_add_competitors_and_citations.py
  modified:
    - backend/app/models/engine_response.py
    - backend/app/models/audit_query.py
    - backend/app/models/audit.py
    - backend/app/models/__init__.py
    - backend/alembic/env.py
    - backend/app/core/config.py
    - backend/requirements.txt
    - backend/app/services/dispatch_service.py
    - backend/app/tasks/audit_tasks.py

key-decisions:
  - "spaCy en_core_web_sm loaded lazily at class level to avoid startup cost"
  - "Entities require at least 2 appearances to filter NER noise (per research pitfall 2)"
  - "Corporate suffixes stripped before rapidfuzz deduplication (85% threshold)"
  - "competitor_audits table created first for FK reference from discovered_competitors"
  - "Citations captured from both Perplexity API metadata and inline URL regex for all engines"

patterns-established:
  - "Lazy NLP model loading: class-level _nlp cache with _get_nlp() classmethod"
  - "Entity deduplication: strip suffixes, rapidfuzz token_set_ratio, group by threshold"
  - "Share-of-voice: entity_mentions / total_mentions * 100, is_user_brand via fuzz.ratio > 90"
  - "Generic blocklist filtering: hardcoded set of non-entity terms"

requirements-completed: [COMP-01, COMP-02, COMP-07]

# Metrics
duration: 6min
completed: 2026-02-22
---

# Phase 7 Plan 01: Entity Extraction Foundation Summary

**spaCy NER entity extraction from AI responses with rapidfuzz deduplication, share-of-voice computation, Perplexity citation capture, and DISCOVERING_COMPETITORS pipeline stage**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-22T21:26:18Z
- **Completed:** 2026-02-22T21:32:22Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- DiscoveredCompetitor and CompetitorAudit models with full schema (SOV, engines, queries, crawl status)
- EntityExtractorService extracting ORG/PRODUCT entities via spaCy NER, deduplicating with rapidfuzz, and computing share-of-voice percentages
- Perplexity citations captured from API response metadata; inline URL extraction for all engines
- 7-stage audit pipeline: CRAWLING -> GENERATING_QUERIES -> DISPATCHING -> ANALYZING -> SCORING -> DISCOVERING_COMPETITORS -> COMPLETED

## Task Commits

Each task was committed atomically:

1. **Task 1: Create competitor models, migration 007, and config settings** - `c59dc3a2` (feat)
2. **Task 2: Create EntityExtractorService, capture Perplexity citations, add DISCOVERING_COMPETITORS pipeline stage** - `f15ee199` (feat)

## Files Created/Modified
- `backend/app/models/competitor.py` - DiscoveredCompetitor and CompetitorAudit SQLAlchemy models
- `backend/app/services/entity_extractor.py` - EntityExtractorService with NER, citation extraction, deduplication, SOV
- `backend/alembic/versions/007_add_competitors_and_citations.py` - Migration: 2 tables, 3 columns
- `backend/app/models/engine_response.py` - Added citations JSONB column
- `backend/app/models/audit_query.py` - Added is_custom and is_editable Boolean columns
- `backend/app/models/audit.py` - Added DISCOVERING_COMPETITORS to AuditStatus enum
- `backend/app/models/__init__.py` - Exported DiscoveredCompetitor, CompetitorAudit
- `backend/alembic/env.py` - Imported competitor models for metadata
- `backend/app/core/config.py` - Phase 7 settings (COMPETITOR_CRAWL_CAP, COMPETITOR_MAX_COUNT, COMPETITOR_URL_RESOLVE_TIMEOUT)
- `backend/requirements.txt` - Added spacy>=3.7
- `backend/app/services/dispatch_service.py` - Perplexity citation capture + inline URL extraction
- `backend/app/tasks/audit_tasks.py` - DISCOVERING_COMPETITORS stage (Stage 6) between SCORING and COMPLETED

## Decisions Made
- **spaCy lazy loading:** Class-level `_nlp` cache avoids loading 12MB model on every service instantiation
- **Min-2-appearances filter:** Entities appearing in only 1 response are filtered out to reduce NER noise (Research pitfall 2)
- **Corporate suffix stripping:** "Inc.", "LLC", "Ltd.", "Corp." stripped before fuzzy comparison to merge "Stripe Inc." with "Stripe"
- **competitor_audits table first:** Created before discovered_competitors to satisfy FK constraint on competitor_audit_id
- **Dual citation capture:** Perplexity API metadata + inline URL regex for all engines ensures maximum citation coverage

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. spaCy en_core_web_sm model should be downloaded at Docker build time via `python -m spacy download en_core_web_sm`.

## Next Phase Readiness
- Entity extraction foundation complete, ready for Plan 02 (competitor URL resolution and crawl)
- DiscoveredCompetitor records will be created during audits, ready for competitor benchmarking
- CompetitorAudit model ready for Plan 03 (competitor scoring pipeline)

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 07-auto-competitor-discovery*
*Completed: 2026-02-22*
