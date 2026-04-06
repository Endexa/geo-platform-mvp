"""Tests for extended Core Web Vitals — CLS and FCP added to AuthorityScorer._check_cwv.

Based on spec: docs/RedwaneNextDirection.md — Axe 5 (UX module: CLS + FCP).

Currently _check_cwv (authority_scorer.py:1508) only extracts LCP (S11).
After this feature is implemented it must also return CLS (S11b) and FCP (S11c).

These tests are FAILING by design until:
    1. _check_cwv() returns a list of 3 ScoringCriterionResults (LCP + CLS + FCP)
    2. score_page() uses results.extend() to add all three
    3. CLS thresholds: < 0.1 = 100, 0.1-0.25 = proportional, > 0.25 = 0
    4. FCP thresholds: < 1800ms = 100, 1800-3000ms = proportional, > 3000ms = 0

Criterion IDs:
  - S11  = LCP (already exists)
  - S11b = CLS (new)
  - S11c = FCP (new)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scoring.base_scorer import ScoringCriterionResult


# ---------------------------------------------------------------------------
# Helper: build a mocked PageSpeed API response
# ---------------------------------------------------------------------------

def _make_pagespeed_response(
    lcp_ms: float = 1800.0,
    cls_value: float = 0.05,
    fcp_ms: float = 1200.0,
) -> dict:
    """Build a minimal PageSpeed Insights API response with LCP, CLS, and FCP."""
    return {
        "lighthouseResult": {
            "audits": {
                "largest-contentful-paint": {"numericValue": lcp_ms},
                "cumulative-layout-shift":  {"numericValue": cls_value},
                "first-contentful-paint":   {"numericValue": fcp_ms},
            }
        }
    }


async def _run_check_cwv(lcp_ms=1800.0, cls_value=0.05, fcp_ms=1200.0):
    """Run _check_cwv with mocked PageSpeed data and return results."""
    from app.services.scoring.authority_scorer import AuthorityScorer

    scorer = AuthorityScorer()
    response_data = _make_pagespeed_response(lcp_ms, cls_value, fcp_ms)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = response_data
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value.__aenter__.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = await scorer._check_cwv("https://example.com")

    return result


# ===========================================================================
# Test: _check_cwv returns 3 criteria
# ===========================================================================

class TestCwvReturnsList:
    """_check_cwv must return a list of 3 ScoringCriterionResults after the extension."""

    @pytest.mark.asyncio
    async def test_check_cwv_returns_list(self):
        """_check_cwv must return a list (not a single ScoringCriterionResult)."""
        result = await _run_check_cwv()
        assert isinstance(result, list), (
            f"Expected list, got {type(result).__name__}. "
            "_check_cwv must be updated to return a list of criteria."
        )

    @pytest.mark.asyncio
    async def test_check_cwv_returns_exactly_three_criteria(self):
        """_check_cwv must return exactly 3 criteria: LCP, CLS, FCP."""
        result = await _run_check_cwv()
        assert len(result) == 3, f"Expected 3 criteria, got {len(result)}"

    @pytest.mark.asyncio
    async def test_all_results_are_scoring_criterion_result(self):
        """All three items must be ScoringCriterionResult instances."""
        result = await _run_check_cwv()
        for item in result:
            assert isinstance(item, ScoringCriterionResult), (
                f"Expected ScoringCriterionResult, got {type(item).__name__}"
            )

    @pytest.mark.asyncio
    async def test_criterion_ids_are_s11_s11b_s11c(self):
        """Criterion IDs must be S11 (LCP), S11b (CLS), S11c (FCP)."""
        result = await _run_check_cwv()
        ids = {r.criterion_id for r in result}
        assert "S11" in ids, f"S11 (LCP) missing from {ids}"
        assert "S11b" in ids, f"S11b (CLS) missing from {ids}"
        assert "S11c" in ids, f"S11c (FCP) missing from {ids}"


# ===========================================================================
# Test: CLS scoring thresholds
# ===========================================================================

class TestCLSScoring:
    """CLS score: <0.1 = 100 (Good), 0.1–0.25 = proportional, >0.25 = 0 (Poor)."""

    def _get_cls_result(self, results: list) -> ScoringCriterionResult:
        for r in results:
            if r.criterion_id == "S11b":
                return r
        raise AssertionError(f"S11b (CLS) criterion not found in results: {[r.criterion_id for r in results]}")

    @pytest.mark.asyncio
    async def test_cls_good_below_0_1_scores_100(self):
        """CLS < 0.1 → score=100 (Good)."""
        result = await _run_check_cwv(cls_value=0.05)
        cls_r = self._get_cls_result(result)
        assert cls_r.score == 100, f"Expected 100 for CLS=0.05, got {cls_r.score}"

    @pytest.mark.asyncio
    async def test_cls_at_boundary_0_1_below_good(self):
        """CLS=0.09 → score=100 (still Good, below threshold)."""
        result = await _run_check_cwv(cls_value=0.09)
        cls_r = self._get_cls_result(result)
        assert cls_r.score == 100, f"Expected 100 for CLS=0.09, got {cls_r.score}"

    @pytest.mark.asyncio
    async def test_cls_needs_improvement_between_0_1_and_0_25(self):
        """CLS=0.175 (midpoint 0.1–0.25) → intermediate score (not 0, not 100)."""
        result = await _run_check_cwv(cls_value=0.175)
        cls_r = self._get_cls_result(result)
        assert 10 < cls_r.score < 90, (
            f"Expected intermediate score for CLS=0.175, got {cls_r.score}"
        )

    @pytest.mark.asyncio
    async def test_cls_poor_above_0_25_scores_zero(self):
        """CLS > 0.25 → score=0 (Poor)."""
        result = await _run_check_cwv(cls_value=0.30)
        cls_r = self._get_cls_result(result)
        assert cls_r.score == 0, f"Expected 0 for CLS=0.30, got {cls_r.score}"

    @pytest.mark.asyncio
    async def test_cls_extremely_bad_scores_zero(self):
        """CLS=1.0 (catastrophic layout shift) → score=0."""
        result = await _run_check_cwv(cls_value=1.0)
        cls_r = self._get_cls_result(result)
        assert cls_r.score == 0, f"Expected 0 for CLS=1.0, got {cls_r.score}"

    @pytest.mark.asyncio
    async def test_cls_result_has_human_summary_mentioning_cls(self):
        """CLS criterion human_summary must mention CLS or layout shift."""
        result = await _run_check_cwv(cls_value=0.05)
        cls_r = self._get_cls_result(result)
        summary_lower = cls_r.human_summary.lower()
        assert "cls" in summary_lower or "layout" in summary_lower or "shift" in summary_lower, (
            f"human_summary '{cls_r.human_summary}' should mention CLS"
        )

    @pytest.mark.asyncio
    async def test_cls_evidence_contains_cls_value(self):
        """CLS criterion evidence must contain the raw cls value."""
        result = await _run_check_cwv(cls_value=0.08)
        cls_r = self._get_cls_result(result)
        assert cls_r.evidence is not None
        assert "cls" in cls_r.evidence or "cumulative_layout_shift" in cls_r.evidence or any(
            "cls" in str(k).lower() for k in cls_r.evidence
        ), f"Evidence {cls_r.evidence} doesn't contain CLS value"


# ===========================================================================
# Test: FCP scoring thresholds
# ===========================================================================

class TestFCPScoring:
    """FCP score: <1800ms = 100 (Good), 1800–3000ms = proportional, >3000ms = 0 (Poor)."""

    def _get_fcp_result(self, results: list) -> ScoringCriterionResult:
        for r in results:
            if r.criterion_id == "S11c":
                return r
        raise AssertionError(f"S11c (FCP) criterion not found in results: {[r.criterion_id for r in results]}")

    @pytest.mark.asyncio
    async def test_fcp_good_below_1800ms_scores_100(self):
        """FCP=1200ms < 1800ms → score=100 (Good)."""
        result = await _run_check_cwv(fcp_ms=1200.0)
        fcp_r = self._get_fcp_result(result)
        assert fcp_r.score == 100, f"Expected 100 for FCP=1200ms, got {fcp_r.score}"

    @pytest.mark.asyncio
    async def test_fcp_at_good_boundary_1799ms(self):
        """FCP=1799ms (just below 1800ms threshold) → score=100."""
        result = await _run_check_cwv(fcp_ms=1799.0)
        fcp_r = self._get_fcp_result(result)
        assert fcp_r.score == 100, f"Expected 100 for FCP=1799ms, got {fcp_r.score}"

    @pytest.mark.asyncio
    async def test_fcp_needs_improvement_between_1800_and_3000(self):
        """FCP=2400ms (midpoint 1800–3000ms) → intermediate score."""
        result = await _run_check_cwv(fcp_ms=2400.0)
        fcp_r = self._get_fcp_result(result)
        assert 10 < fcp_r.score < 90, (
            f"Expected intermediate score for FCP=2400ms, got {fcp_r.score}"
        )

    @pytest.mark.asyncio
    async def test_fcp_poor_above_3000ms_scores_zero(self):
        """FCP=4000ms > 3000ms → score=0 (Poor)."""
        result = await _run_check_cwv(fcp_ms=4000.0)
        fcp_r = self._get_fcp_result(result)
        assert fcp_r.score == 0, f"Expected 0 for FCP=4000ms, got {fcp_r.score}"

    @pytest.mark.asyncio
    async def test_fcp_extremely_slow_scores_zero(self):
        """FCP=10000ms → score=0."""
        result = await _run_check_cwv(fcp_ms=10000.0)
        fcp_r = self._get_fcp_result(result)
        assert fcp_r.score == 0, f"Expected 0 for FCP=10000ms, got {fcp_r.score}"

    @pytest.mark.asyncio
    async def test_fcp_human_summary_mentions_fcp(self):
        """FCP criterion human_summary must mention FCP or first contentful paint."""
        result = await _run_check_cwv(fcp_ms=1200.0)
        fcp_r = self._get_fcp_result(result)
        summary_lower = fcp_r.human_summary.lower()
        assert "fcp" in summary_lower or "first contentful" in summary_lower or "paint" in summary_lower, (
            f"human_summary '{fcp_r.human_summary}' should mention FCP"
        )

    @pytest.mark.asyncio
    async def test_fcp_evidence_contains_fcp_value(self):
        """FCP criterion evidence must contain the raw fcp_ms value."""
        result = await _run_check_cwv(fcp_ms=1200.0)
        fcp_r = self._get_fcp_result(result)
        assert fcp_r.evidence is not None
        assert any("fcp" in str(k).lower() for k in fcp_r.evidence), (
            f"Evidence {fcp_r.evidence} doesn't contain FCP value"
        )


# ===========================================================================
# Test: LCP still works after refactor
# ===========================================================================

class TestLCPStillWorks:
    """Existing LCP scoring (S11) must continue to work after adding CLS and FCP."""

    def _get_lcp_result(self, results: list) -> ScoringCriterionResult:
        for r in results:
            if r.criterion_id == "S11":
                return r
        raise AssertionError(f"S11 (LCP) criterion not found: {[r.criterion_id for r in results]}")

    @pytest.mark.asyncio
    async def test_lcp_still_scores_100_below_2500ms(self):
        """LCP=1800ms < 2500ms → score=100 (existing behavior preserved)."""
        result = await _run_check_cwv(lcp_ms=1800.0)
        lcp_r = self._get_lcp_result(result)
        assert lcp_r.score == 100, f"Expected 100 for LCP=1800ms, got {lcp_r.score}"

    @pytest.mark.asyncio
    async def test_lcp_scores_low_above_4000ms(self):
        """LCP=5000ms → score < 50 (existing behavior preserved)."""
        result = await _run_check_cwv(lcp_ms=5000.0)
        lcp_r = self._get_lcp_result(result)
        assert lcp_r.score < 50, f"Expected <50 for LCP=5000ms, got {lcp_r.score}"


# ===========================================================================
# Test: score_page() integration — all 3 CWV criteria appear in page results
# ===========================================================================

class TestScorePageCWVIntegration:
    """score_page() must include S11, S11b, S11c in its criterion_results."""

    @pytest.mark.asyncio
    async def test_score_page_includes_cls_criterion(self):
        """score_page results include an S11b (CLS) criterion."""
        from app.services.scoring.authority_scorer import AuthorityScorer

        scorer = AuthorityScorer()
        response_data = _make_pagespeed_response(lcp_ms=1800, cls_value=0.05, fcp_ms=1200)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.json.return_value = response_data
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value.__aenter__.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            # Use minimal page_data that won't trigger external API calls
            page_data = {
                "url": "https://example.com",
                "domain": "example.com",
                "html": "<html><head><meta charset='utf-8'></head><body><p>Test</p></body></html>",
                "main_content": "Test content for scoring.",
                "title": "Test Page",
                "meta_description": "Test description",
                "schema_org": [],
                "ai_bot_access": {},
                "og_tags": {},
                "headings": [{"level": 1, "text": "Test"}],
                "word_count": 50,
                "internal_links_count": 3,
                "open_graph": {},
                "microdata": [],
                "content_keywords": [],
                "industry_signals": [],
                "authority_markers": {},
            }

            with patch.object(scorer, "_check_knowledge_graph", return_value=_dummy_criterion("A3")):
                with patch.object(scorer, "_check_wikidata", new_callable=lambda: lambda self: AsyncMock(return_value=_dummy_criterion("A4"))()):
                    results = await scorer.score_page(page_data)

        criterion_ids = {r.criterion_id for r in results}
        assert "S11b" in criterion_ids, (
            f"S11b (CLS) not in score_page results. Found: {sorted(criterion_ids)}"
        )

    @pytest.mark.asyncio
    async def test_score_page_includes_fcp_criterion(self):
        """score_page results include an S11c (FCP) criterion."""
        from app.services.scoring.authority_scorer import AuthorityScorer

        scorer = AuthorityScorer()
        response_data = _make_pagespeed_response(lcp_ms=1800, cls_value=0.05, fcp_ms=1200)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.json.return_value = response_data
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value.__aenter__.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            page_data = {
                "url": "https://example.com",
                "domain": "example.com",
                "html": "<html><head></head><body><p>Test</p></body></html>",
                "main_content": "Test.",
                "title": "Test",
                "meta_description": "",
                "schema_org": [],
                "ai_bot_access": {},
                "og_tags": {},
                "headings": [],
                "word_count": 10,
                "internal_links_count": 0,
                "open_graph": {},
                "microdata": [],
                "content_keywords": [],
                "industry_signals": [],
                "authority_markers": {},
            }

            with patch.object(scorer, "_check_knowledge_graph", return_value=_dummy_criterion("A3")):
                with patch.object(scorer, "_check_wikidata", new_callable=lambda: lambda self: AsyncMock(return_value=_dummy_criterion("A4"))()):
                    results = await scorer.score_page(page_data)

        criterion_ids = {r.criterion_id for r in results}
        assert "S11c" in criterion_ids, (
            f"S11c (FCP) not in score_page results. Found: {sorted(criterion_ids)}"
        )


def _dummy_criterion(criterion_id: str) -> ScoringCriterionResult:
    """Create a dummy criterion result for mocking purposes."""
    return ScoringCriterionResult(
        criterion_id=criterion_id,
        criterion_name=f"Dummy {criterion_id}",
        score=50,
        human_summary="Mocked",
        technical_detail="Mocked for testing",
        checked=False,
    )
