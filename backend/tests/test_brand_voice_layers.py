"""Tests for Brand Signature Engine — Layer 2 (Statistical) and Layer 4 (LLM).

Based on spec: docs/RedwaneNextDirection.md — Axe 4.

These tests are FAILING by design until the following are implemented in
    backend/app/services/brand_voice.py:

Layer 2 — Statistical Fingerprint:
  - BrandVoiceService._check_statistical_layer(text, config) → float [0, 1]
  - process_knowledge_base() stores statistical_baseline JSONB on BrandVoiceConfig
  - Baseline metrics: avg_sentence_length, flesch_score, syllable_ratio, type_token_ratio

Layer 4 — LLM Deep Analysis (conditional):
  - BrandVoiceService._check_llm_layer(text, config, layer3_score) → dict
  - Only triggered when 0.35 <= layer3_score <= 0.65 (ambiguous zone)
  - Returns: {score: float, explanation: str, matches: list, mismatches: list}
  - Requires OPENAI_API_KEY; graceful fallback when key is absent

Scoring formula update (check_voice):
  - Fast mode (layers 1-3): rules×0.2 + stats×0.3 + semantic×0.5
  - Deep mode (all 4, ambiguous zone): rules×0.15 + stats×0.20 + semantic×0.35 + llm×0.30
  - Current formula (rules×0.3 + vector×0.7) must be replaced.

DB model change required:
  - BrandVoiceConfig needs statistical_baseline JSONB column
  - Migration needed: backend/alembic/versions/
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(with_baseline=False, baseline=None):
    """Create a mock BrandVoiceConfig with optional statistical_baseline."""
    config = MagicMock()
    config.id = uuid4()
    config.description = "Professional B2B SaaS brand — concise, technical, trustworthy"
    config.statistical_baseline = baseline if with_baseline else None
    return config


def _make_service():
    """Create a BrandVoiceService with a mocked DB session."""
    from app.services.brand_voice import BrandVoiceService
    mock_db = MagicMock()
    return BrandVoiceService(db=mock_db)


# Sample brand corpus text (formal, technical)
BRAND_CORPUS = (
    "Our platform delivers enterprise-grade analytics. "
    "We optimize for performance and reliability. "
    "Technical excellence drives every product decision. "
    "Integration takes minutes, not weeks."
)

# Very different text (informal, casual)
CASUAL_TEXT = (
    "omg this is like super duper amazing!!! so cool right?? "
    "lol definitely gonna try this out today. wow much fun!"
)

# Similar text (same style as corpus)
SIMILAR_TEXT = (
    "The solution provides high-performance data processing. "
    "Security and reliability are foundational requirements. "
    "Integration with existing infrastructure is seamless."
)


# ===========================================================================
# Layer 2: _check_statistical_layer — existence and interface
# ===========================================================================

class TestStatisticalLayerExists:
    """_check_statistical_layer must exist on BrandVoiceService."""

    def test_method_exists_on_service(self):
        """BrandVoiceService has _check_statistical_layer method."""
        service = _make_service()
        assert callable(getattr(service, "_check_statistical_layer", None))

    def test_method_returns_float(self):
        """_check_statistical_layer returns a float between 0 and 1."""
        service = _make_service()
        config = _make_config(with_baseline=False)
        result = service._check_statistical_layer(BRAND_CORPUS, config)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0


# ===========================================================================
# Layer 2: _check_statistical_layer — no baseline
# ===========================================================================

class TestStatisticalLayerNoBaseline:
    """When no baseline is stored, return 0.5 (neutral / uncertain)."""

    def test_no_baseline_returns_0_5(self):
        """Without a baseline, result is 0.5 (uncertain / middle ground)."""
        service = _make_service()
        config = _make_config(with_baseline=False)
        result = service._check_statistical_layer(BRAND_CORPUS, config)
        assert result == pytest.approx(0.5), (
            f"Expected 0.5 (no baseline), got {result}"
        )

    def test_none_baseline_attribute_returns_0_5(self):
        """statistical_baseline=None → 0.5."""
        service = _make_service()
        config = _make_config(with_baseline=True, baseline=None)
        result = service._check_statistical_layer(BRAND_CORPUS, config)
        assert result == pytest.approx(0.5)

    def test_empty_dict_baseline_returns_0_5(self):
        """statistical_baseline={} → 0.5 (empty baseline treated as absent)."""
        service = _make_service()
        config = _make_config(with_baseline=True, baseline={})
        result = service._check_statistical_layer(BRAND_CORPUS, config)
        assert result == pytest.approx(0.5)


# ===========================================================================
# Layer 2: _check_statistical_layer — with baseline
# ===========================================================================

class TestStatisticalLayerWithBaseline:
    """When a baseline exists, compare text metrics and return similarity score."""

    def _make_baseline_from(self, text: str) -> dict:
        """Compute textstat metrics from text to use as baseline."""
        import textstat
        return {
            "avg_sentence_length": textstat.avg_sentence_length(text),
            "flesch_score": textstat.flesch_reading_ease(text),
            "syllable_ratio": textstat.syllable_count(text) / max(len(text.split()), 1),
            "type_token_ratio": len(set(text.lower().split())) / max(len(text.split()), 1),
        }

    def test_identical_text_returns_near_1(self):
        """Text identical to the baseline returns score close to 1.0."""
        service = _make_service()
        baseline = self._make_baseline_from(BRAND_CORPUS)
        config = _make_config(with_baseline=True, baseline=baseline)
        result = service._check_statistical_layer(BRAND_CORPUS, config)
        assert result >= 0.9, f"Expected near 1.0 for identical text, got {result}"

    def test_very_similar_text_returns_high_score(self):
        """Text with similar style returns score > 0.7."""
        service = _make_service()
        baseline = self._make_baseline_from(BRAND_CORPUS)
        config = _make_config(with_baseline=True, baseline=baseline)
        result = service._check_statistical_layer(SIMILAR_TEXT, config)
        assert result >= 0.7, f"Expected high score for similar text, got {result}"

    def test_very_different_text_returns_low_score(self):
        """Informal text vs formal baseline returns score < 0.4."""
        service = _make_service()
        baseline = self._make_baseline_from(BRAND_CORPUS)
        config = _make_config(with_baseline=True, baseline=baseline)
        result = service._check_statistical_layer(CASUAL_TEXT, config)
        assert result < 0.4, f"Expected low score for different text style, got {result}"

    def test_result_is_always_0_to_1(self):
        """Score is always clamped to [0.0, 1.0]."""
        service = _make_service()
        baseline = self._make_baseline_from(BRAND_CORPUS)
        config = _make_config(with_baseline=True, baseline=baseline)
        for text in [BRAND_CORPUS, SIMILAR_TEXT, CASUAL_TEXT, "", "a"]:
            result = service._check_statistical_layer(text, config)
            assert 0.0 <= result <= 1.0, f"Score {result} out of range for text: {text!r}"


# ===========================================================================
# Layer 2: process_knowledge_base stores statistical_baseline
# ===========================================================================

class TestProcessKnowledgeBaseStoresBaseline:
    """process_knowledge_base must compute and persist statistical_baseline."""

    def test_statistical_baseline_key_present_in_config_after_processing(self):
        """After process_knowledge_base(), config.statistical_baseline is a non-empty dict."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)

        # Mock the embedding call to avoid real API calls
        service._generate_embedding = AsyncMock(return_value=[0.0] * 1536)

        config = MagicMock()
        config.id = uuid4()
        config.statistical_baseline = None
        mock_db.query.return_value.filter.return_value.first.return_value = config

        import asyncio
        asyncio.run(service.process_knowledge_base(config.id, BRAND_CORPUS))

        # statistical_baseline must have been set on config
        assert config.statistical_baseline is not None
        assert isinstance(config.statistical_baseline, dict)
        assert len(config.statistical_baseline) > 0

    def test_statistical_baseline_contains_expected_metrics(self):
        """statistical_baseline contains avg_sentence_length, flesch_score, syllable_ratio, type_token_ratio."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)
        service._generate_embedding = AsyncMock(return_value=[0.0] * 1536)

        config = MagicMock()
        config.id = uuid4()
        config.statistical_baseline = None
        mock_db.query.return_value.filter.return_value.first.return_value = config

        import asyncio
        asyncio.run(service.process_knowledge_base(config.id, BRAND_CORPUS))

        expected_keys = {"avg_sentence_length", "flesch_score", "syllable_ratio", "type_token_ratio"}
        actual_keys = set(config.statistical_baseline.keys())
        missing = expected_keys - actual_keys
        assert not missing, f"Missing baseline keys: {missing}"


# ===========================================================================
# Layer 2: check_voice uses new 3-layer formula
# ===========================================================================

class TestCheckVoiceFormula:
    """check_voice() must use rules×0.2 + stats×0.3 + semantic×0.5 (fast mode)."""

    @pytest.mark.asyncio
    async def test_check_voice_result_has_stats_score(self):
        """check_voice() result must include a 'stats_score' or 'layer2_score' key."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)

        # Mock all sub-checks
        service._calculate_vector_similarity = AsyncMock(return_value=80)
        service._check_rules = MagicMock(return_value={"score": 90, "violations": [], "suggestions": []})
        service._check_statistical_layer = MagicMock(return_value=0.75)

        config_id = uuid4()
        result = await service.check_voice(SIMILAR_TEXT, config_id)

        assert "stats_score" in result or "layer2_score" in result, (
            f"check_voice result missing layer 2 score key. Got keys: {list(result.keys())}"
        )

    @pytest.mark.asyncio
    async def test_check_voice_formula_fast_mode(self):
        """Fast mode formula: rules×0.2 + stats×0.3 + semantic×0.5.

        Given:
          rules_score  = 100 (normalized to 1.0)
          stats_score  = 0.6
          semantic/vector score = 80 (normalized to 0.8)

        fast_score = 1.0×0.2 + 0.6×0.3 + 0.8×0.5
                   = 0.20 + 0.18 + 0.40
                   = 0.78 → hybrid_score ≈ 78
        """
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)

        service._calculate_vector_similarity = AsyncMock(return_value=80)
        service._check_rules = MagicMock(return_value={"score": 100, "violations": [], "suggestions": []})
        service._check_statistical_layer = MagicMock(return_value=0.6)

        config_id = uuid4()
        result = await service.check_voice(SIMILAR_TEXT, config_id)

        expected = round(1.0 * 0.2 + 0.6 * 0.3 + 0.8 * 0.5, 2)  # 0.78
        actual_score = result["hybrid_score"] / 100
        assert abs(actual_score - expected) < 0.02, (
            f"Expected fast mode score ~{expected:.2f}, got {actual_score:.2f}"
        )


# ===========================================================================
# Layer 4: _check_llm_layer — existence and interface
# ===========================================================================

class TestLLMLayerExists:
    """_check_llm_layer must exist on BrandVoiceService."""

    def test_method_exists_on_service(self):
        """BrandVoiceService has _check_llm_layer method."""
        service = _make_service()
        assert callable(getattr(service, "_check_llm_layer", None))


# ===========================================================================
# Layer 4: _check_llm_layer — conditional trigger
# ===========================================================================

class TestLLMLayerTrigger:
    """_check_llm_layer is only called when semantic score is in the ambiguous zone [0.35, 0.65]."""

    @pytest.mark.asyncio
    async def test_llm_not_called_when_score_clearly_low(self):
        """layer3_score=0.10 (clearly bad) → _check_llm_layer not called."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)
        service._check_llm_layer = AsyncMock()
        service._calculate_vector_similarity = AsyncMock(return_value=10)  # 0.10 normalized
        service._check_rules = MagicMock(return_value={"score": 50, "violations": [], "suggestions": []})
        service._check_statistical_layer = MagicMock(return_value=0.3)

        await service.check_voice(CASUAL_TEXT, uuid4())
        service._check_llm_layer.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_not_called_when_score_clearly_high(self):
        """layer3_score=0.90 (clearly good) → _check_llm_layer not called."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)
        service._check_llm_layer = AsyncMock()
        service._calculate_vector_similarity = AsyncMock(return_value=90)  # 0.90 normalized
        service._check_rules = MagicMock(return_value={"score": 90, "violations": [], "suggestions": []})
        service._check_statistical_layer = MagicMock(return_value=0.85)

        await service.check_voice(SIMILAR_TEXT, uuid4())
        service._check_llm_layer.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_called_when_score_is_ambiguous(self):
        """layer3_score=0.50 (ambiguous) → _check_llm_layer is called."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)
        service._check_llm_layer = AsyncMock(return_value={
            "score": 0.50, "explanation": "borderline", "matches": [], "mismatches": []
        })
        service._calculate_vector_similarity = AsyncMock(return_value=50)  # 0.50 — ambiguous
        service._check_rules = MagicMock(return_value={"score": 60, "violations": [], "suggestions": []})
        service._check_statistical_layer = MagicMock(return_value=0.5)

        await service.check_voice(SIMILAR_TEXT, uuid4())
        service._check_llm_layer.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_called_at_lower_ambiguous_boundary(self):
        """layer3_score=0.35 (lower boundary of ambiguous zone) → LLM called."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)
        service._check_llm_layer = AsyncMock(return_value={
            "score": 0.35, "explanation": "borderline low", "matches": [], "mismatches": []
        })
        service._calculate_vector_similarity = AsyncMock(return_value=35)
        service._check_rules = MagicMock(return_value={"score": 50, "violations": [], "suggestions": []})
        service._check_statistical_layer = MagicMock(return_value=0.4)

        await service.check_voice(SIMILAR_TEXT, uuid4())
        service._check_llm_layer.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_called_at_upper_ambiguous_boundary(self):
        """layer3_score=0.65 (upper boundary of ambiguous zone) → LLM called."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)
        service._check_llm_layer = AsyncMock(return_value={
            "score": 0.65, "explanation": "borderline high", "matches": [], "mismatches": []
        })
        service._calculate_vector_similarity = AsyncMock(return_value=65)
        service._check_rules = MagicMock(return_value={"score": 70, "violations": [], "suggestions": []})
        service._check_statistical_layer = MagicMock(return_value=0.6)

        await service.check_voice(SIMILAR_TEXT, uuid4())
        service._check_llm_layer.assert_called_once()


# ===========================================================================
# Layer 4: _check_llm_layer — return structure
# ===========================================================================

class TestLLMLayerReturnStructure:
    """_check_llm_layer must return a structured dict with the correct keys."""

    @pytest.mark.asyncio
    async def test_llm_layer_returns_dict(self):
        """_check_llm_layer returns a dict (not None, not a number)."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)

        # Mock the actual LLM call inside _check_llm_layer
        with patch("litellm.completion") as mock_llm:
            mock_llm.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content='{"score": 72, "explanation": "Good match", "matches": ["concise"], "mismatches": []}'))]
            )
            config = _make_config(with_baseline=True, baseline={"flesch_score": 55.0})
            # Mock pgvector similarity query
            service._get_similar_chunks = AsyncMock(return_value=["Brand example 1", "Brand example 2"])
            result = await service._check_llm_layer(SIMILAR_TEXT, config, layer3_score=0.50)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_llm_layer_result_has_score_key(self):
        """_check_llm_layer result dict must have 'score' key."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)

        with patch("litellm.completion") as mock_llm:
            mock_llm.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content='{"score": 72, "explanation": "Good match", "matches": ["concise"], "mismatches": []}'))]
            )
            service._get_similar_chunks = AsyncMock(return_value=["Brand example 1"])
            config = _make_config(with_baseline=True, baseline={"flesch_score": 55.0})
            result = await service._check_llm_layer(SIMILAR_TEXT, config, layer3_score=0.50)

        assert "score" in result
        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 1.0

    @pytest.mark.asyncio
    async def test_llm_layer_result_has_explanation_key(self):
        """_check_llm_layer result dict must have 'explanation' key (str)."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)

        with patch("litellm.completion") as mock_llm:
            mock_llm.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content='{"score": 72, "explanation": "Good match", "matches": ["concise"], "mismatches": []}'))]
            )
            service._get_similar_chunks = AsyncMock(return_value=["Brand example 1"])
            config = _make_config(with_baseline=True, baseline={"flesch_score": 55.0})
            result = await service._check_llm_layer(SIMILAR_TEXT, config, layer3_score=0.50)

        assert "explanation" in result
        assert isinstance(result["explanation"], str)

    @pytest.mark.asyncio
    async def test_llm_layer_result_has_matches_and_mismatches_keys(self):
        """_check_llm_layer result dict must have 'matches' and 'mismatches' lists."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)

        with patch("litellm.completion") as mock_llm:
            mock_llm.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content='{"score": 72, "explanation": "OK", "matches": ["concise"], "mismatches": ["too formal"]}'))]
            )
            service._get_similar_chunks = AsyncMock(return_value=["Brand example 1"])
            config = _make_config(with_baseline=True, baseline={"flesch_score": 55.0})
            result = await service._check_llm_layer(SIMILAR_TEXT, config, layer3_score=0.50)

        assert "matches" in result and isinstance(result["matches"], list)
        assert "mismatches" in result and isinstance(result["mismatches"], list)


# ===========================================================================
# Layer 4: _check_llm_layer — no API key fallback
# ===========================================================================

class TestLLMLayerNoApiKey:
    """When OPENAI_API_KEY is not set, _check_llm_layer returns graceful fallback."""

    @pytest.mark.asyncio
    async def test_no_api_key_returns_fallback_without_crash(self):
        """With OPENAI_API_KEY unset, _check_llm_layer doesn't raise and returns layer3_score."""
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            config = _make_config()
            layer3_score = 0.50
            result = await service._check_llm_layer(SIMILAR_TEXT, config, layer3_score=layer3_score)

        # Should return the layer3_score as fallback (not crash)
        assert result["score"] == pytest.approx(layer3_score)
        assert result["explanation"] is None


# ===========================================================================
# Layer 4: deep mode formula
# ===========================================================================

class TestDeepModeFormula:
    """When LLM is triggered (ambiguous zone), deep mode formula applies."""

    @pytest.mark.asyncio
    async def test_deep_mode_uses_four_layer_formula(self):
        """Deep mode: rules×0.15 + stats×0.20 + semantic×0.35 + llm×0.30.

        Given:
          rules_score  = 0.90
          stats_score  = 0.75
          semantic     = 0.50  (triggers LLM)
          llm_score    = 0.60

        deep_score = 0.90×0.15 + 0.75×0.20 + 0.50×0.35 + 0.60×0.30
                   = 0.135 + 0.150 + 0.175 + 0.180
                   = 0.640 → hybrid_score ≈ 64
        """
        from app.services.brand_voice import BrandVoiceService

        mock_db = MagicMock()
        service = BrandVoiceService(db=mock_db)

        service._calculate_vector_similarity = AsyncMock(return_value=50)  # semantic = 0.50 → ambiguous
        service._check_rules = MagicMock(return_value={"score": 90, "violations": [], "suggestions": []})
        service._check_statistical_layer = MagicMock(return_value=0.75)
        service._check_llm_layer = AsyncMock(return_value={
            "score": 0.60, "explanation": "Good alignment overall", "matches": ["concise"], "mismatches": []
        })

        result = await service.check_voice(SIMILAR_TEXT, uuid4())

        expected_deep = round(0.90 * 0.15 + 0.75 * 0.20 + 0.50 * 0.35 + 0.60 * 0.30, 2)  # 0.64
        actual = result["hybrid_score"] / 100
        assert abs(actual - expected_deep) < 0.02, (
            f"Deep mode: expected ~{expected_deep:.2f}, got {actual:.2f}"
        )
