# Technology Stack -- New Feature Libraries

**Project:** Endexa GEO Platform v2
**Researched:** 2025-02-25
**Scope:** Additional libraries for scoring, recommendations, reports, chat, payments, and export features on top of the existing FastAPI + Nuxt 3 + Supabase stack.

## Existing Stack (Keep As-Is, Do Not Re-Research)

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | FastAPI | 0.109.0 |
| Frontend | Nuxt 3 (Vue 3) | ^3.9.0 |
| Styling | Tailwind CSS | ^3.4.0 |
| ORM | SQLAlchemy + Alembic | 2.0.25 / 1.13.1 |
| Database | Supabase PostgreSQL + pgvector | -- |
| Task Queue | Celery + Redis | 5.3.4 / 5.0.1 |
| LLM | LiteLLM | 1.17.0 (needs upgrade) |
| Scraping | Playwright + BeautifulSoup4 | 1.41.0 / 4.12.2 |
| Charts | Chart.js + vue-chartjs | ^4.4.1 / ^5.3.0 |
| Payments | Stripe SDK | 7.9.0 (needs upgrade) |
| Templates | Jinja2 | >=3.1 |
| PDF | WeasyPrint | >=62.0 (needs upgrade) |
| Logging | Loguru | 0.7.2 |

---

## Recommended Additions -- Backend (Python)

### 1. Upgrade: Stripe SDK
| Detail | Value |
|--------|-------|
| **Package** | `stripe` |
| **Current** | 7.9.0 |
| **Upgrade to** | `>=14.0.0` |
| **Latest** | 14.3.0 (verified PyPI, Feb 2026) |
| **Why upgrade** | v7.9.0 is 3 major versions behind. v14.x has the new `StripeClient` pattern (instance-based, no global state), native async support via httpx, Checkout Sessions v2, and modern webhook signature verification. The old `stripe.api_key` global pattern is deprecated. |
| **Confidence** | HIGH -- verified via `pip index versions stripe` |
| **Breaking changes** | v8+ replaced `stripe.api_key = ...` with `StripeClient(api_key=...)`. This aligns with the project's existing pattern of passing `api_key=` explicitly (see LiteLLM decision in MEMORY.md). |

### 2. Upgrade: LiteLLM
| Detail | Value |
|--------|-------|
| **Package** | `litellm` |
| **Current** | 1.17.0 |
| **Upgrade to** | `>=1.75.0` |
| **Latest** | 1.81.15 (verified PyPI, Feb 2026) |
| **Why upgrade** | Current version is from early 2024. v1.75+ adds MCP support on /chat/completions, 50% memory leak reduction, better streaming support, improved cost tracking, and support for newer model versions from all providers. The chat assistant feature requires streaming, which has been significantly improved in recent versions. |
| **Confidence** | HIGH -- verified via `pip index versions litellm` |
| **Risk** | LiteLLM has breaking changes between minor versions. Pin to a specific version (e.g., `litellm==1.81.15`) rather than using `>=`. Test thoroughly. |

### 3. Upgrade: WeasyPrint
| Detail | Value |
|--------|-------|
| **Package** | `weasyprint` |
| **Current** | >=62.0 |
| **Upgrade to** | `>=68.0` |
| **Latest** | 68.1 (verified PyPI, Feb 2026) |
| **Why upgrade** | v62 works but v68.x has better CSS grid support, improved rendering accuracy, and bug fixes. For professional audit reports, rendering quality matters. |
| **Confidence** | HIGH -- verified via `pip index versions weasyprint` |

### 4. New: SSE-Starlette (Chat Streaming)
| Detail | Value |
|--------|-------|
| **Package** | `sse-starlette` |
| **Version** | `>=3.2.0` |
| **Latest** | 3.2.0 (verified PyPI) |
| **Purpose** | Server-Sent Events for the chat assistant. Streams LLM responses token-by-token to the frontend. |
| **Why this** | W3C SSE spec-compliant, built for Starlette/FastAPI, handles client disconnect detection and cleanup automatically. FastAPI's built-in `StreamingResponse` works for simple cases but lacks proper SSE event formatting, `Last-Event-ID` support, and reconnection handling. |
| **Why not WebSockets** | The chat assistant is request-response (user asks, server streams answer). SSE is simpler, works through load balancers and proxies without special configuration, and auto-reconnects. WebSockets add bidirectional complexity that is not needed here. |
| **Confidence** | HIGH -- widely used in LLM streaming applications, verified on PyPI |

### 5. No New Libraries Needed: CSV Export
| Detail | Value |
|--------|-------|
| **Package** | Python stdlib `csv` module |
| **Purpose** | Jira CSV export |
| **Why no new library** | Jira CSV import expects a simple comma-separated file with a `Summary` header column. Python's built-in `csv.DictWriter` handles this perfectly. No need for pandas (200MB+ dependency) for writing a few hundred rows. The existing `io.StringIO` + `csv` approach produces exactly the format Jira Cloud and Jira Server expect. |
| **Jira CSV format** | Fields separated by commas, content with commas/newlines in double quotes. Required column: `Summary`. Optional: `Issue Type`, `Priority`, `Description`, `Epic Link`, `Labels`, `Story Points`. The `csv` module handles quoting automatically. |
| **Confidence** | HIGH -- Jira CSV import format is well-documented by Atlassian |

### 6. No New Libraries Needed: Recommendations Engine
| Detail | Value |
|--------|-------|
| **Existing** | `recommendation_engine.py` already implements deterministic gap analysis |
| **Why no new library** | The recommendations engine is already built and is deterministic (compares scores against benchmarks, no LLM calls). It reads CriterionResult records, compares against research benchmarks and competitor averages, and produces prioritized AuditRecommendation records with evidence, code snippets, and action steps. This is the correct architecture -- recommendations should be reproducible and evidence-based, not LLM-hallucinated. |
| **What's needed** | The engine needs to be wired into the audit pipeline (it exists as code but is not called from the Celery task). No new dependencies required. |
| **Confidence** | HIGH -- code reviewed directly |

### 7. No New Libraries Needed: Code Analysis Prompt Generation
| Detail | Value |
|--------|-------|
| **Existing** | Jinja2 (already installed), LiteLLM (already installed) |
| **Purpose** | Generate prompts users run on their own repos, then ingest the output for deeper analysis |
| **Architecture** | Jinja2 templates for prompt generation. LiteLLM for parsing uploaded analysis output. No new dependencies needed. This is a template rendering + LLM parsing workflow, both of which are already available. |
| **Confidence** | HIGH -- straightforward template + LLM pattern |

### 8. Remove: Unused/Stale Dependencies
| Package | Current | Action | Reason |
|---------|---------|--------|--------|
| `langchain` | 0.1.0 | **Remove** | Not used anywhere in the codebase. The project uses LiteLLM directly. LangChain is 200MB+ of dependencies for zero value. |
| `langchain-openai` | 0.0.2 | **Remove** | Dependency of unused langchain. |
| `openai` | 1.7.0 | **Remove** | All LLM calls go through LiteLLM. The old `optimizer.py` imports openai directly but should be migrated to use LiteLLM like everything else. |
| `sentence-transformers` | 2.2.2 | **Keep for now** | Brand Signature is deferred to v3 but this is already installed. Can remove if storage is a concern (700MB+ with PyTorch). |

---

## Recommended Additions -- Frontend (npm)

### 1. New: Marked (Markdown Rendering for Chat)
| Detail | Value |
|--------|-------|
| **Package** | `marked` |
| **Version** | `^17.0.0` |
| **Latest** | 17.0.3 (verified npm) |
| **Purpose** | Parse LLM markdown responses in the chat assistant into HTML. |
| **Why this** | 12M+ weekly downloads, actively maintained, tiny bundle size (~40KB), extensible via plugins. The chat assistant will receive markdown-formatted responses from LLMs (headers, bold, lists, code blocks, tables). Marked parses these into HTML for rendering. |
| **Why not Nuxt Content/MDC** | Nuxt Content is for static content files, not dynamic streaming chat. MDC adds Vue component interpolation overhead that is unnecessary for rendering chat messages. Marked is lightweight and purpose-built for this use case. |
| **Confidence** | HIGH -- industry standard, verified on npm |

### 2. New: marked-highlight (Code Syntax Highlighting)
| Detail | Value |
|--------|-------|
| **Package** | `marked-highlight` |
| **Version** | `^2.2.0` |
| **Latest** | 2.2.3 (verified npm) |
| **Purpose** | Syntax highlighting for code blocks in chat responses and code analysis results. |
| **Why this** | Official marked plugin. LLM responses frequently contain code blocks (JSON-LD examples, robots.txt fixes, HTML snippets). Without highlighting, code blocks are plain text. |
| **Confidence** | HIGH -- official marked ecosystem |

### 3. New: highlight.js (Syntax Highlighting Engine)
| Detail | Value |
|--------|-------|
| **Package** | `highlight.js` |
| **Version** | `^11.11.0` |
| **Latest** | 11.11.1 (verified npm) |
| **Purpose** | Provides the actual syntax highlighting logic used by marked-highlight. |
| **Why this** | Supports 190+ languages, auto-detection, 97 themes. Used with marked-highlight to transform code blocks into highlighted HTML. |
| **Why not Prism.js** | highlight.js has better auto-language-detection (important when LLMs don't always specify language in code fences). Both are excellent; highlight.js is simpler to integrate with marked. |
| **Confidence** | HIGH -- industry standard |

### 4. New: DOMPurify (XSS Sanitization)
| Detail | Value |
|--------|-------|
| **Package** | `dompurify` |
| **Version** | `^3.3.0` |
| **Latest** | 3.3.1 (verified npm) |
| **Purpose** | Sanitize HTML output from marked before rendering in the DOM. **Security-critical.** |
| **Why this** | LLM responses are user-influenced (prompts can contain injection attempts). Rendering unsanitized markdown-to-HTML in the browser is an XSS vector. DOMPurify strips dangerous elements/attributes while preserving safe formatting. |
| **Why mandatory** | The chat assistant renders LLM output as HTML. Without sanitization, a crafted prompt could inject `<script>` tags or event handlers into the rendered output. This is not optional. |
| **Confidence** | HIGH -- security best practice, verified on npm |

### 5. New: @stripe/stripe-js (Frontend Payment)
| Detail | Value |
|--------|-------|
| **Package** | `@stripe/stripe-js` |
| **Version** | `^8.0.0` |
| **Latest** | 8.8.0 (verified npm) |
| **Purpose** | Stripe.js client for Checkout Sessions redirect and Payment Elements. |
| **Why this** | Official Stripe JavaScript SDK. Needed for: (1) redirecting users to Stripe Checkout, (2) rendering Payment Elements for inline payment forms. The backend creates Checkout Sessions; the frontend redirects to them using this library. |
| **Why not @unlok-co/nuxt-stripe** | The Nuxt module (v6.0.2) wraps @stripe/stripe-js with Nuxt-specific composables (`useStripe`). It adds convenience but also adds a dependency layer. For a simple Checkout redirect flow (create session on backend, redirect on frontend), the official SDK is sufficient and more maintainable. Use the Nuxt module only if you need Payment Elements (inline forms). |
| **Recommendation** | Start with `@stripe/stripe-js` directly. If Payment Elements are needed later, consider the Nuxt module. |
| **Confidence** | HIGH -- official Stripe SDK |

### 6. Not Recommended: file-saver
| Detail | Value |
|--------|-------|
| **Package** | `file-saver` |
| **Version** | 2.0.5 (last updated 5 years ago) |
| **Purpose** | Client-side file downloads |
| **Why not** | The package is unmaintained (last publish: 2020). Modern browsers support `URL.createObjectURL()` + `<a download>` natively. For CSV and PDF downloads, use a simple utility function (10 lines) instead of a stale dependency. |
| **Alternative** | A small `downloadFile(blob, filename)` composable using native browser APIs. |
| **Confidence** | HIGH -- native APIs are well-supported |

---

## Architecture Decisions for New Features

### Chat Assistant: Prompt Stuffing, Not RAG
| Decision | Rationale |
|----------|-----------|
| **Approach** | Stuff audit results into the LLM context window (prompt stuffing) |
| **Why not RAG** | An audit produces structured data: ~61 criterion results, ~10-30 recommendations, ~15 queries with mentions. This is 5-15KB of JSON -- easily fits in a 128K context window. RAG adds embedding/retrieval complexity for data that fits in a single prompt. |
| **Implementation** | Serialize audit results (scores, recommendations, content gaps) into a structured prompt. Use LiteLLM streaming with SSE to stream responses. Maintain conversation history in the session (Redis or in-memory). |
| **Cost control** | Use the existing cost tracking service. Chat uses the audit's remaining budget or a separate per-chat budget. Use `gpt-4o-mini` or `gemini-2.5-flash` for chat (cheap, fast). |

### PDF Reports: WeasyPrint + Jinja2 (Already Installed)
| Decision | Rationale |
|----------|-----------|
| **Approach** | Jinja2 HTML templates -> WeasyPrint PDF conversion |
| **Why this** | Both are already in requirements.txt. WeasyPrint renders HTML/CSS to PDF with good fidelity. The audit report is a styled document with scores, charts, tables, and recommendations -- perfect for HTML-to-PDF conversion. |
| **Why not ReportLab** | ReportLab requires programmatic document construction (no HTML/CSS). WeasyPrint lets you design reports in HTML/CSS (easier to iterate, design-system compatible) and converts to PDF. |
| **Charts in PDF** | Chart.js is client-side only. For PDF, render charts as static SVG or PNG on the backend. Options: (a) Use matplotlib/plotly to generate chart images server-side, or (b) Use simple HTML/CSS progress bars and data tables instead of interactive charts. Option (b) is recommended for v2 -- simpler, no extra dependencies. |
| **Confidence** | HIGH -- WeasyPrint + Jinja2 is the standard Python approach |

### Stripe: Checkout Sessions (Not Payment Elements)
| Decision | Rationale |
|----------|-----------|
| **Approach** | Server-side Checkout Session creation -> client-side redirect |
| **Why this** | Simplest payment integration. User clicks "Upgrade", backend creates a Checkout Session with line items, frontend redirects to Stripe-hosted checkout page. Stripe handles all payment UI, PCI compliance, and fraud detection. |
| **Why not Payment Elements** | Payment Elements (inline forms) require handling card tokenization, error states, 3D Secure, and PCI scope increases. For a freemium SaaS with subscription plans, Checkout Sessions handle everything including trial periods, promo codes, and subscription management. |
| **Webhooks** | Backend listens for `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted` events. Uses `stripe.Webhook.construct_event()` for signature verification. |
| **Confidence** | HIGH -- Stripe Checkout is the recommended approach for SaaS subscriptions |

### SSE vs WebSocket for Chat
| Decision | Rationale |
|----------|-----------|
| **Approach** | Server-Sent Events (SSE) via sse-starlette |
| **Why not WebSocket** | Chat is unidirectional streaming (server -> client). The user sends a message via POST, the server streams the response via SSE. No need for persistent bidirectional connection. SSE works through standard HTTP infrastructure (proxies, load balancers, CDNs) without special configuration. WebSockets require sticky sessions and proxy configuration. |
| **Reconnection** | SSE has built-in reconnection with `Last-Event-ID`. If the connection drops mid-stream, the client can resume. |
| **Confidence** | HIGH -- SSE is the standard pattern for LLM streaming (used by OpenAI, Anthropic, etc.) |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| PDF Generation | WeasyPrint + Jinja2 | ReportLab | No HTML/CSS support; programmatic-only API is slower to iterate |
| PDF Generation | WeasyPrint + Jinja2 | Playwright PDF | Heavier (full browser), but would support JS charts. Overkill for styled reports. |
| PDF Generation | WeasyPrint + Jinja2 | xhtml2pdf | Less CSS support, less actively maintained than WeasyPrint |
| Chat Streaming | SSE (sse-starlette) | WebSocket | Bidirectional not needed; SSE simpler through proxies |
| Chat Streaming | SSE (sse-starlette) | Plain StreamingResponse | Lacks SSE event formatting, Last-Event-ID, proper event types |
| Markdown Rendering | marked | @nuxtjs/mdc | MDC is for static content with Vue component embedding; overkill for chat |
| Markdown Rendering | marked | vue-markdown-render | Wrapper around markdown-it; marked is faster and more widely used |
| Markdown Rendering | marked | markstream-vue | Purpose-built for streaming but newer/less proven; marked + manual append achieves same result |
| Frontend Payments | @stripe/stripe-js | @unlok-co/nuxt-stripe | Extra abstraction layer; direct SDK sufficient for Checkout redirect |
| CSV Export | Python stdlib csv | pandas | 200MB+ dependency for writing simple CSV; stdlib handles Jira format perfectly |
| Chat Context | Prompt stuffing | RAG (pgvector) | Audit data fits in context window; RAG adds unnecessary complexity |
| Code Highlighting | highlight.js | Prism.js | Both excellent; highlight.js has better auto-detection for LLM output |
| XSS Sanitization | DOMPurify | sanitize-html | DOMPurify is faster, more battle-tested, browser-native DOM parsing |

---

## Version Pinning Strategy

### Backend (requirements.txt)
Pin exact versions for stability. LiteLLM releases multiple times per week with potential breaking changes.

```
# Upgrades
stripe>=14.0.0,<15.0.0
litellm==1.81.15
weasyprint>=68.0

# New additions
sse-starlette>=3.2.0

# Removals
# langchain==0.1.0        -- REMOVE
# langchain-openai==0.0.2 -- REMOVE
# openai==1.7.0           -- REMOVE (migrate optimizer.py to litellm first)
```

### Frontend (package.json)
Use caret ranges for non-breaking updates.

```json
{
  "dependencies": {
    "marked": "^17.0.0",
    "marked-highlight": "^2.2.0",
    "highlight.js": "^11.11.0",
    "dompurify": "^3.3.0",
    "@stripe/stripe-js": "^8.0.0"
  }
}
```

---

## Installation Commands

### Backend
```bash
cd /home/salim/Informatique/Perso/Endexa/geo-platform-mvp/backend
source venv/bin/activate

# Upgrade existing
pip install "stripe>=14.0.0,<15.0.0"
pip install "litellm==1.81.15"
pip install "weasyprint>=68.0"

# Add new
pip install "sse-starlette>=3.2.0"

# Remove unused (after migrating optimizer.py)
pip uninstall langchain langchain-openai openai -y

# Regenerate requirements
pip freeze > requirements.txt
```

### Frontend
```bash
cd /home/salim/Informatique/Perso/Endexa/geo-platform-mvp/frontend

# Add new
npm install marked marked-highlight highlight.js dompurify @stripe/stripe-js

# Add TypeScript types
npm install -D @types/dompurify
```

---

## Per-Feature Library Summary

| Feature | Backend Libraries | Frontend Libraries | New Dependencies |
|---------|------------------|--------------------|-----------------|
| Scoring Pipeline | None new (scorers exist) | None new | 0 |
| Recommendations | None new (engine exists) | None new | 0 |
| PDF/HTML Reports | WeasyPrint (upgrade), Jinja2 (existing) | None | 0 new, 1 upgrade |
| Jira CSV Export | stdlib csv | None | 0 |
| Chat Assistant | sse-starlette, LiteLLM (upgrade) | marked, marked-highlight, highlight.js, dompurify | 1 new + 1 upgrade backend, 4 new frontend |
| Stripe Payments | stripe (upgrade) | @stripe/stripe-js | 1 upgrade backend, 1 new frontend |
| Competitor Benchmarking | None new (services exist) | None new | 0 |
| Code Analysis Prompts | Jinja2 (existing), LiteLLM (existing) | None | 0 |

**Total new backend packages:** 1 (sse-starlette)
**Total new frontend packages:** 5 (marked, marked-highlight, highlight.js, dompurify, @stripe/stripe-js)
**Total upgrades:** 3 (stripe, litellm, weasyprint)
**Total removals:** 3 (langchain, langchain-openai, openai)

---

## Sources

- Stripe Python SDK: [PyPI](https://pypi.org/project/stripe/) -- v14.3.0 verified via `pip index versions` (HIGH confidence)
- LiteLLM: [PyPI](https://pypi.org/project/litellm/) -- v1.81.15 verified via `pip index versions` (HIGH confidence)
- WeasyPrint: [PyPI](https://pypi.org/project/weasyprint/) -- v68.1 verified via `pip index versions` (HIGH confidence)
- sse-starlette: [PyPI](https://pypi.org/project/sse-starlette/) -- v3.2.0 verified via `pip index versions` (HIGH confidence)
- marked: [npm](https://www.npmjs.com/package/marked) -- v17.0.3 verified via `npm view` (HIGH confidence)
- marked-highlight: [npm](https://www.npmjs.com/package/marked-highlight) -- v2.2.3 verified via `npm view` (HIGH confidence)
- highlight.js: [npm](https://www.npmjs.com/package/highlight.js) -- v11.11.1 verified via `npm view` (HIGH confidence)
- DOMPurify: [npm](https://www.npmjs.com/package/dompurify) -- v3.3.1 verified via `npm view` (HIGH confidence)
- @stripe/stripe-js: [npm](https://www.npmjs.com/package/@stripe/stripe-js) -- v8.8.0 verified via `npm view` (HIGH confidence)
- @unlok-co/nuxt-stripe: [Nuxt Modules](https://nuxt.com/modules/stripe-next) -- v6.0.2 verified via `npm view` (HIGH confidence)
- Jira CSV import format: [Atlassian Docs](https://support.atlassian.com/jira-software-cloud/docs/import-data-to-a-software-project-using-a-csv-file/) (HIGH confidence)
- FastAPI SSE best practices: [Multiple sources](https://mahdijafaridev.medium.com/implementing-server-sent-events-sse-with-fastapi-real-time-updates-made-simple-6492f8bfc154) (MEDIUM confidence -- community patterns)
- RAG vs Prompt Stuffing: [SpyglassMTG](https://www.spyglassmtg.com/blog/rag-vs.-prompt-stuffing-overcoming-context-window-limits-for-large-information-dense-documents) (MEDIUM confidence)
- WeasyPrint vs alternatives: [PDFBolt](https://pdfbolt.com/blog/python-html-to-pdf-library), [Glukhov](https://www.glukhov.org/post/2025/05/generating-pdf-in-python/) (MEDIUM confidence)
