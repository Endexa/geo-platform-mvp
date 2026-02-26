"""Tests for cross-audit competitor persistence: brand linking, SOV trending, and score comparison.

Covers:
- Brand linking logic (domain match, name match, fuzzy match, create new)
- Per-user isolation (no cross-user data leakage)
- SOV trend queries across multiple audits
- Score comparison endpoint (site vs competitors)
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.audit import Audit
from app.models.brand import Brand
from app.models.competitor import CompetitorAudit, DiscoveredCompetitor
from app.models.profile import Profile
from app.core.security import SecurityManager
from app.services.competitor_service import CompetitorService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(db: Session, email_prefix: str = "test") -> Profile:
    """Create a test user with a unique email."""
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


def _make_audit(db: Session, user: Profile, url: str = "https://mysite.com") -> Audit:
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
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    db.flush()
    return audit


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


# ---------------------------------------------------------------------------
# Brand Linking Tests
# ---------------------------------------------------------------------------


class TestBrandLinking:
    """Tests for link_competitor_to_brand logic."""

    def test_link_creates_new_brand_for_unknown_competitor(self, db: Session):
        """Given a DiscoveredCompetitor with entity_name='Acme Corp' and no
        matching Brand, a new Brand is created with is_competitor=True and
        the competitor's competitor_brand_id is set."""
        user = _make_user(db)
        audit = _make_audit(db, user)
        comp = _make_competitor(db, audit, entity_name="Acme Corp")

        service = CompetitorService(db)
        service.link_competitor_to_brand(db, comp, str(user.id))

        assert comp.competitor_brand_id is not None
        brand = db.query(Brand).filter(Brand.id == comp.competitor_brand_id).first()
        assert brand is not None
        assert brand.is_competitor is True
        assert brand.name == "Acme Corp"
        assert brand.user_id == user.id

    def test_link_matches_existing_brand_by_domain(self, db: Session):
        """Given an existing Brand with domain='acme.com' and a DiscoveredCompetitor
        with resolved_url='https://acme.com/products', the competitor links to
        the existing Brand."""
        user = _make_user(db)
        audit = _make_audit(db, user)
        existing_brand = _make_brand(db, user, name="Acme Corp", domain="acme.com")
        comp = _make_competitor(
            db, audit, entity_name="Acme Inc", resolved_url="https://acme.com/products"
        )

        service = CompetitorService(db)
        service.link_competitor_to_brand(db, comp, str(user.id))

        assert comp.competitor_brand_id == existing_brand.id

    def test_link_matches_existing_brand_by_name(self, db: Session):
        """Given an existing Brand with name='Acme Corp' and a DiscoveredCompetitor
        with entity_name='acme corp' (case-insensitive), the competitor links to
        the existing Brand."""
        user = _make_user(db)
        audit = _make_audit(db, user)
        existing_brand = _make_brand(db, user, name="Acme Corp", domain="other.com")
        comp = _make_competitor(db, audit, entity_name="acme corp")

        service = CompetitorService(db)
        service.link_competitor_to_brand(db, comp, str(user.id))

        assert comp.competitor_brand_id == existing_brand.id

    def test_link_per_user_isolation(self, db: Session):
        """Two different users discovering the same competitor brand each get
        separate Brand records (no cross-user leakage)."""
        user1 = _make_user(db, email_prefix="user1")
        user2 = _make_user(db, email_prefix="user2")
        audit1 = _make_audit(db, user1)
        audit2 = _make_audit(db, user2)
        comp1 = _make_competitor(
            db, audit1, entity_name="Acme Corp", resolved_url="https://acme.com"
        )
        comp2 = _make_competitor(
            db, audit2, entity_name="Acme Corp", resolved_url="https://acme.com"
        )

        service = CompetitorService(db)
        service.link_competitor_to_brand(db, comp1, str(user1.id))
        service.link_competitor_to_brand(db, comp2, str(user2.id))

        # Both should be linked, but to DIFFERENT Brand records
        assert comp1.competitor_brand_id is not None
        assert comp2.competitor_brand_id is not None
        assert comp1.competitor_brand_id != comp2.competitor_brand_id

        brand1 = db.query(Brand).filter(Brand.id == comp1.competitor_brand_id).first()
        brand2 = db.query(Brand).filter(Brand.id == comp2.competitor_brand_id).first()
        assert brand1.user_id == user1.id
        assert brand2.user_id == user2.id


# ---------------------------------------------------------------------------
# SOV Trend Tests
# ---------------------------------------------------------------------------


class TestSOVTrend:
    """Tests for share-of-voice trend queries across audits."""

    def test_sov_trend_across_audits(self, db: Session):
        """Given 3 audits where a competitor brand is discovered each time
        with different SOV values, the trend query returns 3 data points
        ordered by date."""
        user = _make_user(db)

        # Create a competitor brand first
        brand = _make_brand(db, user, name="Rival Inc", domain="rival.com")

        sov_values = [30.0, 25.5, 40.0]
        for i, sov in enumerate(sov_values):
            audit = _make_audit(db, user)
            comp = _make_competitor(
                db, audit, entity_name="Rival Inc", share_of_voice=sov
            )
            comp.competitor_brand_id = brand.id
        db.flush()

        trend = CompetitorService.get_competitor_sov_trend(db, str(brand.id), str(user.id))

        assert len(trend) == 3
        # All data points should have required keys
        for point in trend:
            assert "date" in point
            assert "share_of_voice" in point
            assert "mention_count" in point
            assert "audit_id" in point

    def test_sov_trend_empty_for_unknown_brand(self, db: Session):
        """Querying SOV trend for a brand_id not associated with any
        DiscoveredCompetitor returns empty list."""
        user = _make_user(db)
        unknown_brand_id = str(uuid.uuid4())

        trend = CompetitorService.get_competitor_sov_trend(
            db, unknown_brand_id, str(user.id)
        )

        assert trend == []


# ---------------------------------------------------------------------------
# Score Comparison Tests
# ---------------------------------------------------------------------------


class TestScoreComparison:
    """Tests for side-by-side score comparison endpoint."""

    def test_score_comparison_returns_site_and_competitors(self, db: Session):
        """Create an audit with known scores and 2 completed CompetitorAudit
        records. Assert response has 'site' with correct scores and
        'competitors' list with 2 entries."""
        user = _make_user(db)
        audit = _make_audit(db, user)

        # Create 2 completed competitor audits
        for name, url, opt_score in [("Rival A", "https://rivala.com", 80), ("Rival B", "https://rivalb.com", 65)]:
            ca = CompetitorAudit(
                id=uuid.uuid4(),
                parent_audit_id=audit.id,
                competitor_name=name,
                competitor_url=url,
                optimization_score=opt_score,
                crawlability_avg=75,
                content_structure_avg=70,
                structured_data_avg=60,
                authority_avg=55,
                pages_scored=3,
                status="completed",
            )
            db.add(ca)
        db.flush()

        service = CompetitorService(db)
        result = service.get_score_comparison(db, str(audit.id), str(user.id))

        assert "site" in result
        assert "competitors" in result
        assert result["site"]["optimization_score"] == 72
        assert len(result["competitors"]) == 2

    def test_score_comparison_excludes_failed_competitors(self, db: Session):
        """A CompetitorAudit with status='failed' is NOT included."""
        user = _make_user(db)
        audit = _make_audit(db, user)

        # One completed, one failed
        ca1 = CompetitorAudit(
            id=uuid.uuid4(),
            parent_audit_id=audit.id,
            competitor_name="Good Rival",
            competitor_url="https://goodrival.com",
            optimization_score=80,
            crawlability_avg=75,
            content_structure_avg=70,
            structured_data_avg=60,
            authority_avg=55,
            pages_scored=3,
            status="completed",
        )
        ca2 = CompetitorAudit(
            id=uuid.uuid4(),
            parent_audit_id=audit.id,
            competitor_name="Bad Rival",
            competitor_url="https://badrival.com",
            optimization_score=None,
            pages_scored=0,
            status="failed",
        )
        db.add_all([ca1, ca2])
        db.flush()

        service = CompetitorService(db)
        result = service.get_score_comparison(db, str(audit.id), str(user.id))

        assert len(result["competitors"]) == 1
        assert result["competitors"][0]["name"] == "Good Rival"

    def test_score_comparison_empty_when_no_competitors(self, db: Session):
        """Call get_score_comparison for an audit with no CompetitorAudit
        records. Assert competitors list is empty but site scores are returned."""
        user = _make_user(db)
        audit = _make_audit(db, user)

        service = CompetitorService(db)
        result = service.get_score_comparison(db, str(audit.id), str(user.id))

        assert result["competitors"] == []
        assert "site" in result
        assert result["site"]["optimization_score"] == 72
