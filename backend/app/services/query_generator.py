"""QueryGeneratorService -- generates categorized AI brand visibility queries from crawl data.

Uses LiteLLM with Pydantic structured output to produce 10-15 queries across 5 categories:
industry, brand_direct, comparison, problem, recommendation. These queries test how AI
engines perceive and recommend the brand.
"""

import re
from typing import Literal

from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings


class GeneratedQuery(BaseModel):
    """A single categorized query for AI brand visibility audit."""

    category: Literal[
        "industry", "brand_direct", "comparison", "problem", "recommendation"
    ]
    query_text: str = Field(
        description="Natural language query a user would ask an AI engine"
    )
    intent: str = Field(
        description="What this query tests about brand visibility"
    )


class GeneratedQuerySet(BaseModel):
    """Set of generated queries from LLM analysis of crawl data."""

    queries: list[GeneratedQuery] = Field(
        min_length=8,  # Allow some flexibility (target 10-15, minimum 8)
        max_length=15,
        description="10-15 categorized queries for AI brand visibility audit",
    )


SYSTEM_PROMPT = """You are an AI brand visibility analyst. Given crawled website data, \
generate 10-15 queries that real users would ask AI engines (ChatGPT, Claude, Perplexity) \
about this brand's domain. Queries should test whether AI engines know about, recommend, \
or mention this brand.

Categories (generate 2-3 queries per category for 10-15 total):
- industry: General industry questions where the brand should appear (e.g., "best X in Y city")
- brand_direct: Direct questions about the brand (e.g., "what is [brand] known for")
- comparison: Competitive comparison queries (e.g., "X vs Y vs Z")
- problem: Problem-solving queries where the brand's products/services are solutions
- recommendation: Recommendation-seeking queries (e.g., "recommend a good X for Y")

Rules:
- Queries must sound like natural user questions, not keyword strings
- Include the brand name ONLY in brand_direct queries
- Industry, comparison, problem, and recommendation queries should be phrased so the brand \
COULD appear in the answer without being explicitly asked about
- Cover diverse aspects of the brand's offerings based on the crawled content
- Each query should test a different aspect of brand visibility
- Use specific details from the crawled data to make queries relevant and realistic"""


class QueryGeneratorService:
    """Generates categorized AI brand visibility queries from crawl data using LiteLLM."""

    def generate(self, crawl_data: dict, brand_name: str) -> GeneratedQuerySet:
        """Generate categorized queries from crawl data.

        Args:
            crawl_data: Dictionary from CrawlResult.model_dump() with site signals.
            brand_name: Extracted brand name for the site.

        Returns:
            GeneratedQuerySet with 8-15 categorized queries.

        Raises:
            RuntimeError: If the LLM call fails.
        """
        user_prompt = self._build_prompt(crawl_data, brand_name)

        try:
            # Resolve API key based on the model provider
            api_key = self._get_api_key_for_model(settings.QUERY_GEN_MODEL)

            response = completion(
                model=settings.QUERY_GEN_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=GeneratedQuerySet,
                temperature=settings.QUERY_GEN_TEMPERATURE,
                api_key=api_key,
            )

            result = GeneratedQuerySet.model_validate_json(
                response.choices[0].message.content
            )

            # Log query count and category distribution
            category_counts = {}
            for q in result.queries:
                category_counts[q.category] = category_counts.get(q.category, 0) + 1
            logger.info(
                "Generated {} queries for brand '{}': {}",
                len(result.queries),
                brand_name,
                category_counts,
            )

            if len(result.queries) < 10:
                logger.warning(
                    "Generated only {} queries (target 10-15) for brand '{}'. "
                    "Not retrying to avoid extra cost.",
                    len(result.queries),
                    brand_name,
                )

            return result

        except Exception as e:
            logger.error(
                "LLM query generation failed for brand '{}': {}",
                brand_name,
                str(e),
            )
            raise RuntimeError(
                f"Query generation failed for brand '{brand_name}': {e}"
            ) from e

    @staticmethod
    def _get_api_key_for_model(model: str) -> str | None:
        """Resolve the API key for a LiteLLM model string."""
        model_lower = model.lower()
        if model_lower.startswith("gemini/"):
            return settings.GEMINI_API_KEY or None
        if model_lower.startswith("anthropic/") or "claude" in model_lower:
            return settings.ANTHROPIC_API_KEY or None
        if model_lower.startswith("perplexity/"):
            return settings.PERPLEXITYAI_API_KEY or None
        if model_lower.startswith("mistral/"):
            return settings.MISTRAL_API_KEY or None
        # Default to OpenAI
        return settings.OPENAI_API_KEY or None

    def _build_prompt(self, crawl_data: dict, brand_name: str) -> str:
        """Build a structured user prompt from crawl data for the LLM.

        Args:
            crawl_data: Dictionary with crawl signals (from CrawlResult).
            brand_name: Extracted brand name.

        Returns:
            Formatted prompt string with brand context.
        """
        sections = []

        sections.append(f"Brand Name: {brand_name}")
        sections.append(f"Domain: {crawl_data.get('domain', 'unknown')}")

        # Industry signals
        industry_signals = crawl_data.get("industry_signals", [])
        if industry_signals:
            sections.append(f"Industry Signals: {', '.join(industry_signals)}")

        # Page title and meta description
        title = crawl_data.get("title", "")
        if title:
            sections.append(f"Page Title: {title}")

        meta_desc = crawl_data.get("meta_description", "")
        if meta_desc:
            sections.append(f"Meta Description: {meta_desc}")

        # Schema.org types found
        schema_org = crawl_data.get("schema_org", [])
        if schema_org:
            schema_types = []
            for item in schema_org:
                if isinstance(item, dict):
                    schema_type = item.get("@type", "")
                    if isinstance(schema_type, list):
                        schema_types.extend(schema_type)
                    elif schema_type:
                        schema_types.append(schema_type)
            if schema_types:
                sections.append(f"Schema.org Types: {', '.join(schema_types)}")

            # Extract organization/business names from schema.org
            schema_names = []
            for item in schema_org:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    if name and isinstance(name, str):
                        schema_names.append(name)
            if schema_names:
                sections.append(f"Schema.org Names: {', '.join(schema_names[:5])}")

        # Open Graph data
        open_graph = crawl_data.get("open_graph", {})
        if open_graph:
            og_parts = []
            for key in ("og:title", "og:description", "og:type", "og:site_name"):
                value = open_graph.get(key, "")
                if value:
                    og_parts.append(f"  {key}: {value}")
            if og_parts:
                sections.append("Open Graph Data:\n" + "\n".join(og_parts))

        # Top keywords
        keywords = crawl_data.get("content_keywords", [])
        if keywords:
            sections.append(f"Top Keywords: {', '.join(keywords[:15])}")

        # Headings for context
        headings = crawl_data.get("headings", {})
        h1_list = headings.get("h1", [])
        h2_list = headings.get("h2", [])
        if h1_list:
            sections.append(f"H1 Headings: {'; '.join(h1_list[:5])}")
        if h2_list:
            sections.append(f"H2 Headings: {'; '.join(h2_list[:10])}")

        # Main content (truncated to configured limit)
        main_content = crawl_data.get("main_content", "")
        if main_content:
            words = main_content.split()
            max_words = settings.QUERY_GEN_MAX_CONTENT_WORDS
            if len(words) > max_words:
                words = words[:max_words]
            truncated_content = " ".join(words)
            sections.append(f"Main Content (excerpt):\n{truncated_content}")

        return "\n\n".join(sections)

    def extract_brand_name(self, crawl_data: dict) -> str:
        """Extract the brand name from crawl data using priority chain.

        Priority:
            1. schema.org Organization/LocalBusiness name
            2. og:site_name from Open Graph
            3. Title tag -- first segment before common separators
            4. Fallback: domain name

        Args:
            crawl_data: Dictionary from CrawlResult.model_dump().

        Returns:
            Extracted brand name string.
        """
        # Priority 1: schema.org Organization name
        schema_org = crawl_data.get("schema_org", [])
        for item in schema_org:
            if isinstance(item, dict):
                schema_type = item.get("@type", "")
                # Check for Organization-like types
                org_types = {
                    "Organization",
                    "LocalBusiness",
                    "Corporation",
                    "Company",
                    "Brand",
                }
                types_to_check = (
                    schema_type if isinstance(schema_type, list) else [schema_type]
                )
                for t in types_to_check:
                    if t in org_types:
                        name = item.get("name", "")
                        if name and isinstance(name, str):
                            return name.strip()

        # Priority 2: og:site_name from Open Graph
        open_graph = crawl_data.get("open_graph", {})
        og_site_name = open_graph.get("og:site_name", "")
        if og_site_name and isinstance(og_site_name, str):
            return og_site_name.strip()

        # Priority 3: Title tag -- first segment before common separators
        title = crawl_data.get("title", "")
        if title:
            # Split on common separators and take the first segment
            parts = re.split(r"\s*[\|\-:]\s*|\s*::\s*|\s*--\s*", title)
            if parts and parts[0].strip():
                return parts[0].strip()

        # Priority 4: Fallback to domain name
        domain = crawl_data.get("domain", "")
        if domain:
            # Remove www. prefix and TLD for cleaner brand name
            clean = domain.replace("www.", "")
            # Take the main domain part (before TLD)
            parts = clean.split(".")
            if len(parts) >= 2:
                return parts[0].capitalize()
            return clean.capitalize()

        return "Unknown Brand"
