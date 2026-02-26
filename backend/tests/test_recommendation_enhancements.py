"""Tests for vertical-aware recommendation filtering and impact delta calculation.

Tests verify:
1. is_recommendation_relevant() correctly filters schema criteria by vertical
2. _compute_impact_delta() produces valid estimates with proper bounds
3. generate_recommendations() integrates vertical filtering end-to-end
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.audit import Audit
from app.models.audit_recommendation import AuditRecommendation
from app.models.criterion_result import CriterionResult
from app.models.page_score import PageScore
from app.models.profile import Profile
from app.services.recommendation_engine import (
    RecommendationEngine,
    is_recommendation_relevant,
)


# ---------------------------------------------------------------------------
# Unit tests for is_recommendation_relevant()
# ---------------------------------------------------------------------------


class TestIsRecommendationRelevant:
    """Unit tests for the vertical-aware relevance filter."""

    def test_sd8_product_excluded_for_saas(self):
        """SD8 (Product/Offer schema) should be excluded for SaaS verticals."""
        assert is_recommendation_relevant("SD8", "saas") is False

    def test_sd10_claimreview_excluded_for_ecommerce(self):
        """SD10 (ClaimReview schema) should be excluded for e-commerce verticals."""
        assert is_recommendation_relevant("SD10", "ecommerce") is False

    def test_sd10_claimreview_excluded_for_saas(self):
        """SD10 (ClaimReview schema) should be excluded for SaaS verticals."""
        assert is_recommendation_relevant("SD10", "saas") is False

    def test_all_relevant_for_generic(self):
        """All criteria should be relevant when vertical is 'generic'."""
        assert is_recommendation_relevant("SD8", "generic") is True
        assert is_recommendation_relevant("SD10", "generic") is True
        assert is_recommendation_relevant("SD3", "generic") is True

    def test_non_sd_criteria_always_relevant(self):
        """Non-SD criteria (CS, C, A, S) should always be relevant regardless of vertical."""
        assert is_recommendation_relevant("CS1", "saas") is True
        assert is_recommendation_relevant("C9", "ecommerce") is True
        assert is_recommendation_relevant("A3", "local_business") is True
        assert is_recommendation_relevant("S8", "media_blog") is True

    def test_sd3_faq_relevant_for_all_verticals(self):
        """SD3 (FAQPage) should be relevant for all verticals -- FAQ is universal."""
        assert is_recommendation_relevant("SD3", "saas") is True
        assert is_recommendation_relevant("SD3", "ecommerce") is True
        assert is_recommendation_relevant("SD3", "local_business") is True
        assert is_recommendation_relevant("SD3", "media_blog") is True

    def test_sentiment_criteria_always_relevant(self):
        """SENTIMENT criteria should always be relevant."""
        assert is_recommendation_relevant("SENTIMENT", "saas") is True
        assert is_recommendation_relevant("SENTIMENT", "ecommerce") is True


# ---------------------------------------------------------------------------
# Unit tests for _compute_impact_delta()
# ---------------------------------------------------------------------------


class TestComputeImpactDelta:
    """Unit tests for impact delta calculation."""

    def setup_method(self):
        """Create engine with mock DB session."""
        self.engine = RecommendationEngine(MagicMock(spec=Session))

    def test_positive_delta_when_below_target(self):
        """Should return positive value when criterion_score < target_score."""
        delta = self.engine._compute_impact_delta(
            criterion_score=20,
            target_score=60,
            category="structured_data",
            total_pages=1,
        )
        assert delta > 0

    def test_zero_delta_when_at_target(self):
        """Should return 0 when criterion_score >= target_score."""
        delta = self.engine._compute_impact_delta(
            criterion_score=60,
            target_score=60,
            category="structured_data",
            total_pages=1,
        )
        assert delta == 0

    def test_zero_delta_when_above_target(self):
        """Should return 0 when criterion_score > target_score."""
        delta = self.engine._compute_impact_delta(
            criterion_score=80,
            target_score=60,
            category="structured_data",
            total_pages=1,
        )
        assert delta == 0

    def test_delta_capped_at_15(self):
        """No single fix should claim more than 15 points improvement."""
        # Very low score vs very high target = max possible delta
        delta = self.engine._compute_impact_delta(
            criterion_score=0,
            target_score=100,
            category="crawlability",
            total_pages=1,
        )
        assert delta <= 15.0

    def test_multi_page_adjustment(self):
        """Multi-page audits (>1 page) should apply 0.8 conservative multiplier."""
        single_delta = self.engine._compute_impact_delta(
            criterion_score=20,
            target_score=60,
            category="structured_data",
            total_pages=1,
        )
        multi_delta = self.engine._compute_impact_delta(
            criterion_score=20,
            target_score=60,
            category="structured_data",
            total_pages=5,
        )
        assert multi_delta == round(single_delta * 0.8, 1)

    def test_delta_is_rounded(self):
        """Delta should be rounded to 1 decimal place."""
        delta = self.engine._compute_impact_delta(
            criterion_score=30,
            target_score=60,
            category="content_structure",
            total_pages=1,
        )
        # Check it's a float with at most 1 decimal
        assert delta == round(delta, 1)

    def test_different_categories_different_weights(self):
        """Crawlability (0.25) should produce higher delta than authority (0.15) for same gap."""
        crawl_delta = self.engine._compute_impact_delta(
            criterion_score=20,
            target_score=60,
            category="crawlability",
            total_pages=1,
        )
        auth_delta = self.engine._compute_impact_delta(
            criterion_score=20,
            target_score=60,
            category="authority",
            total_pages=1,
        )
        assert crawl_delta > auth_delta


# ---------------------------------------------------------------------------
# Integration tests for vertical filtering in generate_recommendations()
# ---------------------------------------------------------------------------


class TestVerticalFilteringIntegration:
    """Integration tests that verify vertical filtering in the full pipeline."""

    def test_saas_vertical_excludes_product_and_claimreview(self, db, test_user):
        """Calling generate_recommendations with vertical='saas' should produce
        no Product/Offer (SD8) or ClaimReview (SD10) recommendations."""
        audit = Audit(
            id=uuid.uuid4(),
            user_id=test_user.id,
            url="https://saas-example.com",
            domain="saas-example.com",
            status="completed",
            vertical="saas",
        )
        db.add(audit)

        page = PageScore(
            id=uuid.uuid4(),
            audit_id=audit.id,
            page_url="https://saas-example.com",
            was_scored=True,
            crawlability_score=50,
            content_structure_score=50,
            structured_data_score=20,
            authority_score=50,
            overall_page_score=40,
        )
        db.add(page)

        # Create criterion results below thresholds for SD8 and SD10
        # These SHOULD be filtered out for SaaS
        sd8 = CriterionResult(
            id=uuid.uuid4(),
            page_score_id=page.id,
            criterion_id="SD8",
            criterion_name="Product/Offer schema",
            category="structured_data",
            score=0,
            checked=True,
            human_summary="No Product schema found",
            technical_detail="Add Product schema",
        )
        sd10 = CriterionResult(
            id=uuid.uuid4(),
            page_score_id=page.id,
            criterion_id="SD10",
            criterion_name="ClaimReview schema",
            category="structured_data",
            score=0,
            checked=True,
            human_summary="No ClaimReview schema found",
            technical_detail="Add ClaimReview schema",
        )
        # SD3 (FAQPage) should NOT be filtered -- it's relevant for all verticals
        sd3 = CriterionResult(
            id=uuid.uuid4(),
            page_score_id=page.id,
            criterion_id="SD3",
            criterion_name="FAQPage schema",
            category="structured_data",
            score=0,
            checked=True,
            human_summary="No FAQPage schema found",
            technical_detail="Add FAQPage schema",
        )
        db.add_all([sd8, sd10, sd3])
        db.flush()

        engine = RecommendationEngine(db)
        recs = engine.generate_recommendations(
            audit_id=str(audit.id),
            user_id=str(test_user.id),
            vertical="saas",
        )

        rec_criterion_ids = {r.criterion_id for r in recs}

        # SD8 (Product) and SD10 (ClaimReview) should be excluded for SaaS
        assert "SD8" not in rec_criterion_ids, "SD8 (Product schema) should be excluded for SaaS"
        assert "SD10" not in rec_criterion_ids, "SD10 (ClaimReview) should be excluded for SaaS"
        # SD3 (FAQPage) should be included
        assert "SD3" in rec_criterion_ids, "SD3 (FAQPage) should be included for SaaS"

    def test_recommendations_have_estimated_score_delta(self, db, test_user):
        """All generated recommendations should have estimated_score_delta populated."""
        audit = Audit(
            id=uuid.uuid4(),
            user_id=test_user.id,
            url="https://test-delta.com",
            domain="test-delta.com",
            status="completed",
            vertical="generic",
        )
        db.add(audit)

        page = PageScore(
            id=uuid.uuid4(),
            audit_id=audit.id,
            page_url="https://test-delta.com",
            was_scored=True,
            crawlability_score=50,
            content_structure_score=50,
            structured_data_score=20,
            authority_score=50,
            overall_page_score=40,
        )
        db.add(page)

        # Add a criterion with score well below threshold
        cs1 = CriterionResult(
            id=uuid.uuid4(),
            page_score_id=page.id,
            criterion_id="CS1",
            criterion_name="Heading Hierarchy",
            category="content_structure",
            score=0,
            checked=True,
            human_summary="Poor heading hierarchy",
            technical_detail="Fix heading hierarchy",
        )
        db.add(cs1)
        db.flush()

        engine = RecommendationEngine(db)
        recs = engine.generate_recommendations(
            audit_id=str(audit.id),
            user_id=str(test_user.id),
            vertical="generic",
        )

        assert len(recs) > 0, "Should generate at least one recommendation"
        for rec in recs:
            # Skip sentiment recs which don't have estimated_score_delta
            if rec.criterion_id == "SENTIMENT":
                continue
            assert rec.estimated_score_delta is not None, (
                f"Recommendation {rec.criterion_id} should have estimated_score_delta"
            )
            assert float(rec.estimated_score_delta) > 0, (
                f"Recommendation {rec.criterion_id} delta should be positive"
            )
            assert float(rec.estimated_score_delta) <= 15.0, (
                f"Recommendation {rec.criterion_id} delta should be <= 15.0"
            )
