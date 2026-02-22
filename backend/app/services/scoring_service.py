import uuid
from collections import defaultdict
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.models.audit_query import AuditQuery
from app.models.brand_mention import BrandMention
from app.models.engine_response import EngineResponse
from app.models.visibility_score import VisibilityScore


class ScoringService:
    """Computes 0-100 visibility scores from brand mentions.

    Uses a weighted formula: 40% mention rate, 30% position, 30% prominence.
    Produces per-engine breakdown and an overall audit score.
    """

    ALGORITHM_VERSION = "v1"

    def __init__(self, db: Session):
        self.db = db

    def compute_audit_score(self, audit_id: str, total_queries: int) -> VisibilityScore:
        """Compute visibility score for an audit.

        Loads all BrandMention records for the audit (via EngineResponse -> AuditQuery),
        groups by engine, computes per-engine and overall scores.

        Args:
            audit_id: UUID of the audit.
            total_queries: Total number of queries in the audit.

        Returns:
            VisibilityScore model instance (caller manages persistence).
        """
        # Load all mentions for this audit
        mentions = (
            self.db.query(BrandMention)
            .join(EngineResponse)
            .join(AuditQuery)
            .filter(AuditQuery.audit_id == audit_id)
            .all()
        )

        # Load successful engine responses grouped by engine
        successful_responses = (
            self.db.query(EngineResponse)
            .join(AuditQuery)
            .filter(
                AuditQuery.audit_id == audit_id,
                EngineResponse.error_message.is_(None),
            )
            .all()
        )

        # Group responses by engine
        responses_by_engine: dict[str, list[EngineResponse]] = defaultdict(list)
        for resp in successful_responses:
            responses_by_engine[resp.engine].append(resp)

        # Group mentions by engine (via their engine_response)
        mentions_by_engine: dict[str, list[BrandMention]] = defaultdict(list)
        response_engine_map: dict[str, str] = {}
        for resp in successful_responses:
            response_engine_map[str(resp.id)] = resp.engine
        for mention in mentions:
            engine = response_engine_map.get(str(mention.engine_response_id))
            if engine:
                mentions_by_engine[engine].append(mention)

        # Compute per-engine scores
        per_engine_scores: dict[str, int] = {}
        for engine, engine_responses in responses_by_engine.items():
            engine_mentions = mentions_by_engine.get(engine, [])
            # Group mentions by response
            mentions_by_response: dict[str, list[BrandMention]] = defaultdict(list)
            for m in engine_mentions:
                mentions_by_response[str(m.engine_response_id)].append(m)

            score = self._compute_per_engine_score(
                mentions_by_response=mentions_by_response,
                total_responses_for_engine=len(engine_responses),
            )
            per_engine_scores[engine] = score
            logger.info(
                "Engine '{}' score: {} (responses={}, mentions={})",
                engine,
                score,
                len(engine_responses),
                len(engine_mentions),
            )

        # Overall score = average of engine scores (0 if no engines)
        if per_engine_scores:
            overall_score = round(sum(per_engine_scores.values()) / len(per_engine_scores))
        else:
            overall_score = 0

        # Mention count
        mention_count = len(mentions)

        # Query mention rate: percentage of (query, engine) pairs with at least one mention
        total_response_pairs = len(successful_responses)
        responses_with_mentions = sum(
            1 for resp in successful_responses
            if any(str(m.engine_response_id) == str(resp.id) for m in mentions)
        )
        query_mention_rate = Decimal(
            str(round((responses_with_mentions / total_response_pairs * 100) if total_response_pairs > 0 else 0, 2))
        )

        logger.info(
            "Audit {} overall score: {} (engines={}, mentions={}, rate={}%)",
            audit_id,
            overall_score,
            len(per_engine_scores),
            mention_count,
            query_mention_rate,
        )

        return VisibilityScore(
            id=uuid.uuid4(),
            audit_id=audit_id,
            overall_score=overall_score,
            per_engine_scores=per_engine_scores,
            mention_count=mention_count,
            query_mention_rate=query_mention_rate,
            algorithm_version=self.ALGORITHM_VERSION,
        )

    def _compute_per_engine_score(
        self,
        mentions_by_response: dict[str, list[BrandMention]],
        total_responses_for_engine: int,
    ) -> int:
        """Compute score for one engine using weighted formula.

        - mention_rate (40%): % of responses with at least one mention
        - position_score (30%): average normalized position of first mention
        - prominence_score (30%): average confidence of best mention per response

        Returns 0-100 clamped integer.
        """
        if total_responses_for_engine == 0:
            return 0

        # Mention rate: % of responses that have mentions
        responses_with_mentions = len(mentions_by_response)
        mention_rate = (responses_with_mentions / total_responses_for_engine) * 100

        # Position and prominence scores from responses that have mentions
        position_scores: list[float] = []
        prominence_scores: list[float] = []

        for response_id, response_mentions in mentions_by_response.items():
            if not response_mentions:
                continue

            # First mention position (lowest char_offset)
            first_offset = min(m.char_offset for m in response_mentions)
            # Normalize: 100 - (offset / 20), clamped to 0-100
            # Earlier mentions get higher scores
            pos_score = max(0.0, min(100.0, 100.0 - (first_offset / 20.0)))
            position_scores.append(pos_score)

            # Best mention confidence
            best_confidence = max(m.confidence for m in response_mentions)
            prominence_scores.append(float(best_confidence))

        # Average position and prominence (0 if no mentions)
        avg_position = sum(position_scores) / len(position_scores) if position_scores else 0.0
        avg_prominence = sum(prominence_scores) / len(prominence_scores) if prominence_scores else 0.0

        # Weighted formula
        score = mention_rate * 0.40 + avg_position * 0.30 + avg_prominence * 0.30

        # Clamp to 0-100
        return round(max(0.0, min(100.0, score)))
