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
          visibility_score=40

        Technical weights: crawlability=0.25, content_structure=0.25, structured_data=0.20, authority=0.15
        Total technical weight = 0.85

        weighted_sum = 80*0.25 + 70*0.25 + 60*0.20 + 50*0.15
                     = 20 + 17.5 + 12 + 7.5 = 57.0
        active_weight = 0.25 + 0.25 + 0.20 + 0.15 = 0.85
        page_score = (57.0 / 0.85) * 0.85 = 57.0

        With 1 page: mean = 57.0, min = 57.0
        site_technical_score = 0.6 * 57.0 + 0.4 * 57.0 = 57.0

        final = 57.0 + 40 * 0.15 = 57.0 + 6.0 = 63.0
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

        result = orchestrator.compute_optimization_score(page_scores, visibility_score=40)
        assert result == 63, f"Expected 63, got {result}"

    def test_weakest_link_multi_page(self):
        """Two pages with different scores. Weaker page drags the score down.

        Page 1: crawl=90, content=80, structured=70, authority=60
          weighted_sum = 90*0.25 + 80*0.25 + 70*0.20 + 60*0.15
                       = 22.5 + 20 + 14 + 9 = 65.5
          page_score = (65.5 / 0.85) * 0.85 = 65.5

        Page 2: crawl=40, content=30, structured=20, authority=10
          weighted_sum = 40*0.25 + 30*0.25 + 20*0.20 + 10*0.15
                       = 10 + 7.5 + 4 + 1.5 = 23.0
          page_score = (23.0 / 0.85) * 0.85 = 23.0

        mean = (65.5 + 23.0) / 2 = 44.25
        min = 23.0
        site_technical = 0.6 * 44.25 + 0.4 * 23.0 = 26.55 + 9.2 = 35.75

        visibility_score = 50
        final = 35.75 + 50 * 0.15 = 35.75 + 7.5 = 43.25 -> 43

        Verify weak page drags score down (should be < single-page score of page 1 alone).
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

        result = orchestrator.compute_optimization_score(page_scores, visibility_score=50)
        assert result == 43, f"Expected 43, got {result}"

        # Verify the weak page drags the score down: single page 1 would score higher
        single_page = orchestrator.compute_optimization_score(
            [page_scores[0]], visibility_score=50
        )
        assert result < single_page, (
            f"Multi-page score ({result}) should be < single strong page ({single_page})"
        )

    def test_weakest_link_empty_pages(self):
        """No pages scored. Should return visibility contribution only.

        visibility_score = 80
        result = clamp(80 * 0.15) = clamp(12) = 12
        """
        orchestrator = _make_orchestrator()
        result = orchestrator.compute_optimization_score([], visibility_score=80)
        assert result == 12, f"Expected 12, got {result}"

    def test_weakest_link_missing_categories(self):
        """Page missing some categories. Normalization by active weight.

        Page with only crawlability=90 and content_structure=80:
          weighted_sum = 90*0.25 + 80*0.25 = 42.5
          active_weight = 0.25 + 0.25 = 0.50
          page_score = (42.5 / 0.50) * 0.85 = 85 * 0.85 = 72.25

        site_technical = 0.6 * 72.25 + 0.4 * 72.25 = 72.25 (single page)
        final = 72.25 + 0 * 0.15 = 72.25 -> 72
        """
        orchestrator = _make_orchestrator()
        page_scores = [
            {
                "crawlability": 90,
                "content_structure": 80,
            }
        ]

        result = orchestrator.compute_optimization_score(page_scores, visibility_score=0)
        assert result == 72, f"Expected 72, got {result}"

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
        result_zero = orchestrator.compute_optimization_score(page_scores, visibility_score=0)
        assert 0 <= result_zero <= 100

        # All-max scores with max visibility
        page_scores_max = [
            {
                "crawlability": 100,
                "content_structure": 100,
                "structured_data": 100,
                "authority": 100,
            }
        ]
        result_max = orchestrator.compute_optimization_score(page_scores_max, visibility_score=100)
        assert 0 <= result_max <= 100

        # Negative visibility (edge case)
        result_neg = orchestrator.compute_optimization_score(page_scores_max, visibility_score=-100)
        assert 0 <= result_neg <= 100

    def test_weakest_link_all_perfect_scores(self):
        """All categories at 100, visibility at 100.

        weighted_sum = 100*0.25 + 100*0.25 + 100*0.20 + 100*0.15
                     = 25 + 25 + 20 + 15 = 85
        page_score = (85 / 0.85) * 0.85 = 85

        site_technical = 0.6 * 85 + 0.4 * 85 = 85
        final = 85 + 100 * 0.15 = 85 + 15 = 100
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

        result = orchestrator.compute_optimization_score(page_scores, visibility_score=100)
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
