"""Tests for enhanced visibility scoring pipeline (Phase 3).

Covers:
- Confidence level thresholds (unit tests)
- Enriched per-engine breakdown with active and skipped engines (integration)
- Backward compatibility for old/new JSONB formats via _build_per_engine_breakdown
- Weighted-by-queries-sent overall scoring
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.models.audit import Audit, AuditStatus
from app.models.audit_query import AuditQuery
from app.models.brand_mention import BrandMention
from app.models.engine_response import EngineResponse
from app.services.scoring_service import ScoringService


# ---------------------------------------------------------------------------
# 1. Confidence level computation (unit tests)
# ---------------------------------------------------------------------------


def test_confidence_level_high():
    assert ScoringService._compute_confidence_level(10) == "high"
    assert ScoringService._compute_confidence_level(15) == "high"
    assert ScoringService._compute_confidence_level(100) == "high"


def test_confidence_level_medium():
    assert ScoringService._compute_confidence_level(5) == "medium"
    assert ScoringService._compute_confidence_level(9) == "medium"


def test_confidence_level_low():
    assert ScoringService._compute_confidence_level(1) == "low"
    assert ScoringService._compute_confidence_level(4) == "low"


def test_confidence_level_not_measured():
    assert ScoringService._compute_confidence_level(0) == "not_measured"


# ---------------------------------------------------------------------------
# 2. Enhanced compute_audit_score (integration test with DB session)
# ---------------------------------------------------------------------------


def test_enriched_per_engine_breakdown(db, test_user):
    """ScoringService produces enriched per_engine_scores with statistical breakdown."""
    # Create an audit
    audit_id = uuid.uuid4()
    audit = Audit(
        id=audit_id,
        user_id=test_user.id,
        url="https://test-enriched.com",
        domain="test-enriched.com",
        status=AuditStatus.SCORING.value,
    )
    db.add(audit)
    db.flush()

    # Create 10 queries
    queries = []
    for i in range(10):
        q = AuditQuery(
            id=uuid.uuid4(),
            audit_id=audit_id,
            query_text=f"test query {i}",
            category="general",
            sort_order=i,
        )
        db.add(q)
        queries.append(q)
    db.flush()

    # Create engine responses: openai responds to all 10, anthropic responds to all 10
    openai_responses = []
    anthropic_responses = []
    for q in queries:
        openai_resp = EngineResponse(
            id=uuid.uuid4(),
            audit_query_id=q.id,
            engine="openai",
            model_version="gpt-4o",
            response_text="Response mentioning test brand",
            prompt_tokens=100,
            completion_tokens=200,
            cost_usd=0.01,
            cached=False,
        )
        db.add(openai_resp)
        openai_responses.append(openai_resp)

        anthropic_resp = EngineResponse(
            id=uuid.uuid4(),
            audit_query_id=q.id,
            engine="anthropic",
            model_version="claude-3",
            response_text="Response about something",
            prompt_tokens=100,
            completion_tokens=200,
            cost_usd=0.01,
            cached=False,
        )
        db.add(anthropic_resp)
        anthropic_responses.append(anthropic_resp)
    db.flush()

    # Create mentions: 7/10 openai responses have mentions, 4/10 anthropic
    for resp in openai_responses[:7]:
        mention = BrandMention(
            id=uuid.uuid4(),
            engine_response_id=resp.id,
            matched_text="test brand",
            match_type="exact",
            confidence=90,
            char_offset=10,
            context_quote="Response mentioning test brand in context",
        )
        db.add(mention)

    for resp in anthropic_responses[:4]:
        mention = BrandMention(
            id=uuid.uuid4(),
            engine_response_id=resp.id,
            matched_text="test brand",
            match_type="fuzzy",
            confidence=75,
            char_offset=50,
            context_quote="A different context mentioning test brand",
        )
        db.add(mention)
    db.flush()

    # Mock ENGINE_CONFIG to control which engines are "all engines"
    mock_engine_config = {
        "openai": {"model_setting": "DISPATCH_MODEL_OPENAI", "provider": "openai", "api_key_setting": "OPENAI_API_KEY"},
        "anthropic": {"model_setting": "DISPATCH_MODEL_ANTHROPIC", "provider": "anthropic", "api_key_setting": "ANTHROPIC_API_KEY"},
        "perplexity": {"model_setting": "DISPATCH_MODEL_PERPLEXITY", "provider": "perplexity", "api_key_setting": "PERPLEXITYAI_API_KEY"},
        "gemini": {"model_setting": "DISPATCH_MODEL_GEMINI", "provider": "gemini", "api_key_setting": "GEMINI_API_KEY"},
    }

    with patch("app.services.scoring_service.ENGINE_CONFIG", mock_engine_config):
        service = ScoringService(db)
        result = service.compute_audit_score(str(audit_id), 10)

    # Verify per_engine_scores is enriched (dict of dicts, not dict of ints)
    assert isinstance(result.per_engine_scores, dict)
    assert "openai" in result.per_engine_scores
    assert "anthropic" in result.per_engine_scores
    assert isinstance(result.per_engine_scores["openai"], dict)

    # OpenAI breakdown
    openai_data = result.per_engine_scores["openai"]
    assert openai_data["queries_sent"] == 10
    assert openai_data["queries_with_mentions"] == 7
    assert openai_data["mention_rate"] == 70.0
    assert openai_data["skipped"] is False
    assert openai_data["confidence_level"] == "high"  # 10 queries

    # Anthropic breakdown
    anthropic_data = result.per_engine_scores["anthropic"]
    assert anthropic_data["queries_sent"] == 10
    assert anthropic_data["queries_with_mentions"] == 4
    assert anthropic_data["mention_rate"] == 40.0
    assert anthropic_data["skipped"] is False

    # Skipped engines present
    assert "perplexity" in result.per_engine_scores
    assert result.per_engine_scores["perplexity"]["skipped"] is True
    assert result.per_engine_scores["perplexity"]["skip_reason"] == "No API key configured"
    assert "gemini" in result.per_engine_scores
    assert result.per_engine_scores["gemini"]["skipped"] is True

    # Model-level fields
    assert result.confidence_level == "high"  # 10 queries per engine
    assert result.engines_queried == 2
    assert result.engines_skipped == 2
    assert result.algorithm_version == "v2"

    # Overall score is weighted, not equal-weight
    assert isinstance(result.overall_score, int)
    assert 0 <= result.overall_score <= 100


# ---------------------------------------------------------------------------
# 3. Backward compatibility tests for API schema
# ---------------------------------------------------------------------------


def test_per_engine_breakdown_from_old_format():
    """Old audits have per_engine_scores like {"openai": 75}."""
    from app.api.audit import _build_per_engine_breakdown

    old_data = {"openai": 75, "anthropic": 60}
    breakdown = _build_per_engine_breakdown(old_data)
    assert len(breakdown) == 2
    chatgpt = next(e for e in breakdown if e["engine_key"] == "openai")
    assert chatgpt["display_name"] == "ChatGPT"
    assert chatgpt["score"] == 75
    assert chatgpt["queries_sent"] == 0  # unknown for old format
    assert chatgpt["skipped"] is False
    assert chatgpt["confidence_level"] == "unknown"


def test_per_engine_breakdown_from_new_format():
    """New audits have per_engine_scores with enriched dicts."""
    from app.api.audit import _build_per_engine_breakdown

    new_data = {
        "openai": {
            "score": 75,
            "queries_sent": 12,
            "queries_with_mentions": 9,
            "mention_rate": 75.0,
            "total_mentions": 14,
            "avg_confidence": 92,
            "confidence_level": "high",
            "skipped": False,
        }
    }
    breakdown = _build_per_engine_breakdown(new_data)
    assert len(breakdown) == 1
    entry = breakdown[0]
    assert entry["display_name"] == "ChatGPT"
    assert entry["queries_sent"] == 12
    assert entry["confidence_level"] == "high"


# ---------------------------------------------------------------------------
# 4. Weighted scoring test
# ---------------------------------------------------------------------------


def test_weighted_scoring_favors_engine_with_more_queries(db, test_user):
    """Engine with more queries should have more influence on overall score.

    If openai has 12 responses (score ~80) and anthropic has 3 (score ~40):
    Weighted: closer to 80 than 40
    Equal-weight: (80+40)/2 = 60
    """
    audit_id = uuid.uuid4()
    audit = Audit(
        id=audit_id,
        user_id=test_user.id,
        url="https://test-weighted.com",
        domain="test-weighted.com",
        status=AuditStatus.SCORING.value,
    )
    db.add(audit)
    db.flush()

    # Create 12 queries
    queries = []
    for i in range(12):
        q = AuditQuery(
            id=uuid.uuid4(),
            audit_id=audit_id,
            query_text=f"weighted query {i}",
            category="general",
            sort_order=i,
        )
        db.add(q)
        queries.append(q)
    db.flush()

    # OpenAI responds to all 12 with many mentions
    openai_responses = []
    for q in queries:
        resp = EngineResponse(
            id=uuid.uuid4(),
            audit_query_id=q.id,
            engine="openai",
            model_version="gpt-4o",
            response_text="Strong mention response",
            prompt_tokens=100,
            completion_tokens=200,
            cost_usd=0.01,
            cached=False,
        )
        db.add(resp)
        openai_responses.append(resp)

    # Anthropic responds to only 3
    anthropic_responses = []
    for q in queries[:3]:
        resp = EngineResponse(
            id=uuid.uuid4(),
            audit_query_id=q.id,
            engine="anthropic",
            model_version="claude-3",
            response_text="Weak mention response",
            prompt_tokens=100,
            completion_tokens=200,
            cost_usd=0.01,
            cached=False,
        )
        db.add(resp)
        anthropic_responses.append(resp)
    db.flush()

    # OpenAI: 10/12 responses have high-confidence mentions (should produce ~high score)
    for resp in openai_responses[:10]:
        db.add(BrandMention(
            id=uuid.uuid4(),
            engine_response_id=resp.id,
            matched_text="brand",
            match_type="exact",
            confidence=95,
            char_offset=5,
            context_quote="Strong brand mention early in response",
        ))

    # Anthropic: 1/3 responses has a low-confidence mention (should produce ~low score)
    db.add(BrandMention(
        id=uuid.uuid4(),
        engine_response_id=anthropic_responses[0].id,
        matched_text="brand",
        match_type="fuzzy",
        confidence=40,
        char_offset=500,
        context_quote="Weak brand mention far into response",
    ))
    db.flush()

    # Only include these 2 engines in ENGINE_CONFIG to avoid skipped entries
    mock_engine_config = {
        "openai": {"model_setting": "M", "provider": "openai", "api_key_setting": "K"},
        "anthropic": {"model_setting": "M", "provider": "anthropic", "api_key_setting": "K"},
    }

    with patch("app.services.scoring_service.ENGINE_CONFIG", mock_engine_config):
        service = ScoringService(db)
        result = service.compute_audit_score(str(audit_id), 12)

    openai_score = result.per_engine_scores["openai"]["score"]
    anthropic_score = result.per_engine_scores["anthropic"]["score"]

    # OpenAI should score much higher than anthropic
    assert openai_score > anthropic_score, (
        f"OpenAI ({openai_score}) should score higher than Anthropic ({anthropic_score})"
    )

    # Weighted score should be closer to the high-scoring engine with more queries
    # Equal-weight midpoint
    equal_weight_avg = (openai_score + anthropic_score) / 2

    # Weighted should be above equal-weight midpoint (pulled toward openai)
    assert result.overall_score > equal_weight_avg, (
        f"Weighted score ({result.overall_score}) should be above equal-weight "
        f"average ({equal_weight_avg}) because OpenAI has 4x more queries"
    )
