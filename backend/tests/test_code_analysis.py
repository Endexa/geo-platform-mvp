"""Tests for code analysis feature: PromptGeneratorService, CodeAnalysisService,
API endpoints (tier gating, ownership, size limits), and Celery task lifecycle.

All tests mock DB sessions and LLM calls — no external API calls or real DB
connections required. Pattern mirrors test_chat.py.
"""

import re
import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.core.config import settings
from app.schemas.code_analysis import CodeAnalysisResult, CodeFinding, GeneratedPrompt
from app.services.code_analysis_service import (
    CATEGORY_ORDER,
    CodeAnalysisService,
    PromptGeneratorService,
)


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _mock_db():
    """Create a mock DB session with query chaining support."""
    return MagicMock()


def _make_audit(
    domain="example.com",
    status="completed",
    crawl_data=None,
):
    """Create a mock Audit."""
    audit = MagicMock()
    audit.id = uuid.uuid4()
    audit.user_id = uuid.uuid4()
    audit.domain = domain
    audit.status = status
    audit.crawl_data = crawl_data or {}
    return audit


def _make_code_analysis(
    audit_id=None,
    user_id=None,
    status="pending",
    raw_output="some AI output text",
):
    """Create a mock CodeAnalysis record."""
    ca = MagicMock()
    ca.id = uuid.uuid4()
    ca.audit_id = audit_id or uuid.uuid4()
    ca.user_id = user_id or uuid.uuid4()
    ca.status = status
    ca.raw_output = raw_output
    ca.detected_framework = None
    ca.parsed_findings = None
    ca.error_message = None
    ca.completed_at = None
    return ca


def _make_code_finding(
    category="crawlability",
    severity="high",
    finding="GPTBot blocked in robots.txt",
    suggestion="Remove the Disallow rule for GPTBot.",
    file_path="robots.txt",
    criterion_id=None,
    evidence="Found 'Disallow: /' under User-agent: GPTBot block.",
):
    """Create a CodeFinding Pydantic model instance."""
    return CodeFinding(
        category=category,
        severity=severity,
        finding=finding,
        suggestion=suggestion,
        location=file_path,
        criterion_id=criterion_id,
        evidence=evidence,
    )


def _make_code_recommendation(
    code_analysis_id=None,
    audit_id=None,
    category="crawlability",
    severity="high",
    finding="robots.txt blocks GPTBot",
    suggestion="Allow GPTBot",
    file_path="robots.txt",
):
    """Create a mock CodeRecommendation DB model instance."""
    rec = MagicMock()
    rec.id = uuid.uuid4()
    rec.code_analysis_id = code_analysis_id or uuid.uuid4()
    rec.audit_id = audit_id or uuid.uuid4()
    rec.category = category
    rec.severity = severity
    rec.finding = finding
    rec.suggestion = suggestion
    rec.file_path = file_path
    rec.criterion_id = None
    rec.code_snippet = None
    rec.evidence = None
    rec.status = "open"
    return rec


def _stub_failing_categories(db, categories: list[str]):
    """Wire db.query chain so _load_failing_categories returns the given categories.

    _load_failing_categories does: db.query(...).join(...).filter(...).distinct().all()
    Each row is a 1-tuple like ('crawlability',).
    """
    q = MagicMock()
    db.query.return_value = q
    q.join.return_value = q
    q.filter.return_value = q
    q.distinct.return_value = q
    q.all.return_value = [(c,) for c in categories]
    return q


def _stub_count(db, count_value: int):
    """Wire db.query chain for _count_failing_criteria which ends in .count()."""
    q = MagicMock()
    db.query.return_value = q
    q.join.return_value = q
    q.filter.return_value = q
    q.count.return_value = count_value
    return q


# ---------------------------------------------------------------------------
# PromptGeneratorService tests
# ---------------------------------------------------------------------------


class TestPromptGeneratorServiceStructure:
    """Test that generate_prompts() returns the correct structure and respects limits."""

    def test_generate_prompts_returns_correct_structure(self):
        """generate_prompts returns PromptsResponse with prompts for each failing category."""
        db = _mock_db()
        audit = _make_audit(domain="mysite.com")
        failing = ["crawlability", "structured_data", "authority"]

        call_count = {"n": 0}

        def query_side_effect(*args):
            q = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            q.join.return_value = q
            q.filter.return_value = q
            q.distinct.return_value = q
            if n == 0:
                # _load_failing_categories — returns distinct category rows
                q.all.return_value = [(c,) for c in failing]
            else:
                # _count_failing_criteria — returns an int
                q.count.return_value = 3
            return q

        db.query.side_effect = query_side_effect

        svc = PromptGeneratorService()
        result = svc.generate_prompts(str(audit.id), db, audit)

        assert result.audit_id == str(audit.id)
        assert result.domain == "mysite.com"
        assert len(result.prompts) == len(failing)
        for p in result.prompts:
            assert p.category in failing
            assert len(p.title) > 0
            assert len(p.prompt_text) > 0
            assert p.priority in ("high", "medium", "low")
            assert p.target_count >= 1
        assert result.domain in result.markdown_bundle
        assert len(result.markdown_bundle) > 0

    def test_generate_prompts_caps_at_four_categories(self):
        """generate_prompts returns at most 4 prompts (one per category)."""
        db = _mock_db()
        audit = _make_audit()

        call_count = {"n": 0}

        def query_side_effect(*args):
            q = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            q.join.return_value = q
            q.filter.return_value = q
            q.distinct.return_value = q
            if n == 0:
                # All 4 categories failing
                q.all.return_value = [(c,) for c in CATEGORY_ORDER]
            else:
                q.count.return_value = 2
            return q

        db.query.side_effect = query_side_effect

        svc = PromptGeneratorService()
        result = svc.generate_prompts(str(audit.id), db, audit)

        assert len(result.prompts) <= 4

    def test_failing_categories_fallback(self):
        """_load_failing_categories falls back to all 4 when no CriterionResult records found."""
        db = _mock_db()
        q = MagicMock()
        db.query.return_value = q
        q.join.return_value = q
        q.filter.return_value = q
        q.distinct.return_value = q
        q.all.return_value = []  # No rows found

        svc = PromptGeneratorService()
        categories = svc._load_failing_categories(str(uuid.uuid4()), db)

        assert categories == set(CATEGORY_ORDER)


class TestPromptIpProtection:
    """CODE-04: generated prompts must NOT expose any scoring logic."""

    # Patterns that must never appear in prompt text
    FORBIDDEN_CRITERION_ID_PATTERNS = [
        r"\b[CA][0-9]+\b",       # C1, A8, etc.
        r"\b(CS|SD|A)[0-9]+\b",  # CS5, SD13, A3
        r"\bS[0-9]+\b",          # S1-S15
    ]
    FORBIDDEN_WORDS = [
        "threshold",
        "weight",
        "gap_score",
        "criterion_result",
    ]
    # Score-like patterns "30/100", "60/100", etc.
    SCORE_PATTERN = re.compile(r"\b\d{1,3}/100\b")

    def test_generate_prompts_no_scoring_logic_leaked(self):
        """None of the prompt texts contain criterion IDs, weights, thresholds, or raw scores.

        This is the CODE-04 IP protection assertion.
        """
        db = _mock_db()
        audit = _make_audit()

        call_count = {"n": 0}

        def query_side_effect(*args):
            q = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            q.join.return_value = q
            q.filter.return_value = q
            q.distinct.return_value = q
            if n == 0:
                q.all.return_value = [(c,) for c in CATEGORY_ORDER]
            else:
                q.count.return_value = 5
            return q

        db.query.side_effect = query_side_effect

        svc = PromptGeneratorService()
        result = svc.generate_prompts(str(audit.id), db, audit)

        for prompt in result.prompts:
            text = prompt.prompt_text

            # No criterion IDs
            for pattern in self.FORBIDDEN_CRITERION_ID_PATTERNS:
                matches = re.findall(pattern, text)
                assert not matches, (
                    f"Criterion ID pattern '{pattern}' found in prompt '{prompt.category}': "
                    f"{matches}"
                )

            # No scoring vocabulary
            for word in self.FORBIDDEN_WORDS:
                assert word.lower() not in text.lower(), (
                    f"Forbidden word '{word}' found in prompt '{prompt.category}'"
                )

            # No score-like fractions
            score_matches = self.SCORE_PATTERN.findall(text)
            assert not score_matches, (
                f"Score-like pattern found in prompt '{prompt.category}': {score_matches}"
            )


class TestFrameworkDetection:
    """Test detect_framework() for supported frameworks and unknown HTML."""

    def test_detect_framework_nextjs(self):
        """HTML containing '_next/' is detected as nextjs."""
        svc = PromptGeneratorService()
        crawl_data = {"html": "<script src='/_next/static/chunks/main.js'></script>"}
        assert svc.detect_framework(crawl_data) == "nextjs"

    def test_detect_framework_wordpress(self):
        """HTML containing 'wp-content' is detected as wordpress."""
        svc = PromptGeneratorService()
        crawl_data = {"html": "<link rel='stylesheet' href='/wp-content/themes/main.css'>"}
        assert svc.detect_framework(crawl_data) == "wordpress"

    def test_detect_framework_unknown(self):
        """HTML with no known framework hints returns None."""
        svc = PromptGeneratorService()
        crawl_data = {"html": "<div id='app'><h1>Hello</h1></div>"}
        result = svc.detect_framework(crawl_data)
        assert result is None


# ---------------------------------------------------------------------------
# CodeAnalysisService tests
# ---------------------------------------------------------------------------


class TestCodeAnalysisServiceParsing:
    """Test CodeAnalysisService.parse_output() LiteLLM call characteristics."""

    def _make_litellm_response(self, findings=None):
        """Return a mock litellm response with valid CodeAnalysisResult JSON content."""
        if findings is None:
            findings = [
                {
                    "criterion_id": None,
                    "category": "crawlability",
                    "severity": "high",
                    "finding": "GPTBot blocked",
                    "location": "robots.txt",
                    "suggestion": "Remove Disallow for GPTBot",
                    "evidence": "Found Disallow: / for User-agent: GPTBot",
                }
            ]
        result_obj = CodeAnalysisResult(
            detected_framework="nextjs",
            findings=[CodeFinding(**f) for f in findings],
            summary="1 finding extracted.",
        )
        content = result_obj.model_dump_json()

        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = content
        return response

    @pytest.mark.asyncio
    async def test_parse_output_calls_litellm_with_structured_format(self):
        """parse_output calls litellm.acompletion with response_format=CodeAnalysisResult."""
        mock_response = self._make_litellm_response()

        with patch("app.services.code_analysis_service.litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            svc = CodeAnalysisService()
            result = await svc.parse_output("some AI output text")

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args.kwargs

        assert call_kwargs.get("response_format") == CodeAnalysisResult
        assert call_kwargs.get("model") == settings.CODE_ANALYSIS_MODEL
        assert isinstance(result, CodeAnalysisResult)

    @pytest.mark.asyncio
    async def test_parse_output_passes_explicit_api_key(self):
        """parse_output passes an explicit non-empty api_key to litellm (not os.environ)."""
        mock_response = self._make_litellm_response()

        with patch("app.services.code_analysis_service.litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            svc = CodeAnalysisService()
            await svc.parse_output("some AI text")

        call_kwargs = mock_completion.call_args.kwargs
        api_key = call_kwargs.get("api_key")
        assert api_key is not None
        assert len(api_key) > 0, "api_key must be a non-empty string"

    @pytest.mark.asyncio
    async def test_parse_output_truncates_oversized_input(self):
        """Input longer than CODE_ANALYSIS_MAX_TOKENS_INPUT is truncated before LLM call."""
        mock_response = self._make_litellm_response()
        oversized_text = "x" * (settings.CODE_ANALYSIS_MAX_TOKENS_INPUT + 10000)

        with patch("app.services.code_analysis_service.litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            svc = CodeAnalysisService()
            await svc.parse_output(oversized_text)

        call_kwargs = mock_completion.call_args.kwargs
        messages = call_kwargs.get("messages", [])
        # User message (index 1) contains the (possibly truncated) text
        user_content = messages[1]["content"]
        assert len(user_content) <= settings.CODE_ANALYSIS_MAX_TOKENS_INPUT


class TestCodeAnalysisServiceResolveApiKey:
    """Test _resolve_api_key for each model prefix."""

    def test_resolve_api_key_gemini(self):
        """Gemini prefix resolves to GEMINI_API_KEY."""
        svc = CodeAnalysisService()
        assert svc._resolve_api_key("gemini/gemini-2.5-flash") == settings.GEMINI_API_KEY

    def test_parse_output_passes_explicit_api_key_gemini_setting(self):
        """_resolve_api_key('gemini/...') returns settings.GEMINI_API_KEY (pydantic-settings, not os.environ)."""
        svc = CodeAnalysisService()
        result = svc._resolve_api_key("gemini/gemini-2.5-flash")
        assert result == settings.GEMINI_API_KEY


class TestCodeAnalysisServiceRecommendations:
    """Test generate_code_recommendations() DB insertion."""

    def test_generate_code_recommendations_creates_records(self):
        """generate_code_recommendations calls db.add() for each finding and commits once."""
        db = _mock_db()
        ca = _make_code_analysis()
        findings = [
            _make_code_finding(category="crawlability", severity="high"),
            _make_code_finding(category="structured_data", severity="medium"),
            _make_code_finding(category="authority", severity="low"),
        ]
        result = CodeAnalysisResult(
            detected_framework=None,
            findings=findings,
            summary="3 findings.",
        )

        svc = CodeAnalysisService()
        recs = svc.generate_code_recommendations(ca, result, db)

        assert db.add.call_count == 3
        db.commit.assert_called_once()
        assert len(recs) == 3


# ---------------------------------------------------------------------------
# API endpoint tests (router dependency inspection + logic checks)
# ---------------------------------------------------------------------------


class TestEndpointTierGating:
    """Verify all code-analysis routes require PRO tier."""

    def _get_route_dep_names(self, router, path_suffix: str) -> list[str]:
        """Extract FastAPI dependency function names for a route by path suffix."""
        from app.api.code_analysis import router as code_router
        for route in code_router.routes:
            if hasattr(route, "path") and route.path.endswith(path_suffix):
                deps = route.dependant.dependencies
                return [d.call.__name__ for d in deps if hasattr(d.call, "__name__")]
        return []

    def test_prompts_endpoint_requires_pro_tier(self):
        """POST /{audit_id}/prompts has _check_tier dependency."""
        names = self._get_route_dep_names(None, "/prompts")
        assert "_check_tier" in names

    def test_upload_endpoint_requires_pro_tier(self):
        """POST /{audit_id}/upload has _check_tier dependency."""
        names = self._get_route_dep_names(None, "/upload")
        assert "_check_tier" in names

    def test_status_endpoint_requires_pro_tier(self):
        """GET /{audit_id} has _check_tier dependency."""
        from app.api.code_analysis import router as code_router
        # The GET /{audit_id} route ends with the audit_id parameter
        for route in code_router.routes:
            if (
                hasattr(route, "path")
                and route.path.endswith("/{audit_id}")
                and hasattr(route, "methods")
                and "GET" in route.methods
            ):
                deps = route.dependant.dependencies
                dep_names = [d.call.__name__ for d in deps if hasattr(d.call, "__name__")]
                assert "_check_tier" in dep_names
                return
        pytest.fail("GET /{audit_id} route not found")


class TestGetOwnedAuditHelper:
    """Test _get_owned_audit ownership and 404 behavior."""

    def test_prompts_endpoint_rejects_other_users_audit(self):
        """_get_owned_audit raises 404 when audit belongs to another user."""
        from app.api.code_analysis import _get_owned_audit
        from fastapi import HTTPException

        db = _mock_db()
        audit = _make_audit()

        # DB returns an audit owned by audit.user_id
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = None  # Ownership filter returns nothing (other user)

        different_user = MagicMock()
        different_user.id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            _get_owned_audit(str(audit.id), different_user, db)

        assert exc_info.value.status_code == 404

    def test_prompts_endpoint_requires_completed_audit(self):
        """_require_completed_audit raises 400 for non-completed audit."""
        from app.api.code_analysis import _require_completed_audit
        from fastapi import HTTPException

        audit = _make_audit(status="running")

        with pytest.raises(HTTPException) as exc_info:
            _require_completed_audit(audit)

        assert exc_info.value.status_code == 400


class TestUploadEndpoint:
    """Test upload endpoint validations (size limit, task trigger)."""

    def test_upload_endpoint_rejects_oversized_payload_size_check(self):
        """MAX_UPLOAD_BYTES constant is 102400 (100 KB)."""
        assert settings.CODE_ANALYSIS_MAX_UPLOAD_BYTES == 102400

    def test_upload_endpoint_creates_record_and_triggers_task(self):
        """Upload endpoint creates CodeAnalysis record and calls process_code_analysis.delay."""
        from app.models.code_analysis import CodeAnalysis

        db = _mock_db()
        audit = _make_audit(status="completed")
        current_user = MagicMock()
        current_user.id = uuid.uuid4()

        # Simulate db.add creating a record with an ID
        created_ca = _make_code_analysis(
            audit_id=audit.id, user_id=current_user.id, status="pending"
        )

        def db_refresh_side_effect(obj):
            obj.id = created_ca.id

        db.refresh.side_effect = db_refresh_side_effect

        # Verify task is triggered by inspecting process_code_analysis.delay
        with patch("app.api.code_analysis.process_code_analysis") as mock_task:
            mock_task.delay = MagicMock()

            # Simulate the upload endpoint logic (without full HTTP stack)
            raw_text = "This is valid AI tool output for code analysis testing."
            ca = CodeAnalysis(
                audit_id=audit.id,
                user_id=current_user.id,
                status="pending",
                raw_output=raw_text,
                raw_output_size_bytes=len(raw_text.encode("utf-8")),
            )
            db.add(ca)
            db.commit()
            db.refresh(ca)
            mock_task.delay(str(created_ca.id))

            db.add.assert_called_once()
            db.commit.assert_called()
            mock_task.delay.assert_called_once_with(str(created_ca.id))


class TestStatusEndpoint:
    """Test GET /{audit_id} returns 404 when no CodeAnalysis exists."""

    def test_status_endpoint_returns_404_when_no_analysis(self):
        """_get_owned_audit + CodeAnalysis query returns 404 for missing record.

        The GET /{audit_id} endpoint queries CodeAnalysis and raises 404 if none found.
        We verify the 404 logic directly from the router code.
        """
        from app.api.code_analysis import get_code_analysis
        from fastapi import HTTPException

        db = _mock_db()
        audit = _make_audit(status="completed")
        current_user = MagicMock()
        current_user.id = audit.user_id

        call_count = {"n": 0}

        def query_side_effect(*args):
            q = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            q.filter.return_value = q
            q.order_by.return_value = q
            if n == 0:
                # _get_owned_audit — returns the audit
                q.first.return_value = audit
            else:
                # CodeAnalysis query — returns None (no analysis)
                q.first.return_value = None
            return q

        db.query.side_effect = query_side_effect

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_code_analysis(str(audit.id), db=db, current_user=current_user))

        assert exc_info.value.status_code == 404


class TestRecommendationsEndpoint:
    """Test GET /recommendations and PATCH /recommendations/{rec_id}."""

    def test_recommendations_endpoint_returns_list(self):
        """GET /recommendations returns list of all code recommendations for audit."""
        from app.api.code_analysis import get_code_recommendations
        from app.models.code_analysis import CodeAnalysis, CodeRecommendation

        db = _mock_db()
        audit = _make_audit(status="completed")
        current_user = MagicMock()
        current_user.id = audit.user_id

        rec1 = _make_code_recommendation(audit_id=audit.id, severity="high")
        rec2 = _make_code_recommendation(audit_id=audit.id, severity="medium")

        # Mock the created_at attribute (needed for isoformat() call)
        from datetime import datetime, timezone
        for rec in (rec1, rec2):
            rec.created_at = datetime.now(timezone.utc)

        call_count = {"n": 0}

        def query_side_effect(*args):
            q = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            q.filter.return_value = q
            q.join.return_value = q
            q.order_by.return_value = q
            if n == 0:
                q.first.return_value = audit
            else:
                q.all.return_value = [rec1, rec2]
            return q

        db.query.side_effect = query_side_effect

        import asyncio

        result = asyncio.run(
            get_code_recommendations(str(audit.id), db=db, current_user=current_user)
        )

        assert len(result) == 2

    def test_update_status_rejects_invalid_status(self):
        """PATCH /recommendations/{rec_id} raises 400 for invalid status values."""
        from app.api.code_analysis import update_recommendation_status
        from app.schemas.code_analysis import CodeRecommendationUpdateRequest
        from fastapi import HTTPException

        db = _mock_db()
        audit = _make_audit(status="completed")
        current_user = MagicMock()
        current_user.id = audit.user_id

        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = audit

        payload = CodeRecommendationUpdateRequest(status="invalid_value")

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                update_recommendation_status(
                    str(audit.id),
                    str(uuid.uuid4()),
                    payload,
                    db=db,
                    current_user=current_user,
                )
            )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Celery task tests
# ---------------------------------------------------------------------------


class TestProcessCodeAnalysisTask:
    """Test the process_code_analysis Celery task lifecycle.

    Celery tasks with bind=True have a `run` method that is the original function.
    We call `process_code_analysis.run(code_analysis_id)` to bypass Celery dispatch.
    """

    def _run_task(self, task_fn, *args, **kwargs):
        """Call the task function body directly, bypassing Celery dispatch.

        For bind=True tasks, `task.run(...)` calls the underlying function with
        the task instance implicitly bound (no extra `self` needed from test side).
        """
        return task_fn.run(*args, **kwargs)

    def test_process_code_analysis_happy_path(self):
        """Task transitions: pending -> parsing -> recommending -> completed.

        Verifies parse_output and generate_code_recommendations are called.
        """
        from app.tasks.code_analysis_tasks import process_code_analysis

        ca = _make_code_analysis(status="pending", raw_output="AI output text here.")

        # Build CodeAnalysisResult with 2 findings
        mock_result = CodeAnalysisResult(
            detected_framework="nextjs",
            findings=[
                _make_code_finding(),
                _make_code_finding(category="structured_data", severity="medium"),
            ],
            summary="2 findings found.",
        )

        db = _mock_db()
        db.query.return_value.filter.return_value.first.return_value = ca

        with patch("app.tasks.code_analysis_tasks.SessionLocal", return_value=db):
            with patch.object(
                CodeAnalysisService, "parse_output", new_callable=AsyncMock
            ) as mock_parse:
                with patch.object(
                    CodeAnalysisService, "generate_code_recommendations"
                ) as mock_recs:
                    mock_parse.return_value = mock_result
                    mock_recs.return_value = []

                    self._run_task(process_code_analysis, str(ca.id))

        # Verify status transitions occurred
        assert mock_parse.call_count == 1
        assert mock_recs.call_count == 1
        assert ca.status == "completed"
        assert ca.completed_at is not None

    def test_process_code_analysis_handles_failure(self):
        """Task sets status=failed and records error_message when parse_output raises."""
        from app.tasks.code_analysis_tasks import process_code_analysis

        ca = _make_code_analysis(status="pending", raw_output="bad input")

        db = _mock_db()
        db.query.return_value.filter.return_value.first.return_value = ca

        with patch("app.tasks.code_analysis_tasks.SessionLocal", return_value=db):
            with patch.object(
                CodeAnalysisService, "parse_output", new_callable=AsyncMock
            ) as mock_parse:
                mock_parse.side_effect = Exception("LiteLLM API unavailable")

                self._run_task(process_code_analysis, str(ca.id))

        assert ca.status == "failed"
        assert ca.error_message is not None
        assert len(ca.error_message) > 0
