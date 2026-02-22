"""BaseScorer ABC and ScoringCriterionResult dataclass.

Defines the contract that all four category scorers must follow.
Each scorer implements score_page() to evaluate a single page against
all criteria in its category, returning ScoringCriterionResult instances.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScoringCriterionResult:
    """In-memory result from a single criterion evaluation.

    This is the data transfer object used by scorers -- distinct from the
    CriterionResult SQLAlchemy model used for DB persistence.
    """

    criterion_id: str  # e.g., "C1", "CS3"
    criterion_name: str  # e.g., "GPTBot access"
    score: int  # 0-100
    human_summary: str
    technical_detail: str
    max_score: int = 100
    is_binary: bool = False
    evidence: Optional[dict] = field(default=None)
    checked: bool = True  # False = could not check, excluded from scoring


class BaseScorer(ABC):
    """Abstract base class for category scorers.

    Each category scorer (Crawlability, Content Structure, Structured Data,
    Authority) inherits this and implements score_page() to evaluate all
    criteria in its category for a single page.
    """

    @abstractmethod
    async def score_page(self, page_data: dict) -> list[ScoringCriterionResult]:
        """Score a single page against all criteria in the category.

        Args:
            page_data: Dict containing crawl results for the page.
                       Typically a CrawlResult.model_dump() dict.

        Returns:
            List of ScoringCriterionResult, one per criterion.
        """
        ...

    def compute_category_score(self, results: list[ScoringCriterionResult]) -> float:
        """Compute weighted average of checked criteria only.

        Criteria with checked=False are excluded from the average.

        Args:
            results: List of criterion results from score_page().

        Returns:
            Category score as float (0.0-100.0), or 0.0 if no checked results.
        """
        checked = [r for r in results if r.checked]
        if not checked:
            return 0.0
        return sum(r.score for r in checked) / len(checked)

    def _not_checked(
        self, criterion_id: str, criterion_name: str, reason: str
    ) -> ScoringCriterionResult:
        """Create a ScoringCriterionResult for a criterion that could not be checked.

        Args:
            criterion_id: The criterion identifier (e.g., "C5").
            criterion_name: Human-readable criterion name.
            reason: Why the criterion could not be checked.

        Returns:
            ScoringCriterionResult with checked=False, score=0.
        """
        return ScoringCriterionResult(
            criterion_id=criterion_id,
            criterion_name=criterion_name,
            score=0,
            human_summary=f"Could not check: {reason}",
            technical_detail=reason,
            checked=False,
        )
