"""Tests for the v2 audit schema — dual scores, Share of Model, and score delta.

Based on spec: docs/RedwaneNextDirection.md — Axe 1, Axe 2, Axe 3.

These tests are FAILING by design until the following are implemented:

Axe 1 — Score architecture (backend/app/schemas/audit.py):
  - AuditDetailResponse.geo_visibility_score: int
  - AuditDetailResponse.geo_readiness_score: int
  - AuditDetailResponse.geo_combined_score: int   (= (visibility + readiness) // 2)

Axe 2 — Share of Model (backend/app/schemas/audit.py):
  - ShareOfModelEntry schema  {queries_tested, mentions, som_pct}
  - AuditDetailResponse.share_of_model: dict[str, ShareOfModelEntry]

Axe 3 — Score delta (backend/app/schemas/audit.py):
  - ScoreDeltaSchema  {optimization, visibility, prev_audit_id, prev_audit_date}
  - AuditDetailResponse.score_delta: Optional[ScoreDeltaSchema]
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest


# ===========================================================================
# Axe 1: Schema fields — geo_visibility_score, geo_readiness_score, geo_combined_score
# ===========================================================================

class TestGeoScoreFields:
    """AuditDetailResponse must expose three explicit score fields."""

    def test_geo_visibility_score_field_exists(self):
        """AuditDetailResponse has geo_visibility_score field."""
        from app.schemas.audit import AuditDetailResponse
        assert "geo_visibility_score" in AuditDetailResponse.model_fields

    def test_geo_readiness_score_field_exists(self):
        """AuditDetailResponse has geo_readiness_score field."""
        from app.schemas.audit import AuditDetailResponse
        assert "geo_readiness_score" in AuditDetailResponse.model_fields

    def test_geo_combined_score_field_exists(self):
        """AuditDetailResponse has geo_combined_score field."""
        from app.schemas.audit import AuditDetailResponse
        assert "geo_combined_score" in AuditDetailResponse.model_fields

    def test_geo_scores_default_to_zero(self):
        """All three geo score fields default to 0."""
        from app.schemas.audit import AuditDetailResponse
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://example.com",
            domain="example.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
        )
        assert response.geo_visibility_score == 0
        assert response.geo_readiness_score == 0
        assert response.geo_combined_score == 0

    def test_geo_combined_score_is_average_of_visibility_and_readiness(self):
        """geo_combined_score must equal average(geo_visibility_score, geo_readiness_score).

        This validates the formula: combined = (visibility + readiness) // 2.
        """
        from app.schemas.audit import AuditDetailResponse
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://example.com",
            domain="example.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
            geo_visibility_score=60,
            geo_readiness_score=80,
            geo_combined_score=70,  # (60 + 80) // 2
        )
        expected_combined = (response.geo_visibility_score + response.geo_readiness_score) // 2
        assert response.geo_combined_score == expected_combined

    def test_geo_scores_accept_valid_range(self):
        """geo scores must accept values from 0 to 100."""
        from app.schemas.audit import AuditDetailResponse
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://example.com",
            domain="example.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
            geo_visibility_score=43,
            geo_readiness_score=71,
            geo_combined_score=57,
        )
        assert response.geo_visibility_score == 43
        assert response.geo_readiness_score == 71
        assert response.geo_combined_score == 57


# ===========================================================================
# Axe 2: ShareOfModelEntry schema
# ===========================================================================

class TestShareOfModelEntry:
    """ShareOfModelEntry schema must capture per-engine SoM data."""

    def test_share_of_model_entry_is_importable(self):
        """ShareOfModelEntry must be importable from schemas.audit."""
        from app.schemas.audit import ShareOfModelEntry  # noqa: F401

    def test_share_of_model_entry_has_queries_tested(self):
        """ShareOfModelEntry must have queries_tested: int."""
        from app.schemas.audit import ShareOfModelEntry
        assert "queries_tested" in ShareOfModelEntry.model_fields

    def test_share_of_model_entry_has_mentions(self):
        """ShareOfModelEntry must have mentions: int."""
        from app.schemas.audit import ShareOfModelEntry
        assert "mentions" in ShareOfModelEntry.model_fields

    def test_share_of_model_entry_has_som_pct(self):
        """ShareOfModelEntry must have som_pct: float."""
        from app.schemas.audit import ShareOfModelEntry
        assert "som_pct" in ShareOfModelEntry.model_fields

    def test_share_of_model_entry_instantiation(self):
        """ShareOfModelEntry can be instantiated with valid data."""
        from app.schemas.audit import ShareOfModelEntry
        entry = ShareOfModelEntry(queries_tested=12, mentions=7, som_pct=58.3)
        assert entry.queries_tested == 12
        assert entry.mentions == 7
        assert entry.som_pct == pytest.approx(58.3)

    def test_som_pct_is_mentions_over_queries_tested(self):
        """som_pct should reflect mentions / queries_tested as percentage.

        With 7 mentions and 12 queries: 7/12 * 100 ≈ 58.3%.
        """
        from app.schemas.audit import ShareOfModelEntry
        entry = ShareOfModelEntry(queries_tested=12, mentions=7, som_pct=58.3)
        expected_pct = (entry.mentions / entry.queries_tested) * 100
        assert abs(entry.som_pct - expected_pct) < 0.5  # within 0.5% tolerance


# ===========================================================================
# Axe 2: AuditDetailResponse.share_of_model field
# ===========================================================================

class TestShareOfModelField:
    """AuditDetailResponse.share_of_model must be a per-engine SoM dict."""

    def test_share_of_model_field_exists(self):
        """AuditDetailResponse has share_of_model field."""
        from app.schemas.audit import AuditDetailResponse
        assert "share_of_model" in AuditDetailResponse.model_fields

    def test_share_of_model_defaults_to_empty_dict(self):
        """share_of_model defaults to {}."""
        from app.schemas.audit import AuditDetailResponse
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://example.com",
            domain="example.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
        )
        assert response.share_of_model == {}

    def test_share_of_model_accepts_per_engine_entries(self):
        """share_of_model accepts a dict of engine_key → ShareOfModelEntry."""
        from app.schemas.audit import AuditDetailResponse, ShareOfModelEntry
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://example.com",
            domain="example.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
            share_of_model={
                "openai":     ShareOfModelEntry(queries_tested=12, mentions=7,  som_pct=58.3),
                "anthropic":  ShareOfModelEntry(queries_tested=12, mentions=3,  som_pct=25.0),
                "perplexity": ShareOfModelEntry(queries_tested=12, mentions=10, som_pct=83.3),
                "gemini":     ShareOfModelEntry(queries_tested=12, mentions=5,  som_pct=41.7),
            }
        )
        assert "openai" in response.share_of_model
        assert response.share_of_model["openai"].mentions == 7
        assert response.share_of_model["anthropic"].som_pct == pytest.approx(25.0)
        assert response.share_of_model["perplexity"].queries_tested == 12

    def test_share_of_model_engines_cover_expected_providers(self):
        """Standard engines (openai, anthropic, perplexity, gemini) are all valid keys."""
        from app.schemas.audit import AuditDetailResponse, ShareOfModelEntry
        engines = ["openai", "anthropic", "perplexity", "gemini", "mistral"]
        share_of_model = {
            engine: ShareOfModelEntry(queries_tested=10, mentions=5, som_pct=50.0)
            for engine in engines
        }
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://example.com",
            domain="example.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
            share_of_model=share_of_model,
        )
        for engine in engines:
            assert engine in response.share_of_model


# ===========================================================================
# Axe 3: ScoreDeltaSchema
# ===========================================================================

class TestScoreDeltaSchema:
    """ScoreDeltaSchema captures the difference between current and previous audit."""

    def test_score_delta_schema_is_importable(self):
        """ScoreDeltaSchema must be importable from schemas.audit."""
        from app.schemas.audit import ScoreDeltaSchema  # noqa: F401

    def test_score_delta_schema_has_optimization_field(self):
        """ScoreDeltaSchema must have optimization: int (positive = improved)."""
        from app.schemas.audit import ScoreDeltaSchema
        assert "optimization" in ScoreDeltaSchema.model_fields

    def test_score_delta_schema_has_visibility_field(self):
        """ScoreDeltaSchema must have visibility: int."""
        from app.schemas.audit import ScoreDeltaSchema
        assert "visibility" in ScoreDeltaSchema.model_fields

    def test_score_delta_schema_has_prev_audit_id_field(self):
        """ScoreDeltaSchema must have prev_audit_id: UUID."""
        from app.schemas.audit import ScoreDeltaSchema
        assert "prev_audit_id" in ScoreDeltaSchema.model_fields

    def test_score_delta_schema_has_prev_audit_date_field(self):
        """ScoreDeltaSchema must have prev_audit_date: datetime."""
        from app.schemas.audit import ScoreDeltaSchema
        assert "prev_audit_date" in ScoreDeltaSchema.model_fields

    def test_score_delta_schema_instantiation_improvement(self):
        """ScoreDeltaSchema created with positive deltas (improvement)."""
        from app.schemas.audit import ScoreDeltaSchema
        prev_id = uuid4()
        delta = ScoreDeltaSchema(
            optimization=12,
            visibility=8,
            prev_audit_id=prev_id,
            prev_audit_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        assert delta.optimization == 12
        assert delta.visibility == 8
        assert delta.prev_audit_id == prev_id

    def test_score_delta_schema_instantiation_regression(self):
        """ScoreDeltaSchema created with negative deltas (regression)."""
        from app.schemas.audit import ScoreDeltaSchema
        delta = ScoreDeltaSchema(
            optimization=-5,
            visibility=-3,
            prev_audit_id=uuid4(),
            prev_audit_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        assert delta.optimization == -5
        assert delta.visibility == -3


# ===========================================================================
# Axe 3: AuditDetailResponse.score_delta field
# ===========================================================================

class TestScoreDeltaField:
    """AuditDetailResponse.score_delta is Optional[ScoreDeltaSchema]."""

    def test_score_delta_field_exists(self):
        """AuditDetailResponse has score_delta field."""
        from app.schemas.audit import AuditDetailResponse
        assert "score_delta" in AuditDetailResponse.model_fields

    def test_score_delta_defaults_to_none(self):
        """score_delta defaults to None (no previous audit)."""
        from app.schemas.audit import AuditDetailResponse
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://example.com",
            domain="example.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
        )
        assert response.score_delta is None

    def test_score_delta_accepts_schema_instance(self):
        """score_delta accepts a ScoreDeltaSchema instance."""
        from app.schemas.audit import AuditDetailResponse, ScoreDeltaSchema
        prev_id = uuid4()
        delta = ScoreDeltaSchema(
            optimization=12,
            visibility=8,
            prev_audit_id=prev_id,
            prev_audit_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://example.com",
            domain="example.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
            score_delta=delta,
        )
        assert response.score_delta is not None
        assert response.score_delta.optimization == 12
        assert response.score_delta.prev_audit_id == prev_id

    def test_score_delta_is_none_for_first_audit(self):
        """First audit has no previous → score_delta=None."""
        from app.schemas.audit import AuditDetailResponse
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://example.com",
            domain="example.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
            score_delta=None,
        )
        assert response.score_delta is None


# ===========================================================================
# Integration: all new v2 fields coexist
# ===========================================================================

class TestAuditDetailResponseV2Integration:
    """Verify that all v2 fields can be set together on a single response."""

    def test_all_v2_fields_set_together(self):
        """AuditDetailResponse accepts all v2 fields simultaneously."""
        from app.schemas.audit import AuditDetailResponse, ScoreDeltaSchema, ShareOfModelEntry
        prev_id = uuid4()
        response = AuditDetailResponse(
            id=uuid4(),
            url="https://acme.com",
            domain="acme.com",
            status="completed",
            created_at=datetime.now(timezone.utc),
            # Axe 1
            geo_visibility_score=58,
            geo_readiness_score=71,
            geo_combined_score=64,
            # Axe 2
            share_of_model={
                "openai":     ShareOfModelEntry(queries_tested=12, mentions=7,  som_pct=58.3),
                "anthropic":  ShareOfModelEntry(queries_tested=12, mentions=3,  som_pct=25.0),
                "perplexity": ShareOfModelEntry(queries_tested=12, mentions=10, som_pct=83.3),
                "gemini":     ShareOfModelEntry(queries_tested=12, mentions=5,  som_pct=41.7),
            },
            # Axe 3
            score_delta=ScoreDeltaSchema(
                optimization=12,
                visibility=8,
                prev_audit_id=prev_id,
                prev_audit_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            ),
        )
        # Axe 1
        assert response.geo_visibility_score == 58
        assert response.geo_readiness_score == 71
        assert response.geo_combined_score == 64
        # Axe 2
        assert len(response.share_of_model) == 4
        assert response.share_of_model["perplexity"].som_pct == pytest.approx(83.3)
        # Axe 3
        assert response.score_delta.optimization == 12
        assert response.score_delta.prev_audit_id == prev_id
