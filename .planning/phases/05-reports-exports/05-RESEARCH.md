# Phase 5: Reports + Exports - Research

**Researched:** 2026-02-26
**Domain:** PDF/HTML report generation, CSV export
**Confidence:** HIGH

## Summary

Phase 5 adds three export capabilities to completed audits: PDF report (executive-ready), HTML report (browser-viewable), and Jira-compatible CSV export for recommendations. The existing codebase already has WeasyPrint 68.1, Jinja2 3.1.6 installed, and a comprehensive HTML template at `backend/app/templates/audit_report.html` that covers scores, engine breakdown, category scores, recommendations, content gaps, and competitor landscape. The template uses the correct design system colors (#1E40AF primary, #F8FAFC background).

The primary work is: (1) a ReportService that assembles audit data into template context and renders HTML/PDF, (2) a CSV export service for Jira-compatible recommendation export with customizable fields, (3) API endpoints for downloading reports (tier-gated behind PRO), and (4) frontend download buttons on the audit results page.

**Primary recommendation:** Use existing WeasyPrint + Jinja2 stack. The HTML template already exists and covers 90% of report content -- extend it with per-engine enriched data format and action steps. CSV export uses Python stdlib `csv` module (no extra dependency).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RPT-01 | PDF audit report with scores, recommendations, charts | WeasyPrint renders HTML template to PDF; template already exists with score cards, category grid, recommendations table |
| RPT-02 | HTML version of audit report | Same Jinja2 template rendered as HTML string; served with text/html content type |
| RPT-03 | Jira-compatible CSV with customizable fields | Python csv.DictWriter with configurable column mapping; grouping/priority/epic fields |
| RPT-04 | Executive summary, per-category breakdown, top recommendations | Template already has score overview, category grid, recommendations table; add exec summary paragraph |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| WeasyPrint | 68.1 (installed) | HTML-to-PDF rendering | Best Python HTML-to-PDF: CSS support, @page rules, no headless browser needed |
| Jinja2 | 3.1.6 (installed) | HTML template engine | Already used by FastAPI ecosystem; template at `backend/app/templates/audit_report.html` |
| csv (stdlib) | Python 3.12 | CSV generation | No external dependency; DictWriter handles field mapping perfectly |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| io.StringIO/BytesIO | stdlib | In-memory stream for CSV/PDF bytes | Always -- no temp files needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | xhtml2pdf | Less CSS support, no flexbox, worse rendering |
| WeasyPrint | Playwright PDF | Heavier (headless browser), already have WeasyPrint |
| csv stdlib | pandas to_csv | Overkill for simple column export |

**Installation:** Nothing new needed -- all dependencies already in requirements.txt.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── services/
│   └── report_service.py     # ReportService: assemble data, render HTML/PDF, generate CSV
├── api/
│   └── reports.py            # Report API router: download endpoints
├── templates/
│   └── audit_report.html     # Existing Jinja2 template (extend for enriched data)
```

### Pattern 1: Service Layer for Report Generation
**What:** ReportService loads audit data, assembles template context, renders HTML via Jinja2, converts to PDF via WeasyPrint
**When to use:** All report/export endpoints delegate to this service
**Example:**
```python
class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.template_env = Environment(
            loader=FileSystemLoader("app/templates"),
            autoescape=True,
        )

    def _build_context(self, audit_id: str) -> dict:
        """Assemble all audit data into template context dict."""
        ...

    def render_html(self, audit_id: str) -> str:
        """Render audit report as HTML string."""
        ctx = self._build_context(audit_id)
        template = self.template_env.get_template("audit_report.html")
        return template.render(**ctx)

    def render_pdf(self, audit_id: str) -> bytes:
        """Render audit report as PDF bytes."""
        html = self.render_html(audit_id)
        return weasyprint.HTML(string=html).write_pdf()

    def export_csv(self, audit_id: str, fields: list[str] | None = None,
                   grouping: str = "category", epic_link: str | None = None) -> str:
        """Export recommendations as Jira-compatible CSV."""
        ...
```

### Pattern 2: Streaming Response for Large Files
**What:** Use FastAPI `Response` with appropriate content-type and Content-Disposition headers
**When to use:** All download endpoints
**Example:**
```python
@router.get("/{audit_id}/pdf")
def download_pdf(audit_id: str, ...):
    pdf_bytes = service.render_pdf(audit_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{domain}.pdf"'},
    )
```

### Pattern 3: Jira CSV Field Mapping
**What:** Configurable column mapping that produces Jira-importable CSV
**When to use:** CSV export endpoint with query params for field selection
**Jira CSV format requirements:**
- Summary (required) = recommendation summary
- Description = action steps joined
- Priority = mapped from high/medium/low to Jira values
- Issue Type = "Task" or "Story"
- Labels = category
- Epic Link = user-provided epic key (optional)
- Components = criterion category

### Anti-Patterns to Avoid
- **Writing temp files to disk:** Use BytesIO/StringIO for in-memory generation
- **Loading full crawl_data into template:** Template only needs derived scores, not raw crawl HTML
- **Generating reports synchronously for very large audits:** For MVP, sync is fine (reports are small); defer async to future if needed
- **Hardcoding CSV columns:** Make field list configurable via query params

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML to PDF | Custom Playwright script | WeasyPrint | Already installed, CSS @page support, no browser overhead |
| CSV generation | String concatenation | csv.DictWriter | Handles quoting, escaping, encoding edge cases |
| Template rendering | f-strings for HTML | Jinja2 Environment | Auto-escaping, template inheritance, filters |

**Key insight:** The existing HTML template covers 90% of the report -- the main work is wiring data assembly and adding the few missing sections (executive summary, enriched per-engine stats).

## Common Pitfalls

### Pitfall 1: WeasyPrint CSS Flexbox Rendering
**What goes wrong:** WeasyPrint's flexbox support is partial -- some flex properties render differently than in browsers
**Why it happens:** WeasyPrint uses its own rendering engine, not a browser engine
**How to avoid:** The existing template already uses flexbox (`display: flex`, `gap`) and is designed for WeasyPrint. Test PDF output visually after any template changes.
**Warning signs:** Score cards or category grid looking misaligned in PDF

### Pitfall 2: Unicode in CSV
**What goes wrong:** Excel opens UTF-8 CSV without BOM as garbled text
**Why it happens:** Excel defaults to Windows-1252 encoding
**How to avoid:** Write UTF-8 BOM (`\ufeff`) at start of CSV content
**Warning signs:** Non-ASCII characters (accented domains, international content) broken in Excel

### Pitfall 3: Large Response Bodies
**What goes wrong:** Reports with many pages/recommendations exceed memory
**Why it happens:** Entire PDF held in memory
**How to avoid:** For MVP scope this is not an issue (max ~20 pages scored, ~50 recs). Future: StreamingResponse for large reports.
**Warning signs:** >100 recommendations or >50 pages scored

### Pitfall 4: Missing Data Graceful Handling
**What goes wrong:** Template crashes on None values when audit is incomplete
**Why it happens:** Visibility score or optimization score may be None
**How to avoid:** Template already uses `{% if %}` guards. ReportService should default all context values.
**Warning signs:** 500 errors on report generation for partially-completed audits

## Code Examples

### WeasyPrint HTML to PDF
```python
import weasyprint
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("app/templates"), autoescape=True)
template = env.get_template("audit_report.html")
html_string = template.render(domain="example.com", visibility_score=75, ...)

# HTML to PDF in memory
pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()
```

### Jira CSV Export
```python
import csv
import io

def export_jira_csv(recommendations, fields=None, epic_link=None):
    default_fields = ["Summary", "Description", "Priority", "Labels", "Issue Type"]
    if epic_link:
        default_fields.append("Epic Link")
    fields = fields or default_fields

    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()

    PRIORITY_MAP = {"high": "Highest", "medium": "Medium", "low": "Low"}

    for rec in recommendations:
        row = {
            "Summary": rec.summary,
            "Description": "\n".join(rec.action_steps or []),
            "Priority": PRIORITY_MAP.get(rec.priority, "Medium"),
            "Labels": rec.category,
            "Issue Type": "Task",
        }
        if epic_link:
            row["Epic Link"] = epic_link
        writer.writerow(row)

    return output.getvalue()
```

### FastAPI Download Endpoint
```python
from fastapi import Response

@router.get("/{audit_id}/pdf",
            dependencies=[Depends(require_tier(SubscriptionTier.PRO))])
def download_pdf_report(audit_id: str, db=Depends(get_db), current_user=Depends(get_current_active_user)):
    audit = _verify_audit_ownership(audit_id, db, current_user)
    service = ReportService(db)
    pdf_bytes = service.render_pdf(audit_id)
    domain_slug = audit.domain.replace(".", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="endexa-report-{domain_slug}.pdf"'},
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| xhtml2pdf / ReportLab | WeasyPrint | 2020+ | Full CSS3 support, better rendering |
| Temp file PDF generation | In-memory BytesIO | Always | No cleanup needed, faster |
| Fixed CSV columns | Configurable DictWriter | Standard practice | Users choose their Jira fields |

**Deprecated/outdated:**
- xhtml2pdf: Limited CSS support, no flexbox
- pdfkit/wkhtmltopdf: Requires system binary, headless WebKit deprecated

## Open Questions

1. **Chart rendering in PDF**
   - What we know: WeasyPrint doesn't execute JavaScript, so Chart.js charts won't render
   - What's unclear: Whether static chart images are needed for MVP
   - Recommendation: Use CSS-based bar charts (colored divs with percentage widths) for category scores in the template. Defer JS-rendered charts to a future iteration.

## Sources

### Primary (HIGH confidence)
- Codebase exploration: `backend/app/templates/audit_report.html` (existing template)
- Codebase exploration: `backend/requirements.txt` (WeasyPrint 68.1, Jinja2 3.1.6 installed)
- Codebase exploration: `backend/app/models/` (all data models for report context)
- Codebase exploration: `backend/app/core/dependencies.py` (require_tier pattern)

### Secondary (MEDIUM confidence)
- WeasyPrint documentation: HTML to PDF with CSS @page rules
- Python csv module: DictWriter for structured CSV output

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and verified
- Architecture: HIGH - follows existing service layer pattern, template exists
- Pitfalls: HIGH - WeasyPrint flexbox tested via existing template, CSV encoding well-known

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable domain, no fast-moving dependencies)
