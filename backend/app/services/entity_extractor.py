"""
Entity Extractor Service — Extract brands/entities from AI engine responses.

Extracts brand and product names from AI responses using spaCy NER, deduplicates
with rapidfuzz fuzzy matching, computes share-of-voice, and persists
DiscoveredCompetitor records.

Key design choices:
- spaCy NLP model loaded lazily (class-level cache) to avoid startup cost
- Full response text processed (not fragments) per GEO research findings
- Entities require at least 2 appearances to filter out noise
- Corporate suffixes stripped before fuzzy deduplication
- Generic terms blocklisted to avoid false positives
"""

import re
from decimal import Decimal

from loguru import logger
from rapidfuzz import fuzz
from rapidfuzz.fuzz import token_set_ratio
from sqlalchemy.orm import Session

from app.models.audit_query import AuditQuery
from app.models.competitor import DiscoveredCompetitor
from app.models.engine_response import EngineResponse


class EntityExtractorService:
    """Extracts brand/entity names and source citations from AI responses."""

    _nlp = None

    # Generic terms that NER may tag as ORG/PRODUCT but are not real entities
    GENERIC_BLOCKLIST = {
        "the", "this", "that", "these", "those", "it", "its",
        "their", "our", "your", "my", "service", "platform",
        "tool", "product", "company", "website", "app",
        "application", "software", "solution", "system",
    }

    # Corporate suffixes to strip before fuzzy comparison
    CORPORATE_SUFFIXES = re.compile(
        r"\s*\b(Inc\.?|LLC\.?|Ltd\.?|Co\.?|Corp\.?|Corporation|Incorporated|Limited)\s*$",
        re.IGNORECASE,
    )

    @classmethod
    def _get_nlp(cls):
        """Load spaCy model lazily with class-level cache."""
        if cls._nlp is None:
            import spacy
            cls._nlp = spacy.load("en_core_web_sm")
        return cls._nlp

    def extract_entities_from_response(self, response_text: str) -> list[dict]:
        """Run spaCy NER on full response text.

        Returns list of {text, label, start_char, end_char} for ORG and PRODUCT entities.
        Filters out entities shorter than 2 characters.
        """
        nlp = self._get_nlp()
        doc = nlp(response_text)

        entities = []
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT"):
                text = ent.text.strip()
                if len(text) < 2:
                    continue
                entities.append({
                    "text": text,
                    "label": ent.label_,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                })

        return entities

    def extract_citations(
        self, response_text: str, citations_meta: list[str] | None = None
    ) -> list[str]:
        """Extract source URLs from response text and metadata.

        Args:
            response_text: The AI engine response text.
            citations_meta: Perplexity citation URLs from API metadata (if available).

        Returns:
            Sorted deduplicated list of URLs.
        """
        urls = set()

        # Add Perplexity metadata citations
        if citations_meta:
            for url in citations_meta:
                if url:
                    urls.add(url.strip())

        # Regex: extract bare URLs from text
        url_pattern = re.compile(r'https?://[^\s\)\]\},\"\']+', re.IGNORECASE)
        for match in url_pattern.findall(response_text):
            # Strip trailing punctuation that may be part of sentence
            clean_url = match.rstrip(".,;:!?")
            urls.add(clean_url)

        # Markdown link extraction: [text](url)
        md_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
        for _, url in md_pattern.findall(response_text):
            urls.add(url.strip())

        return sorted(urls)

    def extract_all_entities_for_audit(
        self, db: Session, audit_id: str, user_brand_name: str
    ) -> list[dict]:
        """Extract entities and citations from all successful responses for an audit.

        Returns raw entity list: [{text, label, engine, query_id, citations}]
        """
        # Query all successful EngineResponse records via AuditQuery join
        responses = (
            db.query(EngineResponse)
            .join(AuditQuery, EngineResponse.audit_query_id == AuditQuery.id)
            .filter(AuditQuery.audit_id == audit_id)
            .filter(EngineResponse.error_message.is_(None))
            .all()
        )

        raw_entities = []
        for response in responses:
            # Extract entities from response text
            entities = self.extract_entities_from_response(response.response_text)

            # Extract citations (use stored citations as metadata if available)
            citations = self.extract_citations(
                response.response_text,
                citations_meta=response.citations if response.citations else None,
            )

            # Build raw entity records
            for ent in entities:
                raw_entities.append({
                    "text": ent["text"],
                    "label": ent["label"],
                    "engine": response.engine,
                    "query_id": str(response.audit_query_id),
                    "citations": citations,
                })

        logger.info(
            "Audit {}: extracted {} raw entities from {} responses",
            audit_id,
            len(raw_entities),
            len(responses),
        )
        return raw_entities

    def _strip_suffix(self, name: str) -> str:
        """Strip corporate suffixes for fuzzy comparison."""
        return self.CORPORATE_SUFFIXES.sub("", name).strip()

    def deduplicate_entities(
        self, raw_entities: list[dict], threshold: int = 85
    ) -> list[dict]:
        """Deduplicate entities using rapidfuzz fuzzy matching.

        Groups entities with token_set_ratio >= threshold after stripping
        corporate suffixes. Keeps the most frequent variant as canonical name.

        Filters out:
        - Generic blocklisted terms
        - Entities that appear in only 1 response (require at least 2)

        Returns sorted by mention_count descending:
            [{canonical_name, entity_type, mention_count,
              engines_mentioned_in: {engine: count},
              queries_mentioned_in: [query_ids]}]
        """
        if not raw_entities:
            return []

        # Group entities by fuzzy similarity
        groups: list[dict] = []  # each group: {variants: {name: count}, entities: [raw_ent, ...]}

        for ent in raw_entities:
            text = ent["text"]
            stripped = self._strip_suffix(text)

            # Skip blocklisted generic terms
            if stripped.lower() in self.GENERIC_BLOCKLIST:
                continue

            # Try to match to existing group
            matched = False
            for group in groups:
                for existing_name in group["variants"]:
                    existing_stripped = self._strip_suffix(existing_name)
                    score = token_set_ratio(
                        stripped.lower(), existing_stripped.lower()
                    )
                    if score >= threshold:
                        group["variants"][text] = group["variants"].get(text, 0) + 1
                        group["entities"].append(ent)
                        matched = True
                        break
                if matched:
                    break

            if not matched:
                groups.append({
                    "variants": {text: 1},
                    "entities": [ent],
                })

        # Build deduplicated list
        result = []
        for group in groups:
            entities = group["entities"]

            # Filter: require at least 2 appearances
            if len(entities) < 2:
                continue

            # Find most frequent variant as canonical name
            canonical_name = max(group["variants"], key=group["variants"].get)

            # Determine entity type (majority vote)
            type_counts: dict[str, int] = {}
            for ent in entities:
                type_counts[ent["label"]] = type_counts.get(ent["label"], 0) + 1
            entity_type = max(type_counts, key=type_counts.get)

            # Count per engine
            engines: dict[str, int] = {}
            for ent in entities:
                engines[ent["engine"]] = engines.get(ent["engine"], 0) + 1

            # Collect unique query IDs
            query_ids = sorted(set(ent["query_id"] for ent in entities))

            result.append({
                "canonical_name": canonical_name,
                "entity_type": entity_type,
                "mention_count": len(entities),
                "engines_mentioned_in": engines,
                "queries_mentioned_in": query_ids,
            })

        # Sort by mention_count descending
        result.sort(key=lambda x: x["mention_count"], reverse=True)
        return result

    def compute_share_of_voice(
        self, ranked_entities: list[dict], user_brand_name: str
    ) -> list[dict]:
        """Compute share-of-voice percentages and mark user brand.

        SOV = (entity_mentions / total_mentions_across_all_entities) * 100

        Args:
            ranked_entities: Output from deduplicate_entities.
            user_brand_name: The brand name of the audited site.

        Returns:
            Entities with share_of_voice and is_user_brand fields added.
        """
        total_mentions = sum(e["mention_count"] for e in ranked_entities)
        if total_mentions == 0:
            return ranked_entities

        for entity in ranked_entities:
            # Compute SOV
            sov = (entity["mention_count"] / total_mentions) * 100
            entity["share_of_voice"] = round(sov, 1)

            # Check if this is the user's brand
            entity["is_user_brand"] = (
                fuzz.ratio(
                    entity["canonical_name"].lower(),
                    user_brand_name.lower(),
                )
                > 90
            )

        # Sort by mention_count descending
        ranked_entities.sort(key=lambda x: x["mention_count"], reverse=True)
        return ranked_entities

    def discover_competitors_for_audit(
        self, db: Session, audit_id: str, user_brand_name: str
    ) -> list[DiscoveredCompetitor]:
        """Orchestration method: extract -> deduplicate -> SOV -> persist.

        Args:
            db: SQLAlchemy session.
            audit_id: The audit UUID.
            user_brand_name: The brand name of the audited site.

        Returns:
            List of DiscoveredCompetitor ORM objects.
        """
        # Extract all raw entities from AI responses
        raw_entities = self.extract_all_entities_for_audit(db, audit_id, user_brand_name)

        if not raw_entities:
            logger.info("Audit {}: no entities extracted from AI responses", audit_id)
            return []

        # Deduplicate
        deduped = self.deduplicate_entities(raw_entities)

        if not deduped:
            logger.info("Audit {}: no entities survived deduplication", audit_id)
            return []

        # Compute share of voice
        ranked = self.compute_share_of_voice(deduped, user_brand_name)

        # Persist to DB
        competitors = []
        for entity in ranked:
            competitor = DiscoveredCompetitor(
                audit_id=audit_id,
                entity_name=entity["canonical_name"],
                entity_type=entity["entity_type"],
                mention_count=entity["mention_count"],
                share_of_voice=Decimal(str(entity["share_of_voice"])),
                engines_mentioned_in=entity["engines_mentioned_in"],
                queries_mentioned_in=entity["queries_mentioned_in"],
                is_user_brand=entity.get("is_user_brand", False),
            )
            db.add(competitor)
            competitors.append(competitor)

        db.flush()

        logger.info(
            "Audit {}: persisted {} discovered competitors ({} user brand)",
            audit_id,
            len(competitors),
            sum(1 for c in competitors if c.is_user_brand),
        )
        return competitors
