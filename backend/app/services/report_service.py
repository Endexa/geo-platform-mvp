"""Report generation service for HTML/PDF audit reports and Jira CSV export.

Assembles audit data into template context, renders HTML via Jinja2,
converts to PDF via WeasyPrint, and exports recommendations as Jira-
compatible CSV.
"""

import csv
import io
import os
from datetime import datetime, timezone

import weasyprint
from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader
from loguru import logger
from sqlalchemy.orm import Session

from app.models.audit import Audit, AuditStatus
from app.models.audit_recommendation import AuditRecommendation
from app.models.competitor import CompetitorAudit, DiscoveredCompetitor
from app.models.page_score import PageScore
from app.models.visibility_score import VisibilityScore
from app.schemas.audit import ENGINE_DISPLAY_NAMES

# Priority mapping for Jira CSV export
JIRA_PRIORITY_MAP = {"high": "Highest", "medium": "Medium", "low": "Low"}


class ReportService:
    """Generates HTML/PDF audit reports and Jira-compatible CSV exports."""

    def __init__(self, db: Session):
        self.db = db
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "templates"
        )
        self.template_env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True,
        )

    def _build_context(self, audit_id: str) -> dict:
        """Assemble all audit data into a template context dict.

        Args:
            audit_id: UUID string for the audit.

        Returns:
            Dictionary with all values needed to render the report template.

        Raises:
            HTTPException 404 if audit not found or not completed.
        """
        audit = self.db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit or audit.status != AuditStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Completed audit not found",
            )

        # Page scores
        page_scores = (
            self.db.query(PageScore)
            .filter(PageScore.audit_id == audit_id)
            .all()
        )

        # Visibility score
        vis = (
            self.db.query(VisibilityScore)
            .filter(VisibilityScore.audit_id == audit_id)
            .first()
        )

        # Recommendations ordered by priority then gap_score desc
        recommendations = (
            self.db.query(AuditRecommendation)
            .filter(AuditRecommendation.audit_id == audit_id)
            .order_by(
                AuditRecommendation.priority,
                AuditRecommendation.gap_score.desc(),
            )
            .all()
        )

        # Competitors
        all_competitors = (
            self.db.query(DiscoveredCompetitor)
            .filter(DiscoveredCompetitor.audit_id == audit_id)
            .all()
        )

        competitor_audits = (
            self.db.query(CompetitorAudit)
            .filter(CompetitorAudit.parent_audit_id == audit_id)
            .all()
        )

        # Scores with safe defaults
        visibility_score = vis.overall_score if vis else 0
        optimization_score = audit.optimization_score or 0
        combined_geo_score = round(visibility_score * 0.15 + optimization_score * 0.85)
        mention_count = vis.mention_count if vis else 0
        confidence_level = vis.confidence_level if vis else "not_measured"

        # Per-engine scores -- handle both old and enriched formats
        per_engine_scores = {}
        per_engine_breakdown = []
        if vis and vis.per_engine_scores:
            for engine_key, value in vis.per_engine_scores.items():
                display_name = ENGINE_DISPLAY_NAMES.get(engine_key, engine_key.capitalize())
                if isinstance(value, dict):
                    # Enriched format: {"score": 75, "queries_sent": 10, ...}
                    per_engine_scores[display_name] = value.get("score", 0)
                    per_engine_breakdown.append({
                        "engine_key": engine_key,
                        "display_name": display_name,
                        "score": value.get("score", 0),
                        "queries_sent": value.get("queries_sent", 0),
                        "queries_with_mentions": value.get("queries_with_mentions", 0),
                        "mention_rate": value.get("mention_rate", 0),
                        "total_mentions": value.get("total_mentions", 0),
                        "confidence_level": value.get("confidence_level", "not_measured"),
                    })
                else:
                    # Legacy format: {"openai": 75}
                    per_engine_scores[display_name] = value

        # Category averages from page scores
        scored_pages = [p for p in page_scores if p.was_scored]
        category_averages = {
            "crawlability": 0,
            "content_structure": 0,
            "structured_data": 0,
            "authority": 0,
        }
        if scored_pages:
            def _avg(attr):
                vals = [getattr(p, attr) for p in scored_pages if getattr(p, attr) is not None]
                return round(sum(vals) / len(vals)) if vals else 0

            category_averages["crawlability"] = _avg("crawlability_score")
            category_averages["content_structure"] = _avg("content_structure_score")
            category_averages["structured_data"] = _avg("structured_data_score")
            category_averages["authority"] = _avg("authority_score")

        # Executive summary
        executive_summary = self._generate_executive_summary(
            domain=audit.domain,
            optimization_score=optimization_score,
            visibility_score=visibility_score,
            recommendations=recommendations,
        )

        # Content gaps
        content_gaps = audit.content_gaps or []

        # Timestamps
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        completed_at = (
            audit.completed_at.strftime("%Y-%m-%d %H:%M UTC")
            if audit.completed_at
            else None
        )

        return {
            "domain": audit.domain,
            "url": audit.url,
            "generated_at": generated_at,
            "completed_at": completed_at,
            "visibility_score": visibility_score,
            "optimization_score": optimization_score,
            "combined_geo_score": combined_geo_score,
            "mention_count": mention_count,
            "confidence_level": confidence_level,
            "per_engine_scores": per_engine_scores,
            "per_engine_breakdown": per_engine_breakdown,
            "category_averages": category_averages,
            "recommendations": recommendations,
            "content_gaps": content_gaps,
            "all_competitors": all_competitors,
            "competitor_audits": competitor_audits,
            "executive_summary": executive_summary,
            "pages_scored": len(scored_pages),
            "pages_discovered": len(page_scores),
        }

    @staticmethod
    def _generate_executive_summary(
        domain: str,
        optimization_score: int,
        visibility_score: int,
        recommendations: list,
    ) -> str:
        """Generate an executive summary paragraph from audit data.

        Args:
            domain: The audited domain.
            optimization_score: 0-100 optimization score.
            visibility_score: 0-100 AI visibility score.
            recommendations: List of AuditRecommendation objects.

        Returns:
            A formatted summary paragraph string.
        """
        parts = [
            f"Audit of {domain} scored {optimization_score}/100 for optimization "
            f"and {visibility_score}/100 for AI visibility."
        ]

        if optimization_score >= 70:
            parts.append("The site demonstrates strong optimization fundamentals.")
        elif optimization_score >= 40:
            parts.append(
                "The site has a moderate optimization foundation "
                "with room for improvement."
            )
        else:
            parts.append("The site needs significant optimization work.")

        # Top priority recommendation
        high_recs = [r for r in recommendations if r.priority == "high"]
        if high_recs:
            parts.append(f"Top priority: {high_recs[0].summary}")
        else:
            parts.append("No critical issues found.")

        # Recommendation summary
        categories = set(r.category for r in recommendations)
        parts.append(
            f"{len(recommendations)} recommendations identified "
            f"across {len(categories)} categories."
        )

        return " ".join(parts)

    def render_html(self, audit_id: str) -> str:
        """Render an audit report as an HTML string.

        Args:
            audit_id: UUID string for the audit.

        Returns:
            Rendered HTML string.
        """
        ctx = self._build_context(audit_id)
        template = self.template_env.get_template("audit_report.html")
        return template.render(**ctx)

    def render_pdf(self, audit_id: str) -> bytes:
        """Render an audit report as PDF bytes.

        Args:
            audit_id: UUID string for the audit.

        Returns:
            PDF file content as bytes.
        """
        html_string = self.render_html(audit_id)
        logger.info("Rendering PDF for audit {}", audit_id)
        return weasyprint.HTML(string=html_string).write_pdf()

    def export_csv(
        self,
        audit_id: str,
        fields: list[str] | None = None,
        grouping: str = "category",
        epic_link: str | None = None,
    ) -> str:
        """Export recommendations as a Jira-compatible CSV string.

        Args:
            audit_id: UUID string for the audit.
            fields: Optional list of CSV column names. Defaults to Jira standard fields.
            grouping: Sort order -- "category", "priority", or "page".
            epic_link: Optional Jira epic key to include in every row.

        Returns:
            CSV string with UTF-8 BOM prefix for Excel compatibility.
        """
        # Load recommendations
        query = self.db.query(AuditRecommendation).filter(
            AuditRecommendation.audit_id == audit_id
        )

        # Apply ordering based on grouping
        if grouping == "priority":
            query = query.order_by(
                AuditRecommendation.priority,
                AuditRecommendation.gap_score.desc(),
            )
        elif grouping == "page":
            query = query.order_by(
                AuditRecommendation.page_url,
                AuditRecommendation.priority,
            )
        else:
            # Default: category
            query = query.order_by(
                AuditRecommendation.category,
                AuditRecommendation.priority,
                AuditRecommendation.gap_score.desc(),
            )

        recs = query.all()

        # Build field list
        default_fields = [
            "Summary",
            "Description",
            "Priority",
            "Labels",
            "Issue Type",
            "Component",
        ]
        if epic_link:
            default_fields.append("Epic Link")

        csv_fields = fields if fields else default_fields
        if epic_link and "Epic Link" not in csv_fields:
            csv_fields.append("Epic Link")

        # Write CSV with BOM for Excel
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.DictWriter(
            output, fieldnames=csv_fields, extrasaction="ignore"
        )
        writer.writeheader()

        for rec in recs:
            description_parts = rec.action_steps or []
            description = "\n".join(description_parts)
            if rec.code_snippet:
                description += "\n\nCode:\n" + rec.code_snippet

            row = {
                "Summary": rec.summary,
                "Description": description,
                "Priority": JIRA_PRIORITY_MAP.get(rec.priority, "Medium"),
                "Labels": rec.category,
                "Issue Type": "Task",
                "Component": rec.criterion_name,
            }
            if epic_link:
                row["Epic Link"] = epic_link

            writer.writerow(row)

        return output.getvalue()
