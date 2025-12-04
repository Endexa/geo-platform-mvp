"""
GEO Data Points Utilities Package

Exports logging, configuration, and all helper utilities.
"""

from .logging import GeoLogger, get_logger
from .config import GeoConfig, get_config
from .helpers import (
    validate_url,
    normalize_url,
    fetch_url,
    parse_html,
    extract_text,
    get_domain,
    get_base_url,
    make_absolute_url,
    calculate_percentage_score,
    safe_divide,
    format_duration
)

# HTTP Client
from .http_client import (
    get_http_session,
    check_url_status,
    follow_redirects,
    measure_response_time,
    get_final_url,
    check_robots_txt_allows
)

# HTML Parser
from .html_parser import HTMLAnalyzer, parse_html

# Content Analyzer
from .content_analyzer import ContentAnalyzer, analyze_content

# External APIs
from .external_apis import (
    get_knowledge_graph_client,
    get_wikidata_client,
    get_wikipedia_client,
    get_pagespeed_client,
    get_reddit_client,
    get_commoncrawl_client
)

# SEO Helpers
from .seo_helpers import (
    SitemapAnalyzer,
    RobotsTxtAnalyzer,
    check_ssl_certificate,
    validate_canonical,
    validate_hreflang,
    analyze_url_structure
)

# Crawl Helpers
from .crawl_helpers import (
    SiteCrawler,
    detect_redirect_chains,
    calculate_click_depth,
    analyze_internal_linking
)

__all__ = [
    # Logging & Config
    "GeoLogger",
    "get_logger",
    "GeoConfig",
    "get_config",

    # Basic Helpers
    "validate_url",
    "normalize_url",
    "fetch_url",
    "parse_html",
    "extract_text",
    "get_domain",
    "get_base_url",
    "make_absolute_url",
    "calculate_percentage_score",
    "safe_divide",
    "format_duration",

    # HTTP Client
    "get_http_session",
    "check_url_status",
    "follow_redirects",
    "measure_response_time",
    "get_final_url",
    "check_robots_txt_allows",

    # HTML Parser
    "HTMLAnalyzer",

    # Content Analyzer
    "ContentAnalyzer",
    "analyze_content",

    # External APIs
    "get_knowledge_graph_client",
    "get_wikidata_client",
    "get_wikipedia_client",
    "get_pagespeed_client",
    "get_reddit_client",
    "get_commoncrawl_client",

    # SEO Helpers
    "SitemapAnalyzer",
    "RobotsTxtAnalyzer",
    "check_ssl_certificate",
    "validate_canonical",
    "validate_hreflang",
    "analyze_url_structure",

    # Crawl Helpers
    "SiteCrawler",
    "detect_redirect_chains",
    "calculate_click_depth",
    "analyze_internal_linking"
]
