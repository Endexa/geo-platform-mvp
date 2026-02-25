"""Integration tests for all 4 category scorers against known HTML fixtures.

Tests each scorer (Crawlability, Content Structure, Structured Data, Authority)
produces correct criterion counts, score ranges, checked states, and handles
edge cases gracefully. All tests run without external API keys.
"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scoring.base_scorer import ScoringCriterionResult
from app.services.scoring.crawlability_scorer import CrawlabilityScorer
from app.services.scoring.content_structure_scorer import ContentStructureScorer
from app.services.scoring.structured_data_scorer import StructuredDataScorer
from app.services.scoring.authority_scorer import AuthorityScorer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def stripe_crawl_data() -> dict:
    """Load the known-good crawl data fixture (mimics a well-structured page)."""
    with open(FIXTURES_DIR / "stripe_crawl_data.json") as f:
        return json.load(f)


@pytest.fixture()
def minimal_crawl_data() -> dict:
    """A minimal crawl data dict for testing edge cases (empty content)."""
    return {
        "url": "https://empty-test.com",
        "domain": "empty-test.com",
        "html": "",
        "main_content": "",
        "title": "",
        "meta_description": "",
        "schema_org": [],
        "ai_bot_access": {},
        "og_tags": {},
        "headings": [],
        "word_count": 0,
        "internal_links_count": 0,
        "open_graph": {},
        "microdata": [],
        "content_keywords": [],
        "industry_signals": [],
        "authority_markers": {},
    }


def _validate_results(
    results: list[ScoringCriterionResult],
    expected_count: int,
    expected_prefix: str,
):
    """Shared validation: count, score range, criterion_id prefix."""
    assert len(results) == expected_count, (
        f"Expected {expected_count} results, got {len(results)}: "
        f"{[r.criterion_id for r in results]}"
    )
    for r in results:
        assert 0 <= r.score <= 100, (
            f"{r.criterion_id} score {r.score} out of range"
        )
        assert r.criterion_id.startswith(expected_prefix) or r.criterion_id.startswith("S"), (
            f"Unexpected criterion_id prefix: {r.criterion_id}"
        )


# ===========================================================================
# TestCrawlabilityScorer
# ===========================================================================

class TestCrawlabilityScorer:
    """Tests for CrawlabilityScorer (C1-C12)."""

    @pytest.mark.asyncio
    async def test_crawlability_scorer_returns_12_criteria(
        self, stripe_crawl_data
    ):
        """Score_page returns exactly 12 results with criterion IDs C1-C12."""
        scorer = CrawlabilityScorer()

        # Mock all external HTTP calls (robots.txt, TTFB, status code)
        with patch("app.services.scoring.crawlability_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            # Mock robots.txt response
            mock_robots_resp = MagicMock()
            mock_robots_resp.status_code = 200
            mock_robots_resp.text = "User-agent: *\nAllow: /\n"

            # Mock TTFB response
            mock_ttfb_resp = MagicMock()
            mock_ttfb_resp.status_code = 200
            mock_ttfb_resp.elapsed = MagicMock()
            mock_ttfb_resp.elapsed.total_seconds.return_value = 0.35

            # Mock status code response
            mock_status_resp = MagicMock()
            mock_status_resp.status_code = 200
            mock_status_resp.headers = {}

            mock_client.get = AsyncMock(side_effect=[
                mock_robots_resp,  # robots.txt for C4
                mock_robots_resp,  # robots.txt for C6 (cached but method resolves)
                mock_ttfb_resp,    # TTFB for C10
                mock_status_resp,  # Status code for C11
                mock_robots_resp,  # Resource blockage for C12
            ])

            results = await scorer.score_page(stripe_crawl_data)
            await scorer.cleanup()

        assert len(results) == 12
        criterion_ids = {r.criterion_id for r in results}
        expected_ids = {f"C{i}" for i in range(1, 13)}
        assert criterion_ids == expected_ids

    @pytest.mark.asyncio
    async def test_crawlability_bot_access_scores_nonzero(
        self, stripe_crawl_data
    ):
        """With all bots allowed, at least 6 of C1-C8 should be checked=True with score=100."""
        scorer = CrawlabilityScorer()

        with patch("app.services.scoring.crawlability_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "User-agent: *\nAllow: /\n"
            mock_resp.elapsed = MagicMock()
            mock_resp.elapsed.total_seconds.return_value = 0.35
            mock_resp.headers = {}
            mock_client.get = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)
            await scorer.cleanup()

        bot_results = [r for r in results if r.criterion_id.startswith("C") and int(r.criterion_id[1:]) <= 8]
        checked_bots = [r for r in bot_results if r.checked]
        assert len(checked_bots) >= 6, (
            f"Expected at least 6 bot checks to be checked=True, got {len(checked_bots)}"
        )
        # Bots that are True in fixture should score 100
        high_scorers = [r for r in checked_bots if r.score == 100]
        assert len(high_scorers) >= 5

    @pytest.mark.asyncio
    async def test_crawlability_category_score_above_zero(
        self, stripe_crawl_data
    ):
        """Category score for a well-structured page should be > 0."""
        scorer = CrawlabilityScorer()

        with patch("app.services.scoring.crawlability_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "User-agent: *\nAllow: /\n"
            mock_resp.elapsed = MagicMock()
            mock_resp.elapsed.total_seconds.return_value = 0.35
            mock_resp.headers = {}
            mock_client.get = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)
            category_score = scorer.compute_category_score(results)
            await scorer.cleanup()

        assert category_score > 0, "Category score should be > 0 for well-structured page"

    @pytest.mark.asyncio
    async def test_crawlability_empty_html_returns_results(
        self, minimal_crawl_data
    ):
        """Empty HTML should return 12 results without crashing, many NOT_CHECKED."""
        scorer = CrawlabilityScorer()

        with patch("app.services.scoring.crawlability_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            # Simulate failures for external calls
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

            results = await scorer.score_page(minimal_crawl_data)
            await scorer.cleanup()

        assert len(results) == 12
        # With no ai_bot_access fields, bots should still return results (score=100 for no directive)
        not_checked = [r for r in results if not r.checked]
        # C9 (SSR), C10 (TTFB), C11 (status), C12 (resource blockage) should be not_checked
        assert len(not_checked) >= 2, "At least C10, C11 should be NOT_CHECKED on connection failure"


# ===========================================================================
# TestContentStructureScorer
# ===========================================================================

class TestContentStructureScorer:
    """Tests for ContentStructureScorer (CS1-CS13)."""

    @pytest.mark.asyncio
    async def test_content_structure_returns_13_criteria(
        self, stripe_crawl_data
    ):
        """Score_page returns exactly 13 results with criterion IDs CS1-CS13."""
        scorer = ContentStructureScorer()
        results = await scorer.score_page(stripe_crawl_data)

        assert len(results) == 13
        criterion_ids = {r.criterion_id for r in results}
        expected_ids = {f"CS{i}" for i in range(1, 14)}
        assert criterion_ids == expected_ids

    @pytest.mark.asyncio
    async def test_content_structure_scores_in_range(
        self, stripe_crawl_data
    ):
        """All 13 criterion scores should be in 0-100 range."""
        scorer = ContentStructureScorer()
        results = await scorer.score_page(stripe_crawl_data)

        for r in results:
            assert 0 <= r.score <= 100, f"{r.criterion_id} score {r.score} out of range"

    @pytest.mark.asyncio
    async def test_content_structure_well_formed_page_checked_count(
        self, stripe_crawl_data
    ):
        """At least 10 of 13 criteria should be checked=True for well-structured HTML."""
        scorer = ContentStructureScorer()
        results = await scorer.score_page(stripe_crawl_data)

        checked = [r for r in results if r.checked]
        assert len(checked) >= 10, (
            f"Expected at least 10 checked criteria, got {len(checked)}: "
            f"unchecked={[r.criterion_id for r in results if not r.checked]}"
        )

    @pytest.mark.asyncio
    async def test_content_structure_well_formed_page_scores_above_30(
        self, stripe_crawl_data
    ):
        """Category score for a well-structured page should be > 30."""
        scorer = ContentStructureScorer()
        results = await scorer.score_page(stripe_crawl_data)
        category_score = scorer.compute_category_score(results)

        assert category_score > 30, (
            f"Category score {category_score} should be > 30 for well-structured HTML"
        )

    @pytest.mark.asyncio
    async def test_content_structure_heading_hierarchy_well_formed(
        self, stripe_crawl_data
    ):
        """CS1 heading hierarchy should score well for page with proper h1/h2/h3."""
        scorer = ContentStructureScorer()
        results = await scorer.score_page(stripe_crawl_data)

        cs1 = next(r for r in results if r.criterion_id == "CS1")
        assert cs1.checked is True
        assert cs1.score >= 50, f"CS1 score {cs1.score} too low for well-structured headings"

    @pytest.mark.asyncio
    async def test_content_structure_empty_content_returns_results(
        self, minimal_crawl_data
    ):
        """Empty content should return 13 results without crashing."""
        scorer = ContentStructureScorer()
        results = await scorer.score_page(minimal_crawl_data)

        assert len(results) == 13
        # Most criteria should still produce a result (possibly score=0 or not_checked)
        for r in results:
            assert 0 <= r.score <= 100

    @pytest.mark.asyncio
    async def test_content_structure_faq_detected(
        self, stripe_crawl_data
    ):
        """CS5 FAQ presence should detect the FAQ section in the fixture."""
        scorer = ContentStructureScorer()
        results = await scorer.score_page(stripe_crawl_data)

        cs5 = next(r for r in results if r.criterion_id == "CS5")
        assert cs5.checked is True
        assert cs5.score > 0, "CS5 should score > 0 for page with FAQ section"


# ===========================================================================
# TestStructuredDataScorer
# ===========================================================================

class TestStructuredDataScorer:
    """Tests for StructuredDataScorer (SD1-SD13)."""

    @pytest.mark.asyncio
    async def test_structured_data_returns_13_criteria(
        self, stripe_crawl_data
    ):
        """Score_page returns exactly 13 results with criterion IDs SD1-SD13."""
        scorer = StructuredDataScorer()

        # Mock HTTP calls for llms.txt and llms-full.txt
        with patch("app.services.scoring.structured_data_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_client.get = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)

        assert len(results) == 13
        criterion_ids = {r.criterion_id for r in results}
        expected_ids = {f"SD{i}" for i in range(1, 14)}
        assert criterion_ids == expected_ids

    @pytest.mark.asyncio
    async def test_structured_data_scores_in_range(
        self, stripe_crawl_data
    ):
        """All 13 criterion scores should be in 0-100 range."""
        scorer = StructuredDataScorer()

        with patch("app.services.scoring.structured_data_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_client.get = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)

        for r in results:
            assert 0 <= r.score <= 100, f"{r.criterion_id} score {r.score} out of range"

    @pytest.mark.asyncio
    async def test_structured_data_organization_detected(
        self, stripe_crawl_data
    ):
        """SD1 should detect Organization schema and score 100."""
        scorer = StructuredDataScorer()

        with patch("app.services.scoring.structured_data_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_client.get = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)

        sd1 = next(r for r in results if r.criterion_id == "SD1")
        assert sd1.checked is True
        assert sd1.score == 100, f"SD1 should be 100 for Organization schema, got {sd1.score}"

    @pytest.mark.asyncio
    async def test_structured_data_sameas_links(
        self, stripe_crawl_data
    ):
        """SD2 should detect sameAs links and score > 0."""
        scorer = StructuredDataScorer()

        with patch("app.services.scoring.structured_data_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_client.get = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)

        sd2 = next(r for r in results if r.criterion_id == "SD2")
        assert sd2.checked is True
        assert sd2.score > 0, f"SD2 should score > 0 with 5 sameAs links, got {sd2.score}"

    @pytest.mark.asyncio
    async def test_structured_data_article_detected(
        self, stripe_crawl_data
    ):
        """SD4 should detect Article schema and score 100."""
        scorer = StructuredDataScorer()

        with patch("app.services.scoring.structured_data_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_client.get = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)

        sd4 = next(r for r in results if r.criterion_id == "SD4")
        assert sd4.checked is True
        assert sd4.score == 100

    @pytest.mark.asyncio
    async def test_structured_data_empty_schema_returns_results(
        self, minimal_crawl_data
    ):
        """Empty schema_org should produce 13 valid results without crashing."""
        scorer = StructuredDataScorer()

        with patch("app.services.scoring.structured_data_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_client.get = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(minimal_crawl_data)

        assert len(results) == 13
        for r in results:
            assert 0 <= r.score <= 100


# ===========================================================================
# TestAuthorityScorer
# ===========================================================================

class TestAuthorityScorer:
    """Tests for AuthorityScorer (A1-A8, S1-S15)."""

    @pytest.mark.asyncio
    async def test_authority_scorer_returns_23_criteria(
        self, stripe_crawl_data
    ):
        """Score_page returns exactly 23 results (A1-A8 + S1-S15)."""
        scorer = AuthorityScorer()

        # Mock all external HTTP calls
        with patch("app.services.scoring.authority_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            # Mock responses for Wikidata, Wikipedia, sitemap, etc.
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"search": [], "query": {"pages": {"-1": {"missing": ""}}}}
            mock_resp.text = ""
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.head = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)

        assert len(results) == 23, (
            f"Expected 23 results, got {len(results)}: "
            f"{[r.criterion_id for r in results]}"
        )

    @pytest.mark.asyncio
    async def test_authority_scorer_criterion_ids(
        self, stripe_crawl_data
    ):
        """All expected criterion IDs (A1-A8, S1-S15) should be present."""
        scorer = AuthorityScorer()

        with patch("app.services.scoring.authority_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"search": [], "query": {"pages": {"-1": {"missing": ""}}}}
            mock_resp.text = ""
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.head = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)

        criterion_ids = {r.criterion_id for r in results}
        expected_a = {f"A{i}" for i in range(1, 9)}
        expected_s = {f"S{i}" for i in range(1, 16)}
        expected_all = expected_a | expected_s
        assert criterion_ids == expected_all, (
            f"Missing: {expected_all - criterion_ids}, Extra: {criterion_ids - expected_all}"
        )

    @pytest.mark.asyncio
    async def test_authority_scores_in_range(
        self, stripe_crawl_data
    ):
        """All 23 criterion scores should be in 0-100 range."""
        scorer = AuthorityScorer()

        with patch("app.services.scoring.authority_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"search": [], "query": {"pages": {"-1": {"missing": ""}}}}
            mock_resp.text = ""
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.head = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)

        for r in results:
            assert 0 <= r.score <= 100, f"{r.criterion_id} score {r.score} out of range"

    @pytest.mark.asyncio
    async def test_authority_knowledge_graph_not_checked_without_key(
        self, stripe_crawl_data
    ):
        """A3 (Knowledge Graph) should be NOT_CHECKED when GOOGLE_API_KEY is absent."""
        scorer = AuthorityScorer()

        with patch("app.services.scoring.authority_scorer.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = ""
            mock_settings.SCORING_CRAWL_CAP = 25

            with patch("app.services.scoring.authority_scorer.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"search": [], "query": {"pages": {"-1": {"missing": ""}}}}
                mock_resp.text = ""
                mock_resp.raise_for_status = MagicMock()
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_client.head = AsyncMock(return_value=mock_resp)

                results = await scorer.score_page(stripe_crawl_data)

        a3 = next(r for r in results if r.criterion_id == "A3")
        assert a3.checked is False, "A3 should be NOT_CHECKED without GOOGLE_API_KEY"

    @pytest.mark.asyncio
    async def test_authority_checked_count_for_well_structured_page(
        self, stripe_crawl_data
    ):
        """At least 15 criteria should be checked=True for a well-structured page."""
        scorer = AuthorityScorer()

        with patch("app.services.scoring.authority_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"search": [], "query": {"pages": {"-1": {"missing": ""}}}}
            mock_resp.text = ""
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.head = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(stripe_crawl_data)

        checked = [r for r in results if r.checked]
        assert len(checked) >= 15, (
            f"Expected at least 15 checked criteria, got {len(checked)}: "
            f"unchecked={[r.criterion_id for r in results if not r.checked]}"
        )

    @pytest.mark.asyncio
    async def test_authority_minimal_page_returns_results(
        self, minimal_crawl_data
    ):
        """Minimal page data should still return 23 results without crashing."""
        scorer = AuthorityScorer()

        with patch("app.services.scoring.authority_scorer.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"search": [], "query": {"pages": {"-1": {"missing": ""}}}}
            mock_resp.text = ""
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.head = AsyncMock(return_value=mock_resp)

            results = await scorer.score_page(minimal_crawl_data)

        assert len(results) == 23
        for r in results:
            assert 0 <= r.score <= 100
