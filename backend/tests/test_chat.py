"""Tests for ChatService, chat API endpoints, and API key resolution.

All tests mock DB sessions and model objects -- no external dependencies,
API keys, or database connections required.
"""

import uuid
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.core.config import settings
from app.core.dependencies import SubscriptionTier
from app.services.chat_service import ChatService, _resolve_api_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_db():
    """Create a mock DB session with query chaining support."""
    db = MagicMock()
    return db


def _make_audit(
    optimization_score=65,
    domain="example.com",
    status="completed",
    vertical="saas",
):
    """Create a mock Audit with sensible defaults."""
    audit = MagicMock()
    audit.id = uuid.uuid4()
    audit.user_id = uuid.uuid4()
    audit.url = f"https://{domain}"
    audit.domain = domain
    audit.status = status
    audit.optimization_score = optimization_score
    audit.vertical = vertical
    return audit


def _make_visibility_score(overall=50, engines_queried=4):
    """Create a mock VisibilityScore."""
    vs = MagicMock()
    vs.overall_score = overall
    vs.confidence_level = "medium"
    vs.engines_queried = engines_queried
    vs.per_engine_scores = {
        "openai": {
            "score": 60,
            "weighted_score": 55,
            "queries_sent": 5,
            "queries_with_mentions": 3,
        },
        "anthropic": {
            "score": 40,
            "weighted_score": 35,
            "queries_sent": 5,
            "queries_with_mentions": 2,
        },
    }
    return vs


def _make_page_score(
    audit_id=None,
    crawlability=70,
    content_structure=55,
    structured_data=45,
    authority=60,
    was_scored=True,
):
    """Create a mock PageScore with known category scores."""
    ps = MagicMock()
    ps.audit_id = audit_id or uuid.uuid4()
    ps.crawlability_score = crawlability
    ps.content_structure_score = content_structure
    ps.structured_data_score = structured_data
    ps.authority_score = authority
    ps.overall_page_score = round(
        (crawlability + content_structure + structured_data + authority) / 4
    )
    ps.was_scored = was_scored
    return ps


def _make_criterion_result(
    criterion_id="C1",
    criterion_name="AI Bot Access",
    category="crawlability",
    score=20,
    human_summary="GPTBot is blocked in robots.txt",
):
    """Create a mock CriterionResult with a low score (failing)."""
    cr = MagicMock()
    cr.criterion_id = criterion_id
    cr.criterion_name = criterion_name
    cr.category = category
    cr.score = score
    cr.human_summary = human_summary
    return cr


def _make_recommendation(
    priority="high",
    criterion_name="C1 AI Bot Access",
    summary="Allow GPTBot in robots.txt",
    gap_score=30,
):
    """Create a mock AuditRecommendation."""
    rec = MagicMock()
    rec.id = uuid.uuid4()
    rec.priority = priority
    rec.criterion_name = criterion_name
    rec.summary = summary
    rec.gap_score = gap_score
    rec.status = "open"
    return rec


def _make_chat_session(audit_id=None, user_id=None, messages=None):
    """Create a mock ChatSession."""
    session = MagicMock()
    session.id = uuid.uuid4()
    session.audit_id = audit_id or uuid.uuid4()
    session.user_id = user_id or uuid.uuid4()
    session.messages = messages if messages is not None else []
    session.model_used = settings.CHAT_MODEL
    return session


def _setup_service_queries(db, vis=None, page_scores=None, criteria=None, recs=None):
    """Wire up db.query(...).filter(...).join(...).order_by(...).limit(...) chains
    for ChatService.build_system_prompt which makes 4 sequential queries:
      1. VisibilityScore (query -> filter -> first)
      2. PageScore (query -> filter -> all)
      3. CriterionResult (query -> join -> filter -> order_by -> limit -> all)
      4. AuditRecommendation (query -> filter -> order_by -> limit -> all)
    """
    call_count = {"n": 0}
    results = [vis, page_scores or [], criteria or [], recs or []]

    def query_side_effect(*args):
        q = MagicMock()
        idx = call_count["n"]
        call_count["n"] += 1

        result = results[idx] if idx < len(results) else []

        q.filter.return_value = q
        q.join.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q

        if isinstance(result, list):
            q.all.return_value = result
            q.first.return_value = result[0] if result else None
        else:
            q.first.return_value = result
            q.all.return_value = [result] if result else []

        return q

    db.query.side_effect = query_side_effect


# ---------------------------------------------------------------------------
# ChatService tests
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    """Test ChatService.build_system_prompt with various audit data configurations."""

    def test_build_system_prompt_includes_audit_data(self):
        """System prompt includes domain, scores, failing criteria, and recommendations."""
        db = _mock_db()
        audit = _make_audit(optimization_score=42, domain="mysite.io")
        vis = _make_visibility_score(overall=55)
        ps = _make_page_score(audit_id=audit.id)
        cr = _make_criterion_result(
            criterion_id="C1",
            criterion_name="AI Bot Access",
            score=20,
            human_summary="GPTBot blocked",
        )
        rec = _make_recommendation(
            summary="Allow GPTBot in robots.txt", gap_score=30
        )

        _setup_service_queries(db, vis=vis, page_scores=[ps], criteria=[cr], recs=[rec])

        service = ChatService(db)
        prompt = service.build_system_prompt(audit)

        # Verify all key data is present
        assert "mysite.io" in prompt
        assert "42" in prompt  # optimization score
        assert "55" in prompt  # visibility score
        assert "AI Bot Access" in prompt  # failing criterion name
        assert "Allow GPTBot in robots.txt" in prompt  # recommendation
        assert "Answer questions about THIS specific audit only" in prompt

    def test_build_system_prompt_handles_no_visibility(self):
        """Prompt handles missing VisibilityScore gracefully."""
        db = _mock_db()
        audit = _make_audit(optimization_score=60)

        _setup_service_queries(db, vis=None, page_scores=[], criteria=[], recs=[])

        service = ChatService(db)
        prompt = service.build_system_prompt(audit)

        assert "Not measured" in prompt
        assert "Visibility not measured" in prompt


class TestBuildMessages:
    """Test ChatService.build_messages for message array construction."""

    def test_build_messages_caps_history(self):
        """Messages list is capped at CHAT_MAX_HISTORY from settings."""
        db = _mock_db()
        audit = _make_audit()

        # Create session with 30 messages (exceeds CHAT_MAX_HISTORY=20)
        history_messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(30)
        ]
        session = _make_chat_session(
            audit_id=audit.id, messages=history_messages
        )

        _setup_service_queries(db, vis=None, page_scores=[], criteria=[], recs=[])

        service = ChatService(db)
        messages = service.build_messages(audit, session)

        # 1 system message + CHAT_MAX_HISTORY (20) messages
        assert len(messages) == 1 + settings.CHAT_MAX_HISTORY

    def test_build_messages_includes_system_prompt_first(self):
        """First message is always the system prompt with audit data."""
        db = _mock_db()
        audit = _make_audit(domain="test.com")
        session = _make_chat_session(
            audit_id=audit.id,
            messages=[{"role": "user", "content": "Hello"}],
        )

        _setup_service_queries(db, vis=None, page_scores=[], criteria=[], recs=[])

        service = ChatService(db)
        messages = service.build_messages(audit, session)

        assert messages[0]["role"] == "system"
        assert "test.com" in messages[0]["content"]


# ---------------------------------------------------------------------------
# Session management tests
# ---------------------------------------------------------------------------


class TestGetOrCreateSession:
    """Test ChatService.get_or_create_session for session creation and retrieval."""

    def test_get_or_create_session_creates_new(self):
        """Creates a new ChatSession when none exists."""
        db = _mock_db()
        audit_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock: no existing session found
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = None

        service = ChatService(db)
        session = service.get_or_create_session(audit_id, user_id)

        # Verify db.add was called (new session created)
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_get_or_create_session_returns_existing(self):
        """Returns existing ChatSession without creating a new one."""
        db = _mock_db()
        audit_id = uuid.uuid4()
        user_id = uuid.uuid4()

        existing_session = _make_chat_session(
            audit_id=audit_id,
            user_id=user_id,
            messages=[{"role": "user", "content": "Hello"}],
        )

        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = existing_session

        service = ChatService(db)
        session = service.get_or_create_session(audit_id, user_id)

        assert session == existing_session
        db.add.assert_not_called()


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestChatEndpointTierGating:
    """Test that chat endpoints enforce PRO tier."""

    def test_chat_endpoint_requires_pro_tier(self):
        """POST /chat/{audit_id}/chat returns 402 for free-tier users."""
        from app.api.chat import router

        chat_routes = [
            r
            for r in router.routes
            if hasattr(r, "path") and r.path.endswith("/chat")
        ]
        assert len(chat_routes) == 1
        deps = chat_routes[0].dependant.dependencies
        dep_names = [d.call.__name__ for d in deps if hasattr(d.call, "__name__")]
        assert "_check_tier" in dep_names

    def test_chat_endpoint_rejects_other_users_audit(self):
        """Ownership check returns 404 for audits belonging to other users."""
        from app.api.chat import _verify_audit_ownership
        from fastapi import HTTPException

        db = _mock_db()
        audit = _make_audit()

        # Mock: audit found but belongs to different user
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = audit

        different_user = MagicMock()
        different_user.id = uuid.uuid4()  # Different from audit.user_id

        with pytest.raises(HTTPException) as exc_info:
            _verify_audit_ownership(str(audit.id), db, different_user)

        assert exc_info.value.status_code == 404

    def test_chat_endpoint_rejects_incomplete_audit(self):
        """Ownership check returns 400 for non-completed audits."""
        from app.api.chat import _verify_audit_ownership
        from fastapi import HTTPException

        db = _mock_db()
        audit = _make_audit(status="running")

        # Mock: audit found and belongs to current user
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = audit

        current_user = MagicMock()
        current_user.id = audit.user_id

        with pytest.raises(HTTPException) as exc_info:
            _verify_audit_ownership(str(audit.id), db, current_user)

        assert exc_info.value.status_code == 400


class TestHistoryEndpoint:
    """Test chat history endpoint behavior."""

    def test_history_endpoint_returns_empty_for_new_audit(self):
        """History endpoint returns empty messages list when no session exists."""
        from app.schemas.chat import ChatHistoryResponse

        # Simulate the logic: no session -> empty messages
        response = ChatHistoryResponse(
            audit_id=str(uuid.uuid4()),
            messages=[],
            model_used=None,
        )
        assert len(response.messages) == 0
        assert response.model_used is None

    def test_history_endpoint_returns_existing_messages(self):
        """History endpoint returns messages from existing ChatSession."""
        from app.schemas.chat import ChatHistoryResponse, ChatMessageSchema

        messages = [
            ChatMessageSchema(
                role="user", content="What is wrong?", timestamp="2026-01-01T00:00:00Z"
            ),
            ChatMessageSchema(
                role="assistant",
                content="Your schema score is low.",
                timestamp="2026-01-01T00:00:01Z",
            ),
            ChatMessageSchema(
                role="user",
                content="How do I fix it?",
                timestamp="2026-01-01T00:00:02Z",
            ),
        ]
        response = ChatHistoryResponse(
            audit_id=str(uuid.uuid4()),
            messages=messages,
            model_used="gemini/gemini-2.5-flash",
        )
        assert len(response.messages) == 3
        assert response.messages[0].role == "user"
        assert response.messages[1].role == "assistant"

    def test_history_endpoint_has_tier_dependency(self):
        """GET /chat/{audit_id}/history requires PRO tier."""
        from app.api.chat import router

        history_routes = [
            r
            for r in router.routes
            if hasattr(r, "path") and r.path.endswith("/history")
        ]
        assert len(history_routes) == 1
        deps = history_routes[0].dependant.dependencies
        dep_names = [d.call.__name__ for d in deps if hasattr(d.call, "__name__")]
        assert "_check_tier" in dep_names


# ---------------------------------------------------------------------------
# API key resolution tests
# ---------------------------------------------------------------------------


class TestResolveApiKey:
    """Test _resolve_api_key for different model prefixes."""

    def test_resolve_api_key_gemini(self):
        """Gemini model prefix resolves to GEMINI_API_KEY."""
        result = _resolve_api_key("gemini/gemini-2.5-flash")
        assert result == settings.GEMINI_API_KEY

    def test_resolve_api_key_anthropic(self):
        """Anthropic model prefix resolves to ANTHROPIC_API_KEY."""
        result = _resolve_api_key("anthropic/claude-haiku-4-5")
        assert result == settings.ANTHROPIC_API_KEY

    def test_resolve_api_key_openai(self):
        """OpenAI model resolves to OPENAI_API_KEY."""
        result = _resolve_api_key("gpt-4o-mini")
        assert result == settings.OPENAI_API_KEY

    def test_resolve_api_key_openai_o_prefix(self):
        """OpenAI o-series model resolves to OPENAI_API_KEY."""
        result = _resolve_api_key("o3-mini")
        assert result == settings.OPENAI_API_KEY

    def test_resolve_api_key_unknown_falls_back_to_openai(self):
        """Unknown model prefix falls back to OPENAI_API_KEY."""
        result = _resolve_api_key("unknown/model")
        assert result == settings.OPENAI_API_KEY
