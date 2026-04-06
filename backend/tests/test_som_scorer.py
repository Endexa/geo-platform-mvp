"""Tests for SomScorer — converts VisibilityScore per_engine_scores to a COMP1 criterion.

Based on spec: docs/RedwaneNextDirection.md — Axe 5 (SomScorer COMP module).

These tests are FAILING by design until SomScorer is implemented at:
    backend/app/services/scoring/som_scorer.py

SomScorer spec:
- Inherits from BaseScorer
- score_page(page_data) reads page_data["visibility_score_data"]["per_engine_scores"]
- For each engine dict with "queries_with_mentions" + "queries_sent", computes SoM ratio
- Averages SoM ratios across all valid engines → score = int(avg * 100)
- Returns [ScoringCriterionResult(criterion_id="COMP1", ...)]
"""

import pytest

from app.services.scoring.base_scorer import BaseScorer, ScoringCriterionResult


# ===========================================================================
# Test: SomScorer structure and inheritance
# ===========================================================================

class TestSomScorerStructure:
    """SomScorer must satisfy the BaseScorer contract."""

    def test_som_scorer_is_importable(self):
        """SomScorer must be importable from the scoring module."""
        from app.services.scoring.som_scorer import SomScorer  # noqa: F401

    def test_som_scorer_inherits_base_scorer(self):
        """SomScorer must inherit from BaseScorer."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        assert isinstance(scorer, BaseScorer)

    def test_som_scorer_instantiable_without_args(self):
        """SomScorer requires no constructor arguments."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        assert scorer is not None

    def test_som_scorer_has_score_page_method(self):
        """SomScorer must implement the abstract score_page method."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        assert callable(getattr(scorer, "score_page", None))


# ===========================================================================
# Test: score_page() — COMP1 criterion shape
# ===========================================================================

class TestSomScorerCriteria:
    """score_page() must return exactly one COMP1 ScoringCriterionResult."""

    @pytest.mark.asyncio
    async def test_returns_exactly_one_criterion(self):
        """score_page always returns exactly one result."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        results = await scorer.score_page({})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_criterion_id_is_comp1(self):
        """The single criterion must have criterion_id='COMP1'."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        results = await scorer.score_page({})
        assert results[0].criterion_id == "COMP1"

    @pytest.mark.asyncio
    async def test_criterion_is_scoring_criterion_result_instance(self):
        """The returned item must be a ScoringCriterionResult."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        results = await scorer.score_page({})
        assert isinstance(results[0], ScoringCriterionResult)

    @pytest.mark.asyncio
    async def test_criterion_name_describes_share_of_model(self):
        """Criterion name must reference 'share', 'model', or AI engines."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        results = await scorer.score_page({})
        name_lower = results[0].criterion_name.lower()
        assert any(kw in name_lower for kw in ("share", "model", "ai", "engine", "visibility")), (
            f"Criterion name '{results[0].criterion_name}' should describe Share of Model"
        )

    @pytest.mark.asyncio
    async def test_human_summary_mentions_percentage(self):
        """human_summary must mention a percentage or citation rate."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai": {"queries_sent": 10, "queries_with_mentions": 7},
                }
            }
        }
        results = await scorer.score_page(page_data)
        summary_lower = results[0].human_summary.lower()
        assert "%" in results[0].human_summary or "percent" in summary_lower or "70" in results[0].human_summary


# ===========================================================================
# Test: score_page() — scoring math
# ===========================================================================

class TestSomScorerMath:
    """Verify the exact SoM scoring formula: avg(mentions/sent) * 100."""

    @pytest.mark.asyncio
    async def test_empty_page_data_returns_score_zero(self):
        """No visibility data at all → score=0."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        results = await scorer.score_page({})
        assert results[0].score == 0

    @pytest.mark.asyncio
    async def test_empty_per_engine_scores_returns_score_zero(self):
        """Empty per_engine_scores dict → score=0."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {"visibility_score_data": {"per_engine_scores": {}}}
        results = await scorer.score_page(page_data)
        assert results[0].score == 0

    @pytest.mark.asyncio
    async def test_single_engine_perfect_score(self):
        """1 engine, 10/10 mentions → score=100."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai": {"queries_sent": 10, "queries_with_mentions": 10},
                }
            }
        }
        results = await scorer.score_page(page_data)
        assert results[0].score == 100

    @pytest.mark.asyncio
    async def test_single_engine_zero_mentions(self):
        """1 engine, 0/10 mentions → score=0."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai": {"queries_sent": 10, "queries_with_mentions": 0},
                }
            }
        }
        results = await scorer.score_page(page_data)
        assert results[0].score == 0

    @pytest.mark.asyncio
    async def test_single_engine_half_mentions(self):
        """1 engine, 5/10 mentions → score=50."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai": {"queries_sent": 10, "queries_with_mentions": 5},
                }
            }
        }
        results = await scorer.score_page(page_data)
        assert results[0].score == 50

    @pytest.mark.asyncio
    async def test_multi_engine_average(self):
        """Three engines averaged.

        openai:     8/10 = 80%
        anthropic:  4/10 = 40%
        perplexity: 6/10 = 60%
        avg = (80 + 40 + 60) / 3 = 60 → score=60
        """
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai":     {"queries_sent": 10, "queries_with_mentions": 8},
                    "anthropic":  {"queries_sent": 10, "queries_with_mentions": 4},
                    "perplexity": {"queries_sent": 10, "queries_with_mentions": 6},
                }
            }
        }
        results = await scorer.score_page(page_data)
        assert results[0].score == 60

    @pytest.mark.asyncio
    async def test_two_engines_unequal_queries(self):
        """Different queries_sent counts per engine.

        openai:    7/10 = 70%
        anthropic: 3/5  = 60%
        avg = (70 + 60) / 2 = 65 → score=65
        """
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai":    {"queries_sent": 10, "queries_with_mentions": 7},
                    "anthropic": {"queries_sent": 5,  "queries_with_mentions": 3},
                }
            }
        }
        results = await scorer.score_page(page_data)
        assert results[0].score == 65

    @pytest.mark.asyncio
    async def test_score_is_always_0_to_100(self):
        """Score must always be clamped to [0, 100]."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        for queries_with_mentions in [0, 3, 5, 7, 10]:
            page_data = {
                "visibility_score_data": {
                    "per_engine_scores": {
                        "openai": {"queries_sent": 10, "queries_with_mentions": queries_with_mentions},
                    }
                }
            }
            results = await scorer.score_page(page_data)
            assert 0 <= results[0].score <= 100, (
                f"Score {results[0].score} out of range for {queries_with_mentions}/10"
            )


# ===========================================================================
# Test: score_page() — edge cases and resilience
# ===========================================================================

class TestSomScorerEdgeCases:
    """SomScorer must handle malformed input gracefully."""

    @pytest.mark.asyncio
    async def test_skips_engine_with_old_flat_format(self):
        """Engines with old flat {score: 75} format (no queries_with_mentions) are skipped.

        Only openai is valid → score=70.
        """
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai":        {"queries_sent": 10, "queries_with_mentions": 7},
                    "legacy_engine": {"score": 75},  # old flat format — no queries_with_mentions
                }
            }
        }
        results = await scorer.score_page(page_data)
        assert results[0].score == 70  # Only openai counted

    @pytest.mark.asyncio
    async def test_zero_queries_sent_no_division_by_zero(self):
        """queries_sent=0 must not raise ZeroDivisionError."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai": {"queries_sent": 0, "queries_with_mentions": 0},
                }
            }
        }
        # Must not raise
        results = await scorer.score_page(page_data)
        assert 0 <= results[0].score <= 100

    @pytest.mark.asyncio
    async def test_missing_visibility_score_data_key(self):
        """page_data without visibility_score_data key → score=0, no crash."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        results = await scorer.score_page({"url": "https://example.com"})
        assert results[0].score == 0

    @pytest.mark.asyncio
    async def test_non_dict_engine_entry_is_skipped(self):
        """Engines whose value is not a dict are skipped gracefully."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai": {"queries_sent": 10, "queries_with_mentions": 8},
                    "broken": None,
                    "also_broken": "invalid",
                }
            }
        }
        results = await scorer.score_page(page_data)
        assert results[0].score == 80  # Only openai counted


# ===========================================================================
# Test: score_page() — evidence dict
# ===========================================================================

class TestSomScorerEvidence:
    """Evidence dict on COMP1 must expose per-engine SoM for UI display."""

    @pytest.mark.asyncio
    async def test_evidence_is_not_none(self):
        """Evidence must not be None when visibility data is present."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai": {"queries_sent": 10, "queries_with_mentions": 7},
                }
            }
        }
        results = await scorer.score_page(page_data)
        assert results[0].evidence is not None

    @pytest.mark.asyncio
    async def test_evidence_contains_per_engine_som_key(self):
        """Evidence must contain 'per_engine_som' key."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai": {"queries_sent": 10, "queries_with_mentions": 7},
                }
            }
        }
        results = await scorer.score_page(page_data)
        assert "per_engine_som" in results[0].evidence


# ===========================================================================
# Test: compute_category_score() integration
# ===========================================================================

class TestSomScorerCategoryScoreIntegration:
    """compute_category_score(results) from BaseScorer works with COMP1."""

    @pytest.mark.asyncio
    async def test_category_score_matches_criterion_score(self):
        """With a single criterion, category score = that criterion's score."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        page_data = {
            "visibility_score_data": {
                "per_engine_scores": {
                    "openai": {"queries_sent": 10, "queries_with_mentions": 7},
                }
            }
        }
        results = await scorer.score_page(page_data)
        category_score = scorer.compute_category_score(results)
        assert category_score == 70.0

    @pytest.mark.asyncio
    async def test_category_score_zero_when_no_visibility(self):
        """Category score=0 when no visibility data."""
        from app.services.scoring.som_scorer import SomScorer
        scorer = SomScorer()
        results = await scorer.score_page({})
        category_score = scorer.compute_category_score(results)
        assert category_score == 0.0
