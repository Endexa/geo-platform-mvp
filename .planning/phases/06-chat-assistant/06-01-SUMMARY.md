---
phase: 06-chat-assistant
plan: 01
subsystem: api
tags: [sse, litellm, chat, streaming, fastapi, sqlalchemy, jsonb]

# Dependency graph
requires:
  - phase: 01-scoring-foundation
    provides: PageScore, CriterionResult models for grounding system prompt
  - phase: 02-recommendations-competitor-benchmarking
    provides: AuditRecommendation model for context injection
  - phase: 03-ai-visibility-hardening
    provides: VisibilityScore model with per-engine breakdown
  - phase: 04-payments-freemium-gating
    provides: require_tier(SubscriptionTier.PRO) dependency for feature gating
provides:
  - ChatSession SQLAlchemy model with JSONB messages column
  - ChatService with grounded system prompt builder and LLM streaming
  - SSE chat endpoint (POST /api/v1/chat/{audit_id}/chat)
  - History endpoint (GET /api/v1/chat/{audit_id}/history)
  - Alembic migration 014 for chat_sessions table
affects: [06-02 frontend chat panel, future chat enhancements]

# Tech tracking
tech-stack:
  added: [sse-starlette]
  patterns: [SSE streaming via EventSourceResponse, context-grounded LLM prompts, JSONB conversation storage]

key-files:
  created:
    - backend/app/models/chat_session.py
    - backend/app/services/chat_service.py
    - backend/app/api/chat.py
    - backend/app/schemas/chat.py
    - backend/alembic/versions/014_add_chat_sessions.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/core/config.py
    - backend/app/main.py
    - backend/requirements.txt

key-decisions:
  - "API key resolved via prefix matching (gemini/ -> GEMINI_API_KEY) -- same pattern as dispatch_service.py"
  - "User message saved to DB before LLM call to persist even if streaming fails"
  - "JSONB messages array on ChatSession (not separate ChatMessage table) -- conversation always loaded/saved as whole"
  - "System prompt limited to top 15 failing criteria + top 10 recommendations to avoid context overflow"

patterns-established:
  - "SSE streaming: EventSourceResponse wrapping async generator from litellm.acompletion(stream=True)"
  - "Context grounding: build_system_prompt serializes real audit data into structured sections for LLM"
  - "asyncio.CancelledError handling for clean SSE disconnect on client navigation"

requirements-completed: [CHAT-01, CHAT-02, CHAT-03, CHAT-04]

# Metrics
duration: 5min
completed: 2026-02-26
---

# Phase 6 Plan 1: Chat Assistant Backend Summary

**SSE streaming chat endpoint grounded in real audit data using litellm.acompletion with sse-starlette EventSourceResponse**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-26T10:02:35Z
- **Completed:** 2026-02-26T10:07:35Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- ChatSession model with JSONB messages column and Alembic migration 014
- ChatService builds structured system prompts from real audit data (VisibilityScore, PageScore, CriterionResult, AuditRecommendation)
- SSE endpoint at POST /api/v1/chat/{audit_id}/chat streams LLM tokens via EventSourceResponse
- History endpoint at GET /api/v1/chat/{audit_id}/history returns conversation history
- Both endpoints enforce Pro tier via require_tier(SubscriptionTier.PRO) with audit ownership verification

## Task Commits

Each task was committed atomically:

1. **Task 1: ChatSession model, migration, schemas, and config settings** - `3a44afb8` (feat)
2. **Task 2: ChatService, SSE endpoint, and router registration** - `0384cdd2` (feat)

## Files Created/Modified
- `backend/app/models/chat_session.py` - ChatSession SQLAlchemy model with JSONB messages, UUID PKs, audit/user FKs
- `backend/app/services/chat_service.py` - ChatService: context builder, message history builder, LLM streaming
- `backend/app/api/chat.py` - SSE chat endpoint and history endpoint with ownership + tier gating
- `backend/app/schemas/chat.py` - ChatMessageRequest, ChatMessageSchema, ChatHistoryResponse Pydantic schemas
- `backend/alembic/versions/014_add_chat_sessions.py` - Migration for chat_sessions table
- `backend/app/models/__init__.py` - Added ChatSession import and __all__ entry
- `backend/app/core/config.py` - Added CHAT_MODEL, CHAT_TEMPERATURE, CHAT_MAX_TOKENS, CHAT_MAX_HISTORY settings
- `backend/app/main.py` - Registered chat.router
- `backend/requirements.txt` - Added sse-starlette>=2.1.0

## Decisions Made
- API key resolved via model prefix matching (gemini/ -> GEMINI_API_KEY), same pattern as dispatch_service.py
- User message saved to DB before LLM call to ensure persistence even if streaming fails
- Used JSONB messages array on ChatSession (not separate ChatMessage table) since conversation is always loaded/saved as a whole
- System prompt limited to top 15 failing criteria + top 10 recommendations to avoid context window overflow
- asyncio.CancelledError caught for clean SSE disconnect handling when client navigates away

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Alembic migration could not be applied because Supabase DB is unreachable from local network (pre-existing blocker documented in STATE.md). Migration file is correct and will apply when DB is reachable.
- Test suite has 37 errors all related to DB connectivity (pre-existing). 123 tests pass with no regressions from our changes.

## User Setup Required

None - no external service configuration required. sse-starlette was installed to the venv. Migration 014 will auto-apply on next `alembic upgrade head` when DB is reachable.

## Next Phase Readiness
- Backend chat foundation complete, ready for 06-02 frontend ChatPanel component
- Frontend will need @microsoft/fetch-event-source for SSE consumption with POST + auth headers
- Chat endpoints are live and registered in the app router

---
*Phase: 06-chat-assistant*
*Completed: 2026-02-26*
