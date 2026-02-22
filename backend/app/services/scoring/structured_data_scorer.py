"""StructuredDataScorer -- evaluates structured data quality for AI readiness.

Checks 13 criteria covering schema.org presence and completeness, JSON-LD
validity, structured data coverage breadth, sameAs entity links, and
llms.txt/llms-full.txt presence.

Research backing:
- JSON-LD is 2.3-2.5x more likely in AI Overviews (BrightEdge)
- FAQPage schema gives +28% AI citations (Frase.io), 3.2x citation rate
- sameAs links strengthen entity resolution for Knowledge Graph
- llms.txt adopted by 844K+ sites (growing standard)
"""

import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.services.scoring.base_scorer import BaseScorer, ScoringCriterionResult

# Schema type tier classification
SCHEMA_TIERS: dict[str, list[str]] = {
    "Foundation": ["Organization", "WebSite", "BreadcrumbList", "WebPage"],
    "Content": [
        "Article",
        "BlogPosting",
        "FAQPage",
        "HowTo",
        "Product",
        "Offer",
        "Review",
    ],
    "Supplementary": [
        "Person",
        "ClaimReview",
        "Event",
        "VideoObject",
        "ImageObject",
    ],
}

# Required fields per schema type for completeness checking
SCHEMA_REQUIRED_FIELDS: dict[str, list[str]] = {
    "Organization": ["name", "url"],
    "FAQPage": ["mainEntity"],
    "Article": ["headline", "author", "datePublished"],
    "BlogPosting": ["headline", "author", "datePublished"],
    "HowTo": ["name", "step"],
    "Product": ["name"],
    "BreadcrumbList": ["itemListElement"],
    "Person": ["name"],
    "ClaimReview": ["claimReviewed", "reviewRating"],
}

# Authoritative platforms for sameAs link validation
KNOWN_PLATFORMS: dict[str, str] = {
    "linkedin.com": "LinkedIn",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "facebook.com": "Facebook",
    "wikipedia.org": "Wikipedia",
    "wikidata.org": "Wikidata",
    "github.com": "GitHub",
    "youtube.com": "YouTube",
    "g2.com": "G2",
    "trustpilot.com": "Trustpilot",
    "crunchbase.com": "Crunchbase",
}


class StructuredDataScorer(BaseScorer):
    """Scores structured data quality across 13 criteria (SD1-SD13).

    Evaluates schema.org types, JSON-LD validity, coverage breadth,
    entity linking (sameAs), and AI-specific files (llms.txt).
    """

    async def score_page(self, page_data: dict) -> list[ScoringCriterionResult]:
        """Score a single page against all 13 structured data criteria.

        Args:
            page_data: Dict containing crawl results. Expected keys:
                - url: Page URL
                - domain: Site domain
                - main_content: HTML content (used for JSON-LD validation)
                - schema_org: List of JSON-LD objects (from CrawlerService extruct)

        Returns:
            List of 13 ScoringCriterionResult instances (SD1-SD13).
        """
        schemas = page_data.get("schema_org", [])
        html = page_data.get("main_content", "")
        domain = page_data.get("domain", "")

        # Flatten any @graph-wrapped schemas for uniform access
        flat_schemas = self._flatten_schemas(schemas)

        # Run all 13 criteria
        results: list[ScoringCriterionResult] = []

        # SD1-SD6: Schema type presence checks
        results.append(self._check_organization(flat_schemas))
        results.append(self._check_same_as(flat_schemas))
        results.append(self._check_faqpage(flat_schemas))
        results.append(self._check_article(flat_schemas))
        results.append(self._check_howto(flat_schemas))
        results.append(self._check_breadcrumb(flat_schemas))

        # SD7: JSON-LD syntax validation
        results.append(self._check_jsonld_validity(html))

        # SD8-SD10: Additional schema type checks
        results.append(self._check_product(flat_schemas))
        results.append(self._check_person(flat_schemas))
        results.append(self._check_claim_review(flat_schemas))

        # SD11: Coverage breadth
        results.append(self._check_coverage(flat_schemas))

        # SD12-SD13: llms.txt files (async)
        results.append(await self._check_llms_txt(domain))
        results.append(await self._check_llms_full_txt(domain))

        return results

    # ------------------------------------------------------------------ #
    # SD1: Organization schema
    # ------------------------------------------------------------------ #

    def _check_organization(
        self, schemas: list[dict]
    ) -> ScoringCriterionResult:
        """SD1: Check for Organization or LocalBusiness schema."""
        found = self._find_schemas_by_type(
            schemas, ["Organization", "LocalBusiness"]
        )

        if found:
            item = found[0]
            schema_type = self._get_type(item)
            return ScoringCriterionResult(
                criterion_id="SD1",
                criterion_name="Organization schema",
                score=100,
                is_binary=True,
                human_summary=(
                    f"Organization schema found -- AI can identify your brand entity"
                ),
                technical_detail=(
                    f"Found {schema_type} schema with name "
                    f"'{item.get('name', 'N/A')}'"
                ),
                evidence={
                    "found": True,
                    "type": schema_type,
                    "name": item.get("name"),
                    "url": item.get("url"),
                },
            )

        return ScoringCriterionResult(
            criterion_id="SD1",
            criterion_name="Organization schema",
            score=0,
            is_binary=True,
            human_summary=(
                "No Organization schema -- AI may not recognize your brand"
            ),
            technical_detail="No Organization or LocalBusiness schema found",
            evidence={"found": False},
        )

    # ------------------------------------------------------------------ #
    # SD2: sameAs links
    # ------------------------------------------------------------------ #

    def _check_same_as(self, schemas: list[dict]) -> ScoringCriterionResult:
        """SD2: Count sameAs links to authoritative platforms."""
        org_schemas = self._find_schemas_by_type(
            schemas, ["Organization", "LocalBusiness"]
        )

        platforms_found: list[str] = []
        same_as_urls: list[str] = []

        for org in org_schemas:
            same_as = org.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            if not isinstance(same_as, list):
                continue

            for url in same_as:
                if not isinstance(url, str):
                    continue
                same_as_urls.append(url)
                for domain_pattern, platform_name in KNOWN_PLATFORMS.items():
                    if domain_pattern in url.lower():
                        if platform_name not in platforms_found:
                            platforms_found.append(platform_name)

        count = len(platforms_found)
        all_platform_names = list(set(KNOWN_PLATFORMS.values()))
        platforms_missing = [
            p for p in all_platform_names if p not in platforms_found
        ]

        if count == 0:
            score = 0
            strength = "No"
        elif count <= 2:
            score = 40
            strength = "Weak"
        elif count <= 4:
            score = 60
            strength = "Moderate"
        elif count <= 6:
            score = 80
            strength = "Strong"
        else:
            score = 100
            strength = "Strong"

        return ScoringCriterionResult(
            criterion_id="SD2",
            criterion_name="sameAs entity links",
            score=score,
            is_binary=False,
            human_summary=(
                f"{count} platform links -- "
                f"{strength} multi-platform entity signal"
            ),
            technical_detail=(
                f"Found {count} authoritative platform links in sameAs: "
                f"{', '.join(platforms_found) if platforms_found else 'none'}"
            ),
            evidence={
                "count": count,
                "platforms_found": platforms_found,
                "platforms_missing": platforms_missing,
            },
        )

    # ------------------------------------------------------------------ #
    # SD3: FAQPage schema
    # ------------------------------------------------------------------ #

    def _check_faqpage(self, schemas: list[dict]) -> ScoringCriterionResult:
        """SD3: Check for FAQPage schema with Q&A pairs."""
        found = self._find_schemas_by_type(schemas, ["FAQPage"])

        if not found:
            return ScoringCriterionResult(
                criterion_id="SD3",
                criterion_name="FAQPage schema",
                score=0,
                is_binary=True,
                human_summary=(
                    "No FAQPage schema -- missing highest-impact "
                    "structured data for AI citations"
                ),
                technical_detail="No FAQPage schema found on page",
                evidence={"found": False, "question_count": 0},
            )

        faq = found[0]
        main_entity = faq.get("mainEntity", [])
        if isinstance(main_entity, dict):
            main_entity = [main_entity]
        if not isinstance(main_entity, list):
            main_entity = []

        # Count Question/Answer pairs
        questions: list[str] = []
        for item in main_entity:
            if isinstance(item, dict):
                item_type = self._get_type(item)
                if item_type == "Question":
                    q_name = item.get("name", item.get("text", ""))
                    if q_name:
                        questions.append(str(q_name))

        question_count = len(questions)
        questions_preview = questions[:5]  # Show up to 5

        if question_count >= 3:
            score = 100
        elif question_count >= 1:
            score = 70
        else:
            score = 0

        return ScoringCriterionResult(
            criterion_id="SD3",
            criterion_name="FAQPage schema",
            score=score,
            is_binary=True,
            human_summary=(
                f"FAQPage schema with {question_count} Q&A pairs -- "
                f"3.2x higher AI citation rate (BrightEdge)"
                if question_count > 0
                else "FAQPage schema found but no valid Q&A pairs"
            ),
            technical_detail=(
                f"FAQPage with {question_count} Question entities"
            ),
            evidence={
                "found": True,
                "question_count": question_count,
                "questions_preview": questions_preview,
            },
        )

    # ------------------------------------------------------------------ #
    # SD4: Article/BlogPosting schema
    # ------------------------------------------------------------------ #

    def _check_article(self, schemas: list[dict]) -> ScoringCriterionResult:
        """SD4: Check for Article, BlogPosting, NewsArticle, or TechArticle."""
        article_types = ["Article", "BlogPosting", "NewsArticle", "TechArticle"]
        found = self._find_schemas_by_type(schemas, article_types)

        if found:
            item = found[0]
            schema_type = self._get_type(item)
            has_author = bool(item.get("author"))
            has_date = bool(item.get("datePublished"))

            return ScoringCriterionResult(
                criterion_id="SD4",
                criterion_name="Article schema",
                score=100,
                is_binary=True,
                human_summary=(
                    f"{schema_type} schema found -- "
                    f"E-E-A-T signals (author, dates)"
                ),
                technical_detail=(
                    f"Found {schema_type} with "
                    f"author={'yes' if has_author else 'no'}, "
                    f"datePublished={'yes' if has_date else 'no'}"
                ),
                evidence={
                    "found": True,
                    "type": schema_type,
                    "has_author": has_author,
                    "has_date": has_date,
                },
            )

        return ScoringCriterionResult(
            criterion_id="SD4",
            criterion_name="Article schema",
            score=0,
            is_binary=True,
            human_summary="No Article schema",
            technical_detail="No Article/BlogPosting/NewsArticle/TechArticle found",
            evidence={"found": False},
        )

    # ------------------------------------------------------------------ #
    # SD5: HowTo schema
    # ------------------------------------------------------------------ #

    def _check_howto(self, schemas: list[dict]) -> ScoringCriterionResult:
        """SD5: Check for HowTo schema with steps."""
        found = self._find_schemas_by_type(schemas, ["HowTo"])

        if not found:
            return ScoringCriterionResult(
                criterion_id="SD5",
                criterion_name="HowTo schema",
                score=0,
                is_binary=True,
                human_summary="No HowTo schema",
                technical_detail="No HowTo schema found on page",
                evidence={"found": False},
            )

        howto = found[0]
        steps = howto.get("step", [])
        if isinstance(steps, dict):
            steps = [steps]
        if not isinstance(steps, list):
            steps = []

        step_count = len(steps)

        if step_count > 0:
            score = 100
            summary = (
                f"HowTo schema with {step_count} steps -- "
                f"AI can extract step-by-step instructions"
            )
        else:
            score = 50
            summary = "HowTo schema found but no steps defined"

        return ScoringCriterionResult(
            criterion_id="SD5",
            criterion_name="HowTo schema",
            score=score,
            is_binary=True,
            human_summary=summary,
            technical_detail=f"HowTo with {step_count} step entries",
            evidence={
                "found": True,
                "step_count": step_count,
            },
        )

    # ------------------------------------------------------------------ #
    # SD6: BreadcrumbList schema
    # ------------------------------------------------------------------ #

    def _check_breadcrumb(self, schemas: list[dict]) -> ScoringCriterionResult:
        """SD6: Check for BreadcrumbList schema."""
        found = self._find_schemas_by_type(schemas, ["BreadcrumbList"])

        if found:
            item = found[0]
            items = item.get("itemListElement", [])
            if isinstance(items, dict):
                items = [items]
            item_count = len(items) if isinstance(items, list) else 0

            if item_count > 0:
                return ScoringCriterionResult(
                    criterion_id="SD6",
                    criterion_name="BreadcrumbList schema",
                    score=100,
                    is_binary=True,
                    human_summary=(
                        "BreadcrumbList schema found -- "
                        "site structure is clear to AI"
                    ),
                    technical_detail=(
                        f"BreadcrumbList with {item_count} items"
                    ),
                    evidence={"found": True, "item_count": item_count},
                )

        return ScoringCriterionResult(
            criterion_id="SD6",
            criterion_name="BreadcrumbList schema",
            score=0,
            is_binary=True,
            human_summary="No BreadcrumbList schema",
            technical_detail="No BreadcrumbList schema found on page",
            evidence={"found": False},
        )

    # ------------------------------------------------------------------ #
    # SD7: JSON-LD validation
    # ------------------------------------------------------------------ #

    def _check_jsonld_validity(self, html: str) -> ScoringCriterionResult:
        """SD7: Validate JSON-LD syntax in HTML script tags."""
        soup = BeautifulSoup(html, "html.parser")
        ld_scripts = soup.find_all("script", {"type": "application/ld+json"})

        if not ld_scripts:
            return ScoringCriterionResult(
                criterion_id="SD7",
                criterion_name="JSON-LD validation",
                score=0,
                is_binary=False,
                human_summary="0/0 JSON-LD blocks valid -- No structured data",
                technical_detail="No <script type='application/ld+json'> tags found",
                evidence={
                    "total_blocks": 0,
                    "valid_blocks": 0,
                    "invalid_blocks": 0,
                    "errors": [],
                },
            )

        total = len(ld_scripts)
        valid = 0
        errors: list[str] = []

        for i, script in enumerate(ld_scripts):
            content = script.string or ""
            try:
                parsed = json.loads(content)
                if not isinstance(parsed, (dict, list)):
                    errors.append(f"Block {i + 1}: not a JSON object or array")
                    continue

                # Check for common issues
                items = [parsed] if isinstance(parsed, dict) else parsed
                for item in items:
                    if isinstance(item, dict):
                        if not item.get("@context"):
                            errors.append(
                                f"Block {i + 1}: missing @context"
                            )
                        if not item.get("@type"):
                            errors.append(
                                f"Block {i + 1}: missing @type"
                            )
                valid += 1
            except json.JSONDecodeError as e:
                errors.append(f"Block {i + 1}: invalid JSON -- {e}")

        invalid = total - valid

        if valid == total and total > 0:
            score = 100
            quality = "All valid"
        elif valid > 0:
            score = 50
            quality = "Some errors"
        else:
            score = 0
            quality = "All invalid"

        return ScoringCriterionResult(
            criterion_id="SD7",
            criterion_name="JSON-LD validation",
            score=score,
            is_binary=False,
            human_summary=(
                f"{valid}/{total} JSON-LD blocks valid -- {quality}"
            ),
            technical_detail=(
                f"{valid} valid, {invalid} invalid out of {total} blocks. "
                + (f"Issues: {'; '.join(errors[:5])}" if errors else "No issues")
            ),
            evidence={
                "total_blocks": total,
                "valid_blocks": valid,
                "invalid_blocks": invalid,
                "errors": errors[:10],
            },
        )

    # ------------------------------------------------------------------ #
    # SD8: Product/Offer schema
    # ------------------------------------------------------------------ #

    def _check_product(self, schemas: list[dict]) -> ScoringCriterionResult:
        """SD8: Check for Product, Offer, SoftwareApplication, or Service."""
        product_types = ["Product", "Offer", "SoftwareApplication", "Service"]
        found = self._find_schemas_by_type(schemas, product_types)

        if found:
            item = found[0]
            schema_type = self._get_type(item)
            has_price = bool(
                item.get("price")
                or item.get("offers", {}).get("price")
                if isinstance(item.get("offers"), dict)
                else item.get("price")
            )
            has_name = bool(item.get("name"))

            return ScoringCriterionResult(
                criterion_id="SD8",
                criterion_name="Product/Offer schema",
                score=100,
                is_binary=True,
                human_summary=f"Product schema found",
                technical_detail=f"Found {schema_type} schema",
                evidence={
                    "found": True,
                    "type": schema_type,
                    "has_price": has_price,
                    "has_name": has_name,
                },
            )

        return ScoringCriterionResult(
            criterion_id="SD8",
            criterion_name="Product/Offer schema",
            score=0,
            is_binary=True,
            human_summary=(
                "No Product/Offer schema "
                "(may not be relevant for this page type)"
            ),
            technical_detail="No Product/Offer/SoftwareApplication/Service found",
            evidence={"found": False},
        )

    # ------------------------------------------------------------------ #
    # SD9: Person schema
    # ------------------------------------------------------------------ #

    def _check_person(self, schemas: list[dict]) -> ScoringCriterionResult:
        """SD9: Check for Person schema or author info in Article schemas."""
        # First check for standalone Person schema
        person_schemas = self._find_schemas_by_type(schemas, ["Person"])

        if person_schemas:
            person = person_schemas[0]
            name = person.get("name", "Unknown")
            has_job_title = bool(person.get("jobTitle"))
            has_affiliation = bool(person.get("affiliation"))
            has_same_as = bool(person.get("sameAs"))
            has_credentials = has_job_title or has_affiliation or has_same_as

            if has_credentials:
                score = 100
                summary = (
                    f"Author identified as {name} with credentials -- "
                    f"strong E-E-A-T signal"
                )
            else:
                score = 60
                summary = (
                    f"Person schema for {name} but no credentials "
                    f"(jobTitle, affiliation, sameAs)"
                )

            return ScoringCriterionResult(
                criterion_id="SD9",
                criterion_name="Person/Author schema",
                score=score,
                is_binary=False,
                human_summary=summary,
                technical_detail=(
                    f"Person '{name}': jobTitle={'yes' if has_job_title else 'no'}, "
                    f"affiliation={'yes' if has_affiliation else 'no'}, "
                    f"sameAs={'yes' if has_same_as else 'no'}"
                ),
                evidence={
                    "found": True,
                    "type": "Person",
                    "name": name,
                    "has_job_title": has_job_title,
                    "has_affiliation": has_affiliation,
                    "has_same_as": has_same_as,
                },
            )

        # Check for inline author in Article schemas
        article_types = ["Article", "BlogPosting", "NewsArticle", "TechArticle"]
        articles = self._find_schemas_by_type(schemas, article_types)

        for article in articles:
            author = article.get("author")
            if not author:
                continue

            # Author can be a dict (Person) or string
            if isinstance(author, dict):
                author_type = self._get_type(author)
                author_name = author.get("name", "Unknown")
                has_job_title = bool(author.get("jobTitle"))
                has_affiliation = bool(author.get("affiliation"))
                has_same_as = bool(author.get("sameAs"))
                has_credentials = has_job_title or has_affiliation or has_same_as

                if has_credentials:
                    score = 100
                    summary = (
                        f"Author identified as {author_name} with "
                        f"credentials -- strong E-E-A-T signal"
                    )
                else:
                    score = 60
                    summary = (
                        f"Author {author_name} in {self._get_type(article)} "
                        f"but no credentials"
                    )

                return ScoringCriterionResult(
                    criterion_id="SD9",
                    criterion_name="Person/Author schema",
                    score=score,
                    is_binary=False,
                    human_summary=summary,
                    technical_detail=(
                        f"Author '{author_name}' (inline in "
                        f"{self._get_type(article)})"
                    ),
                    evidence={
                        "found": True,
                        "type": "inline_author",
                        "name": author_name,
                        "has_job_title": has_job_title,
                        "has_affiliation": has_affiliation,
                        "has_same_as": has_same_as,
                    },
                )

            if isinstance(author, str):
                return ScoringCriterionResult(
                    criterion_id="SD9",
                    criterion_name="Person/Author schema",
                    score=30,
                    is_binary=False,
                    human_summary=(
                        f"Author name '{author}' found but as text only -- "
                        f"no structured Person schema"
                    ),
                    technical_detail=(
                        f"Author '{author}' is a plain string in "
                        f"{self._get_type(article)}, not a Person object"
                    ),
                    evidence={
                        "found": True,
                        "type": "text_only",
                        "name": author,
                    },
                )

            # Author is a list
            if isinstance(author, list) and author:
                first = author[0]
                if isinstance(first, dict):
                    author_name = first.get("name", "Unknown")
                    return ScoringCriterionResult(
                        criterion_id="SD9",
                        criterion_name="Person/Author schema",
                        score=60,
                        is_binary=False,
                        human_summary=(
                            f"Author {author_name} found in list"
                        ),
                        technical_detail=(
                            f"Author list with {len(author)} entries"
                        ),
                        evidence={
                            "found": True,
                            "type": "inline_author",
                            "name": author_name,
                        },
                    )

        return ScoringCriterionResult(
            criterion_id="SD9",
            criterion_name="Person/Author schema",
            score=0,
            is_binary=False,
            human_summary="No author information found",
            technical_detail="No Person schema or author field in Article schemas",
            evidence={"found": False},
        )

    # ------------------------------------------------------------------ #
    # SD10: ClaimReview schema
    # ------------------------------------------------------------------ #

    def _check_claim_review(
        self, schemas: list[dict]
    ) -> ScoringCriterionResult:
        """SD10: Check for ClaimReview schema (fact-checking content)."""
        found = self._find_schemas_by_type(schemas, ["ClaimReview"])

        if found:
            item = found[0]
            return ScoringCriterionResult(
                criterion_id="SD10",
                criterion_name="ClaimReview schema",
                score=100,
                is_binary=True,
                human_summary="ClaimReview schema found -- fact-checking signals",
                technical_detail=(
                    f"ClaimReview for: "
                    f"{item.get('claimReviewed', 'N/A')}"
                ),
                evidence={
                    "found": True,
                    "claim": item.get("claimReviewed"),
                },
            )

        return ScoringCriterionResult(
            criterion_id="SD10",
            criterion_name="ClaimReview schema",
            score=0,
            is_binary=True,
            human_summary="No ClaimReview schema",
            technical_detail=(
                "No ClaimReview found (only relevant for fact-checking content)"
            ),
            evidence={"found": False},
        )

    # ------------------------------------------------------------------ #
    # SD11: Structured data coverage
    # ------------------------------------------------------------------ #

    def _check_coverage(self, schemas: list[dict]) -> ScoringCriterionResult:
        """SD11: Evaluate breadth of schema type usage."""
        types_found: set[str] = set()
        tiers_represented: set[str] = set()

        # Build a flat lookup of type -> tier
        type_to_tier: dict[str, str] = {}
        for tier, types in SCHEMA_TIERS.items():
            for t in types:
                type_to_tier[t] = tier

        for schema in schemas:
            schema_type = self._get_type(schema)
            if schema_type:
                types_found.add(schema_type)
                tier = type_to_tier.get(schema_type)
                if tier:
                    tiers_represented.add(tier)

        count = len(types_found)
        tier_count = len(tiers_represented)

        if count == 0:
            score = 0
            quality = "No"
        elif count == 1:
            score = 30
            quality = "Minimal"
        elif count <= 3:
            score = 50
            quality = "Basic"
        elif count <= 5:
            score = 70
            quality = "Good"
        elif (
            count >= 6
            and "Foundation" in tiers_represented
            and "Content" in tiers_represented
        ):
            score = 100
            quality = "Comprehensive"
        else:
            score = 80
            quality = "Good"

        tier_names = sorted(tiers_represented) if tiers_represented else ["none"]

        return ScoringCriterionResult(
            criterion_id="SD11",
            criterion_name="Structured data coverage",
            score=score,
            is_binary=False,
            human_summary=(
                f"{count} schema types across {tier_count} tiers -- "
                f"{quality} structured data"
            ),
            technical_detail=(
                f"Types: {', '.join(sorted(types_found)) if types_found else 'none'}. "
                f"Tiers: {', '.join(tier_names)}"
            ),
            evidence={
                "total_types": count,
                "types_found": sorted(types_found),
                "tiers_represented": sorted(tiers_represented),
            },
        )

    # ------------------------------------------------------------------ #
    # SD12: llms.txt presence
    # ------------------------------------------------------------------ #

    async def _check_llms_txt(self, domain: str) -> ScoringCriterionResult:
        """SD12: Check for llms.txt at site root."""
        if not domain:
            return self._not_checked("SD12", "llms.txt presence", "No domain available")

        url = f"https://{domain}/llms.txt"
        try:
            async with httpx.AsyncClient(
                timeout=5.0, follow_redirects=True
            ) as client:
                resp = await client.get(url)

            if resp.status_code == 200:
                content = resp.text
                content_type = resp.headers.get("content-type", "")

                # Check if it's actually text (not HTML error page)
                is_html = "<html" in content[:500].lower()
                if is_html:
                    return ScoringCriterionResult(
                        criterion_id="SD12",
                        criterion_name="llms.txt presence",
                        score=50,
                        is_binary=True,
                        human_summary=(
                            "llms.txt found but contains HTML -- malformed"
                        ),
                        technical_detail="llms.txt returned HTML instead of text",
                        evidence={
                            "found": True,
                            "status_code": 200,
                            "has_title": False,
                            "line_count": 0,
                            "malformed": True,
                        },
                    )

                lines = content.strip().splitlines()
                has_title = bool(lines and lines[0].strip().startswith("#"))
                line_count = len(lines)

                if has_title:
                    score = 100
                    summary = (
                        "llms.txt found -- low-cost AI accessibility signal "
                        "(844K+ sites adopted)"
                    )
                else:
                    score = 50
                    summary = "llms.txt found but no title line (should start with #)"

                return ScoringCriterionResult(
                    criterion_id="SD12",
                    criterion_name="llms.txt presence",
                    score=score,
                    is_binary=True,
                    human_summary=summary,
                    technical_detail=f"llms.txt: {line_count} lines, title={'yes' if has_title else 'no'}",
                    evidence={
                        "found": True,
                        "status_code": 200,
                        "has_title": has_title,
                        "line_count": line_count,
                    },
                )

            return ScoringCriterionResult(
                criterion_id="SD12",
                criterion_name="llms.txt presence",
                score=0,
                is_binary=True,
                human_summary="No llms.txt -- optional but growing standard",
                technical_detail=f"llms.txt returned HTTP {resp.status_code}",
                evidence={
                    "found": False,
                    "status_code": resp.status_code,
                },
            )

        except Exception as e:
            logger.debug("llms.txt check failed for {}: {}", domain, str(e))
            return ScoringCriterionResult(
                criterion_id="SD12",
                criterion_name="llms.txt presence",
                score=0,
                is_binary=True,
                human_summary="No llms.txt -- optional but growing standard",
                technical_detail=f"llms.txt fetch failed: {str(e)[:100]}",
                evidence={"found": False, "error": str(e)[:200]},
            )

    # ------------------------------------------------------------------ #
    # SD13: llms-full.txt presence
    # ------------------------------------------------------------------ #

    async def _check_llms_full_txt(
        self, domain: str
    ) -> ScoringCriterionResult:
        """SD13: Check for llms-full.txt at site root."""
        if not domain:
            return self._not_checked(
                "SD13", "llms-full.txt presence", "No domain available"
            )

        url = f"https://{domain}/llms-full.txt"
        try:
            async with httpx.AsyncClient(
                timeout=5.0, follow_redirects=True
            ) as client:
                resp = await client.get(url)

            if resp.status_code == 200:
                content_length = len(resp.text)
                is_html = "<html" in resp.text[:500].lower()

                if is_html:
                    return ScoringCriterionResult(
                        criterion_id="SD13",
                        criterion_name="llms-full.txt presence",
                        score=0,
                        is_binary=True,
                        human_summary="No llms-full.txt (URL returned HTML)",
                        technical_detail="llms-full.txt returned HTML, not text",
                        evidence={
                            "found": False,
                            "status_code": 200,
                            "content_length": content_length,
                            "malformed": True,
                        },
                    )

                return ScoringCriterionResult(
                    criterion_id="SD13",
                    criterion_name="llms-full.txt presence",
                    score=100,
                    is_binary=True,
                    human_summary=(
                        "llms-full.txt found -- full content accessible "
                        "to AI tools"
                    ),
                    technical_detail=(
                        f"llms-full.txt: {content_length} bytes"
                    ),
                    evidence={
                        "found": True,
                        "status_code": 200,
                        "content_length": content_length,
                    },
                )

            return ScoringCriterionResult(
                criterion_id="SD13",
                criterion_name="llms-full.txt presence",
                score=0,
                is_binary=True,
                human_summary="No llms-full.txt",
                technical_detail=f"llms-full.txt returned HTTP {resp.status_code}",
                evidence={
                    "found": False,
                    "status_code": resp.status_code,
                },
            )

        except Exception as e:
            logger.debug(
                "llms-full.txt check failed for {}: {}", domain, str(e)
            )
            return ScoringCriterionResult(
                criterion_id="SD13",
                criterion_name="llms-full.txt presence",
                score=0,
                is_binary=True,
                human_summary="No llms-full.txt",
                technical_detail=f"llms-full.txt fetch failed: {str(e)[:100]}",
                evidence={"found": False, "error": str(e)[:200]},
            )

    # ------------------------------------------------------------------ #
    # Helper methods
    # ------------------------------------------------------------------ #

    def _find_schemas_by_type(
        self, schemas: list[dict], types: list[str]
    ) -> list[dict]:
        """Search schema list for matching @type values.

        Handles both flat JSON-LD objects and @graph-wrapped arrays.

        Args:
            schemas: List of parsed JSON-LD objects.
            types: List of @type values to match (case-sensitive).

        Returns:
            List of matching schema objects.
        """
        matches: list[dict] = []
        for schema in schemas:
            if not isinstance(schema, dict):
                continue

            schema_type = self._get_type(schema)
            if schema_type in types:
                matches.append(schema)

            # Check inside @graph
            graph = schema.get("@graph", [])
            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict):
                        item_type = self._get_type(item)
                        if item_type in types:
                            matches.append(item)

        return matches

    def _flatten_schemas(self, schemas: list[dict]) -> list[dict]:
        """Flatten @graph-wrapped schemas into a flat list.

        Ensures both top-level schemas and @graph children are in the list
        for uniform processing by coverage and type-checking methods.

        Args:
            schemas: Raw list of JSON-LD objects from crawl_data.

        Returns:
            Flat list of all schema objects (top-level + @graph children).
        """
        flat: list[dict] = []
        for schema in schemas:
            if not isinstance(schema, dict):
                continue
            flat.append(schema)
            graph = schema.get("@graph", [])
            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict):
                        flat.append(item)
        return flat

    def _get_type(self, schema: dict) -> str:
        """Extract @type as a string from a schema object.

        Handles @type as string or list (takes first element).

        Args:
            schema: JSON-LD object.

        Returns:
            Type string, or empty string if not found.
        """
        raw_type = schema.get("@type", "")
        if isinstance(raw_type, list):
            return raw_type[0] if raw_type else ""
        return str(raw_type) if raw_type else ""
