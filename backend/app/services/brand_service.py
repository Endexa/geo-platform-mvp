"""Brand management service.

Handles CRUD operations for brands, retroactive audit association,
and domain-based brand lookup for auto-association on audit creation.
"""

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit import Audit
from app.models.audit_query import AuditQuery
from app.models.audit_recommendation import AuditRecommendation
from app.models.brand import Brand
from app.models.brand_mention import BrandMention
from app.models.engine_response import EngineResponse
from app.models.visibility_score import VisibilityScore
from app.schemas.brand import BrandCreate, BrandUpdate, normalize_domain


class BrandService:
    """Service for multi-brand management with audit association."""

    def __init__(self, db: Session):
        self.db = db

    def create_brand(self, user_id: str, data: BrandCreate) -> Brand:
        """Create a brand and retroactively associate matching audits.

        Args:
            user_id: The owner's profile ID.
            data: Brand creation data (name, url, description).

        Returns:
            The created Brand.

        Raises:
            ValueError: If a brand with the same domain already exists for this user.
        """
        domain = normalize_domain(data.url)

        # Check uniqueness (user_id + domain)
        existing = (
            self.db.query(Brand)
            .filter(Brand.user_id == user_id, Brand.domain == domain)
            .first()
        )
        if existing:
            raise ValueError("Brand with this domain already exists")

        brand = Brand(
            user_id=user_id,
            name=data.name,
            url=data.url,
            domain=domain,
            description=data.description,
        )
        self.db.add(brand)
        self.db.flush()  # Get brand.id before retroactive association

        # Retroactive association: link existing audits with matching domain
        count = self._associate_audits(brand)
        if count > 0:
            logger.info(
                "Brand {}: retroactively associated {} audits for domain {}",
                brand.id,
                count,
                domain,
            )

        self.db.commit()
        self.db.refresh(brand)
        return brand

    def list_brands(self, user_id: str) -> list[Brand]:
        """List all brands for a user, ordered by creation date (newest first).

        Args:
            user_id: The owner's profile ID.

        Returns:
            List of Brand objects.
        """
        brands = (
            self.db.query(Brand)
            .filter(Brand.user_id == user_id)
            .order_by(Brand.created_at.desc())
            .all()
        )
        return brands

    def get_brand(self, brand_id: str, user_id: str) -> Brand:
        """Get a brand by ID, verifying ownership.

        Args:
            brand_id: The brand UUID.
            user_id: The owner's profile ID.

        Returns:
            The Brand object.

        Raises:
            ValueError: If brand not found or not owned by user.
        """
        brand = (
            self.db.query(Brand)
            .filter(Brand.id == brand_id, Brand.user_id == user_id)
            .first()
        )
        if not brand:
            raise ValueError("Brand not found")
        return brand

    def update_brand(self, brand_id: str, user_id: str, data: BrandUpdate) -> Brand:
        """Update a brand's fields. Re-normalizes domain if URL changes.

        Args:
            brand_id: The brand UUID.
            user_id: The owner's profile ID.
            data: Fields to update (only non-None fields are applied).

        Returns:
            The updated Brand.

        Raises:
            ValueError: If brand not found or not owned by user.
        """
        brand = self.get_brand(brand_id, user_id)

        if data.name is not None:
            brand.name = data.name
        if data.description is not None:
            brand.description = data.description
        if data.url is not None:
            brand.url = data.url
            new_domain = normalize_domain(data.url)
            if new_domain != brand.domain:
                # Domain changed: check uniqueness
                existing = (
                    self.db.query(Brand)
                    .filter(
                        Brand.user_id == user_id,
                        Brand.domain == new_domain,
                        Brand.id != brand_id,
                    )
                    .first()
                )
                if existing:
                    raise ValueError("Brand with this domain already exists")
                brand.domain = new_domain
                # Re-run retroactive association for new domain
                self._associate_audits(brand)

        self.db.commit()
        self.db.refresh(brand)
        return brand

    def delete_brand(self, brand_id: str, user_id: str) -> None:
        """Delete a brand. Unlinks associated audits (sets brand_id=NULL).

        Args:
            brand_id: The brand UUID.
            user_id: The owner's profile ID.

        Raises:
            ValueError: If brand not found or not owned by user.
        """
        brand = self.get_brand(brand_id, user_id)

        # Unlink audits (don't delete them)
        self.db.query(Audit).filter(Audit.brand_id == brand.id).update(
            {"brand_id": None}
        )

        self.db.delete(brand)
        self.db.commit()

    def get_brand_audit_count(self, brand_id: str) -> int:
        """Count audits associated with a brand.

        Args:
            brand_id: The brand UUID.

        Returns:
            Integer count of audits.
        """
        return (
            self.db.query(func.count(Audit.id))
            .filter(Audit.brand_id == brand_id)
            .scalar()
        )

    def find_brand_by_domain(self, user_id: str, domain: str) -> Brand | None:
        """Find a brand by user and normalized domain.

        Args:
            user_id: The owner's profile ID.
            domain: Normalized domain string.

        Returns:
            Brand if found, None otherwise.
        """
        return (
            self.db.query(Brand)
            .filter(Brand.user_id == user_id, Brand.domain == domain)
            .first()
        )

    def get_multi_brand_overview(self, user_id: str) -> list[dict]:
        """Get a lightweight overview of all brands with latest audit metrics.

        For each brand, finds the latest completed audit and fetches:
        - visibility_score from VisibilityScore table
        - optimization_score from Audit column
        - combined_geo_score (50/50 blend)
        - mention_count from BrandMention via AuditQuery/EngineResponse
        - top_issues_count (high priority open recommendations)
        - audit_count
        - last_audited_at

        Args:
            user_id: The owner's profile ID.

        Returns:
            List of dicts matching MultiBrandOverviewEntry fields.
        """
        brands = self.list_brands(user_id)
        result = []

        for brand in brands:
            # Count total audits for this brand
            audit_count = (
                self.db.query(func.count(Audit.id))
                .filter(Audit.brand_id == brand.id)
                .scalar()
            )

            # Find latest completed audit
            latest_audit = (
                self.db.query(Audit)
                .filter(
                    Audit.brand_id == brand.id,
                    Audit.status == "completed",
                )
                .order_by(Audit.created_at.desc())
                .first()
            )

            entry = {
                "brand_id": brand.id,
                "brand_name": brand.name,
                "brand_url": brand.url,
                "brand_domain": brand.domain,
                "latest_audit_id": None,
                "combined_geo_score": None,
                "visibility_score": None,
                "optimization_score": None,
                "mention_count": 0,
                "top_issues_count": 0,
                "audit_count": audit_count,
                "last_audited_at": None,
            }

            if latest_audit:
                entry["latest_audit_id"] = latest_audit.id
                entry["last_audited_at"] = (
                    latest_audit.completed_at or latest_audit.created_at
                )

                # Visibility score
                vs = (
                    self.db.query(VisibilityScore)
                    .filter(VisibilityScore.audit_id == latest_audit.id)
                    .first()
                )
                vis = vs.overall_score if vs else None
                opt = latest_audit.optimization_score

                entry["visibility_score"] = vis
                entry["optimization_score"] = opt

                if vis is not None and opt is not None:
                    entry["combined_geo_score"] = round(vis * 0.5 + opt * 0.5)

                # Mention count via AuditQuery -> EngineResponse -> BrandMention
                mention_count = (
                    self.db.query(func.count(BrandMention.id))
                    .join(
                        EngineResponse,
                        BrandMention.engine_response_id == EngineResponse.id,
                    )
                    .join(
                        AuditQuery,
                        EngineResponse.audit_query_id == AuditQuery.id,
                    )
                    .filter(AuditQuery.audit_id == latest_audit.id)
                    .scalar()
                )
                entry["mention_count"] = mention_count or 0

                # Top issues: high priority open recommendations
                top_issues_count = (
                    self.db.query(func.count(AuditRecommendation.id))
                    .filter(
                        AuditRecommendation.audit_id == latest_audit.id,
                        AuditRecommendation.status == "open",
                        AuditRecommendation.priority == "high",
                    )
                    .scalar()
                )
                entry["top_issues_count"] = top_issues_count or 0

            result.append(entry)

        return result

    def _associate_audits(self, brand: Brand) -> int:
        """Associate existing audits with a brand by matching normalized domain.

        Matches audits where the audit's domain (after normalization) matches
        the brand's domain, the user_id matches, and brand_id is currently NULL.

        Args:
            brand: The Brand to associate audits with.

        Returns:
            Number of audits associated.
        """
        # Match against both raw domain and www-prefixed domain
        # since older audits stored urlparse.netloc which may include www.
        domain_variants = [brand.domain, f"www.{brand.domain}"]

        count = (
            self.db.query(Audit)
            .filter(
                Audit.user_id == brand.user_id,
                Audit.domain.in_(domain_variants),
                Audit.brand_id.is_(None),
            )
            .update({"brand_id": brand.id}, synchronize_session="fetch")
        )
        return count
