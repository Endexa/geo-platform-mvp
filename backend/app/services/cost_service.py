from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_cost import AuditCostLedger


class CostTrackingService:
    """Tracks per-audit API costs and enforces budget caps."""

    def __init__(self, db: Session):
        self.db = db

    def record_cost(
        self,
        audit_id: UUID,
        engine: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: Decimal,
        cached: bool = False,
    ) -> AuditCostLedger:
        """Create and persist a cost ledger entry. Returns the created entry."""
        entry = AuditCostLedger(
            audit_id=audit_id,
            engine=engine,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            cached=cached,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_audit_spend(self, audit_id: UUID) -> Decimal:
        """Return total USD spent for an audit. Returns Decimal('0') if no entries."""
        result = (
            self.db.query(func.sum(AuditCostLedger.cost_usd))
            .filter(AuditCostLedger.audit_id == audit_id)
            .scalar()
        )
        return Decimal(str(result)) if result is not None else Decimal("0")

    def get_audit_cost_breakdown(self, audit_id: UUID) -> list[dict]:
        """Return per-engine cost summary for an audit.

        Returns list of dicts:
            [{"engine": "openai", "total_cost": Decimal, "request_count": int}, ...]
        """
        rows = (
            self.db.query(
                AuditCostLedger.engine,
                func.sum(AuditCostLedger.cost_usd).label("total_cost"),
                func.count(AuditCostLedger.id).label("request_count"),
            )
            .filter(AuditCostLedger.audit_id == audit_id)
            .group_by(AuditCostLedger.engine)
            .all()
        )
        return [
            {
                "engine": row.engine,
                "total_cost": Decimal(str(row.total_cost)),
                "request_count": row.request_count,
            }
            for row in rows
        ]

    def check_budget(
        self, audit_id: UUID, budget_usd: Decimal | None = None
    ) -> bool:
        """Check if audit spend is within budget.

        Returns True if within budget, False if exceeded.
        Defaults to settings.AUDIT_BUDGET_USD if no budget provided.
        """
        if budget_usd is None:
            budget_usd = Decimal(str(settings.AUDIT_BUDGET_USD))
        spend = self.get_audit_spend(audit_id)
        return spend <= budget_usd

    def get_remaining_budget(
        self, audit_id: UUID, budget_usd: Decimal | None = None
    ) -> Decimal:
        """Return remaining budget for an audit, clamped to 0 minimum."""
        if budget_usd is None:
            budget_usd = Decimal(str(settings.AUDIT_BUDGET_USD))
        spend = self.get_audit_spend(audit_id)
        remaining = budget_usd - spend
        return max(remaining, Decimal("0"))
