"""ContentStructureScorer -- evaluates page content structure for AI extraction.

Analyzes 13 criteria measuring whether content is structured for AI extraction:
heading hierarchy, answer-first format, paragraph length, data density, FAQ
presence, content length, readability, citations, content freshness, statistics,
quotations, entity density, and sentence variety.

Content Structure is 25% of the Optimization Score. Research shows:
- Answer-first format yields +40% citations (Princeton GEO paper)
- Clean heading hierarchy gives 2.8x citation rate
- Data tables yield 4.1x more citations (Surfer SEO)
- FAQPage schema: +28% citations (Frase.io)
"""

import re
import statistics
from datetime import datetime, timezone

import textstat
from bs4 import BeautifulSoup, Tag
from loguru import logger

try:
    import nltk

    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    import nltk

    nltk.download("punkt_tab", quiet=True)

from app.services.scoring.base_scorer import BaseScorer, ScoringCriterionResult

# Question-word prefixes for detecting question-style headings
QUESTION_WORDS = (
    "what",
    "how",
    "why",
    "when",
    "where",
    "which",
    "who",
    "can",
    "does",
    "is",
    "do",
    "are",
    "should",
    "will",
    "could",
    "would",
)

# Authoritative domains for citation detection
AUTHORITATIVE_DOMAINS = (
    ".edu",
    ".gov",
    "wikipedia.org",
    "arxiv.org",
    "pubmed",
    "doi.org",
    "scholar.google",
    "ncbi.nlm.nih.gov",
)

# Text citation patterns
CITATION_PATTERNS = [
    re.compile(r"\[\d+\]"),  # [1], [2], etc.
    re.compile(r"\(Source:", re.IGNORECASE),
    re.compile(r"according to\s", re.IGNORECASE),
    re.compile(r"study by\s", re.IGNORECASE),
    re.compile(r"research shows", re.IGNORECASE),
    re.compile(r"research from\s", re.IGNORECASE),
    re.compile(r"published in\s", re.IGNORECASE),
    re.compile(r"data from\s", re.IGNORECASE),
]

# Date patterns for freshness detection
DATE_PATTERNS = [
    re.compile(
        r"\b(\d{4})-(\d{2})-(\d{2})\b"
    ),  # YYYY-MM-DD
    re.compile(
        r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"
    ),  # DD/MM/YYYY or MM/DD/YYYY
    re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
        re.IGNORECASE,
    ),  # Month DD, YYYY
    re.compile(
        r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{4})\b",
        re.IGNORECASE,
    ),  # DD Month YYYY
]

MONTH_MAP = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

# Statistics patterns for density detection
STAT_PATTERNS = [
    re.compile(r"\d+\.?\d*%"),  # percentages: 45%, 2.5%
    re.compile(r"\$[\d,.]+[KMBTkmbt]?"),  # dollar amounts: $1.2M
    re.compile(r"\d+\.?\d*[xX]\b"),  # multipliers: 3.2x, 4X
    re.compile(
        r"\d{1,3}(?:,\d{3})+\s+\w+"
    ),  # large numbers with units: 1,325 rows
]

# Quotation patterns
INLINE_QUOTE_PATTERNS = [
    re.compile(r'"[^"]{20,}"'),  # ASCII straight quotes
    re.compile(r"\u201c[^\u201d]{20,}\u201d"),  # Unicode curly quotes
]

ATTRIBUTION_PATTERNS = [
    re.compile(r"--\s*[A-Z]"),  # -- John Doe
    re.compile(r"\u2014\s*[A-Z]"),  # em-dash attribution
    re.compile(r"says\s+(?:CEO|CTO|CFO|COO|founder|director|president)", re.IGNORECASE),
    re.compile(r"says\s+[A-Z][a-z]+", re.IGNORECASE),
    re.compile(r"said\s+[A-Z][a-z]+", re.IGNORECASE),
]

# Entity detection pattern (capitalized multi-word phrases not at sentence start)
ENTITY_PATTERN = re.compile(
    r"(?<![.!?]\s)\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b"
)


class ContentStructureScorer(BaseScorer):
    """Scores page content structure across 13 criteria for AI extraction readiness.

    Criteria: CS1 heading hierarchy, CS2 answer-first format, CS3 paragraph length,
    CS4 data density, CS5 FAQ presence, CS6 content length, CS7 readability,
    CS8 citations, CS9 freshness, CS10 statistics, CS11 quotations, CS12 entity
    density, CS13 sentence variety.
    """

    async def score_page(
        self, page_data: dict
    ) -> list[ScoringCriterionResult]:
        """Score a page against all 13 content structure criteria.

        Args:
            page_data: CrawlResult dict with url, html, main_content, etc.

        Returns:
            List of 13 ScoringCriterionResult instances.
        """
        html = page_data.get("html", "")
        main_content = page_data.get("main_content", "")
        crawl_data = page_data

        # Parse HTML once for all criteria that need it
        soup = BeautifulSoup(html, "lxml") if html else None

        results = []
        results.append(self._check_heading_hierarchy(soup))
        results.append(self._check_answer_first(soup))
        results.append(self._check_paragraph_length(soup))
        results.append(self._check_data_density(soup))
        results.append(self._check_faq_presence(soup))
        results.append(self._check_content_length(main_content))
        results.append(self._check_readability(main_content))
        results.append(self._check_citations(soup, main_content))
        results.append(self._check_freshness(soup, crawl_data))
        results.append(self._check_statistics(main_content))
        results.append(self._check_quotations(soup, main_content))
        results.append(self._check_entity_density(main_content))
        results.append(self._check_sentence_variety(main_content))

        return results

    # ------------------------------------------------------------------
    # CS1: Heading hierarchy quality
    # ------------------------------------------------------------------

    def _check_heading_hierarchy(
        self, soup: BeautifulSoup | None
    ) -> ScoringCriterionResult:
        """Evaluate heading hierarchy quality (H1>H2>H3).

        Checks for exactly 1 H1, proper nesting without skipped levels,
        and sufficient heading count.

        Score starts at 100 and deducts for issues:
        - -30 if no H1
        - -20 if multiple H1s
        - -15 per skipped level (e.g. H1 directly to H3)
        - -10 if fewer than 2 H2s
        """
        criterion_id = "CS1"
        criterion_name = "Heading hierarchy quality"

        if soup is None:
            return self._not_checked(criterion_id, criterion_name, "No HTML available")

        h1s = soup.find_all("h1")
        h2s = soup.find_all("h2")
        h3s = soup.find_all("h3")

        h1_count = len(h1s)
        h2_count = len(h2s)
        h3_count = len(h3s)

        score = 100
        issues = []

        # Check H1 presence
        if h1_count == 0:
            score -= 30
            issues.append("No H1 tag found")
        elif h1_count > 1:
            score -= 20
            issues.append(f"Multiple H1 tags ({h1_count})")

        # Check for skipped levels
        skipped_levels = 0
        if h1_count > 0 and h3_count > 0 and h2_count == 0:
            skipped_levels += 1
            issues.append("H3 used without H2 parent")

        # Walk the heading order to detect jumps
        all_headings = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            level = int(tag.name[1])
            all_headings.append(level)

        for i in range(1, len(all_headings)):
            if all_headings[i] - all_headings[i - 1] > 1:
                skipped_levels += 1

        score -= 15 * skipped_levels
        if skipped_levels > 0 and "H3 used without H2 parent" not in issues:
            issues.append(f"{skipped_levels} skipped heading level(s)")

        # Check H2 count
        if h2_count < 2:
            score -= 10
            issues.append(f"Only {h2_count} H2 tags (need at least 2)")

        score = max(0, min(100, score))

        if issues:
            summary = f"Issues: {', '.join(issues)}"
        else:
            summary = (
                f"Good heading structure: {h1_count} H1, {h2_count} H2s, "
                f"{h3_count} H3s -- clean hierarchy"
            )

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=summary,
            technical_detail=f"h1={h1_count}, h2={h2_count}, h3={h3_count}, "
            f"skipped_levels={skipped_levels}, issues={issues}",
            evidence={
                "h1_count": h1_count,
                "h2_count": h2_count,
                "h3_count": h3_count,
                "skipped_levels": skipped_levels,
                "issues": issues,
            },
        )

    # ------------------------------------------------------------------
    # CS2: Answer-first format detection
    # ------------------------------------------------------------------

    def _check_answer_first(
        self, soup: BeautifulSoup | None
    ) -> ScoringCriterionResult:
        """Detect answer-first format in content sections.

        For each H2/H3, checks if heading is question-like and if the first
        sentence after it is a direct answer (10-60 words, declarative).
        """
        criterion_id = "CS2"
        criterion_name = "Answer-first format"

        if soup is None:
            return self._not_checked(criterion_id, criterion_name, "No HTML available")

        headings = soup.find_all(["h2", "h3"])
        if not headings:
            return ScoringCriterionResult(
                criterion_id=criterion_id,
                criterion_name=criterion_name,
                score=0,
                human_summary="No H2/H3 headings found to evaluate answer-first format",
                technical_detail="total_sections=0",
                evidence={
                    "total_sections": 0,
                    "answer_first_count": 0,
                    "question_headings_count": 0,
                },
            )

        total_sections = 0
        answer_first_count = 0
        question_headings_count = 0
        section_scores = []

        for heading in headings:
            heading_text = heading.get_text(strip=True)
            if not heading_text:
                continue

            total_sections += 1
            section_score = 0

            # Check if heading is question-like
            is_question = heading_text.rstrip().endswith("?")
            if not is_question:
                lower_heading = heading_text.lower().strip()
                is_question = any(
                    lower_heading.startswith(qw + " ") for qw in QUESTION_WORDS
                )

            if is_question:
                question_headings_count += 1
                section_score += 40

            # Get first text block after heading
            first_text = self._get_first_text_after(heading)
            if first_text:
                sentences = nltk.sent_tokenize(first_text)
                if sentences:
                    first_sentence = sentences[0]
                    word_count = len(first_sentence.split())

                    # Direct answer: 10-60 words, declarative (not a question)
                    is_direct_answer = (
                        10 <= word_count <= 60
                        and not first_sentence.rstrip().endswith("?")
                    )
                    if is_direct_answer:
                        section_score += 40
                        if is_question:
                            answer_first_count += 1

                    # Has supporting detail (more than 1 sentence)
                    if len(sentences) > 1:
                        section_score += 20

            section_scores.append(section_score)

        overall_score = (
            round(sum(section_scores) / len(section_scores))
            if section_scores
            else 0
        )
        overall_score = max(0, min(100, overall_score))

        quality = "Good" if overall_score >= 60 else "Needs improvement"
        summary = (
            f"{answer_first_count} of {total_sections} sections follow "
            f"answer-first format -- {quality}"
        )

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=overall_score,
            human_summary=summary,
            technical_detail=(
                f"total_sections={total_sections}, "
                f"answer_first_count={answer_first_count}, "
                f"question_headings_count={question_headings_count}"
            ),
            evidence={
                "total_sections": total_sections,
                "answer_first_count": answer_first_count,
                "question_headings_count": question_headings_count,
            },
        )

    def _get_first_text_after(self, heading: Tag) -> str:
        """Get the first meaningful text block after a heading element.

        Walks siblings to find the first <p> or text-containing element.
        Returns the text content or empty string.
        """
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag):
                if sibling.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    break  # Hit next heading, stop
                text = sibling.get_text(strip=True)
                if text and len(text.split()) >= 5:
                    return text
        return ""

    # ------------------------------------------------------------------
    # CS3: Paragraph length
    # ------------------------------------------------------------------

    def _check_paragraph_length(
        self, soup: BeautifulSoup | None
    ) -> ScoringCriterionResult:
        """Evaluate paragraph length for AI extraction.

        Ideal: 2-4 sentences per paragraph. Too short (1 sentence) or too long
        (7+ sentences) reduces the score.
        """
        criterion_id = "CS3"
        criterion_name = "Paragraph length"

        if soup is None:
            return self._not_checked(criterion_id, criterion_name, "No HTML available")

        paragraphs = soup.find_all("p")
        # Filter to meaningful paragraphs (>20 words)
        meaningful = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text.split()) > 20:
                meaningful.append(text)

        if len(meaningful) < 3:
            return ScoringCriterionResult(
                criterion_id=criterion_id,
                criterion_name=criterion_name,
                score=30,
                human_summary="Too few meaningful paragraphs to evaluate",
                technical_detail=f"total_paragraphs={len(meaningful)}, min_required=3",
                evidence={
                    "total_paragraphs": len(meaningful),
                    "avg_sentences": 0,
                    "ideal_count": 0,
                    "long_count": 0,
                    "short_count": 0,
                },
            )

        paragraph_scores = []
        sentence_counts = []
        ideal_count = 0
        long_count = 0
        short_count = 0

        for text in meaningful:
            sentences = nltk.sent_tokenize(text)
            n_sentences = len(sentences)
            sentence_counts.append(n_sentences)

            if 2 <= n_sentences <= 4:
                paragraph_scores.append(100)
                ideal_count += 1
            elif n_sentences == 1:
                paragraph_scores.append(60)
                short_count += 1
            elif 5 <= n_sentences <= 6:
                paragraph_scores.append(70)
                long_count += 1
            else:  # 7+
                paragraph_scores.append(30)
                long_count += 1

        avg_sentences = round(
            sum(sentence_counts) / len(sentence_counts), 1
        )
        overall = round(sum(paragraph_scores) / len(paragraph_scores))
        overall = max(0, min(100, overall))

        if avg_sentences < 2:
            quality = "too short"
        elif avg_sentences > 5:
            quality = "too long"
        else:
            quality = "ideal for AI extraction"

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=overall,
            human_summary=(
                f"Average {avg_sentences} sentences per paragraph -- {quality}"
            ),
            technical_detail=(
                f"total_paragraphs={len(meaningful)}, avg_sentences={avg_sentences}, "
                f"ideal={ideal_count}, long={long_count}, short={short_count}"
            ),
            evidence={
                "total_paragraphs": len(meaningful),
                "avg_sentences": avg_sentences,
                "ideal_count": ideal_count,
                "long_count": long_count,
                "short_count": short_count,
            },
        )

    # ------------------------------------------------------------------
    # CS4: Data density
    # ------------------------------------------------------------------

    def _check_data_density(
        self, soup: BeautifulSoup | None
    ) -> ScoringCriterionResult:
        """Measure data density: tables, lists, statistics in content.

        Tables: 30 pts max, lists: 30 pts max, statistics: 40 pts max.
        Scale each: 0 items = 0, 1 item = half, 2+ items = full.
        """
        criterion_id = "CS4"
        criterion_name = "Data density"

        if soup is None:
            return self._not_checked(criterion_id, criterion_name, "No HTML available")

        # Count tables
        table_count = len(soup.find_all("table"))

        # Count lists with >2 items
        list_count = 0
        for tag in soup.find_all(["ol", "ul"]):
            items = tag.find_all("li", recursive=False)
            if len(items) > 2:
                list_count += 1

        # Count statistics in text
        text = soup.get_text(separator=" ", strip=True)
        stat_examples = []
        stat_count = 0
        for pattern in STAT_PATTERNS:
            matches = pattern.findall(text)
            stat_count += len(matches)
            stat_examples.extend(matches[:3])

        # Scoring
        if table_count == 0:
            table_pts = 0
        elif table_count == 1:
            table_pts = 15
        else:
            table_pts = 30

        if list_count == 0:
            list_pts = 0
        elif list_count == 1:
            list_pts = 15
        else:
            list_pts = 30

        if stat_count == 0:
            stat_pts = 0
        elif stat_count == 1:
            stat_pts = 20
        else:
            stat_pts = 40

        score = max(0, min(100, table_pts + list_pts + stat_pts))

        if score >= 70:
            density = "Rich"
        elif score >= 30:
            density = "Moderate"
        else:
            density = "Low"

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=(
                f"Data density: {table_count} tables, {list_count} lists, "
                f"{stat_count} statistics -- {density}"
            ),
            technical_detail=(
                f"tables={table_count} ({table_pts}pts), "
                f"lists={list_count} ({list_pts}pts), "
                f"stats={stat_count} ({stat_pts}pts)"
            ),
            evidence={
                "table_count": table_count,
                "list_count": list_count,
                "statistic_count": stat_count,
                "statistic_examples": stat_examples[:5],
            },
        )

    # ------------------------------------------------------------------
    # CS5: FAQ section presence
    # ------------------------------------------------------------------

    def _check_faq_presence(
        self, soup: BeautifulSoup | None
    ) -> ScoringCriterionResult:
        """Detect FAQ sections via headings, details/summary, definition lists.

        Score: 100 if FAQ with 3+ Q&A, 70 if 1-2 pairs, 40 if question headings
        but no formal section, 0 if no FAQ signals.
        """
        criterion_id = "CS5"
        criterion_name = "FAQ section presence"

        if soup is None:
            return self._not_checked(criterion_id, criterion_name, "No HTML available")

        faq_detected = False
        detection_method = "none"
        question_count = 0

        # Check 1: Heading containing "FAQ" or "Frequently Asked"
        faq_heading = None
        for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
            heading_text = heading.get_text(strip=True).lower()
            if "faq" in heading_text or "frequently asked" in heading_text:
                faq_heading = heading
                faq_detected = True
                detection_method = "faq_heading"
                break

        # Count questions in FAQ section (elements between FAQ heading and next same-level heading)
        if faq_heading:
            for sibling in faq_heading.next_siblings:
                if isinstance(sibling, Tag):
                    if sibling.name == faq_heading.name:
                        break  # Hit next same-level heading
                    sibling_text = sibling.get_text(strip=True)
                    if sibling_text.endswith("?"):
                        question_count += 1
                    elif sibling.name in ("h3", "h4", "h5"):
                        text = sibling.get_text(strip=True)
                        if text.endswith("?"):
                            question_count += 1

        # Check 2: <details>/<summary> elements
        if not faq_detected:
            details_elements = soup.find_all("details")
            if details_elements:
                faq_detected = True
                detection_method = "details_summary"
                question_count = len(details_elements)

        # Check 3: Definition lists with question-like dt
        if not faq_detected:
            for dl in soup.find_all("dl"):
                dts = dl.find_all("dt")
                q_dts = [
                    dt
                    for dt in dts
                    if dt.get_text(strip=True).endswith("?")
                ]
                if q_dts:
                    faq_detected = True
                    detection_method = "definition_list"
                    question_count = len(q_dts)
                    break

        # Check 4: Consecutive question-style H3s (3+)
        if not faq_detected:
            h3s = soup.find_all("h3")
            consecutive_questions = 0
            max_consecutive = 0
            for h3 in h3s:
                text = h3.get_text(strip=True)
                if text.endswith("?"):
                    consecutive_questions += 1
                    max_consecutive = max(max_consecutive, consecutive_questions)
                else:
                    consecutive_questions = 0
            if max_consecutive >= 3:
                faq_detected = True
                detection_method = "consecutive_question_headings"
                question_count = max_consecutive

        # Scoring
        if faq_detected and question_count >= 3:
            score = 100
        elif faq_detected and question_count >= 1:
            score = 70
        elif not faq_detected:
            # Check for any question-style headings as weak signal
            any_question_headings = sum(
                1
                for h in soup.find_all(["h2", "h3"])
                if h.get_text(strip=True).endswith("?")
            )
            if any_question_headings >= 2:
                score = 40
                detection_method = "weak_question_headings"
                question_count = any_question_headings
            else:
                score = 0
        else:
            score = 40

        if faq_detected:
            summary = (
                f"FAQ section found with {question_count} questions -- "
                f"great for AI query matching"
            )
        elif score == 40:
            summary = (
                f"{question_count} question-style headings detected but "
                f"no formal FAQ section"
            )
        else:
            summary = "No FAQ section detected"

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=summary,
            technical_detail=(
                f"faq_detected={faq_detected}, "
                f"method={detection_method}, questions={question_count}"
            ),
            evidence={
                "faq_detected": faq_detected,
                "detection_method": detection_method,
                "question_count": question_count,
            },
        )

    # ------------------------------------------------------------------
    # CS6: Content length
    # ------------------------------------------------------------------

    def _check_content_length(self, main_content: str) -> ScoringCriterionResult:
        """Evaluate content length for AI extraction.

        Optimal range: 1200-1800 words. Too short or too long reduces score.
        """
        criterion_id = "CS6"
        criterion_name = "Content length"

        word_count = len(main_content.split()) if main_content else 0

        if word_count < 300:
            score = 20
            quality = "Short"
        elif word_count < 600:
            score = 40
            quality = "Short"
        elif word_count < 1200:
            score = 60
            quality = "Moderate"
        elif word_count <= 1800:
            score = 100
            quality = "Optimal"
        elif word_count <= 3000:
            score = 80
            quality = "Slightly long"
        elif word_count <= 5000:
            score = 60
            quality = "Long"
        else:
            score = 40
            quality = "Very long"

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=f"{word_count} words -- {quality} for AI extraction",
            technical_detail=f"word_count={word_count}, optimal_range=1200-1800",
            evidence={
                "word_count": word_count,
                "optimal_range": "1200-1800",
            },
        )

    # ------------------------------------------------------------------
    # CS7: Readability score
    # ------------------------------------------------------------------

    def _check_readability(self, main_content: str) -> ScoringCriterionResult:
        """Score readability using Flesch-Kincaid grade level.

        Target: grade 8-10 is ideal for AI extraction. Too simple (<4) or
        too complex (>14) reduces score.
        """
        criterion_id = "CS7"
        criterion_name = "Readability score"

        word_count = len(main_content.split()) if main_content else 0
        if word_count < 100:
            return self._not_checked(
                criterion_id, criterion_name, "Content too short (<100 words)"
            )

        fk_grade = textstat.flesch_kincaid_grade(main_content)
        reading_ease = textstat.flesch_reading_ease(main_content)

        if 8 <= fk_grade <= 10:
            score = 100
            quality = "Clear and accessible"
        elif (6 <= fk_grade < 8) or (10 < fk_grade <= 12):
            score = 80
            quality = "Good readability"
        elif (4 <= fk_grade < 6) or (12 < fk_grade <= 14):
            score = 50
            quality = "Too simple" if fk_grade < 6 else "Too complex"
        else:
            score = 20
            quality = "Too simple" if fk_grade < 4 else "Too complex"

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=(
                f"Grade level {fk_grade:.1f} -- {quality} for AI extraction"
            ),
            technical_detail=(
                f"flesch_kincaid_grade={fk_grade:.1f}, "
                f"flesch_reading_ease={reading_ease:.1f}"
            ),
            evidence={
                "flesch_kincaid_grade": round(fk_grade, 1),
                "flesch_reading_ease": round(reading_ease, 1),
            },
        )

    # ------------------------------------------------------------------
    # CS8: Citation/reference presence
    # ------------------------------------------------------------------

    def _check_citations(
        self, soup: BeautifulSoup | None, main_content: str
    ) -> ScoringCriterionResult:
        """Detect citations and references to authoritative sources.

        Counts outbound links to .edu/.gov/wikipedia/arxiv and text citation
        patterns like [1], (Source:), "according to", etc.
        """
        criterion_id = "CS8"
        criterion_name = "Citation/reference presence"

        authoritative_links = 0
        text_citations = 0

        # Check outbound links
        if soup:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].lower()
                if any(domain in href for domain in AUTHORITATIVE_DOMAINS):
                    authoritative_links += 1

        # Check text citation patterns
        for pattern in CITATION_PATTERNS:
            text_citations += len(pattern.findall(main_content))

        total = authoritative_links + text_citations

        if total == 0:
            score = 0
            quality = "No"
        elif total <= 2:
            score = 40
            quality = "Some"
        elif total <= 5:
            score = 70
            quality = "Good"
        else:
            score = 100
            quality = "Strong"

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=(
                f"{total} citations/references detected -- "
                f"{quality} source attribution"
            ),
            technical_detail=(
                f"authoritative_links={authoritative_links}, "
                f"text_citations={text_citations}, total={total}"
            ),
            evidence={
                "citation_count": total,
                "authoritative_links": authoritative_links,
                "text_citations": text_citations,
            },
        )

    # ------------------------------------------------------------------
    # CS9: Content freshness
    # ------------------------------------------------------------------

    def _check_freshness(
        self, soup: BeautifulSoup | None, crawl_data: dict
    ) -> ScoringCriterionResult:
        """Detect content freshness from dates in HTML and meta tags.

        Checks <time> elements, meta tags (article:published_time, datePublished,
        dateModified), and visible date patterns.
        """
        criterion_id = "CS9"
        criterion_name = "Content freshness"

        dates_found: list[datetime] = []
        now = datetime.now(timezone.utc)

        if soup:
            # Check <time> elements
            for time_tag in soup.find_all("time"):
                dt_attr = time_tag.get("datetime", "")
                parsed = self._parse_date_string(dt_attr)
                if parsed:
                    dates_found.append(parsed)

            # Check meta tags
            meta_date_names = [
                "article:published_time",
                "article:modified_time",
                "datePublished",
                "dateModified",
                "date",
                "last-modified",
            ]
            for name in meta_date_names:
                meta = soup.find("meta", attrs={"property": name}) or soup.find(
                    "meta", attrs={"name": name}
                )
                if meta and meta.get("content"):
                    parsed = self._parse_date_string(meta["content"])
                    if parsed:
                        dates_found.append(parsed)

            # Check JSON-LD for datePublished/dateModified
            for script in soup.find_all("script", type="application/ld+json"):
                text = script.string or ""
                for key in ("datePublished", "dateModified"):
                    pattern = re.compile(rf'"{key}"\s*:\s*"([^"]+)"')
                    match = pattern.search(text)
                    if match:
                        parsed = self._parse_date_string(match.group(1))
                        if parsed:
                            dates_found.append(parsed)

        # Check visible date patterns in text
        text = crawl_data.get("main_content", "")
        for pattern in DATE_PATTERNS:
            for match in pattern.finditer(text):
                parsed = self._parse_date_match(match)
                if parsed:
                    dates_found.append(parsed)

        # Find most recent date
        if not dates_found:
            score = 10
            summary = "No date signals found -- freshness unknown"
            days_since = -1
            most_recent = None
        else:
            # Filter out future dates
            valid_dates = [d for d in dates_found if d <= now]
            if not valid_dates:
                score = 10
                summary = "No valid dates found"
                days_since = -1
                most_recent = None
            else:
                most_recent = max(valid_dates)
                days_since = (now - most_recent).days

                if days_since < 30:
                    score = 100
                    freshness = "Fresh"
                elif days_since < 90:
                    score = 80
                    freshness = "Recent"
                elif days_since < 365:
                    score = 50
                    freshness = "Aging"
                elif days_since < 730:
                    score = 25
                    freshness = "Stale"
                else:
                    score = 10
                    freshness = "Outdated"

                summary = (
                    f"Last updated {most_recent.strftime('%Y-%m-%d')} "
                    f"({days_since} days ago) -- {freshness}"
                )

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=summary,
            technical_detail=(
                f"dates_found={len(dates_found)}, "
                f"most_recent={most_recent.isoformat() if most_recent else 'none'}, "
                f"days_since={days_since}"
            ),
            evidence={
                "dates_found": len(dates_found),
                "most_recent_date": (
                    most_recent.isoformat() if most_recent else None
                ),
                "days_since_update": days_since,
            },
        )

    def _parse_date_string(self, date_str: str) -> datetime | None:
        """Parse a date string into a timezone-aware datetime, or None."""
        if not date_str or not date_str.strip():
            return None

        date_str = date_str.strip()

        # Try ISO 8601 formats
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(date_str[:len(fmt) + 5], fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, IndexError):
                continue

        return None

    def _parse_date_match(self, match: re.Match) -> datetime | None:
        """Parse a regex date match into a timezone-aware datetime, or None."""
        groups = match.groups()
        try:
            text = match.group(0)
            # YYYY-MM-DD
            if re.match(r"\d{4}-\d{2}-\d{2}", text):
                return datetime(
                    int(groups[0]), int(groups[1]), int(groups[2]),
                    tzinfo=timezone.utc,
                )
            # DD/MM/YYYY
            if re.match(r"\d{1,2}/\d{1,2}/\d{4}", text):
                # Assume MM/DD/YYYY (US format) for ambiguous cases
                month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                if month > 12:
                    month, day = day, month
                return datetime(year, month, day, tzinfo=timezone.utc)
            # Month DD, YYYY
            month_name = None
            for g in groups:
                if g.lower() in MONTH_MAP:
                    month_name = g.lower()
                    break
            if month_name:
                month_num = MONTH_MAP[month_name]
                # Find numeric groups
                nums = [int(g) for g in groups if g.isdigit()]
                if len(nums) >= 2:
                    day = nums[0] if nums[0] <= 31 else nums[1]
                    year = nums[1] if nums[1] > 31 else nums[0]
                    return datetime(year, month_num, day, tzinfo=timezone.utc)
        except (ValueError, TypeError, IndexError):
            pass
        return None

    # ------------------------------------------------------------------
    # CS10: Statistics density
    # ------------------------------------------------------------------

    def _check_statistics(self, main_content: str) -> ScoringCriterionResult:
        """Measure statistics density in content.

        Counts percentages, dollar amounts, multipliers, and large numbers
        per 1000 words.
        """
        criterion_id = "CS10"
        criterion_name = "Statistics density"

        word_count = len(main_content.split()) if main_content else 0
        if word_count == 0:
            return ScoringCriterionResult(
                criterion_id=criterion_id,
                criterion_name=criterion_name,
                score=0,
                human_summary="No content to analyze for statistics",
                technical_detail="word_count=0",
                evidence={
                    "stat_count": 0,
                    "per_1000_words": 0,
                    "examples": [],
                },
            )

        stat_count = 0
        examples = []
        for pattern in STAT_PATTERNS:
            matches = pattern.findall(main_content)
            stat_count += len(matches)
            examples.extend(matches[:3])

        per_1000 = round(stat_count / (word_count / 1000), 1) if word_count > 0 else 0

        if per_1000 == 0:
            score = 0
            density = "Low"
        elif per_1000 <= 2:
            score = 30
            density = "Low"
        elif per_1000 <= 5:
            score = 60
            density = "Moderate"
        elif per_1000 <= 10:
            score = 90
            density = "Rich"
        else:
            score = 100
            density = "Rich"

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=(
                f"{stat_count} statistics ({per_1000} per 1000 words) -- "
                f"{density} data signals"
            ),
            technical_detail=(
                f"stat_count={stat_count}, per_1000_words={per_1000}, "
                f"word_count={word_count}"
            ),
            evidence={
                "stat_count": stat_count,
                "per_1000_words": per_1000,
                "examples": examples[:5],
            },
        )

    # ------------------------------------------------------------------
    # CS11: Quotation presence
    # ------------------------------------------------------------------

    def _check_quotations(
        self, soup: BeautifulSoup | None, main_content: str
    ) -> ScoringCriterionResult:
        """Detect expert quotes and blockquotes in content.

        Counts <blockquote> elements, inline quotes (20+ chars), and
        attributed quotes ("-- Name", "says CEO").
        """
        criterion_id = "CS11"
        criterion_name = "Quotation presence"

        blockquote_count = 0
        if soup:
            blockquote_count = len(soup.find_all("blockquote"))

        inline_count = 0
        for pattern in INLINE_QUOTE_PATTERNS:
            inline_count += len(pattern.findall(main_content))

        attributed_count = 0
        for pattern in ATTRIBUTION_PATTERNS:
            attributed_count += len(pattern.findall(main_content))

        total = blockquote_count + inline_count
        if total == 0:
            score = 0
            quality = "No"
        elif total == 1:
            score = 40
            quality = "Some"
        elif total <= 3:
            score = 70
            quality = "Good"
        else:
            score = 100
            quality = "Strong"

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=(
                f"{total} expert quotes detected -- "
                f"{quality} authority signals"
            ),
            technical_detail=(
                f"blockquotes={blockquote_count}, inline_quotes={inline_count}, "
                f"attributed={attributed_count}"
            ),
            evidence={
                "blockquote_count": blockquote_count,
                "inline_quote_count": inline_count,
                "attributed_count": attributed_count,
            },
        )

    # ------------------------------------------------------------------
    # CS12: Entity density
    # ------------------------------------------------------------------

    def _check_entity_density(
        self, main_content: str
    ) -> ScoringCriterionResult:
        """Measure named entity density using regex-based detection.

        Detects capitalized multi-word phrases, URLs, email addresses, and
        @handles. Scores by entities per 100 words.
        """
        criterion_id = "CS12"
        criterion_name = "Entity density"

        word_count = len(main_content.split()) if main_content else 0
        if word_count == 0:
            return ScoringCriterionResult(
                criterion_id=criterion_id,
                criterion_name=criterion_name,
                score=0,
                human_summary="No content to analyze for entities",
                technical_detail="word_count=0",
                evidence={
                    "entity_count": 0,
                    "per_100_words": 0,
                    "sample_entities": [],
                },
            )

        entities: list[str] = []

        # Capitalized multi-word phrases (not at sentence start)
        for match in ENTITY_PATTERN.finditer(main_content):
            entities.append(match.group())

        # URL patterns
        url_pattern = re.compile(r"https?://\S+")
        entities.extend(url_pattern.findall(main_content))

        # Email patterns
        email_pattern = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
        entities.extend(email_pattern.findall(main_content))

        # @handles
        handle_pattern = re.compile(r"@\w{2,}")
        entities.extend(handle_pattern.findall(main_content))

        entity_count = len(entities)
        per_100 = round(entity_count / (word_count / 100), 1) if word_count > 0 else 0

        if per_100 < 1:
            score = 20
            density = "Low"
        elif per_100 < 2:
            score = 40
            density = "Low"
        elif per_100 < 4:
            score = 70
            density = "Moderate"
        elif per_100 < 6:
            score = 90
            density = "High"
        else:
            score = 100
            density = "High"

        # Deduplicate sample entities for display
        unique_entities = list(dict.fromkeys(entities))

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=(
                f"{per_100} named entities per 100 words -- "
                f"{density} entity density"
            ),
            technical_detail=(
                f"entity_count={entity_count}, per_100_words={per_100}, "
                f"word_count={word_count}"
            ),
            evidence={
                "entity_count": entity_count,
                "per_100_words": per_100,
                "sample_entities": unique_entities[:10],
            },
        )

    # ------------------------------------------------------------------
    # CS13: Sentence length variety
    # ------------------------------------------------------------------

    def _check_sentence_variety(
        self, main_content: str
    ) -> ScoringCriterionResult:
        """Measure sentence length variety using coefficient of variation.

        High variety (CV > 0.5) is ideal for engaging AI-readable content.
        Monotonous sentence lengths (CV < 0.15) indicate robotic writing.
        """
        criterion_id = "CS13"
        criterion_name = "Sentence length variety"

        sentences = nltk.sent_tokenize(main_content) if main_content else []
        if len(sentences) < 5:
            return self._not_checked(
                criterion_id, criterion_name,
                f"Too few sentences ({len(sentences)}) to evaluate variety"
            )

        lengths = [len(s.split()) for s in sentences]
        mean_len = statistics.mean(lengths)
        std_dev = statistics.stdev(lengths)
        cv = std_dev / mean_len if mean_len > 0 else 0

        min_len = min(lengths)
        max_len = max(lengths)

        if cv > 0.5:
            score = 100
            variety = "High"
        elif cv > 0.3:
            score = 70
            variety = "Moderate"
        elif cv > 0.15:
            score = 40
            variety = "Low"
        else:
            score = 20
            variety = "Very low (monotonous)"

        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=score,
            human_summary=(
                f"Sentence length variety: {variety} -- "
                f"mix of {min_len} to {max_len} word sentences"
            ),
            technical_detail=(
                f"mean={mean_len:.1f}, std_dev={std_dev:.1f}, cv={cv:.2f}, "
                f"min={min_len}, max={max_len}, n={len(sentences)}"
            ),
            evidence={
                "mean_sentence_length": round(mean_len, 1),
                "std_dev": round(std_dev, 1),
                "cv": round(cv, 2),
                "min_length": min_len,
                "max_length": max_len,
                "sentence_count": len(sentences),
            },
        )
