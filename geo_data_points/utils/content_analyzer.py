"""
Content Analysis Utilities

NLP, entity extraction, readability scoring, sentiment analysis,
and content quality metrics.
"""

import re
from typing import List, Dict, Any, Set, Tuple, Optional
from functools import lru_cache
import textstat
from collections import Counter

from .logging import get_logger


logger = get_logger("content_analyzer")


class ContentAnalyzer:
    """Advanced content analysis and NLP operations."""

    def __init__(self, text: str):
        """
        Initialize content analyzer.

        Args:
            text: Text content to analyze
        """
        self.text = text
        self._sentences = None
        self._words = None
        self._paragraphs = None

    # ========== Basic Metrics ==========

    @property
    def sentences(self) -> List[str]:
        """Split text into sentences (cached)."""
        if self._sentences is None:
            # Simple sentence tokenization
            self._sentences = [s.strip() for s in re.split(r'[.!?]+', self.text) if s.strip()]
        return self._sentences

    @property
    def words(self) -> List[str]:
        """Extract words (cached)."""
        if self._words is None:
            self._words = re.findall(r'\b\w+\b', self.text.lower())
        return self._words

    @property
    def paragraphs(self) -> List[str]:
        """Split text into paragraphs (cached)."""
        if self._paragraphs is None:
            self._paragraphs = [p.strip() for p in self.text.split('\n\n') if p.strip()]
        return self._paragraphs

    def get_word_count(self) -> int:
        """Total word count."""
        return len(self.words)

    def get_sentence_count(self) -> int:
        """Total sentence count."""
        return len(self.sentences)

    def get_paragraph_count(self) -> int:
        """Total paragraph count."""
        return len(self.paragraphs)

    def get_character_count(self, exclude_spaces: bool = False) -> int:
        """Character count."""
        if exclude_spaces:
            return len(self.text.replace(' ', ''))
        return len(self.text)

    # ========== Readability Metrics ==========

    def get_flesch_reading_ease(self) -> float:
        """
        Flesch Reading Ease Score (0-100).
        90-100: Very Easy
        60-70: Standard
        0-30: Very Difficult
        """
        try:
            return textstat.flesch_reading_ease(self.text)
        except Exception:
            return 0.0

    def get_flesch_kincaid_grade(self) -> float:
        """
        Flesch-Kincaid Grade Level.
        Corresponds to US school grade (e.g., 8.0 = 8th grade).
        """
        try:
            return textstat.flesch_kincaid_grade(self.text)
        except Exception:
            return 0.0

    def get_gunning_fog(self) -> float:
        """Gunning Fog Index (years of education needed)."""
        try:
            return textstat.gunning_fog(self.text)
        except Exception:
            return 0.0

    def get_smog_index(self) -> float:
        """SMOG Index (Simple Measure of Gobbledygook)."""
        try:
            return textstat.smog_index(self.text)
        except Exception:
            return 0.0

    def get_readability_scores(self) -> Dict[str, float]:
        """Get all readability scores."""
        return {
            'flesch_reading_ease': self.get_flesch_reading_ease(),
            'flesch_kincaid_grade': self.get_flesch_kincaid_grade(),
            'gunning_fog': self.get_gunning_fog(),
            'smog_index': self.get_smog_index()
        }

    # ========== Sentence & Paragraph Analysis ==========

    def get_average_sentence_length(self) -> float:
        """Average words per sentence."""
        if not self.sentences:
            return 0.0

        total_words = sum(len(re.findall(r'\b\w+\b', s)) for s in self.sentences)
        return total_words / len(self.sentences)

    def get_average_paragraph_length(self) -> float:
        """Average words per paragraph."""
        if not self.paragraphs:
            return 0.0

        total_words = sum(len(re.findall(r'\b\w+\b', p)) for p in self.paragraphs)
        return total_words / len(self.paragraphs)

    def get_sentence_length_distribution(self) -> Dict[str, int]:
        """Categorize sentences by length."""
        distribution = {
            'very_short': 0,  # < 10 words
            'short': 0,        # 10-20 words
            'medium': 0,       # 20-30 words
            'long': 0,         # 30-40 words
            'very_long': 0     # > 40 words
        }

        for sentence in self.sentences:
            word_count = len(re.findall(r'\b\w+\b', sentence))

            if word_count < 10:
                distribution['very_short'] += 1
            elif word_count < 20:
                distribution['short'] += 1
            elif word_count < 30:
                distribution['medium'] += 1
            elif word_count < 40:
                distribution['long'] += 1
            else:
                distribution['very_long'] += 1

        return distribution

    # ========== Keyword Analysis ==========

    def get_keyword_density(self, keyword: str) -> float:
        """
        Calculate keyword density as percentage.

        Args:
            keyword: Target keyword (can be multi-word)

        Returns:
            Density as percentage
        """
        keyword_lower = keyword.lower()
        text_lower = self.text.lower()

        occurrences = text_lower.count(keyword_lower)
        total_words = self.get_word_count()

        if total_words == 0:
            return 0.0

        # Adjust for multi-word keywords
        keyword_words = len(keyword.split())
        return (occurrences * keyword_words / total_words) * 100

    def get_top_keywords(self, n: int = 10, min_length: int = 3) -> List[Tuple[str, int]]:
        """
        Extract top N keywords by frequency.

        Args:
            n: Number of keywords to return
            min_length: Minimum word length

        Returns:
            List of (word, count) tuples
        """
        # Filter stopwords (basic list)
        stopwords = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
            'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
            'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go',
            'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know',
            'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them',
            'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over',
            'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work',
            'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
            'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'has', 'had',
            'were', 'said', 'did', 'having', 'may', 'should', 'am', 'being', 'might'
        }

        filtered_words = [w for w in self.words if len(w) >= min_length and w not in stopwords]

        counter = Counter(filtered_words)
        return counter.most_common(n)

    # ========== Entity Extraction (Simple, no spaCy) ==========

    def extract_capitalized_entities(self) -> List[str]:
        """
        Extract simple entities (capitalized words).

        Note: For production, use spaCy. This is a lightweight fallback.
        """
        # Find sequences of capitalized words
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        entities = re.findall(pattern, self.text)

        # Deduplicate
        return list(set(entities))

    def extract_urls(self) -> List[str]:
        """Extract URLs from text."""
        pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_\+.~#?&/=]*'
        return re.findall(pattern, self.text)

    def extract_email_addresses(self) -> List[str]:
        """Extract email addresses."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(pattern, self.text)

    def extract_phone_numbers(self) -> List[str]:
        """Extract phone numbers (US format)."""
        patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (123) 456-7890
            r'\+1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'  # +1 (123) 456-7890
        ]

        numbers = []
        for pattern in patterns:
            numbers.extend(re.findall(pattern, self.text))

        return list(set(numbers))

    # ========== Sentiment Analysis (VADER-based) ==========

    def get_sentiment_score(self) -> Dict[str, float]:
        """
        Get sentiment polarity score.

        Returns compound score between -1 (negative) and +1 (positive).
        This is a simplified version. For production, use VADER or Transformers.
        """
        # Simplified sentiment analysis using word lists
        positive_words = {
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'best', 'better', 'awesome', 'brilliant', 'outstanding', 'perfect',
            'love', 'like', 'enjoy', 'happy', 'pleased', 'satisfied',
            'beautiful', 'quality', 'recommend', 'impressive', 'helpful',
            'easy', 'reliable', 'effective', 'efficient', 'success', 'win'
        }

        negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'poor', 'worst', 'worse',
            'hate', 'dislike', 'disappointed', 'frustrated', 'angry', 'annoyed',
            'problem', 'issue', 'fail', 'failure', 'broken', 'wrong', 'error',
            'difficult', 'hard', 'slow', 'complicated', 'expensive', 'waste',
            'useless', 'worthless', 'disappointing', 'unsatisfied'
        }

        positive_count = sum(1 for word in self.words if word in positive_words)
        negative_count = sum(1 for word in self.words if word in negative_words)

        total = positive_count + negative_count

        if total == 0:
            compound = 0.0
        else:
            compound = (positive_count - negative_count) / total

        return {
            'compound': compound,
            'positive': positive_count,
            'negative': negative_count,
            'neutral': len(self.words) - total
        }

    # ========== Citation Detection ==========

    def detect_citations(self) -> Dict[str, Any]:
        """
        Detect citations (quotes, references, links).

        Returns count and ratio of citations to claims.
        """
        # Detect quoted text
        quoted_text = re.findall(r'"([^"]*)"', self.text)
        single_quotes = re.findall(r"'([^']*)'", self.text)

        # Detect numbered references [1], [2], etc.
        numbered_refs = re.findall(r'\[\d+\]', self.text)

        # Detect parenthetical citations (Author, Year)
        parenthetical = re.findall(r'\([A-Z][a-z]+,\s*\d{4}\)', self.text)

        # Detect URLs
        urls = self.extract_urls()

        total_citations = len(quoted_text) + len(numbered_refs) + len(parenthetical) + len(urls)

        # Rough estimate: citation ratio (citations per 100 sentences)
        citation_ratio = (total_citations / max(len(self.sentences), 1)) * 100

        return {
            'total_citations': total_citations,
            'quoted_text': len(quoted_text),
            'numbered_references': len(numbered_refs),
            'parenthetical_citations': len(parenthetical),
            'url_citations': len(urls),
            'citation_ratio': citation_ratio
        }

    # ========== Active/Passive Voice Detection ==========

    def detect_passive_voice(self) -> Dict[str, Any]:
        """
        Detect passive voice sentences.

        Uses simple heuristic: "to be" verb + past participle.
        """
        # Common "to be" forms
        be_verbs = r'\b(am|is|are|was|were|be|been|being)\b'

        # Past participle endings (simplified)
        past_participle = r'\b\w+(?:ed|en)\b'

        passive_sentences = []
        for sentence in self.sentences:
            if re.search(be_verbs, sentence, re.I) and re.search(past_participle, sentence):
                passive_sentences.append(sentence)

        total_sentences = len(self.sentences)
        passive_count = len(passive_sentences)

        active_percent = ((total_sentences - passive_count) / max(total_sentences, 1)) * 100

        return {
            'passive_sentences': passive_count,
            'total_sentences': total_sentences,
            'active_voice_percent': active_percent,
            'passive_voice_percent': 100 - active_percent
        }

    # ========== Content Structure ==========

    def analyze_visual_hierarchy(self, html: str) -> Dict[str, int]:
        """
        Analyze use of emphasis tags.

        Args:
            html: HTML content (needed for tags)

        Returns:
            Counts of bold, italic, underline usage
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'lxml')

        return {
            'bold': len(soup.find_all(['b', 'strong'])),
            'italic': len(soup.find_all(['i', 'em'])),
            'underline': len(soup.find_all('u')),
            'highlight': len(soup.find_all('mark'))
        }

    # ========== Content Freshness Indicators ==========

    def extract_dates(self) -> List[str]:
        """Extract date patterns from text."""
        # Match various date formats
        patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # Month DD, YYYY
            r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',  # DD Month YYYY
        ]

        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, self.text, re.I))

        return list(set(dates))

    # ========== Duplicate Content Detection ==========

    def calculate_shingling_hash(self, shingle_size: int = 5) -> Set[int]:
        """
        Generate shingles (k-grams) for duplicate detection.

        Args:
            shingle_size: Number of words per shingle

        Returns:
            Set of shingle hashes
        """
        words = self.words
        shingles = set()

        for i in range(len(words) - shingle_size + 1):
            shingle = ' '.join(words[i:i + shingle_size])
            shingles.add(hash(shingle))

        return shingles

    def calculate_similarity(self, other_text: str, shingle_size: int = 5) -> float:
        """
        Calculate Jaccard similarity with another text.

        Args:
            other_text: Text to compare against
            shingle_size: Shingle size

        Returns:
            Similarity score (0-1)
        """
        shingles1 = self.calculate_shingling_hash(shingle_size)

        other_analyzer = ContentAnalyzer(other_text)
        shingles2 = other_analyzer.calculate_shingling_hash(shingle_size)

        if not shingles1 or not shingles2:
            return 0.0

        intersection = len(shingles1 & shingles2)
        union = len(shingles1 | shingles2)

        return intersection / union if union > 0 else 0.0


def analyze_content(text: str) -> ContentAnalyzer:
    """
    Create content analyzer instance.

    Args:
        text: Text to analyze

    Returns:
        ContentAnalyzer instance
    """
    return ContentAnalyzer(text)
