"""Dashboard aggregation and export service.

Provides methods to aggregate audit data for the dashboard overview,
fetch audit history for trend charts, and export full reports as
PDF (WeasyPrint) or CSV.
"""

import csv
import io
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader
from loguru import logger
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.models.audit import Audit
from app.models.audit_recommendation import AuditRecommendation
from app.models.competitor import CompetitorAudit, DiscoveredCompetitor
from app.models.engine_response import EngineResponse
from app.models.mention_sentiment import MentionSentiment
from app.models.page_score import PageScore
from app.models.visibility_score import VisibilityScore


class DashboardService:
    """Aggregates audit data for dashboard display and report export."""

    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, audit_id: str, user_id: str) -> dict:
        """Aggregate all dashboard data for a single audit.

        Returns a dict matching DashboardOverviewResponse fields.

        Raises:
            ValueError: If audit not found or not owned by user.
        """
        audit = self.db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise ValueError("Audit not found")
        if str(audit.user_id) != user_id:
            raise ValueError("Access denied")

        # Visibility score
        vs = (
            self.db.query(VisibilityScore)
            .filter(VisibilityScore.audit_id == audit_id)
            .first()
        )

        visibility = vs.overall_score if vs else 0
        optimization = audit.optimization_score or 0
        combined = round(visibility * 0.5 + optimization * 0.5)

        # Top 5 high-priority open recommendations
        top_recs = (
            self.db.query(AuditRecommendation)
            .filter(
                AuditRecommendation.audit_id == audit_id,
                AuditRecommendation.priority == "high",
                AuditRecommendation.status == "open",
            )
            .order_by(AuditRecommendation.gap_score.desc())
            .limit(5)
            .all()
        )

        # Top 5 competitors by share of voice
        competitors = (
            self.db.query(DiscoveredCompetitor)
            .filter(
                DiscoveredCompetitor.audit_id == audit_id,
                DiscoveredCompetitor.is_user_brand == False,  # noqa: E712
            )
            .order_by(DiscoveredCompetitor.share_of_voice.desc())
            .limit(5)
            .all()
        )

        # Competitor audit scores
        comp_audits = (
            self.db.query(CompetitorAudit)
            .filter(
                CompetitorAudit.parent_audit_id == audit_id,
                CompetitorAudit.status == "completed",
            )
            .all()
        )
        comp_audit_map = {ca.competitor_name: ca for ca in comp_audits}

        # User's page-level category averages
        page_scores = (
            self.db.query(PageScore)
            .filter(
                PageScore.audit_id == audit_id,
                PageScore.was_scored == True,  # noqa: E712
            )
            .all()
        )

        user_category_avgs = self._compute_category_averages(page_scores)

        # Build competitive position
        user_scores = {
            "visibility": float(visibility),
            "optimization": float(optimization),
            "crawlability": user_category_avgs.get("crawlability", 0),
            "content": user_category_avgs.get("content_structure", 0),
            "schema": user_category_avgs.get("structured_data", 0),
            "authority": user_category_avgs.get("authority", 0),
        }

        competitor_entries = []
        for comp in competitors:
            ca = comp_audit_map.get(comp.entity_name)
            comp_scores = {
                "visibility": float(comp.share_of_voice or 0),
                "optimization": float(ca.optimization_score or 0) if ca else 0,
                "crawlability": float(ca.crawlability_avg or 0) if ca else 0,
                "content": float(ca.content_structure_avg or 0) if ca else 0,
                "schema": float(ca.structured_data_avg or 0) if ca else 0,
                "authority": float(ca.authority_avg or 0) if ca else 0,
            }
            competitor_entries.append(
                {
                    "name": comp.entity_name,
                    "share_of_voice": float(comp.share_of_voice or 0),
                    "scores": comp_scores,
                }
            )

        # Recommendation progress
        all_recs = (
            self.db.query(AuditRecommendation)
            .filter(AuditRecommendation.audit_id == audit_id)
            .all()
        )
        progress = {"done": 0, "dismissed": 0, "open": 0, "total": len(all_recs)}
        for rec in all_recs:
            progress[rec.status] = progress.get(rec.status, 0) + 1

        return {
            "audit_id": str(audit.id),
            "domain": audit.domain,
            "url": audit.url,
            "completed_at": (
                audit.completed_at.isoformat() if audit.completed_at else None
            ),
            "combined_geo_score": combined,
            "visibility_score": visibility,
            "optimization_score": optimization,
            "per_engine_scores": vs.per_engine_scores if vs else {},
            "mention_count": vs.mention_count if vs else 0,
            "query_mention_rate": float(vs.query_mention_rate) if vs else 0.0,
            "top_issues": [
                {
                    "id": str(r.id),
                    "page_url": r.page_url,
                    "criterion_id": r.criterion_id,
                    "criterion_name": r.criterion_name,
                    "category": r.category,
                    "priority": r.priority,
                    "impact_label": r.impact_label,
                    "summary": r.summary,
                    "gap_score": r.gap_score,
                }
                for r in top_recs
            ],
            "competitive_position": {
                "user_scores": user_scores,
                "competitors": competitor_entries,
            },
            "recommendation_progress": progress,
        }

    def get_audit_history(self, domain: str, user_id: str) -> dict:
        """Get all completed audits for a domain, ordered by date.

        Filters by both domain AND user_id to prevent cross-user data leakage.

        Returns dict with domain, entries list, and total count.
        """
        audits = (
            self.db.query(Audit)
            .filter(
                Audit.domain == domain,
                Audit.user_id == user_id,
                Audit.status == "completed",
            )
            .order_by(Audit.created_at.asc())
            .all()
        )

        entries = []
        for audit in audits:
            vs = (
                self.db.query(VisibilityScore)
                .filter(VisibilityScore.audit_id == audit.id)
                .first()
            )

            vis = vs.overall_score if vs else 0
            opt = audit.optimization_score or 0

            # Compute category averages from page scores
            page_scores = (
                self.db.query(PageScore)
                .filter(
                    PageScore.audit_id == audit.id,
                    PageScore.was_scored == True,  # noqa: E712
                )
                .all()
            )
            cat_avgs = self._compute_category_averages(page_scores)

            entries.append(
                {
                    "audit_id": str(audit.id),
                    "date": (
                        audit.completed_at.isoformat()
                        if audit.completed_at
                        else audit.created_at.isoformat()
                    ),
                    "visibility_score": vis,
                    "optimization_score": opt,
                    "combined_score": round(vis * 0.5 + opt * 0.5),
                    "mention_count": vs.mention_count if vs else 0,
                    "per_engine_scores": vs.per_engine_scores if vs else {},
                    "crawlability_avg": cat_avgs["crawlability"],
                    "content_structure_avg": cat_avgs["content_structure"],
                    "structured_data_avg": cat_avgs["structured_data"],
                    "authority_avg": cat_avgs["authority"],
                }
            )

        return {
            "domain": domain,
            "entries": entries,
            "total": len(entries),
        }

    def _gather_full_report_data(self, audit_id: str, user_id: str) -> dict:
        """Comprehensive data collection for PDF/CSV export.

        Includes all scores, recommendations, competitors, page scores,
        engine responses, sentiment data, and content gaps.
        """
        overview = self.get_overview(audit_id, user_id)

        # All recommendations (not just top 5)
        all_recs = (
            self.db.query(AuditRecommendation)
            .filter(AuditRecommendation.audit_id == audit_id)
            .order_by(
                AuditRecommendation.priority,
                AuditRecommendation.gap_score.desc(),
            )
            .all()
        )

        # All competitors
        all_competitors = (
            self.db.query(DiscoveredCompetitor)
            .filter(
                DiscoveredCompetitor.audit_id == audit_id,
                DiscoveredCompetitor.is_user_brand == False,  # noqa: E712
            )
            .order_by(DiscoveredCompetitor.share_of_voice.desc())
            .all()
        )

        # Competitor audits
        comp_audits = (
            self.db.query(CompetitorAudit)
            .filter(
                CompetitorAudit.parent_audit_id == audit_id,
                CompetitorAudit.status == "completed",
            )
            .all()
        )

        # Page scores with category breakdowns
        page_scores = (
            self.db.query(PageScore)
            .filter(
                PageScore.audit_id == audit_id,
                PageScore.was_scored == True,  # noqa: E712
            )
            .all()
        )

        # Sentiment data
        sentiments = (
            self.db.query(MentionSentiment)
            .filter(MentionSentiment.audit_id == audit_id)
            .all()
        )

        # Content gaps from audit JSONB column
        audit = self.db.query(Audit).filter(Audit.id == audit_id).first()
        content_gaps = audit.content_gaps or []

        # Category averages for user
        category_avgs = self._compute_category_averages(page_scores)

        return {
            **overview,
            "generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
            "recommendations": all_recs,
            "all_competitors": all_competitors,
            "competitor_audits": comp_audits,
            "page_scores": page_scores,
            "sentiments": sentiments,
            "content_gaps": content_gaps,
            "category_averages": category_avgs,
        }

    def export_pdf(self, audit_id: str, user_id: str) -> tuple[bytes, str]:
        """Generate PDF report for an audit.

        Returns tuple of (pdf_bytes, domain) for response construction.
        """
        data = self._gather_full_report_data(audit_id, user_id)

        env = Environment(loader=FileSystemLoader("app/templates"))
        template = env.get_template("audit_report.html")
        html_content = template.render(**data)

        pdf_bytes = HTML(string=html_content).write_pdf()
        logger.info(
            "PDF report generated for audit {} ({} bytes)",
            audit_id,
            len(pdf_bytes),
        )
        return pdf_bytes, data["domain"]

    def export_csv(self, audit_id: str, user_id: str) -> tuple[str, str]:
        """Generate CSV report content for an audit.

        Returns tuple of (csv_content, domain) for response construction.
        """
        data = self._gather_full_report_data(audit_id, user_id)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header section
        writer.writerow(["GEO Audit Report", data["domain"]])
        writer.writerow(["Generated", data["generated_at"]])
        writer.writerow(["URL", data["url"]])
        writer.writerow([])

        # Scores section
        writer.writerow(["Score Type", "Value"])
        writer.writerow(["Combined GEO Score", data["combined_geo_score"]])
        writer.writerow(["Visibility Score", data["visibility_score"]])
        writer.writerow(["Optimization Score", data["optimization_score"]])
        writer.writerow([])

        # Per-engine breakdown
        writer.writerow(["Engine", "Score"])
        for engine, score in data["per_engine_scores"].items():
            writer.writerow([engine, score])
        writer.writerow([])

        # Category scores
        writer.writerow(["Category", "Average Score"])
        for cat_key, cat_label in [
            ("crawlability", "Crawlability"),
            ("content_structure", "Content Structure"),
            ("structured_data", "Structured Data"),
            ("authority", "Authority"),
        ]:
            writer.writerow(
                [cat_label, data["category_averages"].get(cat_key, "N/A")]
            )
        writer.writerow([])

        # Recommendations
        writer.writerow(
            ["Priority", "Category", "Criterion", "Summary", "Gap", "Impact", "Status"]
        )
        for rec in data["recommendations"]:
            writer.writerow(
                [
                    rec.priority,
                    rec.category,
                    rec.criterion_name,
                    rec.summary,
                    rec.gap_score,
                    rec.impact_label,
                    rec.status,
                ]
            )
        writer.writerow([])

        # Content Gaps
        writer.writerow(["Content Gaps"])
        writer.writerow(["Query", "Competitors Mentioned", "Suggested Title"])
        for gap in data["content_gaps"]:
            competitors_str = "; ".join(gap.get("competitors_mentioned", []))
            brief = gap.get("brief", {})
            writer.writerow(
                [
                    gap.get("query_text", ""),
                    competitors_str,
                    brief.get("title", ""),
                ]
            )
        writer.writerow([])

        # Competitors
        writer.writerow(["Competitor", "Share of Voice (%)", "Optimization Score", "URL"])
        for comp in data["all_competitors"]:
            ca_match = next(
                (
                    ca
                    for ca in data["competitor_audits"]
                    if ca.competitor_name == comp.entity_name
                ),
                None,
            )
            writer.writerow(
                [
                    comp.entity_name,
                    float(comp.share_of_voice or 0),
                    ca_match.optimization_score if ca_match else "N/A",
                    comp.resolved_url or "N/A",
                ]
            )

        logger.info("CSV report generated for audit {}", audit_id)
        return output.getvalue(), data["domain"]

    @staticmethod
    def _compute_category_averages(page_scores: list) -> dict:
        """Compute average category scores across all scored pages."""
        if not page_scores:
            return {
                "crawlability": 0,
                "content_structure": 0,
                "structured_data": 0,
                "authority": 0,
            }

        totals = {
            "crawlability": 0,
            "content_structure": 0,
            "structured_data": 0,
            "authority": 0,
        }
        counts = {
            "crawlability": 0,
            "content_structure": 0,
            "structured_data": 0,
            "authority": 0,
        }

        for ps in page_scores:
            if ps.crawlability_score is not None:
                totals["crawlability"] += ps.crawlability_score
                counts["crawlability"] += 1
            if ps.content_structure_score is not None:
                totals["content_structure"] += ps.content_structure_score
                counts["content_structure"] += 1
            if ps.structured_data_score is not None:
                totals["structured_data"] += ps.structured_data_score
                counts["structured_data"] += 1
            if ps.authority_score is not None:
                totals["authority"] += ps.authority_score
                counts["authority"] += 1

        return {
            key: round(totals[key] / counts[key]) if counts[key] > 0 else 0
            for key in totals
        }
