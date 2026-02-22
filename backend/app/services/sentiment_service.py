"""LLM-based sentiment classification for brand mentions.

Classifies each BrandMention.context_quote as positive/negative/neutral using
gemini-2.5-flash via LiteLLM JSON mode. Runs once per audit at completion time
(batch), storing results in the MentionSentiment table. Per-engine aggregation
is computed at query time via a single GROUP BY query.

CRITICAL: API key must be passed explicitly to litellm.completion() because
pydantic-settings loads .env into Settings, NOT into os.environ.
"""

import json

import litellm
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_query import AuditQuery
from app.models.brand_mention import BrandMention
from app.models.engine_response import EngineResponse
from app.models.mention_sentiment import MentionSentiment


class SentimentService:
    """Classify brand mention sentiments using LLM zero-shot classification."""

    SENTIMENT_MODEL = "gemini/gemini-2.5-flash"

    def __init__(self, db: Session):
        self.db = db

    def classify_mention_sentiment(self, context_quote: str) -> dict:
        """Classify a single mention's sentiment.

        Returns:
            dict with "sentiment" (positive/negative/neutral) and "confidence" (0-100).
            Falls back to neutral with 50 confidence if no API key or on error.
        """
        if not settings.GEMINI_API_KEY:
            return {"sentiment": "neutral", "confidence": 50}

        try:
            response = litellm.completion(
                model=self.SENTIMENT_MODEL,
                api_key=settings.GEMINI_API_KEY,
                response_format={"type": "json_object"},
                temperature=0.0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a brand mention sentiment classifier. "
                            "Classify the brand mention as positive, negative, or neutral. "
                            "Consider the full context -- a mention can be positive even if "
                            "it includes a minor caveat, and negative even if politely worded. "
                            "Return only valid JSON: "
                            '{"sentiment": "positive" | "negative" | "neutral", "confidence": 0-100}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f'Classify the sentiment of this brand mention:\n\n'
                            f'"{context_quote}"'
                        ),
                    },
                ],
            )
            result = json.loads(response.choices[0].message.content)
            # Validate response shape
            sentiment = result.get("sentiment", "neutral")
            if sentiment not in ("positive", "negative", "neutral"):
                sentiment = "neutral"
            confidence = result.get("confidence", 50)
            if not isinstance(confidence, int) or confidence < 0 or confidence > 100:
                confidence = 50
            return {"sentiment": sentiment, "confidence": confidence}
        except Exception as e:
            logger.warning("Sentiment LLM call failed: {}", str(e))
            return {"sentiment": "neutral", "confidence": 50}

    def analyze_audit_sentiments(
        self, audit_id: str
    ) -> list[MentionSentiment]:
        """Batch-classify all brand mentions for an audit.

        Queries BrandMention records joined through EngineResponse and AuditQuery
        to get the engine name. Creates a MentionSentiment record for each.

        Each classification is wrapped in try/except to ensure one failed
        LLM call doesn't block the rest.
        """
        mention_rows = (
            self.db.query(BrandMention, EngineResponse.engine)
            .join(
                EngineResponse,
                BrandMention.engine_response_id == EngineResponse.id,
            )
            .join(
                AuditQuery,
                EngineResponse.audit_query_id == AuditQuery.id,
            )
            .filter(AuditQuery.audit_id == audit_id)
            .all()
        )

        if not mention_rows:
            logger.debug("Audit {}: no brand mentions to classify", audit_id)
            return []

        logger.info(
            "Audit {}: classifying sentiment for {} mentions",
            audit_id,
            len(mention_rows),
        )

        results: list[MentionSentiment] = []
        for mention, engine in mention_rows:
            try:
                classification = self.classify_mention_sentiment(
                    mention.context_quote
                )
                record = MentionSentiment(
                    audit_id=audit_id,
                    brand_mention_id=mention.id,
                    engine=engine,
                    sentiment=classification.get("sentiment", "neutral"),
                    confidence=classification.get("confidence", 50),
                    context_quote=mention.context_quote,
                )
                self.db.add(record)
                results.append(record)
            except Exception as e:
                logger.warning(
                    "Sentiment classification failed for mention {}: {}",
                    mention.id,
                    str(e),
                )

        self.db.flush()
        logger.info(
            "Audit {}: classified {}/{} mentions",
            audit_id,
            len(results),
            len(mention_rows),
        )
        return results

    def get_per_engine_summary(self, audit_id: str) -> dict[str, dict]:
        """Return per-engine sentiment breakdown for display.

        Single aggregating SQL query using GROUP BY engine + sentiment.
        Returns dict: {engine_name: {positive: N, negative: N, neutral: N,
                                      total: N, dominant: "positive"|...}}
        """
        rows = (
            self.db.query(
                MentionSentiment.engine,
                MentionSentiment.sentiment,
                func.count(MentionSentiment.id).label("count"),
            )
            .filter(MentionSentiment.audit_id == audit_id)
            .group_by(MentionSentiment.engine, MentionSentiment.sentiment)
            .all()
        )

        summary: dict[str, dict] = {}
        for engine, sentiment, count in rows:
            if engine not in summary:
                summary[engine] = {
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0,
                    "total": 0,
                }
            summary[engine][sentiment] = count
            summary[engine]["total"] += count

        # Determine dominant sentiment per engine
        for engine_data in summary.values():
            if engine_data["total"] > 0:
                engine_data["dominant"] = max(
                    ["positive", "negative", "neutral"],
                    key=lambda s: engine_data[s],
                )
            else:
                engine_data["dominant"] = "neutral"

        return summary
