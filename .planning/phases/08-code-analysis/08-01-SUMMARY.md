---
phase: 08-code-analysis
plan: 01
subsystem: code-analysis-backend
tags: [code-analysis, prompt-generation, litellm, celery, alembic, pydantic, pro-tier]
dependency_graph:
  requires: [audits, profiles, criterion_results, page_scores, celery, litellm]
  provides: [code_analyses table, code_recommendations table, code analysis API, prompt generator, LLM parser]
  affects: [main.py router registry, celery_app include list, models __init__.py]
tech_stack:
  added: []
  patterns: [LiteLLM structured output with response_format=CodeAnalysisResult, template-based prompt generation, Celery async upload pattern (202 + poll)]
key_files:
  created:
    - backend/app/models/code_analysis.py
    - backend/app/schemas/code_analysis.py
    - backend/app/services/code_analysis_service.py
    - backend/app/tasks/code_analysis_tasks.py
    - backend/app/api/code_analysis.py
    - backend/alembic/versions/015_add_code_analysis.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/core/config.py
    - backend/app/tasks/celery_app.py
    - backend/app/main.py
decisions:
  - key: Prompt generation is purely template-based with zero LLM calls — sub-200ms response
  - key: Prompts expose zero scoring logic — no criterion IDs, no thresholds, no weights — IP protection enforced
  - key: Download endpoint is a separate /prompts/download route rather than Accept-header negotiation to avoid FastAPI response_model conflict
  - key: Pre-existing test_payments failure (NameError on Audit import in test file) is out-of-scope — confirmed pre-existing before Task 2
metrics:
  duration_minutes: 45
  completed_at: "2026-02-26T12:50:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 4
---

# Phase 8 Plan 01: Code Analysis Backend Summary

Code analysis backend built end-to-end: SQLAlchemy models + Alembic migration 015, Pydantic schemas including LLM structured output types, PromptGeneratorService (deterministic, template-based, zero LLM), CodeAnalysisService (LiteLLM `response_format=CodeAnalysisResult` with explicit `api_key=`), Celery processing task, and 6 Pro-tier API endpoints registered in main.py.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Models, migration, schemas, config | a911a21a | code_analysis.py (model), schemas/code_analysis.py, config.py, 015_add_code_analysis.py, models/__init__.py |
| 2 | Service, Celery task, API router, main.py | 8d0ec385 | code_analysis_service.py, code_analysis_tasks.py, api/code_analysis.py, main.py, celery_app.py |

## What Was Built

### DB Layer (Task 1)
- **CodeAnalysis** model (`code_analyses` table): tracks one upload session per audit. Columns: id, audit_id, user_id, status (pending/parsing/recommending/completed/failed), raw_output (Text), raw_output_size_bytes, detected_framework, parsed_findings (JSONB), prompt_categories_used (JSONB), model_used, error_message, created_at, completed_at.
- **CodeRecommendation** model (`code_recommendations` table): one row per finding. Columns: id, code_analysis_id, audit_id, criterion_id (nullable), category, severity (high/medium/low), finding, file_path, suggestion, code_snippet, evidence, status (open/done/dismissed), created_at.
- Migration 015 applied — both tables created with 4 indexes.

### Config (Task 1)
Three new settings in `Settings`:
- `CODE_ANALYSIS_MODEL = "gemini/gemini-2.5-flash"`
- `CODE_ANALYSIS_MAX_UPLOAD_BYTES = 102400` (100KB)
- `CODE_ANALYSIS_MAX_TOKENS_INPUT = 50000`

### Schemas (Task 1)
- `CodeUploadRequest`, `GeneratedPrompt`, `PromptsResponse` (request + prompt schemas)
- `CodeFinding`, `CodeAnalysisResult` (LLM structured output — used as `response_format=`)
- `CodeAnalysisResponse`, `CodeRecommendationResponse`, `CodeRecommendationUpdateRequest` (API responses)

### Services (Task 2)
**PromptGeneratorService:**
- `CATEGORY_TEMPLATES` dict with 4 categories (crawlability, content_structure, structured_data, authority) — full diagnostic prompt text, zero scoring logic
- `detect_framework()`: case-insensitive HTML/headers scan across 11 frameworks
- `_load_failing_categories()`: joins CriterionResult → PageScore, filters score < 50, distinct categories
- `generate_prompts()`: ordered by priority (crawlability/structured_data first), appends framework hints when detected, builds downloadable Markdown bundle

**CodeAnalysisService:**
- `_resolve_api_key()`: prefix-based model → API key (gemini/anthropic/gpt/o1/o3)
- `parse_output()`: truncates to 50K chars, calls `litellm.acompletion(response_format=CodeAnalysisResult, api_key=api_key, temperature=0.1)`, validates with `CodeAnalysisResult.model_validate_json()`
- `generate_code_recommendations()`: bulk insert CodeRecommendation rows from parsed findings

### Celery Task (Task 2)
`process_code_analysis` (`app.tasks.code_analysis.process_upload`): status lifecycle pending → parsing → recommending → completed/failed. Uses `asyncio.run()` for the async LiteLLM call within sync Celery context. Registered in `celery_app.py` include list.

### API Endpoints (Task 2)
All 6 routes at prefix `/api/v1/code-analysis/{audit_id}`, all `require_tier(SubscriptionTier.PRO)`, all verify audit ownership:

| Method | Path | Response |
|--------|------|----------|
| POST | `/{audit_id}/prompts` | PromptsResponse (JSON) |
| POST | `/{audit_id}/prompts/download` | Markdown file (text/markdown) |
| POST | `/{audit_id}/upload` | 202 + {id, status, message} |
| GET | `/{audit_id}` | CodeAnalysisResponse |
| GET | `/{audit_id}/recommendations` | list[CodeRecommendationResponse] |
| PATCH | `/{audit_id}/recommendations/{rec_id}` | CodeRecommendationResponse |

Upload endpoint: accepts both `UploadFile` (multipart) and `CodeUploadRequest` (JSON body); enforces 100KB limit (413 if exceeded); triggers `process_code_analysis.delay(str(code_analysis.id))`.

## Verification Results

All plan verifications passed:
- `python -c "from app.models.code_analysis import CodeAnalysis, CodeRecommendation; print('Models OK:', ...)"` — PASSED
- `python -c "from app.schemas.code_analysis import ...; print('Schemas OK')"` — PASSED
- `python -c "from app.core.config import settings; print('Model:', settings.CODE_ANALYSIS_MODEL, ...)"` — PASSED: `gemini/gemini-2.5-flash`, `102400`
- `alembic current` — PASSED: `015 (head)`
- `python -c "from app.services.code_analysis_service import ...; print('Services OK')"` — PASSED
- `python -c "from app.tasks.code_analysis_tasks import process_code_analysis; print('Task OK:', ...)"` — PASSED: `app.tasks.code_analysis.process_upload`
- Router routes verification — PASSED: 6 routes listed
- Main app routes — PASSED: 6 `/code-analysis` routes registered
- `grep "api_key=" app/services/code_analysis_service.py` — PASSED: explicit `api_key=api_key`
- IP protection check — PASSED: no criterion IDs/scores/thresholds in CATEGORY_TEMPLATES
- pytest (72 passing tests) — PASSED. 1 pre-existing failure in `test_payments.py::TestTierGatingIntegration::test_recommendations_endpoint_returns_402_for_free_user` (NameError on Audit import in test file — pre-dates Phase 8, confirmed by stash check)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one deliberate extension:

**Download endpoint as separate route (not Accept-header negotiation):**
The plan described Accept-header negotiation on `POST /{audit_id}/prompts`. FastAPI's `response_model=PromptsResponse` annotation conflicts with returning `PlainTextResponse` from the same function. To avoid a messy type override, the download path was exposed as a clean separate route `POST /{audit_id}/prompts/download`. The JSON endpoint `POST /{audit_id}/prompts` returns `PromptsResponse` (including `markdown_bundle` in the JSON so the frontend can still do its own download). This is cleaner and more explicit than header negotiation.

## Decisions Made

1. Prompt generation is template-based with zero LLM calls — sub-200ms guaranteed, no per-call cost
2. IP protection enforced: CATEGORY_TEMPLATES contain only diagnostic questions ("Find all...", "Check for...") — zero criterion IDs, scores, or weights
3. Download endpoint is `/prompts/download` (separate route) rather than Accept-header switching on same endpoint — avoids FastAPI response_model conflict
4. Framework detection appends a lightweight note to prompt text rather than rewriting the template — keeps templates clean and reusable
5. Pre-existing `test_payments.py` test failure (NameError) documented as out-of-scope — not caused by Phase 8 changes

## Self-Check: PASSED

Files created:
- backend/app/models/code_analysis.py: FOUND
- backend/app/schemas/code_analysis.py: FOUND
- backend/app/services/code_analysis_service.py: FOUND
- backend/app/tasks/code_analysis_tasks.py: FOUND
- backend/app/api/code_analysis.py: FOUND
- backend/alembic/versions/015_add_code_analysis.py: FOUND

Commits:
- a911a21a: FOUND (feat(08-01): add code analysis models, schemas, config, and migration)
- 8d0ec385: FOUND (feat(08-01): add code analysis service, Celery task, API router, and main.py registration)

DB: Migration 015 applied — `alembic current` shows `015 (head)`.
