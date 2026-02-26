"""Integration tests for the full Phase 2 pipeline: scoring -> vertical -> recommendations -> competitors -> brands.

Tests verify:
1. SaaS vertical filters irrelevant schema recommendations
2. Generic vertical passes all recommendations
3. Fixture classifies to a valid non-generic vertical
4. Brand linking creates Brand records with is_competitor=True
5. Brand linking deduplicates across audits (same entity -> same Brand)
6. SOV trend returns chronological data points
"""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.audit import Audit
from app.models.audit_recommendation import AuditRecommendation
from app.models.brand import Brand
from app.models.competitor import CompetitorAudit, DiscoveredCompetitor
from app.models.criterion_result import CriterionResult
from app.models.page_score import PageScore
from app.models.profile import Profile
from app.services.competitor_service import CompetitorService
from app.services.recommendation_engine import RecommendationEngine
from app.services.vertical_classifier import SiteVertical, VerticalClassifier


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(db: Session, email_prefix: str = "p2int") -> Profile:
    """Create a test user with unique email."""
    from app.core.security import SecurityManager

    user = Profile(
        id=uuid.uuid4(),
        email=f"{email_prefix}-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=SecurityManager.hash_password("TestPassword123@"),
        full_name="Test User",
        is_active=True,
        role="member",
    )
    db.add(user)
    db.flush()
    return user


def _make_audit(
    db: Session,
    user: Profile,
    url: str = "https://mysite.com",
    vertical: str = "generic",
) -> Audit:
    """Create a test audit for a user."""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc
    audit = Audit(
        id=uuid.uuid4(),
        user_id=user.id,
        url=url,
        domain=domain,
        status="completed",
        optimization_score=72,
        vertical=vertical,
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    db.flush()
    return audit


def _make_page_with_criteria(
    db: Session,
    audit: Audit,
    criterion_ids: list[str],
    category: str = "structured_data",
    score: int = 0,
) -> PageScore:
    """Create a PageScore with CriterionResult records below thresholds."""
    page = PageScore(
        id=uuid.uuid4(),
        audit_id=audit.id,
        page_url=audit.url,
        was_scored=True,
        crawlability_score=50,
        content_structure_score=50,
        structured_data_score=20,
        authority_score=50,
        overall_page_score=40,
    )
    db.add(page)
    db.flush()

    for cid in criterion_ids:
        cr = CriterionResult(
            id=uuid.uuid4(),
            page_score_id=page.id,
            criterion_id=cid,
            criterion_name=f"Criterion {cid}",
            category=category,
            score=score,
            checked=True,
            human_summary=f"No {cid} found",
            technical_detail=f"Add {cid}",
        )
        db.add(cr)
    db.flush()
    return page


def _make_competitor(
    db: Session,
    audit: Audit,
    entity_name: str = "Acme Corp",
    resolved_url: str | None = None,
    share_of_voice: float = 25.0,
    mention_count: int = 10,
) -> DiscoveredCompetitor:
    """Create a DiscoveredCompetitor record."""
    comp = DiscoveredCompetitor(
        id=uuid.uuid4(),
        audit_id=audit.id,
        entity_name=entity_name,
        entity_type="ORG",
        mention_count=mention_count,
        share_of_voice=Decimal(str(share_of_voice)),
        resolved_url=resolved_url,
        is_user_brand=False,
    )
    db.add(comp)
    db.flush()
    return comp


def _make_brand(
    db: Session,
    user: Profile,
    name: str = "Acme Corp",
    domain: str = "acme.com",
    is_competitor: bool = True,
) -> Brand:
    """Create a Brand record."""
    brand = Brand(
        id=uuid.uuid4(),
        user_id=user.id,
        name=name,
        url=f"https://{domain}",
        domain=domain,
        is_competitor=is_competitor,
    )
    db.add(brand)
    db.flush()
    return brand


# ===========================================================================
# Test 1: SaaS vertical filters irrelevant schema recommendations
# ===========================================================================


class TestRecommendationPipelineWithSaasVertical:
    """Verify that SaaS vertical excludes SD8 (Product) and SD10 (ClaimReview)
    recommendations, but keeps universally relevant criteria."""

    def test_saas_vertical_filters_irrelevant_recs(self, db: Session):
        """Score fixture data, classify as SaaS, generate recs with vertical filtering.

        Assert: no LocalBusiness or ClaimReview schema recs, but
        Crawlability/Content/Authority recs ARE generated."""
        user = _make_user(db)
        audit = _make_audit(db, user, url="https://saas-example.com", vertical="saas")

        # Create criterion results for multiple categories including SD8, SD10, and universals
        page = PageScore(
            id=uuid.uuid4(),
            audit_id=audit.id,
            page_url=audit.url,
            was_scored=True,
            crawlability_score=30,
            content_structure_score=30,
            structured_data_score=10,
            authority_score=30,
            overall_page_score=25,
        )
        db.add(page)
        db.flush()

        # Schema criteria that SHOULD be excluded for SaaS
        excluded_criteria = [
            ("SD8", "structured_data", "Product/Offer schema"),
            ("SD10", "structured_data", "ClaimReview schema"),
        ]
        # Criteria that SHOULD pass through for SaaS
        included_criteria = [
            ("SD3", "structured_data", "FAQPage schema"),
            ("SD1", "structured_data", "Organization schema"),
            ("CS1", "content_structure", "Heading Hierarchy"),
            ("C9", "crawlability", "SSR Detection"),
            ("A3", "authority", "Knowledge Graph Presence"),
        ]

        all_criteria = excluded_criteria + included_criteria
        for cid, cat, name in all_criteria:
            cr = CriterionResult(
                id=uuid.uuid4(),
                page_score_id=page.id,
                criterion_id=cid,
                criterion_name=name,
                category=cat,
                score=0,  # Below all thresholds
                checked=True,
                human_summary=f"No {name} found",
                technical_detail=f"Add {name}",
            )
            db.add(cr)
        db.flush()

        engine = RecommendationEngine(db)
        recs = engine.generate_recommendations(
            audit_id=str(audit.id),
            user_id=str(user.id),
            vertical="saas",
        )

        rec_ids = {r.criterion_id for r in recs}

        # SD8 (Product) and SD10 (ClaimReview) should be excluded for SaaS
        assert "SD8" not in rec_ids, "SD8 (Product schema) should be excluded for SaaS"
        assert "SD10" not in rec_ids, "SD10 (ClaimReview) should be excluded for SaaS"

        # Universal criteria should be present
        assert "SD3" in rec_ids, "SD3 (FAQPage) should be included for SaaS"

        # Non-SD criteria should always be present
        non_sd_recs = [r for r in recs if not r.criterion_id.startswith("SD")]
        assert len(non_sd_recs) > 0, "Non-SD recommendations should be generated"

        # Each recommendation should have valid estimated_score_delta
        for rec in recs:
            if rec.criterion_id == "SENTIMENT":
                continue
            assert rec.estimated_score_delta is not None
            assert float(rec.estimated_score_delta) > 0
            assert float(rec.estimated_score_delta) <= 15.0

        # Recommendations should be sorted by priority (high before medium before low)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(recs) - 1):
            current_priority = priority_order.get(recs[i].priority, 2)
            next_priority = priority_order.get(recs[i + 1].priority, 2)
            assert current_priority <= next_priority, (
                f"Recommendations not sorted by priority: "
                f"{recs[i].priority} before {recs[i+1].priority}"
            )


# ===========================================================================
# Test 2: Generic vertical passes all recommendations
# ===========================================================================


class TestRecommendationPipelineWithGenericVertical:
    """Verify that generic vertical does not filter any recommendations."""

    def test_generic_vertical_passes_all_recs(self, db: Session):
        """Generate recs with vertical='generic'. Assert SD8 and SD10 are NOT filtered."""
        user = _make_user(db)
        audit = _make_audit(db, user, url="https://generic-example.com", vertical="generic")

        page = _make_page_with_criteria(
            db, audit,
            criterion_ids=["SD8", "SD10", "SD3", "CS1"],
            category="structured_data",
            score=0,
        )
        # Fix categories for non-SD criteria (CS1 should be content_structure)
        cs1_result = (
            db.query(CriterionResult)
            .filter(CriterionResult.page_score_id == page.id)
            .filter(CriterionResult.criterion_id == "CS1")
            .first()
        )
        if cs1_result:
            cs1_result.category = "content_structure"
            db.flush()

        engine = RecommendationEngine(db)
        recs_generic = engine.generate_recommendations(
            audit_id=str(audit.id),
            user_id=str(user.id),
            vertical="generic",
        )

        rec_ids_generic = {r.criterion_id for r in recs_generic}

        # Generic should include ALL schema criteria
        assert "SD8" in rec_ids_generic, "SD8 should be included for generic vertical"
        assert "SD10" in rec_ids_generic, "SD10 should be included for generic vertical"
        assert "SD3" in rec_ids_generic, "SD3 should be included for generic vertical"

    def test_generic_has_more_or_equal_recs_than_saas(self, db: Session):
        """Generic vertical should produce >= recommendation count compared to SaaS."""
        user = _make_user(db)

        # Audit 1: SaaS
        audit_saas = _make_audit(db, user, url="https://saas1.com", vertical="saas")
        _make_page_with_criteria(
            db, audit_saas,
            criterion_ids=["SD8", "SD10", "SD3"],
            category="structured_data",
            score=0,
        )

        # Audit 2: Generic (same criteria)
        audit_generic = _make_audit(db, user, url="https://generic1.com", vertical="generic")
        _make_page_with_criteria(
            db, audit_generic,
            criterion_ids=["SD8", "SD10", "SD3"],
            category="structured_data",
            score=0,
        )

        engine = RecommendationEngine(db)
        recs_saas = engine.generate_recommendations(
            audit_id=str(audit_saas.id), user_id=str(user.id), vertical="saas"
        )
        recs_generic = engine.generate_recommendations(
            audit_id=str(audit_generic.id), user_id=str(user.id), vertical="generic"
        )

        assert len(recs_generic) >= len(recs_saas), (
            f"Generic ({len(recs_generic)}) should have >= recs than SaaS ({len(recs_saas)})"
        )


# ===========================================================================
# Test 3: Vertical classification matches fixture
# ===========================================================================


class TestVerticalClassificationMatchesFixture:
    """Verify the VerticalClassifier produces a valid non-generic result for the fixture."""

    def test_fixture_classifies_to_valid_vertical(self):
        """Load stripe_crawl_data.json and classify. Result should be a valid
        SiteVertical enum and NOT GENERIC (the fixture has enough signals)."""
        with open(FIXTURES_DIR / "stripe_crawl_data.json") as f:
            crawl_data = json.load(f)

        classifier = VerticalClassifier()
        result = classifier.classify(crawl_data)

        # Should be a valid SiteVertical enum member
        assert isinstance(result, SiteVertical), (
            f"Expected SiteVertical enum, got {type(result)}"
        )
        assert result.value in [v.value for v in SiteVertical], (
            f"Result {result.value} is not a valid SiteVertical"
        )

        # The fixture has Organization + Article schemas, pricing page,
        # signup/integrations/API content -- should NOT be generic
        assert result != SiteVertical.GENERIC, (
            f"Expected non-generic vertical for fixture with rich signals, got {result}"
        )

    def test_empty_crawl_data_returns_generic(self):
        """Empty crawl data should fallback to GENERIC safely."""
        classifier = VerticalClassifier()
        result = classifier.classify({
            "url": "",
            "html": "",
            "schema_org": [],
        })
        assert result == SiteVertical.GENERIC


# ===========================================================================
# Test 4: Competitor brand linking creates brands
# ===========================================================================


class TestCompetitorBrandLinkingCreatesBrands:
    """Verify link_competitor_to_brand creates Brand records with correct attributes."""

    def test_linking_creates_brand_with_is_competitor(self, db: Session):
        """Each linked competitor should have a non-null competitor_brand_id
        pointing to a Brand with is_competitor=True."""
        user = _make_user(db)
        audit = _make_audit(db, user)

        competitors = [
            _make_competitor(
                db, audit,
                entity_name=f"Competitor {i}",
                resolved_url=f"https://competitor{i}.com",
            )
            for i in range(3)
        ]

        service = CompetitorService(db)
        for comp in competitors:
            service.link_competitor_to_brand(db, comp, str(user.id))
        db.flush()

        for comp in competitors:
            assert comp.competitor_brand_id is not None, (
                f"Competitor '{comp.entity_name}' should have competitor_brand_id set"
            )
            brand = db.query(Brand).filter(Brand.id == comp.competitor_brand_id).first()
            assert brand is not None
            assert brand.is_competitor is True, (
                f"Brand for '{comp.entity_name}' should have is_competitor=True"
            )

    def test_batch_linking_returns_count(self, db: Session):
        """link_audit_competitors_to_brands should return the count of newly linked."""
        user = _make_user(db)
        audit = _make_audit(db, user)

        for i in range(4):
            _make_competitor(
                db, audit,
                entity_name=f"BatchComp {i}",
                resolved_url=f"https://batchcomp{i}.com",
            )

        service = CompetitorService(db)
        count = service.link_audit_competitors_to_brands(db, str(audit.id), str(user.id))

        assert count == 4, f"Expected 4 linked competitors, got {count}"


# ===========================================================================
# Test 5: Competitor brand linking deduplicates across audits
# ===========================================================================


class TestCompetitorBrandLinkingDeduplicates:
    """Verify that the same entity name across audits links to the same Brand."""

    def test_same_entity_same_brand_across_audits(self, db: Session):
        """Create 2 audits for the same user, each with DiscoveredCompetitor
        'Acme Corp'. After linking, both should point to the SAME Brand."""
        user = _make_user(db)

        audit1 = _make_audit(db, user, url="https://mysite.com")
        audit2 = _make_audit(db, user, url="https://mysite.com")

        comp1 = _make_competitor(
            db, audit1,
            entity_name="Acme Corp",
            resolved_url="https://acme.com",
            share_of_voice=30.0,
        )
        comp2 = _make_competitor(
            db, audit2,
            entity_name="Acme Corp",
            resolved_url="https://acme.com",
            share_of_voice=35.0,
        )

        service = CompetitorService(db)

        # Link first audit's competitor (creates new Brand)
        service.link_competitor_to_brand(db, comp1, str(user.id))
        db.flush()

        # Link second audit's competitor (should reuse existing Brand)
        service.link_competitor_to_brand(db, comp2, str(user.id))
        db.flush()

        assert comp1.competitor_brand_id is not None
        assert comp2.competitor_brand_id is not None
        assert comp1.competitor_brand_id == comp2.competitor_brand_id, (
            "Both competitors should link to the same Brand (deduplication)"
        )

        # Verify only 1 Brand was created
        brands = (
            db.query(Brand)
            .filter(Brand.user_id == user.id)
            .filter(Brand.name == "Acme Corp")
            .all()
        )
        assert len(brands) == 1, f"Expected 1 Brand for 'Acme Corp', got {len(brands)}"


# ===========================================================================
# Test 6: SOV trend returns chronological data
# ===========================================================================


class TestSOVTrendReturnsChronologicalData:
    """Verify SOV trend query returns correctly ordered time-series data."""

    def test_sov_trend_returns_ordered_data_points(self, db: Session):
        """Set up 3 audits with DiscoveredCompetitor records linked to the same Brand.
        Each with different share_of_voice values. Assert 3 data points, ordered by date."""
        user = _make_user(db)
        brand = _make_brand(db, user, name="Trend Corp", domain="trendcorp.com")

        sov_values = [20.0, 35.5, 45.0]
        for sov in sov_values:
            audit = _make_audit(db, user)
            comp = _make_competitor(
                db, audit,
                entity_name="Trend Corp",
                share_of_voice=sov,
            )
            comp.competitor_brand_id = brand.id
        db.flush()

        trend = CompetitorService.get_competitor_sov_trend(
            db, str(brand.id), str(user.id)
        )

        assert len(trend) == 3, f"Expected 3 data points, got {len(trend)}"

        # Verify all required fields are present
        for point in trend:
            assert "date" in point
            assert "share_of_voice" in point
            assert "mention_count" in point
            assert "audit_id" in point

        # Verify ordered by date ascending
        dates = [point["date"] for point in trend]
        assert dates == sorted(dates), (
            f"Data points should be ordered by date ascending: {dates}"
        )

    def test_sov_trend_empty_for_no_data(self, db: Session):
        """Brand with no DiscoveredCompetitor links should return empty trend."""
        user = _make_user(db)
        brand = _make_brand(db, user, name="Lonely Corp", domain="lonely.com")

        trend = CompetitorService.get_competitor_sov_trend(
            db, str(brand.id), str(user.id)
        )

        assert trend == [], f"Expected empty trend, got {len(trend)} points"
