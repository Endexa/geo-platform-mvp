"""Unit tests for VerticalClassifier -- detects website industry vertical from crawl data.

Tests verify classification into 6 verticals: SaaS, e-commerce, local business,
media/blog, B2B services, and generic (fallback). Schema.org @type takes priority
over URL/content pattern matching.
"""

import pytest

from app.services.vertical_classifier import SiteVertical, VerticalClassifier


@pytest.fixture()
def classifier():
    return VerticalClassifier()


@pytest.fixture()
def base_crawl_data():
    """Minimal crawl data dict -- override schema_org/html/url per test."""
    return {
        "url": "https://example.com",
        "domain": "example.com",
        "html": "<html><body>Hello</body></html>",
        "main_content": "Hello",
        "schema_org": [],
        "ai_bot_access": {},
        "headings": [],
        "word_count": 100,
    }


class TestEcommerceDetection:
    """E-commerce vertical detection from Product/Offer schema types."""

    def test_product_schema_returns_ecommerce(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "Product", "name": "Widget"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.ECOMMERCE

    def test_offer_schema_returns_ecommerce(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "Offer", "price": "19.99"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.ECOMMERCE

    def test_aggregate_offer_schema_returns_ecommerce(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "AggregateOffer"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.ECOMMERCE


class TestLocalBusinessDetection:
    """Local business vertical detection from LocalBusiness/Restaurant schema types."""

    def test_local_business_schema(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "LocalBusiness", "name": "Joe's Diner"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.LOCAL_BUSINESS

    def test_restaurant_schema(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "Restaurant", "name": "Fine Dining"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.LOCAL_BUSINESS

    def test_store_schema(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "Store"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.LOCAL_BUSINESS


class TestSaaSDetection:
    """SaaS vertical detection from SoftwareApplication schema + URL patterns."""

    def test_software_application_schema(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "SoftwareApplication"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.SAAS

    def test_web_application_schema(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "WebApplication"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.SAAS

    def test_saas_from_url_patterns(self, classifier, base_crawl_data):
        """SaaS detection from URL/content signals when no schema matches."""
        base_crawl_data["html"] = "<html><body><a href='/pricing'>Pricing</a><a href='/signup'>Sign Up</a></body></html>"
        assert classifier.classify(base_crawl_data) == SiteVertical.SAAS


class TestMediaBlogDetection:
    """Media/blog vertical detection from BlogPosting/NewsArticle schema types."""

    def test_blog_posting_schema(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "BlogPosting"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.MEDIA_BLOG

    def test_news_article_schema(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "NewsArticle"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.MEDIA_BLOG

    def test_news_media_organization_schema(self, classifier, base_crawl_data):
        base_crawl_data["schema_org"] = [{"@type": "NewsMediaOrganization"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.MEDIA_BLOG


class TestB2BDetection:
    """B2B services detection from Organization schema (fallback)."""

    def test_organization_only_returns_b2b(self, classifier, base_crawl_data):
        """Organization schema with no other signals falls back to B2B."""
        base_crawl_data["schema_org"] = [{"@type": "Organization", "name": "Acme Corp"}]
        assert classifier.classify(base_crawl_data) == SiteVertical.B2B_SERVICES


class TestGenericFallback:
    """Generic fallback when no recognizable signals are found."""

    def test_empty_schema_no_patterns_returns_generic(self, classifier, base_crawl_data):
        assert classifier.classify(base_crawl_data) == SiteVertical.GENERIC

    def test_empty_crawl_data_returns_generic(self, classifier):
        assert classifier.classify({}) == SiteVertical.GENERIC


class TestPriorityOrder:
    """Schema.org types take priority over URL patterns."""

    def test_product_schema_beats_saas_url(self, classifier, base_crawl_data):
        """A site with Product schema AND /pricing URL = ecommerce, not SaaS."""
        base_crawl_data["schema_org"] = [{"@type": "Product", "name": "Widget"}]
        base_crawl_data["html"] = "<html><body><a href='/pricing'>Pricing</a></body></html>"
        assert classifier.classify(base_crawl_data) == SiteVertical.ECOMMERCE

    def test_local_business_schema_beats_ecommerce_url(self, classifier, base_crawl_data):
        """LocalBusiness schema takes priority over /shop URL pattern."""
        base_crawl_data["schema_org"] = [{"@type": "LocalBusiness"}]
        base_crawl_data["html"] = "<html><body><a href='/shop'>Shop</a></body></html>"
        assert classifier.classify(base_crawl_data) == SiteVertical.LOCAL_BUSINESS


class TestSchemaTypeExtraction:
    """Test _extract_schema_types handles various schema_org data shapes."""

    def test_list_type_values(self, classifier, base_crawl_data):
        """Handle @type as a list (e.g. ["Organization", "Corporation"])."""
        base_crawl_data["schema_org"] = [{"@type": ["Organization", "Corporation"]}]
        types = classifier._extract_schema_types(base_crawl_data)
        assert "Organization" in types
        assert "Corporation" in types

    def test_string_type_value(self, classifier, base_crawl_data):
        """Handle @type as a single string."""
        base_crawl_data["schema_org"] = [{"@type": "Product"}]
        types = classifier._extract_schema_types(base_crawl_data)
        assert "Product" in types

    def test_multiple_schema_items(self, classifier, base_crawl_data):
        """Extract types from multiple schema.org items."""
        base_crawl_data["schema_org"] = [
            {"@type": "Organization"},
            {"@type": "Article"},
        ]
        types = classifier._extract_schema_types(base_crawl_data)
        assert "Organization" in types
        assert "Article" in types

    def test_missing_type_key(self, classifier, base_crawl_data):
        """Schema items without @type are skipped gracefully."""
        base_crawl_data["schema_org"] = [{"name": "No type here"}]
        types = classifier._extract_schema_types(base_crawl_data)
        assert types == []
