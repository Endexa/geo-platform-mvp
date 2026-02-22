# Phase 9: Dashboard & Reporting - Research

**Researched:** 2026-02-23
**Domain:** Frontend dashboard composition, PDF/CSV export, audit history/trend visualization
**Confidence:** HIGH

## Summary

Phase 9 consolidates all existing data from phases 1-8 into a single-screen dashboard and adds export/history capabilities. The good news: **all backend data already exists**. The Audit model stores both Visibility Score (via `visibility_scores` table) and Optimization Score (via `audits.optimization_score` + `page_scores`). Competitors are in `discovered_competitors` and `competitor_audits`. Recommendations are in `audit_recommendations`. The current `dashboard.vue` page is a **legacy stub** that queries the old `Analysis` model -- it needs a complete rewrite to use the new audit pipeline.

The primary work is: (1) a new backend endpoint that aggregates audit summary data into a dashboard-friendly shape, (2) a new backend endpoint for audit history/trends, (3) a frontend dashboard rewrite with Chart.js visualizations, (4) PDF export via WeasyPrint (HTML-to-PDF), and (5) CSV export via Python's built-in `csv` module.

**Primary recommendation:** Rewrite the dashboard API and page from scratch, reuse all existing components (OptimizationScore, CompetitorComparison, RecommendationProgress), add Chart.js trend charts, use WeasyPrint for PDF export (HTML template to PDF -- no new frontend dependency), and Python `csv` + `io.StringIO` for CSV export.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | Dashboard shows single-screen overview: combined GEO Score, per-engine breakdown, top issues, competitive position summary | New `/api/v1/dashboard/overview/{audit_id}` endpoint aggregating VisibilityScore + Audit.optimization_score + top 5 AuditRecommendation (high priority) + top 5 DiscoveredCompetitor. Frontend dashboard page rewrite with existing components. |
| DASH-02 | Competitive position map showing user vs discovered competitors across key metrics | Radar chart via Chart.js (already installed) + vue-chartjs showing user vs top competitors across: visibility, optimization, crawlability, content structure, structured data, authority. Data from CompetitorAudit model + DiscoveredCompetitor share_of_voice. |
| DASH-03 | Export complete audit report as PDF or CSV | WeasyPrint for PDF (HTML template rendered server-side), Python csv module for CSV. Two new endpoints: `/api/v1/audit/{id}/export/pdf` and `/api/v1/audit/{id}/export/csv`. |
| DASH-04 | Audit history stored for trend tracking across re-audits | Audits already stored per-user with `created_at` timestamps. New `/api/v1/dashboard/history` endpoint queries completed audits for same domain, returns time-series data. Frontend Line chart via vue-chartjs. |
</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Chart.js | ^4.4.1 | Chart rendering (line, radar, bar) | Already in package.json, mature, lightweight |
| vue-chartjs | ^5.3.0 | Vue 3 Chart.js wrapper | Already in package.json, composable API |
| FastAPI | 0.109.0 | API endpoints | Already installed |
| SQLAlchemy | 2.0.25 | DB queries for aggregation | Already installed |

### New Dependencies
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| WeasyPrint | >=62.0 | HTML-to-PDF conversion | PDF report export (DASH-03) |
| Jinja2 | >=3.1 | HTML templating for PDF | Render audit report HTML template |
| chartjs-adapter-date-fns | ^3.0.0 | Time axis for Chart.js | Trend charts with date axes (DASH-04) |
| date-fns | ^3.0.0 | Date formatting for Chart.js adapter | Required by chartjs-adapter-date-fns |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | ReportLab | ReportLab gives more control but requires programmatic layout; WeasyPrint lets us reuse HTML/CSS which is faster to build and maintain |
| WeasyPrint | fpdf2 | fpdf2 is lighter but no CSS support; WeasyPrint handles complex layouts with CSS |
| WeasyPrint | Puppeteer/Playwright | Already have Playwright but it requires a browser process for PDF; WeasyPrint is pure Python with no browser overhead |
| chartjs-adapter-date-fns | chartjs-adapter-luxon | date-fns is lighter than luxon, sufficient for our date formatting needs |

### Installation

**Backend:**
```bash
pip install weasyprint>=62.0 jinja2>=3.1
```

**Frontend:**
```bash
npm install chartjs-adapter-date-fns date-fns
```

**Docker (system deps for WeasyPrint):**
Add to `backend/Dockerfile`:
```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/
│   └── dashboard.py          # REWRITE: new dashboard + export endpoints
├── services/
│   └── dashboard_service.py   # NEW: aggregation queries + export logic
├── templates/
│   └── audit_report.html      # NEW: Jinja2 template for PDF export
├── schemas/
│   └── dashboard.py           # NEW: dashboard response schemas

frontend/
├── pages/
│   └── dashboard.vue          # REWRITE: single-screen overview
├── components/
│   ├── DashboardHero.vue      # NEW: combined GEO score display
│   ├── CompetitorRadar.vue    # NEW: radar chart for competitive position
│   ├── TrendChart.vue         # NEW: line chart for audit history
│   └── ExportActions.vue      # NEW: PDF/CSV export buttons
```

### Pattern 1: Dashboard Aggregation Endpoint
**What:** Single API endpoint that returns all data needed for the dashboard in one request, avoiding N+1 frontend fetches.
**When to use:** When a page needs data from multiple tables (audits, visibility_scores, discovered_competitors, audit_recommendations).
**Example:**
```python
# backend/app/services/dashboard_service.py
class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, audit_id: str, user_id: str) -> dict:
        """Single query that returns everything the dashboard needs."""
        audit = self.db.query(Audit).filter(
            Audit.id == audit_id,
            Audit.user_id == user_id,
        ).first()

        # Visibility score
        vs = self.db.query(VisibilityScore).filter(
            VisibilityScore.audit_id == audit_id
        ).first()

        # Top 5 high-priority open recommendations
        top_recs = self.db.query(AuditRecommendation).filter(
            AuditRecommendation.audit_id == audit_id,
            AuditRecommendation.priority == "high",
            AuditRecommendation.status == "open",
        ).order_by(AuditRecommendation.gap_score.desc()).limit(5).all()

        # Top competitors by share of voice
        competitors = self.db.query(DiscoveredCompetitor).filter(
            DiscoveredCompetitor.audit_id == audit_id,
            DiscoveredCompetitor.is_user_brand == False,
        ).order_by(DiscoveredCompetitor.share_of_voice.desc()).limit(5).all()

        # Competitor audit scores
        comp_audits = self.db.query(CompetitorAudit).filter(
            CompetitorAudit.parent_audit_id == audit_id,
            CompetitorAudit.status == "completed",
        ).all()

        # Combined GEO score
        visibility = vs.overall_score if vs else 0
        optimization = audit.optimization_score or 0
        combined = round(visibility * 0.5 + optimization * 0.5)

        return {
            "audit": audit,
            "combined_geo_score": combined,
            "visibility_score": visibility,
            "optimization_score": optimization,
            "per_engine_scores": vs.per_engine_scores if vs else {},
            "mention_count": vs.mention_count if vs else 0,
            "top_issues": top_recs,
            "competitors": competitors,
            "competitor_audits": comp_audits,
        }
```

### Pattern 2: Audit History for Trends
**What:** Query all completed audits for the same domain, ordered by date, to show score trends.
**When to use:** DASH-04 trend charts.
**Example:**
```python
def get_audit_history(self, domain: str, user_id: str) -> list[dict]:
    """Get all completed audits for a domain, ordered by date."""
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

    history = []
    for audit in audits:
        vs = self.db.query(VisibilityScore).filter(
            VisibilityScore.audit_id == audit.id
        ).first()

        history.append({
            "audit_id": str(audit.id),
            "date": audit.completed_at.isoformat(),
            "visibility_score": vs.overall_score if vs else 0,
            "optimization_score": audit.optimization_score or 0,
            "combined_score": round(
                (vs.overall_score if vs else 0) * 0.5
                + (audit.optimization_score or 0) * 0.5
            ),
            "mention_count": vs.mention_count if vs else 0,
        })

    return history
```

### Pattern 3: PDF Export via WeasyPrint
**What:** Render a Jinja2 HTML template with audit data, convert to PDF with WeasyPrint.
**When to use:** DASH-03 PDF export.
**Example:**
```python
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
from fastapi.responses import Response

def export_pdf(self, audit_id: str, user_id: str) -> bytes:
    """Generate PDF report for an audit."""
    data = self._gather_full_report_data(audit_id, user_id)

    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("audit_report.html")
    html_content = template.render(**data)

    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes

# In the API endpoint:
@router.get("/{audit_id}/export/pdf")
def export_pdf(audit_id: str, ...):
    service = DashboardService(db)
    pdf_bytes = service.export_pdf(audit_id, current_user.id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="audit-report-{domain}.pdf"'},
    )
```

### Pattern 4: CSV Export via Python csv Module
**What:** Use Python's built-in `csv` module with `io.StringIO` to generate CSV, return as StreamingResponse.
**When to use:** DASH-03 CSV export.
**Example:**
```python
import csv
import io
from fastapi.responses import StreamingResponse

def export_csv(self, audit_id: str, user_id: str) -> str:
    """Generate CSV report content for an audit."""
    data = self._gather_full_report_data(audit_id, user_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header section
    writer.writerow(["GEO Audit Report", data["domain"]])
    writer.writerow(["Date", data["completed_at"]])
    writer.writerow([])

    # Scores section
    writer.writerow(["Score Type", "Value"])
    writer.writerow(["Combined GEO Score", data["combined_score"]])
    writer.writerow(["Visibility Score", data["visibility_score"]])
    writer.writerow(["Optimization Score", data["optimization_score"]])
    writer.writerow([])

    # Per-engine breakdown
    writer.writerow(["Engine", "Score"])
    for engine, score in data["per_engine_scores"].items():
        writer.writerow([engine, score])
    writer.writerow([])

    # Recommendations
    writer.writerow(["Priority", "Category", "Criterion", "Summary", "Gap", "Impact"])
    for rec in data["recommendations"]:
        writer.writerow([rec.priority, rec.category, rec.criterion_name,
                        rec.summary, rec.gap_score, rec.impact_label])

    return output.getvalue()

# In the API endpoint:
@router.get("/{audit_id}/export/csv")
def export_csv(audit_id: str, ...):
    content = service.export_csv(audit_id, current_user.id)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="audit-report-{domain}.csv"'},
    )
```

### Pattern 5: Chart.js Radar Chart for Competitor Position Map
**What:** Use vue-chartjs Radar component to visualize user vs competitors across multiple dimensions.
**When to use:** DASH-02 competitive position visualization.
**Example:**
```vue
<script setup lang="ts">
import { Radar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const props = defineProps<{
  userScores: { visibility: number; optimization: number; crawlability: number; content: number; schema: number; authority: number }
  competitors: Array<{ name: string; scores: typeof props.userScores }>
}>()

const chartData = computed(() => ({
  labels: ['Visibility', 'Optimization', 'Crawlability', 'Content', 'Schema', 'Authority'],
  datasets: [
    {
      label: 'Your Site',
      data: [
        props.userScores.visibility,
        props.userScores.optimization,
        props.userScores.crawlability,
        props.userScores.content,
        props.userScores.schema,
        props.userScores.authority,
      ],
      borderColor: '#1E40AF',
      backgroundColor: 'rgba(30, 64, 175, 0.2)',
    },
    ...props.competitors.map((comp, i) => ({
      label: comp.name,
      data: [comp.scores.visibility, comp.scores.optimization, comp.scores.crawlability,
             comp.scores.content, comp.scores.schema, comp.scores.authority],
      borderColor: ['#EF4444', '#F59E0B', '#10B981'][i % 3],
      backgroundColor: ['rgba(239,68,68,0.1)', 'rgba(245,158,11,0.1)', 'rgba(16,185,129,0.1)'][i % 3],
    })),
  ],
}))

const chartOptions = {
  responsive: true,
  scales: { r: { min: 0, max: 100, ticks: { stepSize: 20 } } },
  plugins: { legend: { position: 'bottom' as const } },
}
</script>
```

### Anti-Patterns to Avoid
- **Multiple API calls from dashboard page:** Don't fetch audit, competitors, recommendations, and sentiment separately. Use a single aggregation endpoint.
- **Storing dashboard snapshots:** Don't create a new table for dashboard data. All data already exists in existing tables; aggregate on read.
- **Client-side PDF generation:** Don't use html2canvas/jspdf in the browser. Server-side WeasyPrint produces better quality and doesn't require sending all data to the client.
- **Heavy chart libraries:** Don't add D3.js, ECharts, or ApexCharts. Chart.js + vue-chartjs are already installed and sufficient for line/radar/bar charts.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF generation | Custom PDF byte manipulation | WeasyPrint + Jinja2 HTML templates | Complex layout, fonts, colors handled by CSS |
| CSV export | Manual string concatenation | Python `csv` module + `io.StringIO` | Handles escaping, quoting, unicode properly |
| Time-series chart axis | Custom date parsing/formatting | chartjs-adapter-date-fns | Chart.js needs an adapter for time scale |
| Combined GEO score | Complex weighted aggregation | Simple 50/50 weighted average | Visibility and Optimization are already 0-100 |
| Competitive radar chart | SVG/Canvas from scratch | Chart.js Radar chart type | Handles scaling, labels, tooltips, responsiveness |

**Key insight:** This phase is primarily about **composition and aggregation** of existing data, not new computation. Every score, mention, competitor, and recommendation already exists in the database from phases 4-8. The dashboard just needs to fetch, aggregate, and display it.

## Common Pitfalls

### Pitfall 1: Legacy Dashboard API Uses Wrong Model
**What goes wrong:** The current `dashboard.py` API router queries the `Analysis` model (the old pre-audit system), not the `Audit` model.
**Why it happens:** The dashboard was created before the audit pipeline existed in phase 2.
**How to avoid:** Completely rewrite `dashboard.py` to use `Audit`, `VisibilityScore`, `AuditRecommendation`, `DiscoveredCompetitor`, and `CompetitorAudit` models.
**Warning signs:** Any import of `Analysis` or `Website` in the new dashboard code.

### Pitfall 2: WeasyPrint System Dependencies Missing in Docker
**What goes wrong:** `pip install weasyprint` succeeds but WeasyPrint crashes at runtime with missing Pango/Cairo libraries.
**Why it happens:** WeasyPrint requires system libraries (Pango, HarfBuzz, GdkPixbuf) that aren't in python:3.11-slim.
**How to avoid:** Add `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 libffi-dev libjpeg-dev libopenjp2-7-dev` to the Dockerfile `apt-get install` line.
**Warning signs:** ImportError or OSError mentioning cairo, pango, or gobject.

### Pitfall 3: Chart.js Missing Time Scale Adapter
**What goes wrong:** Trend chart shows error "This method is not implemented: Check that a complete date adapter is provided."
**Why it happens:** Chart.js requires a date adapter package for time-based axes. It doesn't ship one by default.
**How to avoid:** Install `chartjs-adapter-date-fns` and `date-fns`, import the adapter before using time scale.
**Warning signs:** Empty chart or console error about date adapter.

### Pitfall 4: N+1 Query in Dashboard Overview
**What goes wrong:** Dashboard endpoint makes dozens of DB queries (one per competitor, one per recommendation, etc.).
**Why it happens:** Naive implementation fetches audit, then loops over relationships.
**How to avoid:** Use SQLAlchemy `joinedload()` or batch queries. The DashboardService should make at most 4-5 queries total.
**Warning signs:** Slow dashboard load (>500ms for a single audit's data).

### Pitfall 5: Combined GEO Score Formula Not Defined
**What goes wrong:** Ambiguity about how to combine Visibility Score and Optimization Score.
**Why it happens:** Requirements say "weighted blend" but don't specify the weights.
**How to avoid:** Use equal 50/50 weighting. Both scores are 0-100. `combined = round(visibility * 0.5 + optimization * 0.5)`. This is the simplest correct approach -- users can see individual scores for detail.
**Warning signs:** Debate about weighting that blocks implementation.

### Pitfall 6: Audit History Requires Same-Domain Matching
**What goes wrong:** Trend chart shows audits for different domains mixed together.
**Why it happens:** Filtering only by user_id without also filtering by domain.
**How to avoid:** History endpoint must filter by `Audit.domain` AND `Audit.user_id`. The dashboard should auto-detect the current audit's domain and fetch history for that domain.
**Warning signs:** Chart showing jumpy/inconsistent scores.

### Pitfall 7: PDF Export Blocking the Event Loop
**What goes wrong:** WeasyPrint PDF generation (500ms-2s) blocks the async FastAPI event loop.
**Why it happens:** WeasyPrint is synchronous and CPU-bound.
**How to avoid:** Run WeasyPrint in a thread pool using `asyncio.to_thread()` or make the endpoint synchronous (FastAPI auto-runs sync endpoints in a threadpool).
**Warning signs:** Other API requests stalling during PDF generation.

## Code Examples

### Dashboard Overview API Endpoint
```python
# Source: Derived from existing patterns in audit.py and recommendations.py
@router.get("/overview/{audit_id}")
def get_dashboard_overview(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    service = DashboardService(db)
    data = service.get_overview(audit_id, str(current_user.id))
    return DashboardOverviewResponse(**data)
```

### Dashboard Overview Response Schema
```python
class DashboardOverviewResponse(BaseModel):
    audit_id: str
    domain: str
    url: str
    completed_at: str | None
    combined_geo_score: int
    visibility_score: int
    optimization_score: int
    per_engine_scores: dict[str, int]
    mention_count: int
    query_mention_rate: float
    top_issues: list[TopIssueSchema]
    competitive_position: CompetitivePositionSchema
    recommendation_progress: RecommendationProgressSchema
```

### Vue-chartjs Line Chart for Trends
```vue
<!-- Source: vue-chartjs docs + Chart.js time series docs -->
<script setup lang="ts">
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import 'chartjs-adapter-date-fns'

ChartJS.register(CategoryScale, LinearScale, TimeScale, PointElement, LineElement, Title, Tooltip, Legend)

const props = defineProps<{
  history: Array<{
    date: string
    combined_score: number
    visibility_score: number
    optimization_score: number
  }>
}>()

const chartData = computed(() => ({
  datasets: [
    {
      label: 'Combined GEO Score',
      data: props.history.map(h => ({ x: h.date, y: h.combined_score })),
      borderColor: '#1E40AF',
      tension: 0.3,
    },
    {
      label: 'Visibility',
      data: props.history.map(h => ({ x: h.date, y: h.visibility_score })),
      borderColor: '#3B82F6',
      borderDash: [5, 5],
      tension: 0.3,
    },
    {
      label: 'Optimization',
      data: props.history.map(h => ({ x: h.date, y: h.optimization_score })),
      borderColor: '#F59E0B',
      borderDash: [5, 5],
      tension: 0.3,
    },
  ],
}))

const chartOptions = {
  responsive: true,
  scales: {
    x: { type: 'time' as const, time: { unit: 'day' as const } },
    y: { min: 0, max: 100, title: { display: true, text: 'Score' } },
  },
  plugins: {
    legend: { position: 'bottom' as const },
  },
}
</script>
```

### Jinja2 HTML Template for PDF Report (Skeleton)
```html
<!-- Source: WeasyPrint docs pattern -->
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: sans-serif; color: #1E3A8A; margin: 40px; }
    .header { border-bottom: 3px solid #1E40AF; padding-bottom: 20px; margin-bottom: 30px; }
    .score-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
    .score-card { background: #F8FAFC; border-radius: 8px; padding: 20px; text-align: center; }
    .score-value { font-size: 48px; font-weight: bold; }
    .score-label { font-size: 14px; color: #64748B; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th { background: #1E40AF; color: white; padding: 10px; text-align: left; }
    td { padding: 8px 10px; border-bottom: 1px solid #E2E8F0; }
    .priority-high { color: #DC2626; font-weight: bold; }
    .priority-medium { color: #D97706; }
    .priority-low { color: #059669; }
    @page { size: A4; margin: 2cm; }
  </style>
</head>
<body>
  <div class="header">
    <h1>GEO Audit Report: {{ domain }}</h1>
    <p>Generated: {{ generated_at }} | URL: {{ url }}</p>
  </div>

  <div class="score-grid">
    <div class="score-card">
      <div class="score-value">{{ combined_score }}</div>
      <div class="score-label">Combined GEO Score</div>
    </div>
    <!-- ... visibility, optimization cards ... -->
  </div>

  <!-- Per-engine breakdown, recommendations table, competitor comparison, mentions -->
</body>
</html>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `dashboard.py` queries `Analysis` model | Must query `Audit` + related models | Phase 2+ (Audit model created) | Dashboard API is completely stale |
| `dashboard.vue` shows `avgGeoScore` from old system | Must show combined GEO, visibility, optimization | Phase 6 (dual-score architecture) | Frontend dashboard page needs full rewrite |
| No export capability | PDF via WeasyPrint + CSV via Python csv | Phase 9 (new) | New feature |
| No audit history/trends | Query completed audits by domain + visualize | Phase 9 (new) | New feature |

**Deprecated/outdated:**
- `dashboard.py` current code: References `Analysis`, `Website` models that are from the legacy system. Must be rewritten entirely.
- `dashboard.vue` current code: Uses old `fetch()` against legacy `/dashboard/stats` endpoint. Must be rewritten entirely.
- The `Analysis` model and `Website` model: Not used by the audit pipeline (phases 2-8). Dashboard should exclusively use `Audit` and its relationships.

## Open Questions

1. **Combined GEO Score Weights**
   - What we know: Requirements say "weighted blend" of Visibility + Optimization
   - What's unclear: Exact weights (50/50? 60/40? configurable?)
   - Recommendation: Use 50/50 for MVP. Both scores are equally important to the user. Can be adjusted later.

2. **Audit Selection for Dashboard**
   - What we know: User may have multiple completed audits for different domains
   - What's unclear: Should dashboard show the most recent audit? Let user pick? Show a list?
   - Recommendation: Dashboard shows the most recent completed audit by default, with a dropdown to select from all user audits. If no audit exists, show empty state with CTA to start one.

3. **Competitor Visibility Scores in Radar**
   - What we know: CompetitorAudit has optimization category scores (crawlability_avg, etc.) but not visibility scores
   - What's unclear: How to show competitor visibility on the radar chart
   - Recommendation: Use share_of_voice from DiscoveredCompetitor as the competitor's "visibility" dimension. For the user, use VisibilityScore.overall_score.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `backend/app/models/audit.py`, `visibility_score.py`, `page_score.py`, `competitor.py`, `audit_recommendation.py` -- all data models verified
- Codebase analysis: `backend/app/api/dashboard.py` -- confirmed legacy code using `Analysis` model
- Codebase analysis: `frontend/package.json` -- confirmed Chart.js 4.4.1 + vue-chartjs 5.3.0 already installed
- Codebase analysis: `backend/Dockerfile` -- confirmed python:3.11-slim base image
- [Chart.js Radar Chart docs](https://www.chartjs.org/docs/latest/charts/radar.html) -- radar chart API
- [Chart.js Time Series Axis docs](https://www.chartjs.org/docs/latest/axes/cartesian/timeseries.html) -- time scale configuration
- [vue-chartjs docs](https://vue-chartjs.org/guide/) -- Vue 3 wrapper API

### Secondary (MEDIUM confidence)
- [WeasyPrint First Steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) -- installation and system deps
- [WeasyPrint PyPI](https://pypi.org/project/weasyprint/) -- version 68.1 as of Feb 2026
- [FastAPI Custom Responses](https://fastapi.tiangolo.com/advanced/custom-response/) -- StreamingResponse for file downloads
- [Sling Academy - FastAPI CSV](https://www.slingacademy.com/article/how-to-return-a-csv-file-in-fastapi/) -- CSV export pattern

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All core libraries already installed (Chart.js, vue-chartjs). WeasyPrint is well-documented and mature.
- Architecture: HIGH - All data models and relationships already exist. Dashboard is pure aggregation.
- Pitfalls: HIGH - Verified legacy dashboard code, Docker base image, and Chart.js adapter requirements directly in codebase.

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable domain, all dependencies are mature libraries)
