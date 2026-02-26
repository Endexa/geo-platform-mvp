# Plan 05-01 Summary: ReportService + API Endpoints

**Status:** Complete
**Duration:** ~4min
**Commit:** 9a32edaf

## What Was Built

### ReportService (`backend/app/services/report_service.py`)
- `_build_context(audit_id)`: Loads Audit, PageScore, VisibilityScore, AuditRecommendation, DiscoveredCompetitor, CompetitorAudit and assembles template context dict with safe defaults
- `_generate_executive_summary()`: Static method producing summary paragraph with optimization assessment and top priority
- `render_html(audit_id)`: Renders Jinja2 template to HTML string
- `render_pdf(audit_id)`: Renders HTML then converts to PDF bytes via WeasyPrint
- `export_csv(audit_id, fields, grouping, epic_link)`: Jira-compatible CSV with BOM prefix, configurable field list, grouping by category/priority/page, optional epic link column

### Reports API Router (`backend/app/api/reports.py`)
- `GET /api/v1/reports/{audit_id}/pdf` - PDF download (application/pdf)
- `GET /api/v1/reports/{audit_id}/html` - HTML download (text/html)
- `GET /api/v1/reports/{audit_id}/csv` - CSV download (text/csv) with query params: grouping, epic_link, fields
- All 3 endpoints gated behind `require_tier(SubscriptionTier.PRO)`
- All verify audit ownership (404/403)

### Template Updates (`backend/app/templates/audit_report.html`)
- Added Executive Summary section after header
- Added enriched per-engine table (Mention Rate, Queries Sent, Confidence) with fallback to legacy format
- Added pages scored/discovered info in category scores section
- Added CSS for `.executive-summary` and `.pages-info`

### Router Registration (`backend/app/main.py`)
- Reports router registered after payments router

## Verification
- ReportService imports cleanly with all 5 methods
- All 3 routes registered in FastAPI app
- All routes have require_tier dependency
- Combined GEO score uses correct formula: round(visibility * 0.15 + optimization * 0.85)

## Decisions
- Template directory resolved via `os.path.dirname` relative path (not hardcoded "app/templates")
- Per-engine breakdown uses ENGINE_DISPLAY_NAMES from schemas/audit.py for consistent naming
- CSV priority mapping: high -> Highest, medium -> Medium, low -> Low (Jira standard)
- Executive summary thresholds: >=70 strong, >=40 moderate, <40 needs work
