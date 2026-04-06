"""Unit tests for ScoringOrchestrator aggregation and link discovery.

Tests the weakest-link aggregation formula (compute_optimization_score),
link discovery (_discover_internal_links), and edge cases.
All tests use mocked DB and no real HTTP calls.
"""

from unittest.mock import MagicMock

import pytest

from app.services.scoring.scoring_orchestrator import ScoringOrchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_orchestrator() -> ScoringOrchestrator:
    """Create a ScoringOrchestrator with a mocked DB session."""
    mock_db = MagicMock()
    return ScoringOrchestrator(db=mock_db)


# ===========================================================================
# Test: compute_optimization_score (weakest-link aggregation)
# ===========================================================================

class TestWeakestLinkAggregation:
    """Tests for the weakest-link aggregation formula."""

    def test_weakest_link_single_page(self):
        """One page with known category scores. Hand-calculated expected result.

        Given:
          crawlability=80, content_structure=70, structured_data=60, authority=50

        Technical weights: crawlability=0.25, content_structure=0.25, structured_data=0.20, authority=0.15
        weighted_sum = 80*0.25 + 70*0.25 + 60*0.20 + 50*0.15
                     = 20 + 17.5 + 12 + 7.5 = 57.0
        active_weight = 0.25 + 0.25 + 0.20 + 0.15 = 0.85
        page_score = 57.0 / 0.85 = 67.06

        With 1 page: mean = min = 67.06
        site_technical_score = 0.6 * 67.06 + 0.4 * 67.06 = 67.06 -> 67
        """
        orchestrator = _make_orchestrator()
        page_scores = [
            {
                "crawlability": 80,
                "content_structure": 70,
                "structured_data": 60,
                "authority": 50,
            }
        ]

        result = orchestrator.compute_optimization_score(page_scores)
        assert result == 67, f"Expected 67, got {result}"

    def test_weakest_link_multi_page(self):
        """Two pages with different scores. Weaker page drags the score down.

        Page 1: crawl=90, content=80, structured=70, authority=60
          weighted_sum = 90*0.25 + 80*0.25 + 70*0.20 + 60*0.15
                       = 22.5 + 20 + 14 + 9 = 65.5
          page_score = 65.5 / 0.85 = 77.06

        Page 2: crawl=40, content=30, structured=20, authority=10
          weighted_sum = 40*0.25 + 30*0.25 + 20*0.20 + 10*0.15
                       = 10 + 7.5 + 4 + 1.5 = 23.0
          page_score = 23.0 / 0.85 = 27.06

        mean = (77.06 + 27.06) / 2 = 52.06
        min = 27.06
        site_technical = 0.6 * 52.06 + 0.4 * 27.06 = 31.24 + 10.82 = 42.06 -> 42
        """
        orchestrator = _make_orchestrator()
        page_scores = [
            {
                "crawlability": 90,
                "content_structure": 80,
                "structured_data": 70,
                "authority": 60,
            },
            {
                "crawlability": 40,
                "content_structure": 30,
                "structured_data": 20,
                "authority": 10,
            },
        ]

        result = orchestrator.compute_optimization_score(page_scores)
        assert result == 42, f"Expected 42, got {result}"

        # Verify the weak page drags the score down: single page 1 would score higher
        single_page = orchestrator.compute_optimization_score([page_scores[0]])
        assert result < single_page, (
            f"Multi-page score ({result}) should be < single strong page ({single_page})"
        )

    def test_weakest_link_empty_pages(self):
        """No pages scored. Should return 0."""
        orchestrator = _make_orchestrator()
        result = orchestrator.compute_optimization_score([])
        assert result == 0, f"Expected 0, got {result}"

    def test_weakest_link_missing_categories(self):
        """Page missing some categories. Normalization by active weight.

        Page with only crawlability=90 and content_structure=80:
          weighted_sum = 90*0.25 + 80*0.25 = 42.5
          active_weight = 0.25 + 0.25 = 0.50
          page_score = 42.5 / 0.50 = 85.0

        site_technical = 85.0 -> 85
        """
        orchestrator = _make_orchestrator()
        page_scores = [
            {
                "crawlability": 90,
                "content_structure": 80,
            }
        ]

        result = orchestrator.compute_optimization_score(page_scores)
        assert result == 85, f"Expected 85, got {result}"

    def test_score_clamped_0_100(self):
        """Verify result is always in 0-100 range even with extreme inputs."""
        orchestrator = _make_orchestrator()

        # All-zero scores
        page_scores = [
            {
                "crawlability": 0,
                "content_structure": 0,
                "structured_data": 0,
                "authority": 0,
            }
        ]
        result_zero = orchestrator.compute_optimization_score(page_scores)
        assert 0 <= result_zero <= 100

        # All-max scores
        page_scores_max = [
            {
                "crawlability": 100,
                "content_structure": 100,
                "structured_data": 100,
                "authority": 100,
            }
        ]
        result_max = orchestrator.compute_optimization_score(page_scores_max)
        assert result_max == 100
        assert 0 <= result_max <= 100

    def test_weakest_link_all_perfect_scores(self):
        """All categories at 100.

        weighted_sum = 100*0.25 + 100*0.25 + 100*0.20 + 100*0.15 = 85
        page_score = 85 / 0.85 = 100
        site_technical = 100
        result = 100
        """
        orchestrator = _make_orchestrator()
        page_scores = [
            {
                "crawlability": 100,
                "content_structure": 100,
                "structured_data": 100,
                "authority": 100,
            }
        ]

        result = orchestrator.compute_optimization_score(page_scores)
        assert result == 100, f"Expected 100, got {result}"


# ===========================================================================
# Test: _discover_internal_links
# ===========================================================================

class TestDiscoverInternalLinks:
    """Tests for internal link discovery from HTML."""

    def test_discover_links_from_html(self):
        """Provide real HTML with anchor tags. Verify internal links are found."""
        orchestrator = _make_orchestrator()
        html = """
        <html><body>
            <a href="/about">About</a>
            <a href="/pricing">Pricing</a>
            <a href="/features">Features</a>
            <a href="https://example.com/blog">Blog</a>
            <a href="/about">About Again</a>
        </body></html>
        """

        links = orchestrator._discover_internal_links(
            html=html, base_url="https://example.com", domain="example.com"
        )

        # Links should be found and sorted by count
        assert len(links) > 0
        urls = [url for url, count in links]
        # /about appears twice so should have count=2
        about_entry = next((url, count) for url, count in links if "/about" in url)
        assert about_entry[1] == 2, f"Expected /about count=2, got {about_entry[1]}"

    def test_discover_links_skips_external(self):
        """External domain links should be excluded."""
        orchestrator = _make_orchestrator()
        html = """
        <html><body>
            <a href="/internal">Internal</a>
            <a href="https://other-domain.com/page">External</a>
            <a href="https://another.org/path">External2</a>
        </body></html>
        """

        links = orchestrator._discover_internal_links(
            html=html, base_url="https://example.com", domain="example.com"
        )

        urls = [url for url, count in links]
        for url in urls:
            assert "other-domain.com" not in url
            assert "another.org" not in url

    def test_discover_links_skips_non_content(self):
        """Non-content URLs (/login, /admin, .pdf) should be skipped."""
        orchestrator = _make_orchestrator()
        html = """
        <html><body>
            <a href="/about">About</a>
            <a href="/login">Login</a>
            <a href="/admin/dashboard">Admin</a>
            <a href="/docs/guide.pdf">PDF Guide</a>
            <a href="/api/v1/users">API</a>
            <a href="/pricing">Pricing</a>
        </body></html>
        """

        links = orchestrator._discover_internal_links(
            html=html, base_url="https://example.com", domain="example.com"
        )

        urls = [url for url, count in links]
        for url in urls:
            assert "/login" not in url, f"Login URL should be skipped: {url}"
            assert "/admin" not in url, f"Admin URL should be skipped: {url}"
            assert ".pdf" not in url, f"PDF URL should be skipped: {url}"
            assert "/api/" not in url, f"API URL should be skipped: {url}"

    def test_discover_links_empty_html(self):
        """Empty string should return empty list without crashing."""
        orchestrator = _make_orchestrator()

        links = orchestrator._discover_internal_links(
            html="", base_url="https://example.com", domain="example.com"
        )

        assert links == []


# ===========================================================================
# Test: CATEGORY_WEIGHTS — structure validation
# ===========================================================================

class TestCategoryWeights:
    """CATEGORY_WEIGHTS must reflect the full 5-category scoring architecture."""

    def test_category_weights_contains_ai_visibility(self):
        """CATEGORY_WEIGHTS must include 'ai_visibility' (SomScorer target category).

        Added in docs/RedwaneNextDirection.md Axe 5.
        """
        orchestrator = _make_orchestrator()
        assert "ai_visibility" in orchestrator.CATEGORY_WEIGHTS, (
            "ai_visibility must be in CATEGORY_WEIGHTS to enable SomScorer registration"
        )

    def test_category_weights_ai_visibility_value(self):
        """ai_visibility weight must be 0.15 as specified in the architecture."""
        orchestrator = _make_orchestrator()
        assert orchestrator.CATEGORY_WEIGHTS["ai_visibility"] == pytest.approx(0.15)

    def test_category_weights_sum_to_1(self):
        """All CATEGORY_WEIGHTS must sum to exactly 1.0."""
        orchestrator = _make_orchestrator()
        total = sum(orchestrator.CATEGORY_WEIGHTS.values())
        assert total == pytest.approx(1.0), (
            f"CATEGORY_WEIGHTS sum to {total:.3f}, expected 1.0"
        )

    def test_category_weights_contains_all_five_categories(self):
        """CATEGORY_WEIGHTS must have exactly 5 categories."""
        orchestrator = _make_orchestrator()
        expected = {"crawlability", "content_structure", "structured_data", "authority", "ai_visibility"}
        actual = set(orchestrator.CATEGORY_WEIGHTS.keys())
        assert actual == expected, (
            f"Expected categories {expected}, got {actual}"
        )

    def test_compute_optimization_score_excludes_ai_visibility(self):
        """compute_optimization_score uses technical_weights only (no ai_visibility).

        This is intentional: the optimization score is a pure technical readiness
        proxy. ai_visibility (Share of Model) is tracked separately as geo_visibility_score.
        Adding ai_visibility to page_category_scores must not change the result.
        """
        orchestrator = _make_orchestrator()

        # Page with technical categories only
        page_scores_without_som = [
            {"crawlability": 80, "content_structure": 70, "structured_data": 60, "authority": 50}
        ]
        # Same page with ai_visibility added
        page_scores_with_som = [
            {"crawlability": 80, "content_structure": 70, "structured_data": 60, "authority": 50, "ai_visibility": 20}
        ]

        score_without = orchestrator.compute_optimization_score(page_scores_without_som)
        score_with = orchestrator.compute_optimization_score(page_scores_with_som)

        assert score_without == score_with, (
            f"ai_visibility ({score_with}) changed optimization score vs without ({score_without}). "
            "compute_optimization_score must use technical_weights only."
        )
