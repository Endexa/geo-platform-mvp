---
phase: 08-code-analysis
plan: 02
subsystem: code-analysis-frontend-tests
tags: [code-analysis, vue3, nuxt3, composables, vueuse, unit-tests, ip-protection]
dependency_graph:
  requires: [08-01, useApiFetch, useSubscription, useIntervalFn, audit.vue]
  provides: [useCodeAnalysis, CodeAnalysisPrompts, CodeAnalysisUpload, CodeRecommendationCard, test_code_analysis]
  affects: [frontend/pages/audit.vue]
tech_stack:
  added: []
  patterns: [useIntervalFn polling (3-second interval, stops on completed/failed), Nuxt 3 component auto-import, blob download trigger from composable, asyncio.run mock in Celery task tests]
key_files:
  created:
    - frontend/composables/useCodeAnalysis.ts
    - frontend/components/CodeAnalysisPrompts.vue
    - frontend/components/CodeAnalysisUpload.vue
    - frontend/components/CodeRecommendationCard.vue
    - backend/tests/test_code_analysis.py
  modified:
    - frontend/pages/audit.vue
decisions:
  - key: CodeRecommendationCard extracted as separate component — CodeAnalysisUpload delegates card rendering to keep template manageable
  - key: Celery task tests use task.run() instead of __wrapped__ — run() is the correct way to invoke bind=True tasks in unit tests without Celery infrastructure
  - key: IP protection test (CODE-04) uses three regex patterns to catch criterion IDs in any form (C1, CS5, SD13, A8, S15)
  - key: Pre-existing test_payments.py failures (2 tests, same NameError on Audit import) confirmed out-of-scope — predates Phase 8
metrics:
  duration_minutes: 35
  completed_at: "2026-02-26T14:15:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 1
---

# Phase 8 Plan 02: Code Analysis Frontend + Tests Summary

Frontend code analysis experience built end-to-end: `useCodeAnalysis` composable (prompt download blob trigger, upload, 3-second `useIntervalFn` polling, recommendations fetch), `CodeAnalysisPrompts` component (download button with category pills and step instructions), `CodeAnalysisUpload` component (paste/file upload tabs, animated status, recommendations grouped by severity with `CodeRecommendationCard`), `audit.vue` integration behind `isProUser` gate, and 25 backend unit tests covering all services, endpoints, and Celery task lifecycle.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Frontend: composable, components, audit.vue integration | b8fab5df | useCodeAnalysis.ts, CodeAnalysisPrompts.vue, CodeAnalysisUpload.vue, CodeRecommendationCard.vue, audit.vue |
| 2 | Backend: 25 unit tests for code analysis | c6e9f917 | test_code_analysis.py |

## What Was Built

### useCodeAnalysis Composable (Task 1)

`frontend/composables/useCodeAnalysis.ts`:
- Exports `useCodeAnalysis(auditId: Ref<string>)` returning `{ isDownloading, isUploading, isPolling, codeAnalysis, recommendations, error, downloadPrompts, uploadOutput, loadAnalysis, loadRecommendations }`
- `downloadPrompts()`: POSTs to `/code-analysis/{id}/prompts`, creates `Blob` from `markdown_bundle`, triggers browser download via anchor click + `URL.createObjectURL`
- `uploadOutput(text, categories)`: Guards on `isUploading` and `text.trim().length < 10`, POSTs to `/code-analysis/{id}/upload`, starts 3-second polling on success
- `loadAnalysis()`: GETs current status, silently ignores 404 (no analysis yet), calls `loadRecommendations()` on `completed`, sets `error.value` on `failed`
- Polling: `useIntervalFn` from `@vueuse/core` at 3000ms (immediate: false), stops automatically when status is `completed` or `failed`
- `watch(auditId, ..., { immediate: true })`: checks for existing analysis on mount/ID change

### CodeAnalysisPrompts Component (Task 1)

`frontend/components/CodeAnalysisPrompts.vue`:
- Section header with "Code Analysis" (Fira Code font-mono) and "Pro" badge (blue-100/blue-800)
- Description text explaining the workflow
- 4 category pills: Crawlability (blue), Content Structure (green), Structured Data (purple), Authority & SEO (amber)
- Download button: bg-blue-700, ArrowDownTrayIcon SVG, loading spinner during `isDownloading`, disabled state with opacity
- 5-step numbered instructions below button
- Error display (red-600) when `error` is set
- All interactive elements: `cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500`

### CodeAnalysisUpload Component (Task 1)

`frontend/components/CodeAnalysisUpload.vue`:
- Three view states: upload form (null/failed), status progress (pending/parsing/recommending), results (completed)
- Upload form: category checkboxes (4), tabbed interface (Paste/File), textarea (min-h-200px, font-mono, focus ring), file input accepting .txt/.md/.json with FileReader, character count with 100KB amber warning
- Status section: color-coded pills (gray/blue+pulse/amber+pulse/red), status messages, polling indicator
- Results section: framework badge, issues count, recommendations grouped by High/Medium/Low severity with icons (ExclamationTriangle, ExclamationCircle, InformationCircle SVG)
- Delegates individual rec rendering to `CodeRecommendationCard`
- Status update: PATCH call via `useApiFetch` on select change

### CodeRecommendationCard Component (Task 1)

`frontend/components/CodeRecommendationCard.vue`:
- Category pill with per-category color mapping (crawlability=blue, content_structure=green, structured_data=purple, authority=amber)
- Criterion ID badge (gray font-mono) when present
- Status dropdown (open/done/dismissed) emitting `status-change` event
- Finding text (font-semibold), file path (font-mono with folder SVG), suggestion text
- Code snippet in `<pre><code>` with max-h-32 overflow-y-auto
- Collapsible evidence section ("Show/Hide evidence" toggle)

### audit.vue Integration (Task 1)

- Code Analysis section added below export buttons (mt-6, border-t, pt-6)
- `v-if="isProUser"`: renders `<CodeAnalysisPrompts>` + `<CodeAnalysisUpload>` with `auditId`
- `v-else`: shows "Upgrade to Pro to get code-level recommendations" with /pricing link
- Section is inside the `v-if="isCompleted && auditId"` wrapper — only visible on completed audits

### Backend Tests (Task 2)

`backend/tests/test_code_analysis.py` — 25 tests across 9 test classes:

**TestPromptGeneratorServiceStructure (3 tests):**
- `test_generate_prompts_returns_correct_structure`: mocks DB returning 3 failing categories, verifies PromptsResponse structure, non-empty title/prompt_text/priority, domain in markdown_bundle
- `test_generate_prompts_caps_at_four_categories`: all 4 categories failing → at most 4 prompts
- `test_failing_categories_fallback`: empty DB result → returns all 4 categories

**TestPromptIpProtection (1 test — CODE-04):**
- `test_generate_prompts_no_scoring_logic_leaked`: generates prompts for all 4 categories, asserts no criterion IDs (regex `[CA][0-9]+`, `(CS|SD|A)[0-9]+`, `S[0-9]+`), no forbidden words (threshold/weight/gap_score/criterion_result), no score fractions (e.g., "30/100")

**TestFrameworkDetection (3 tests):**
- nextjs (`_next/` in HTML), wordpress (`wp-content`), unknown (no hints → None)

**TestCodeAnalysisServiceParsing (3 tests):**
- `test_parse_output_calls_litellm_with_structured_format`: verifies `response_format=CodeAnalysisResult`, `model=settings.CODE_ANALYSIS_MODEL`
- `test_parse_output_passes_explicit_api_key`: verifies `api_key` is non-None, non-empty
- `test_parse_output_truncates_oversized_input`: 60K+ char input truncated to ≤ `CODE_ANALYSIS_MAX_TOKENS_INPUT`

**TestCodeAnalysisServiceResolveApiKey (2 tests):**
- gemini prefix → `settings.GEMINI_API_KEY` (pydantic-settings, not os.environ)

**TestCodeAnalysisServiceRecommendations (1 test):**
- `test_generate_code_recommendations_creates_records`: 3 findings → `db.add` called 3 times, `db.commit` once

**TestEndpointTierGating (3 tests):** `_check_tier` dependency present on prompts/upload/status routes

**TestGetOwnedAuditHelper (2 tests):** 404 for other user's audit, 400 for non-completed audit

**TestUploadEndpoint (2 tests):** 100KB constant correct (102400), record creation + `process_code_analysis.delay` called

**TestStatusEndpoint (1 test):** 404 when no CodeAnalysis record in DB

**TestRecommendationsEndpoint (2 tests):** 2 items returned, invalid status → 400

**TestProcessCodeAnalysisTask (2 tests):**
- Happy path: mocks `CodeAnalysisService.parse_output` + `generate_code_recommendations`, calls `task.run(id)`, asserts `ca.status == "completed"` and `ca.completed_at is not None`
- Failure: `parse_output` raises → `ca.status == "failed"` and `ca.error_message` non-empty

## Verification Results

All plan verifications passed:
- `npm run build` — PASSED: frontend builds with no TypeScript or template errors
- `grep "export function useCodeAnalysis"` — PASSED
- `grep -c "CodeAnalysisPrompts" audit.vue` → 3 (>= 2 requirement) — PASSED
- `grep -c "CodeAnalysisUpload" audit.vue` → 3 (>= 2 requirement) — PASSED
- `grep "isProUser" audit.vue` — PASSED: code analysis section gated
- `pytest tests/test_code_analysis.py -v` — PASSED: 25/25 green
- `pytest tests/ -q --ignore=tests/test_payments.py` — PASSED: 194 passed
- `grep "test_generate_prompts_no_scoring_logic_leaked"` — PASSED: IP protection test present
- `grep "useIntervalFn" useCodeAnalysis.ts` — PASSED: polling implemented

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] CodeRecommendationCard extracted as standalone component**
- **Found during:** Task 1, implementing CodeAnalysisUpload
- **Issue:** Plan specified inline recommendation cards within CodeAnalysisUpload, but the full card spec (category pills, file path, code snippet, evidence toggle, status dropdown) would make the template unwieldy (200+ lines inline)
- **Fix:** Extracted `CodeRecommendationCard.vue` as a separate auto-imported Nuxt component. CodeAnalysisUpload uses `<CodeRecommendationCard>` for each severity group. This is a clean composition pattern consistent with the project's component style.
- **Files modified:** CodeAnalysisUpload.vue, CodeRecommendationCard.vue (new)
- **Impact:** None — Nuxt auto-imports both components; build passes

**2. [Rule 1 - Bug] Celery task test invocation via `task.run()` not `__wrapped__`**
- **Found during:** Task 2, first test run
- **Issue:** Initial implementation used `process_code_analysis.__wrapped__(process_code_analysis, str(ca.id))` which passed 3 args to a `bind=True` function expecting 2
- **Fix:** Changed to `task_fn.run(*args)` — Celery's `run` attribute calls the underlying function with the task instance already bound
- **Files modified:** test_code_analysis.py
- **Commit:** c6e9f917 (fixed before commit)

### Pre-existing Issues (Out of Scope)

**test_payments.py failures (2 tests):**
Both `TestTierGatingIntegration::test_recommendations_endpoint_returns_402_for_free_user` and `TestFreeTierFilteringIntegration::test_free_user_sees_limited_response` fail with `NameError: name 'Audit' is not defined`. Same root cause as documented in 08-01 summary. Pre-dates Phase 8. Not caused by Phase 8 changes.

## Decisions Made

1. CodeRecommendationCard extracted as standalone component — keeps CodeAnalysisUpload template under 200 lines and follows the project's single-responsibility component pattern
2. Celery task unit tests call `task.run()` (not `task.apply()` or `__wrapped__`) — `run` is the correct attribute for testing bind=True tasks without Celery infrastructure
3. IP protection test checks three distinct regex patterns + 4 forbidden words + score fraction pattern — comprehensive coverage of all ways scoring logic could accidentally leak into prompts
4. `watch(auditId, ..., { immediate: true })` used instead of `onMounted` — correctly handles both initial mount and cases where auditId changes after mount

## Self-Check: PASSED

Files created:
- frontend/composables/useCodeAnalysis.ts: FOUND
- frontend/components/CodeAnalysisPrompts.vue: FOUND
- frontend/components/CodeAnalysisUpload.vue: FOUND
- frontend/components/CodeRecommendationCard.vue: FOUND
- backend/tests/test_code_analysis.py: FOUND

Files modified:
- frontend/pages/audit.vue: FOUND (contains CodeAnalysisPrompts, CodeAnalysisUpload, isProUser references)

Commits:
- b8fab5df: FOUND (feat(08-02): add useCodeAnalysis composable, CodeAnalysisPrompts, CodeAnalysisUpload, audit.vue integration)
- c6e9f917: FOUND (test(08-02): add comprehensive backend unit tests for code analysis feature)

Tests: 25/25 passing in test_code_analysis.py
Build: npm run build succeeds (nitro output generated)
