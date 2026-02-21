# GEO Data Points System

> 108 measurements across 7 modules. The core intellectual property of the platform.

---

## Overview

Each data point measures one specific aspect of how well a website is optimized for AI language models (ChatGPT, Claude, Perplexity, etc.).

**Current status:** 108 scripts created. 5 fully functional, 103 stubs returning score 0.

---

## Modules

| Module | Code | Data Points | Description |
|--------|------|-------------|-------------|
| Web Infrastructure | WI | 31 | Robots.txt, schemas, sitemaps, performance, technical SEO |
| Content | CNT | 24 | Readability, entity density, freshness, structure, citations |
| Brand Visibility | BV | 15 | Knowledge graph, Wikipedia, reviews, media, E-E-A-T |
| SEO | SEO | 12 | Backlinks, domain authority, SERP features, rankings |
| User Experience | UX | 8 | Core Web Vitals (LCP, CLS, FID), page speed, mobile |
| Competitive | COMP | 8 | Competitor comparison, content gaps, market position |
| Legal | LEG | 5 | Privacy policy, GDPR, cookies, accessibility, TDM |
| **Total** | | **108** | |

---

## Scoring Methodology

### Individual Data Point (0-100)

Each script returns:
```python
{
    "score": 85,           # 0-100
    "comment": "GPTBot access allowed via robots.txt",
    "metadata": {
        "raw_value": True,
        "method": "robots.txt parsing"
    }
}
```

Score bands:
- 90-100: Excellent
- 70-89: Good, minor improvements
- 50-69: Average, improvements needed
- 30-49: Poor, critical issues
- 0-29: Very poor, major problems

### Module Score

Average of all data points in the module:
```
WI_score = sum(wi_scores) / 31
```

### Overall GEO Score

Weighted average of module scores:
```
GEO = (WI * w_wi) + (CNT * w_cnt) + (BV * w_bv) + (SEO * w_seo) + (UX * w_ux) + (COMP * w_comp) + (LEG * w_leg)
```

Weights TBD — currently simplified to: `(Visibility * 0.4) + (Readability * 0.3) + (Authority * 0.3)`.

---

## File Structure

```
geo_data_points/
├── measurements/
│   ├── wi_001_gptbot.py          # Working example
│   ├── wi_002_claudebot.py       # Working example
│   ├── wi_003_schema_org.py      # Working example
│   ├── wi_004_response_time.py   # Working example
│   ├── wi_005_title_tag.py       # Working example
│   ├── wi_006_perplexitybot.py   # Stub
│   ├── ...                       # 103 more stubs
│   └── leg_005_accessibility.py
├── orchestrator/
│   └── run_all.py                # Runs all measurements for a URL
├── utils/
│   ├── http_client.py            # Async HTTP with connection pooling
│   ├── html_parser.py            # HTML parsing utilities
│   ├── content_analyzer.py       # NLP and content analysis
│   ├── external_apis.py          # External API clients (Ahrefs, SEMrush, etc.)
│   ├── seo_helpers.py            # SEO-specific utilities
│   └── crawl_helpers.py          # Website crawling helpers
├── db/
│   ├── models.py                 # SQLAlchemy models for GEO results
│   └── database.py               # DB connection
├── data_points.json              # 108 data point definitions (metadata)
└── README.md                     # Module-specific docs
```

---

## How to Add/Implement a Measurement Script

### 1. Find the stub

All stubs follow the same pattern. Example: `measurements/wi_006_perplexitybot.py`

### 2. Use a working script as reference

Copy the pattern from `measurements/wi_001_gptbot.py`:

```python
import asyncio
from typing import Dict, Any

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    """
    WI-006: Check if PerplexityBot has access via robots.txt
    """
    try:
        # 1. Fetch the data (robots.txt, HTML, API, etc.)
        robots_url = url.rstrip('/') + '/robots.txt'
        # ... fetch and parse ...

        # 2. Calculate score (0-100)
        score = 100 if bot_allowed else 0

        # 3. Return structured result
        return {
            "score": score,
            "comment": f"PerplexityBot {'allowed' if bot_allowed else 'blocked'}",
            "metadata": {
                "bot_name": "PerplexityBot",
                "raw_value": bot_allowed,
            }
        }
    except Exception as e:
        return {
            "score": 0,
            "comment": f"Error: {str(e)}",
            "metadata": {"error": str(e)}
        }
```

### 3. Key rules

- Always return `{score, comment, metadata}` — never raise exceptions
- Score must be 0-100 integer
- Comment must be human-readable (shown in UI)
- Use `async def measure(url, **kwargs)` signature
- Use utilities from `utils/` for HTTP, parsing, NLP
- Handle timeouts and errors gracefully (return score 0 with error comment)

### 4. Test your script

```bash
cd geo_data_points
python -c "
import asyncio
from measurements.wi_006_perplexitybot import measure
result = asyncio.run(measure('https://example.com'))
print(result)
"
```

---

## Fully Implemented Scripts (5/108)

| Code | Name | Module | Status |
|------|------|--------|--------|
| WI-001 | Robots.txt GPTBot Access | Web Infrastructure | Functional |
| WI-002 | Robots.txt ClaudeBot Access | Web Infrastructure | Functional |
| WI-003 | Schema.org Organization | Web Infrastructure | Functional |
| WI-004 | Response Time (TTFB) | Web Infrastructure | Functional |
| WI-005 | Title Tag Optimization | Web Infrastructure | Functional |

Full list of all 108 data points: see `docs/archive/IMPLEMENTATION_PROGRESS.md`.

---

## Data Points JSON Schema

`data_points.json` defines metadata for each data point:

```json
{
    "code": "WI-001",
    "name": "Robots.txt GPTBot Access",
    "module": "WI",
    "category": "Web Infrastructure",
    "description": "Checks if GPTBot can access the site via robots.txt",
    "weight": 1.0,
    "script": "wi_001_gptbot.py"
}
```

See also: `geo_data_points/README.md` for module-specific documentation.
