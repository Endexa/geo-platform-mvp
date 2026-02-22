import re
from dataclasses import dataclass

from loguru import logger
from rapidfuzz import fuzz

from app.core.config import settings


# Common corporate suffixes to strip for variant generation
_CORPORATE_SUFFIXES = [
    "Inc.", "Inc", "LLC", "Ltd.", "Ltd", "Co.", "Co",
    "Corp.", "Corp", "Corporation", "Group", "Holdings",
]

_SUFFIX_PATTERN = re.compile(
    r"\s+(?:" + "|".join(re.escape(s) for s in _CORPORATE_SUFFIXES) + r")\s*$",
    re.IGNORECASE,
)


class MentionDetectorService:
    """Layered brand mention detection: exact regex + fuzzy RapidFuzz fallback.

    Detects brand name mentions in AI response text and extracts verbatim
    context quotes around each match.
    """

    def __init__(
        self,
        fuzzy_threshold: int | None = None,
        short_name_threshold: int | None = None,
        context_window_chars: int | None = None,
    ):
        self.fuzzy_threshold = fuzzy_threshold or settings.MENTION_FUZZY_THRESHOLD
        self.short_name_threshold = short_name_threshold or settings.MENTION_SHORT_NAME_THRESHOLD
        self.context_window_chars = context_window_chars or settings.MENTION_CONTEXT_WINDOW_CHARS

    def generate_brand_variants(self, brand_name: str) -> list[str]:
        """Generate brand name variants for matching.

        Produces lowercase, uppercase, suffix-stripped, abbreviation, and
        domain-style variants. The original brand_name is NOT included
        (it is matched separately in detect_mentions).
        """
        variants: set[str] = set()
        clean = brand_name.strip()

        if not clean:
            return []

        # Lowercase / uppercase forms
        variants.add(clean.lower())
        variants.add(clean.upper())

        # Without corporate suffixes
        stripped = _SUFFIX_PATTERN.sub("", clean).strip()
        if stripped and stripped != clean:
            variants.add(stripped)
            variants.add(stripped.lower())
            variants.add(stripped.upper())

        # Abbreviation for multi-word names (first letter of each word)
        words = stripped.split() if stripped else clean.split()
        if len(words) >= 2:
            abbrev = "".join(w[0] for w in words if w).upper()
            if len(abbrev) >= 2:
                variants.add(abbrev)

        # Domain-style (no spaces, lowered)
        domain_style = clean.replace(" ", "").lower()
        if domain_style != clean.lower():
            variants.add(domain_style)

        # Discard the original from the variant list
        variants.discard(clean)

        return sorted(variants)

    def detect_mentions(
        self,
        response_text: str,
        brand_name: str,
        brand_variants: list[str],
    ) -> list[dict]:
        """Two-pass brand mention detection.

        Pass 1: Exact regex matching with word boundaries.
        Pass 2: Fuzzy matching (only if no exact matches found).

        Returns list of mention dicts with keys:
            matched_text, match_type, confidence, char_offset, context_quote
        """
        if not response_text or not brand_name:
            return []

        is_short = len(brand_name.strip()) < 4
        if is_short:
            logger.warning(
                "Short brand name '{}' (< 4 chars) -- using stricter matching",
                brand_name,
            )

        # Pass 1: Exact regex matching
        exact_mentions = self._exact_pass(response_text, brand_name, brand_variants, is_short)

        if exact_mentions:
            logger.info(
                "Found {} exact match(es) for '{}'",
                len(exact_mentions),
                brand_name,
            )
            return self._deduplicate(exact_mentions)

        # Pass 2: Fuzzy matching (fallback)
        fuzzy_mentions = self._fuzzy_pass(response_text, brand_name, is_short)

        if fuzzy_mentions:
            logger.info(
                "Found {} fuzzy match(es) for '{}' (no exact matches)",
                len(fuzzy_mentions),
                brand_name,
            )
        else:
            logger.info("No mentions found for '{}'", brand_name)

        return self._deduplicate(fuzzy_mentions)

    def _exact_pass(
        self,
        text: str,
        brand_name: str,
        brand_variants: list[str],
        is_short: bool,
    ) -> list[dict]:
        """Pass 1: Exact regex matching with word boundaries."""
        mentions: list[dict] = []
        names_to_match = [brand_name] + brand_variants

        for name in names_to_match:
            if not name or not name.strip():
                continue

            # For short brand names, use case-sensitive matching to avoid false positives
            flags = 0 if (is_short or len(name.strip()) < 4) else re.IGNORECASE
            try:
                pattern = re.compile(r"\b" + re.escape(name) + r"\b", flags)
            except re.error:
                logger.warning("Invalid regex for brand name variant: '{}'", name)
                continue

            for match in pattern.finditer(text):
                context_quote = self._extract_context(text, match.start(), match.end())
                mentions.append({
                    "matched_text": match.group(),
                    "match_type": "exact",
                    "confidence": 100,
                    "char_offset": match.start(),
                    "context_quote": context_quote,
                })

        return mentions

    def _fuzzy_pass(
        self,
        text: str,
        brand_name: str,
        is_short: bool,
    ) -> list[dict]:
        """Pass 2: Fuzzy matching using RapidFuzz on sentences."""
        mentions: list[dict] = []
        threshold = self.short_name_threshold if is_short else self.fuzzy_threshold
        sentences = self._split_sentences(text)

        for sentence in sentences:
            sentence_stripped = sentence.strip()
            if not sentence_stripped:
                continue

            token_score = fuzz.token_set_ratio(brand_name.lower(), sentence_stripped.lower())
            if token_score < threshold:
                continue

            partial_score = fuzz.partial_ratio(brand_name.lower(), sentence_stripped.lower())
            if partial_score < threshold:
                continue

            confidence = min(token_score, partial_score)
            char_offset = text.find(sentence_stripped)
            if char_offset == -1:
                char_offset = 0

            mentions.append({
                "matched_text": sentence_stripped,
                "match_type": "fuzzy",
                "confidence": confidence,
                "char_offset": char_offset,
                "context_quote": sentence_stripped,
            })

        return mentions

    def _extract_context(self, text: str, match_start: int, match_end: int) -> str:
        """Extract verbatim quote around a match.

        Uses a character window (context_window_chars / 2 before and after),
        expands to sentence boundaries, and caps at 500 chars.
        """
        half_window = self.context_window_chars // 2

        # Initial window
        ctx_start = max(0, match_start - half_window)
        ctx_end = min(len(text), match_end + half_window)

        # Expand outward to sentence boundaries (look for .!?\n within 50 chars of edges)
        search_start = max(0, ctx_start - 50)
        boundary_region = text[search_start:ctx_start]
        for boundary_char in ".!?\n":
            pos = boundary_region.rfind(boundary_char)
            if pos != -1:
                ctx_start = search_start + pos + 1
                break

        search_end = min(len(text), ctx_end + 50)
        boundary_region = text[ctx_end:search_end]
        for boundary_char in ".!?\n":
            pos = boundary_region.find(boundary_char)
            if pos != -1:
                ctx_end = ctx_end + pos + 1
                break

        # Cap at 500 chars
        if ctx_end - ctx_start > 500:
            ctx_end = ctx_start + 500

        return text[ctx_start:ctx_end].strip()

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences using simple regex.

        Sufficient for AI-generated text which has clean punctuation.
        """
        return re.split(r"(?<=[.!?])\s+", text)

    def _deduplicate(self, mentions: list[dict]) -> list[dict]:
        """Deduplicate mentions by char_offset overlap.

        Same offset = same mention from different variants -> keep highest confidence.
        Overlapping ranges (fuzzy vs exact within 50 chars) -> keep exact.
        """
        if not mentions:
            return mentions

        # Sort by char_offset, then prefer exact over fuzzy
        sorted_mentions = sorted(
            mentions,
            key=lambda m: (m["char_offset"], 0 if m["match_type"] == "exact" else 1),
        )
        result: list[dict] = []

        for mention in sorted_mentions:
            is_duplicate = False
            replace_idx = None

            for idx, existing in enumerate(result):
                # Same offset = same physical match from different variants
                if mention["char_offset"] == existing["char_offset"]:
                    # Keep the one with higher confidence (exact > fuzzy)
                    if mention["confidence"] > existing["confidence"]:
                        replace_idx = idx
                    else:
                        is_duplicate = True
                    break

                # Overlapping ranges: fuzzy vs exact within 50 chars
                if abs(mention["char_offset"] - existing["char_offset"]) < 50:
                    if existing["match_type"] == "exact" and mention["match_type"] == "fuzzy":
                        is_duplicate = True
                        break
                    elif mention["match_type"] == "exact" and existing["match_type"] == "fuzzy":
                        replace_idx = idx
                        break

            if replace_idx is not None:
                result[replace_idx] = mention
            elif not is_duplicate:
                result.append(mention)

        return result
