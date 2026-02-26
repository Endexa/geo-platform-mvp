"""Detect website industry vertical from crawl data signals.

Uses a 3-priority heuristic approach:
1. Schema.org @type lookup (strongest signal)
2. URL/HTML content pattern matching
3. Organization type fallback to B2B

Falls back to GENERIC when confidence is low -- better to show a potentially
irrelevant recommendation than to miss a relevant one.
"""

from enum import Enum


class SiteVertical(str, Enum):
    """Website industry verticals for recommendation filtering."""

    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    LOCAL_BUSINESS = "local_business"
    MEDIA_BLOG = "media_blog"
    B2B_SERVICES = "b2b_services"
    GENERIC = "generic"  # Fallback -- no filtering applied


class VerticalClassifier:
    """Classify website vertical from crawl data signals.

    Heuristic priority:
    1. Schema.org @type (strongest signal)
    2. URL/HTML content patterns
    3. Organization type fallback to B2B
    4. Default to GENERIC
    """

    # Schema types that strongly indicate a vertical
    SCHEMA_VERTICAL_MAP: dict[str, str] = {
        # E-commerce signals
        "Product": "ecommerce",
        "Offer": "ecommerce",
        "AggregateOffer": "ecommerce",
        "ShoppingCenter": "ecommerce",
        "OnlineStore": "ecommerce",
        # Local business signals
        "LocalBusiness": "local_business",
        "Restaurant": "local_business",
        "Store": "local_business",
        "MedicalBusiness": "local_business",
        "LegalService": "local_business",
        # Media/blog signals
        "NewsArticle": "media_blog",
        "BlogPosting": "media_blog",
        "NewsMediaOrganization": "media_blog",
        # SaaS signals
        "SoftwareApplication": "saas",
        "WebApplication": "saas",
    }

    # URL/content patterns per vertical
    ECOMMERCE_SIGNALS: list[str] = [
        "cart", "checkout", "add-to-cart", "shop", "product", "price",
    ]
    LOCAL_SIGNALS: list[str] = [
        "directions", "hours", "location", "near-me", "appointment",
    ]
    SAAS_SIGNALS: list[str] = [
        "pricing", "signup", "sign-up", "demo", "trial", "features",
        "integrations", "api",
    ]

    def classify(self, crawl_data: dict) -> SiteVertical:
        """Classify from crawl_data dict (CrawlResult.model_dump()).

        Returns the detected vertical with highest confidence signal.
        """
        schema_types = self._extract_schema_types(crawl_data)

        # Priority 1: Schema.org types (strongest signal)
        for schema_type in schema_types:
            if schema_type in self.SCHEMA_VERTICAL_MAP:
                return SiteVertical(self.SCHEMA_VERTICAL_MAP[schema_type])

        # Priority 2: URL/HTML content patterns
        url = crawl_data.get("url", "").lower()
        html = crawl_data.get("html", "").lower()

        if any(sig in html for sig in self.ECOMMERCE_SIGNALS):
            return SiteVertical.ECOMMERCE
        if any(sig in html for sig in self.LOCAL_SIGNALS):
            return SiteVertical.LOCAL_BUSINESS
        if any(sig in url or sig in html for sig in self.SAAS_SIGNALS):
            return SiteVertical.SAAS

        # Priority 3: Organization type in schema -> B2B fallback
        if "Organization" in schema_types:
            return SiteVertical.B2B_SERVICES

        return SiteVertical.GENERIC

    def _extract_schema_types(self, crawl_data: dict) -> list[str]:
        """Extract all @type values from schema_org data.

        Handles both string and list @type values, and multiple schema items.
        """
        schema_org = crawl_data.get("schema_org", [])
        types: list[str] = []
        for item in schema_org:
            if isinstance(item, dict):
                t = item.get("@type", "")
                if isinstance(t, list):
                    types.extend(t)
                elif isinstance(t, str) and t:
                    types.append(t)
        return types
