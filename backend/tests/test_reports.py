"""Tests for ReportService: executive summary, CSV export, HTML/PDF rendering, and tier gating.

All rendering tests mock the DB session and model objects -- no external
dependencies or API keys required.
"""

import csv
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.core.dependencies import SubscriptionTier
from app.services.report_service import ReportService, JIRA_PRIORITY_MAP


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_db():
    """Create a mock DB session with query chaining support."""
    db = MagicMock()
    return db


def _make_audit(optimization_score=65, domain="example.com"):
    """Create a mock Audit with sensible defaults."""
    audit = MagicMock()
    audit.id = uuid.uuid4()
    audit.user_id = uuid.uuid4()
    audit.url = f"https://{domain}"
    audit.domain = domain
    audit.status = "completed"
    audit.optimization_score = optimization_score
    audit.content_gaps = []
    audit.completed_at = None
    return audit


def _make_page_score(
    crawlability=70,
    content_structure=55,
    structured_data=45,
    authority=60,
    was_scored=True,
):
    """Create a mock PageScore with known category scores."""
    ps = MagicMock()
    ps.crawlability_score = crawlability
    ps.content_structure_score = content_structure
    ps.structured_data_score = structured_data
    ps.authority_score = authority
    ps.was_scored = was_scored
    ps.overall_page_score = round(
        (crawlability + content_structure + structured_data + authority) / 4
    )
    return ps


def _make_visibility_score(overall=50, mention_count=8):
    """Create a mock VisibilityScore."""
    vs = MagicMock()
    vs.overall_score = overall
    vs.mention_count = mention_count
    vs.confidence_level = "medium"
    vs.per_engine_scores = {
        "openai": {"score": 60, "queries_sent": 5, "queries_with_mentions": 3,
                   "mention_rate": 0.6, "total_mentions": 4, "confidence_level": "medium"},
    }
    return vs


def _make_recommendation(priority="high", category="crawlability", summary="Fix robots.txt"):
    """Create a mock AuditRecommendation."""
    rec = MagicMock()
    rec.id = uuid.uuid4()
    rec.priority = priority
    rec.category = category
    rec.summary = summary
    rec.criterion_name = "C1"
    rec.action_steps = ["Step 1: Do this", "Step 2: Do that"]
    rec.code_snippet = None
    rec.gap_score = 25
    rec.page_url = None
    return rec


# ---------------------------------------------------------------------------
# Executive summary tests
# ---------------------------------------------------------------------------


class TestExecutiveSummary:
    """Test _generate_executive_summary static method."""

    def test_high_score_wording(self):
        result = ReportService._generate_executive_summary(
            domain="example.com",
            optimization_score=80,
            visibility_score=60,
            recommendations=[],
        )
        assert "strong optimization fundamentals" in result

    def test_medium_score_wording(self):
        result = ReportService._generate_executive_summary(
            domain="example.com",
            optimization_score=55,
            visibility_score=40,
            recommendations=[],
        )
        assert "moderate optimization foundation" in result

    def test_low_score_wording(self):
        result = ReportService._generate_executive_summary(
            domain="example.com",
            optimization_score=30,
            visibility_score=20,
            recommendations=[],
        )
        assert "needs significant optimization work" in result

    def test_includes_domain(self):
        result = ReportService._generate_executive_summary(
            domain="mysite.io",
            optimization_score=50,
            visibility_score=50,
            recommendations=[],
        )
        assert "mysite.io" in result

    def test_includes_top_priority_recommendation(self):
        rec = _make_recommendation(priority="high", summary="Block GPTBot in robots.txt")
        result = ReportService._generate_executive_summary(
            domain="example.com",
            optimization_score=50,
            visibility_score=50,
            recommendations=[rec],
        )
        assert "Block GPTBot in robots.txt" in result

    def test_no_high_recs_shows_no_critical(self):
        rec = _make_recommendation(priority="low", summary="Minor fix")
        result = ReportService._generate_executive_summary(
            domain="example.com",
            optimization_score=80,
            visibility_score=70,
            recommendations=[rec],
        )
        assert "No critical issues found" in result

    def test_recommendation_count_in_summary(self):
        recs = [
            _make_recommendation(category="crawlability"),
            _make_recommendation(category="content_structure"),
            _make_recommendation(category="authority"),
        ]
        result = ReportService._generate_executive_summary(
            domain="example.com",
            optimization_score=50,
            visibility_score=50,
            recommendations=recs,
        )
        assert "3 recommendations" in result
        assert "3 categories" in result


# ---------------------------------------------------------------------------
# CSV export tests
# ---------------------------------------------------------------------------


def _parse_csv(csv_string: str) -> list[dict]:
    """Parse CSV string (with BOM) into list of dicts."""
    clean = csv_string.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(clean))
    return list(reader)


class TestCsvExport:
    """Test export_csv method."""

    def _service_with_recs(self, recs):
        """Create a ReportService with mocked DB returning given recommendations."""
        db = _mock_db()
        query_mock = MagicMock()
        db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = recs

        service = ReportService.__new__(ReportService)
        service.db = db
        return service

    def test_csv_has_bom_prefix(self):
        service = self._service_with_recs([])
        result = service.export_csv("fake-id")
        assert result.startswith("\ufeff")

    def test_csv_default_fields(self):
        service = self._service_with_recs([])
        result = service.export_csv("fake-id")
        rows = _parse_csv(result)
        # Even with no data, the header should contain default fields
        clean = result.lstrip("\ufeff")
        header = clean.split("\r\n")[0] if "\r\n" in clean else clean.split("\n")[0]
        for field in ["Summary", "Description", "Priority", "Labels", "Issue Type", "Component"]:
            assert field in header

    def test_csv_priority_mapping(self):
        recs = [
            _make_recommendation(priority="high"),
            _make_recommendation(priority="medium"),
            _make_recommendation(priority="low"),
        ]
        service = self._service_with_recs(recs)
        result = service.export_csv("fake-id")
        rows = _parse_csv(result)
        priorities = [r["Priority"] for r in rows]
        assert priorities == ["Highest", "Medium", "Low"]

    def test_csv_with_epic_link(self):
        recs = [_make_recommendation()]
        service = self._service_with_recs(recs)
        result = service.export_csv("fake-id", epic_link="PROJ-123")
        rows = _parse_csv(result)
        assert len(rows) == 1
        assert rows[0]["Epic Link"] == "PROJ-123"

    def test_csv_empty_recommendations(self):
        service = self._service_with_recs([])
        result = service.export_csv("fake-id")
        rows = _parse_csv(result)
        assert len(rows) == 0

    def test_csv_description_includes_action_steps(self):
        rec = _make_recommendation()
        rec.action_steps = ["Install plugin", "Configure settings"]
        rec.code_snippet = None
        service = self._service_with_recs([rec])
        result = service.export_csv("fake-id")
        rows = _parse_csv(result)
        assert "Install plugin" in rows[0]["Description"]
        assert "Configure settings" in rows[0]["Description"]

    def test_csv_description_includes_code_snippet(self):
        rec = _make_recommendation()
        rec.action_steps = ["Add schema"]
        rec.code_snippet = '{"@type": "FAQPage"}'
        service = self._service_with_recs([rec])
        result = service.export_csv("fake-id")
        rows = _parse_csv(result)
        assert "FAQPage" in rows[0]["Description"]


# ---------------------------------------------------------------------------
# HTML/PDF rendering tests
# ---------------------------------------------------------------------------


def _setup_build_context_mocks(db, audit, page_scores, vis, recs, competitors=None, comp_audits=None):
    """Wire up db.query(...).filter(...) chains for _build_context."""
    call_count = {"n": 0}
    results = [audit, page_scores, vis, recs, competitors or [], comp_audits or []]

    original_query = db.query

    def query_side_effect(*args):
        q = MagicMock()
        idx = call_count["n"]
        call_count["n"] += 1

        result = results[idx] if idx < len(results) else []

        q.filter.return_value = q
        q.order_by.return_value = q

        if isinstance(result, list):
            q.all.return_value = result
            q.first.return_value = result[0] if result else None
        else:
            q.first.return_value = result
            q.all.return_value = [result] if result else []

        return q

    db.query.side_effect = query_side_effect


class TestHtmlRendering:
    """Test render_html method."""

    def test_render_html_returns_string(self):
        db = _mock_db()
        audit = _make_audit(optimization_score=65)
        # Make status match the enum check
        from app.models.audit import AuditStatus
        audit.status = AuditStatus.COMPLETED
        ps = _make_page_score()
        vis = _make_visibility_score()
        rec = _make_recommendation()

        _setup_build_context_mocks(db, audit, [ps], vis, [rec])

        service = ReportService(db)
        html = service.render_html(str(audit.id))

        assert isinstance(html, str)
        assert len(html) > 0
        assert "GEO Audit Report" in html

    def test_render_html_contains_executive_summary(self):
        db = _mock_db()
        audit = _make_audit(optimization_score=80)
        from app.models.audit import AuditStatus
        audit.status = AuditStatus.COMPLETED
        ps = _make_page_score()
        vis = _make_visibility_score()

        _setup_build_context_mocks(db, audit, [ps], vis, [])

        service = ReportService(db)
        html = service.render_html(str(audit.id))

        assert "Executive Summary" in html

    def test_render_html_contains_scores(self):
        db = _mock_db()
        audit = _make_audit(optimization_score=72)
        from app.models.audit import AuditStatus
        audit.status = AuditStatus.COMPLETED
        ps = _make_page_score()
        vis = _make_visibility_score(overall=60)

        _setup_build_context_mocks(db, audit, [ps], vis, [])

        service = ReportService(db)
        html = service.render_html(str(audit.id))

        # Combined GEO score = round(60 * 0.15 + 72 * 0.85) = round(70.2) = 70
        assert "72" in html  # optimization score
        assert "60" in html  # visibility score


class TestPdfRendering:
    """Test render_pdf method."""

    @patch("app.services.report_service.weasyprint")
    def test_render_pdf_returns_bytes(self, mock_weasyprint):
        """Verify render_pdf returns bytes (WeasyPrint mocked)."""
        mock_weasyprint.HTML.return_value.write_pdf.return_value = b"%PDF-1.4 fake"

        db = _mock_db()
        audit = _make_audit()
        from app.models.audit import AuditStatus
        audit.status = AuditStatus.COMPLETED
        ps = _make_page_score()
        vis = _make_visibility_score()

        _setup_build_context_mocks(db, audit, [ps], vis, [])

        service = ReportService(db)
        result = service.render_pdf(str(audit.id))

        assert isinstance(result, bytes)
        assert len(result) > 0
        mock_weasyprint.HTML.assert_called_once()


# ---------------------------------------------------------------------------
# Context building tests
# ---------------------------------------------------------------------------


class TestBuildContext:
    """Test _build_context assembles correct data."""

    def test_combined_geo_score_formula(self):
        db = _mock_db()
        audit = _make_audit(optimization_score=70)
        from app.models.audit import AuditStatus
        audit.status = AuditStatus.COMPLETED
        vis = _make_visibility_score(overall=60)
        ps = _make_page_score()

        _setup_build_context_mocks(db, audit, [ps], vis, [])

        service = ReportService(db)
        ctx = service._build_context(str(audit.id))

        # combined = round(60 * 0.15 + 70 * 0.85) = round(68.5) = 68
        assert ctx["combined_geo_score"] == round(60 * 0.15 + 70 * 0.85)

    def test_category_averages_computed(self):
        db = _mock_db()
        audit = _make_audit()
        from app.models.audit import AuditStatus
        audit.status = AuditStatus.COMPLETED

        ps1 = _make_page_score(crawlability=80, content_structure=60, structured_data=40, authority=70)
        ps2 = _make_page_score(crawlability=60, content_structure=40, structured_data=60, authority=50)
        vis = _make_visibility_score()

        _setup_build_context_mocks(db, audit, [ps1, ps2], vis, [])

        service = ReportService(db)
        ctx = service._build_context(str(audit.id))

        assert ctx["category_averages"]["crawlability"] == 70  # (80+60)/2
        assert ctx["category_averages"]["content_structure"] == 50  # (60+40)/2
        assert ctx["category_averages"]["structured_data"] == 50  # (40+60)/2
        assert ctx["category_averages"]["authority"] == 60  # (70+50)/2

    def test_no_visibility_score_defaults(self):
        db = _mock_db()
        audit = _make_audit(optimization_score=50)
        from app.models.audit import AuditStatus
        audit.status = AuditStatus.COMPLETED

        _setup_build_context_mocks(db, audit, [], None, [])

        service = ReportService(db)
        ctx = service._build_context(str(audit.id))

        assert ctx["visibility_score"] == 0
        assert ctx["mention_count"] == 0
        assert ctx["confidence_level"] == "not_measured"

    def test_pages_scored_count(self):
        db = _mock_db()
        audit = _make_audit()
        from app.models.audit import AuditStatus
        audit.status = AuditStatus.COMPLETED

        scored = _make_page_score(was_scored=True)
        unscored = _make_page_score(was_scored=False)
        vis = _make_visibility_score()

        _setup_build_context_mocks(db, audit, [scored, unscored], vis, [])

        service = ReportService(db)
        ctx = service._build_context(str(audit.id))

        assert ctx["pages_scored"] == 1
        assert ctx["pages_discovered"] == 2


# ---------------------------------------------------------------------------
# Report endpoint tier gating verification
# ---------------------------------------------------------------------------


class TestReportEndpointTierGating:
    """Verify report routes are gated behind PRO tier."""

    def test_pdf_endpoint_has_tier_dependency(self):
        from app.api.reports import router
        pdf_routes = [r for r in router.routes if hasattr(r, "path") and r.path.endswith("/pdf")]
        assert len(pdf_routes) == 1
        deps = pdf_routes[0].dependant.dependencies
        dep_names = [d.call.__name__ for d in deps if hasattr(d.call, "__name__")]
        assert "_check_tier" in dep_names

    def test_html_endpoint_has_tier_dependency(self):
        from app.api.reports import router
        html_routes = [r for r in router.routes if hasattr(r, "path") and r.path.endswith("/html")]
        assert len(html_routes) == 1
        deps = html_routes[0].dependant.dependencies
        dep_names = [d.call.__name__ for d in deps if hasattr(d.call, "__name__")]
        assert "_check_tier" in dep_names

    def test_csv_endpoint_has_tier_dependency(self):
        from app.api.reports import router
        csv_routes = [r for r in router.routes if hasattr(r, "path") and r.path.endswith("/csv")]
        assert len(csv_routes) == 1
        deps = csv_routes[0].dependant.dependencies
        dep_names = [d.call.__name__ for d in deps if hasattr(d.call, "__name__")]
        assert "_check_tier" in dep_names

    def test_all_three_formats_registered(self):
        from app.api.reports import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert any(p.endswith("/pdf") for p in paths)
        assert any(p.endswith("/html") for p in paths)
        assert any(p.endswith("/csv") for p in paths)


# ---------------------------------------------------------------------------
# Priority mapping tests
# ---------------------------------------------------------------------------


class TestJiraPriorityMap:
    """Test the priority mapping constant."""

    def test_high_maps_to_highest(self):
        assert JIRA_PRIORITY_MAP["high"] == "Highest"

    def test_medium_maps_to_medium(self):
        assert JIRA_PRIORITY_MAP["medium"] == "Medium"

    def test_low_maps_to_low(self):
        assert JIRA_PRIORITY_MAP["low"] == "Low"
