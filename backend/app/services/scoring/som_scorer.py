"""SomScorer -- converts VisibilityScore per_engine_scores into a COMP1 criterion.

Bridges Stage 4 (visibility) and Stage 5 (optimization scoring) by expressing
Share of Model (SoM) as a scored criterion within the BaseScorer framework.

SoM ratio per engine = queries_with_mentions / queries_sent
Overall SoM score = int(avg(per-engine SoM ratios) * 100)

Registered under category "ai_visibility" (weight 0.15 in CATEGORY_WEIGHTS).
Does NOT affect compute_optimization_score() (pure technical readiness),
but DOES appear in per-page overall_page_score and CriterionResult table.
"""

from app.services.scoring.base_scorer import BaseScorer, ScoringCriterionResult


class SomScorer(BaseScorer):
    """Share of Model scorer -- single criterion COMP1."""

    async def score_page(self, page_data: dict) -> list[ScoringCriterionResult]:
        """Score a page based on Share of Model visibility data.

        Reads per-engine mention ratios from page_data and computes
        the average Share of Model across all valid engines.

        Args:
            page_data: Dict containing visibility_score_data with per_engine_scores.

        Returns:
            Single-element list with COMP1 ScoringCriterionResult.
        """
        vis_data = page_data.get("visibility_score_data", {}) or {}
        per_engine = vis_data.get("per_engine_scores", {}) or {}

        som_ratios: dict[str, float] = {}
        for engine, data in per_engine.items():
            if not isinstance(data, dict):
                continue
            if "queries_with_mentions" not in data:
                continue
            queries_sent = data.get("queries_sent", 0)
            if queries_sent == 0:
                continue
            ratio = data["queries_with_mentions"] / queries_sent
            som_ratios[engine] = ratio

        if som_ratios:
            average = sum(som_ratios.values()) / len(som_ratios)
            score = round(average * 100)
        else:
            average = 0.0
            score = 0

        pct = round(average * 100)
        human_summary = (
            f"Brand appears in {pct}% of AI engine responses on average"
            if som_ratios
            else "No AI engine visibility data available (0%)"
        )

        evidence = {
            "per_engine_som": {
                engine: round(ratio * 100, 1)
                for engine, ratio in som_ratios.items()
            },
            "engines_evaluated": len(som_ratios),
            "engines_skipped": len(per_engine) - len(som_ratios),
        }

        return [
            ScoringCriterionResult(
                criterion_id="COMP1",
                criterion_name="Share of Model - AI Engine Visibility",
                score=score,
                human_summary=human_summary,
                technical_detail=f"Average SoM across {len(som_ratios)} engine(s): {pct}%",
                evidence=evidence,
            )
        ]
