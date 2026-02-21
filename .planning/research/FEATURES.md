# Feature Landscape: AI Brand Visibility Auditor

**Domain:** AI Brand Visibility / Generative Engine Optimization (GEO) Monitoring
**Researched:** 2026-02-21
**Overall confidence:** MEDIUM (based on training data knowledge of competitors; web verification tools were unavailable during this research session -- findings should be spot-checked against current competitor sites)

---

## Competitive Landscape Overview

The GEO/AIO monitoring space has matured rapidly since 2024. Key players examined:

| Competitor | Focus | Pricing Model | Target |
|------------|-------|---------------|--------|
| **Profound** (getprofound.ai) | AI search visibility tracking, brand monitoring across AI engines | SaaS, tiered by queries/brands | Enterprise, agencies |
| **Otterly.ai** | AI search monitoring, SERP + AI answer tracking | SaaS, tiered by keywords | SEO teams, agencies |
| **Peec AI** | AI visibility analytics, content optimization for AI | SaaS | Content teams, marketers |
| **Knowatoa** | AI brand mention tracking, competitive intelligence | SaaS | Brands, agencies |
| **Others** | Scrunch AI, HubSpot AI tools, Semrush/Ahrefs (adding GEO features), BrightEdge, seoClarity | Various | Various |

**Confidence note:** Competitor feature details below are MEDIUM confidence from training data. This space evolves fast -- specific feature availability and pricing should be verified against current competitor websites before finalizing requirements.

---

## Table Stakes

Features users expect. Missing any of these means the product feels incomplete compared to competitors.

| # | Feature | Why Expected | Complexity | Confidence | Notes |
|---|---------|--------------|------------|------------|-------|
| TS-1 | **Multi-engine AI querying** | Every competitor queries at least ChatGPT + Perplexity + Gemini. Users expect coverage across major AI engines. | High | HIGH | ChatGPT, Claude, Perplexity minimum. Gemini strongly recommended. Each engine has different API patterns. |
| TS-2 | **Brand mention detection with verbatim quotes** | Core value prop of the entire category. Users want to see exactly what AI says about them, word for word. | Medium | HIGH | Must capture the actual text, not just "mentioned: yes/no". Profound and Otterly both show real quotes. |
| TS-3 | **Visibility score (0-100)** | Quantified metric that can be tracked over time and reported to stakeholders. Every competitor has some version of this. | Medium | HIGH | Must be transparent about how it is calculated. Breakdowns by engine, by topic, by query type add significant value. |
| TS-4 | **Competitor comparison / gap analysis** | Users cannot evaluate their visibility in isolation. "You are mentioned 3/10 times, but [Competitor X] is mentioned 8/10" is the core insight. | High | HIGH | Requires querying for competitors too, which multiplies API costs. Essential for agencies managing multiple brands. |
| TS-5 | **Query/prompt management** | Users need to control what questions are asked to AI engines. Auto-generation gets them started, custom queries let them dig deeper. | Medium | HIGH | Profound allows custom prompt sets. Otterly tracks keyword-based queries. Both auto-suggest and manual are expected. |
| TS-6 | **Dashboard with score overview** | Single-screen summary: overall score, per-engine breakdown, trend direction, top issues. Every SaaS product has this. | Medium | HIGH | Must be scannable in under 10 seconds. Agencies need multi-brand dashboard views. |
| TS-7 | **Actionable recommendations** | Users want to know WHAT TO DO, not just WHAT THE SCORE IS. "Add FAQ schema," "Cite authoritative sources," "Structure for entity extraction." | Medium | HIGH | Generic recommendations are table stakes. Specific, prioritized recommendations are a differentiator (see below). |
| TS-8 | **Export / reporting** | Agencies need to send reports to clients. In-house teams need to report to leadership. PDF or CSV export minimum. | Low | HIGH | PDF reports with brand logo are the standard. CSV for data portability. |
| TS-9 | **Query history and results over time** | Users need to see if their changes are working. "Last month: mentioned 2/10 times. This month: 5/10." | Medium | MEDIUM | Requires storing historical results. Natural upsell for monitoring tier. |
| TS-10 | **Site crawl and AI-readiness signals** | Checking structured data, schema.org, robots.txt AI directives, content structure. This is the "technical audit" component. | Medium | HIGH | Already partially built in existing codebase. Complements the AI query results. |

---

## Differentiators

Features that set the product apart. Not universally expected but highly valued. These create competitive advantage.

| # | Feature | Value Proposition | Complexity | Confidence | Notes |
|---|---------|-------------------|------------|------------|-------|
| DF-1 | **URL-first instant audit** (enter URL, get results) | Most competitors require keyword setup, brand name configuration, onboarding flow. A "just paste your URL and see results" flow is dramatically lower friction. Profound and Peec require setup; an instant audit is a wedge. | Medium | HIGH | This is the project's stated approach and a genuine differentiator in the market. The auto-generated queries from crawled site content are the key enabler. |
| DF-2 | **AI engine response sentiment analysis** | Beyond "mentioned or not" -- is the AI saying positive, negative, or neutral things? "ChatGPT recommends your competitor for quality but mentions you for price" is a richer insight than just presence/absence. | Medium | MEDIUM | Few competitors do sentiment well. Requires NLP/LLM analysis of captured responses. pgvector embeddings in the existing stack support this. |
| DF-3 | **Contextual mention analysis** (in what context are you mentioned?) | Categorize mentions: recommendation vs. comparison vs. warning vs. factual. "Claude recommends you for enterprise" vs. "Claude warns about your pricing" are very different. | High | MEDIUM | This goes beyond basic mention detection. LLM-based classification of the context around each mention. |
| DF-4 | **AI content gap identification** | Not just "you are not mentioned" but "here is the specific type of content/authority signal that would get you mentioned." Connects the gap to an actionable content strategy. | High | MEDIUM | Requires analyzing WHY competitors get mentioned (their content structure, authority signals) and mapping that to what the user lacks. |
| DF-5 | **Per-query drill-down with full AI response** | Show the complete AI response for each query, with the brand mention highlighted in context. Users want to read the full answer, not just an extracted snippet. | Low | HIGH | Simple to implement but surprisingly few competitors do this well. Storing full responses is the key requirement. |
| DF-6 | **Automated query generation from site content** | Crawl the site, identify the brand's domain/topics/products, auto-generate the most relevant queries an AI user would ask. Zero-config onboarding. | High | HIGH | Core part of the stated product vision. Competitors typically require manual keyword/query entry. This is a significant UX advantage. |
| DF-7 | **Multi-brand management for agencies** | One account, multiple brands, each with their own queries, competitors, and scores. Agency billing with per-brand pricing. | Medium | MEDIUM | Table stakes for agency-focused tools (Profound, Otterly have this). Differentiator if done with particularly good UX -- quick switching, consolidated reporting, white-label. |
| DF-8 | **Source attribution tracking** | When an AI cites sources in its response, track which sources are cited alongside (or instead of) the user's brand. "Perplexity cites competitor.com as its source for this answer." | Medium | MEDIUM | Perplexity includes citations natively. ChatGPT browse mode does too. Tracking cited sources reveals optimization targets. |
| DF-9 | **Content-level recommendations** (not just technical) | "Your About page lacks E-E-A-T signals" is technical. "Rewrite your FAQ to directly answer 'What is the best X for Y?' with structured claims" is content-level. The latter is far more actionable. | High | MEDIUM | Requires LLM-powered analysis comparing user content to what AI engines are actually surfacing. Significant cost per analysis. |
| DF-10 | **Prompt variation testing** | Same intent, different phrasings. "Best CRM for small business" vs "What CRM should a startup use?" vs "Compare CRM tools" -- visibility can vary dramatically by phrasing. | Medium | MEDIUM | Shows users that AI visibility is not monolithic. Reveals which phrasings they rank for and which they do not. Adds to query volume/cost. |

---

## Anti-Features

Features to explicitly NOT build. Either they are traps, off-strategy, or negative-value.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|--------------|-----------|-------------------|
| AF-1 | **Real-time continuous monitoring in MVP** | Multiplies API costs by orders of magnitude. Adds infrastructure complexity (scheduler, queue management, alerting). The stated plan correctly defers this to v2 paid tier. | One-time audit with optional re-run. Store results for comparison. Monitoring is a natural upsell. |
| AF-2 | **Content rewriting / generation** | Scope creep into a completely different product category (AI writing tools). Agencies have their own content workflows and tools. | Provide specific, actionable recommendations. Tell users WHAT to fix and WHY, not write it for them. Link to specific pages/sections. |
| AF-3 | **Traditional SEO metrics** (backlinks, keyword rankings, SERP position) | Existing tools (Ahrefs, Semrush, Moz) own this completely. Competing on SEO metrics is a losing battle and dilutes the GEO positioning. | Focus exclusively on AI engine visibility. Reference traditional SEO only where it directly impacts AI mentions (e.g., "high-authority backlinks correlate with AI citation"). |
| AF-4 | **Social media monitoring** | Different domain entirely. Brands already use Brandwatch, Mention, Sprout Social. Adding social monitoring muddies the value proposition. | Stay focused on AI engine responses to user queries. Social signals may inform AI training data, but tracking social is out of scope. |
| AF-5 | **White-label / API-first for MVP** | Engineering overhead for multi-tenancy, custom branding, API documentation, rate limiting per tenant. Premature optimization for market fit stage. | Build clean internal APIs. White-label can be layered on later. Agency features (multi-brand) are different from white-label. |
| AF-6 | **Manual prompt engineering interface** | Building a prompt playground where users craft and test AI prompts is a different product. Tempting because the infrastructure exists, but it distracts from the audit value. | Auto-generate queries from site content. Allow users to add/edit queries, but do not build a prompt engineering tool. |
| AF-7 | **AI chatbot / assistant** | Adding a "ask our AI about your results" chatbot adds significant complexity and cost with marginal value at MVP stage. The dashboard should be self-explanatory. | Invest in clear dashboard UX, tooltips, and contextual help. If users cannot understand the score without a chatbot, the UX needs work. |
| AF-8 | **Browser extension** | Engineering distraction. Different platform, different review process, different support burden. | Web-first. A bookmarklet or simple URL input is sufficient for triggering audits. |

---

## What Competitors Do Well (lessons to absorb)

### Profound (getprofound.ai)
- **Strength:** Deep tracking across multiple AI engines with trend data over time. Clean dashboard with per-engine breakdowns. Strong agency focus with multi-brand management.
- **Weakness:** Requires onboarding setup. No instant audit. Pricing reportedly high for smaller teams.
- **Learn:** Their per-engine breakdown visualization is the right pattern. Score decomposition matters.

### Otterly.ai
- **Strength:** Combines traditional SERP monitoring with AI answer tracking. Good at showing when AI answers replace organic results. Keyword-centric approach aligns with SEO team mental models.
- **Weakness:** More focused on AI Overviews in Google than standalone AI engines like ChatGPT/Claude. Less focused on brand perception, more on keyword presence.
- **Learn:** The bridge from traditional SEO to GEO is valuable for user education. Showing AI answer vs. organic result side-by-side is insightful.

### Peec AI
- **Strength:** Content optimization focus. Analyzes what makes content AI-friendly and provides specific optimization guidance.
- **Weakness:** Less emphasis on actual AI query monitoring. More diagnostic than monitoring.
- **Learn:** Their content analysis approach is complementary to query-based monitoring. Both are needed.

### Knowatoa
- **Strength:** Competitive intelligence angle. Good at showing relative brand position in AI responses. Clean, focused product.
- **Weakness:** Smaller engine coverage in earlier versions. Less established brand.
- **Learn:** Competitive positioning view is essential. "You vs. Competitor X across 50 queries" is a killer view.

### Common gaps across all competitors
- **No instant, URL-first audit flow.** All require setup/onboarding.
- **Limited explanation of WHY.** They show scores but rarely explain the causal chain: "Your content lacks structured FAQs -> AI engines cannot extract authoritative answers -> low mention rate."
- **Weak content-to-visibility mapping.** They track AI mentions but do not connect back to specific pages/content on the user's site that should be driving those mentions.
- **Limited prompt variation analysis.** Most use fixed queries, not testing how different phrasings affect visibility.

---

## Feature Dependencies

```
TS-1 (Multi-engine querying) --> TS-2 (Mention detection with quotes)
                             --> TS-3 (Visibility score)
                             --> TS-4 (Competitor comparison)
                             --> DF-5 (Full response drill-down)
                             --> DF-8 (Source attribution)

TS-10 (Site crawl) --> DF-6 (Auto query generation)
                   --> DF-4 (Content gap identification)

DF-6 (Auto query generation) --> TS-5 (Query management - needs auto-gen as starting point)

TS-2 (Mention detection) --> DF-2 (Sentiment analysis)
                         --> DF-3 (Contextual mention analysis)

TS-3 (Visibility score) --> TS-9 (History/trends - requires score to track)

TS-4 (Competitor comparison) --> DF-4 (Content gap identification)

TS-6 (Dashboard) --> TS-8 (Export/reporting - dashboard data feeds reports)

TS-7 (Recommendations) --> DF-9 (Content-level recommendations - enhanced version)
```

### Critical Path

The critical dependency chain is:
1. **Site crawl** (TS-10) feeds **auto query generation** (DF-6)
2. **Multi-engine querying** (TS-1) is the foundation for all mention/score features
3. **Mention detection** (TS-2) + **Visibility score** (TS-3) are the core output
4. **Competitor comparison** (TS-4) requires running the same pipeline for competitor brands
5. Everything else layers on top of these four pillars

---

## MVP Recommendation

### Must Build (Phase 1 - Core Audit Loop)

1. **TS-10: Site crawl and AI-readiness signals** -- already partially built. Foundation for auto-generation.
2. **DF-6: Auto query generation from site content** -- THE differentiator for onboarding. Makes the URL-first instant audit possible.
3. **TS-1: Multi-engine AI querying** -- ChatGPT + Claude + Perplexity minimum. This is the product.
4. **TS-2: Brand mention detection with verbatim quotes** -- Core output. Without quotes, there is no proof.
5. **TS-3: Visibility score** -- The metric users will track and report.
6. **DF-5: Per-query drill-down with full AI response** -- Low complexity, high value. Store and display full responses.

### Must Build (Phase 2 - Competitive Intelligence)

7. **TS-4: Competitor comparison / gap analysis** -- This is what makes the audit actionable. "You are not mentioned, but here is who is."
8. **TS-5: Query/prompt management** -- Let users customize after auto-generation gives them a starting point.
9. **TS-7: Actionable recommendations** -- Even basic recommendations dramatically increase perceived value.
10. **TS-6: Dashboard** -- Aggregate view of all the above.

### Build Later (Phase 3+)

11. **TS-9: Query history over time** -- Natural when monitoring tier launches.
12. **TS-8: Export/reporting** -- Important for agencies but can ship after core loop is solid.
13. **DF-2: Sentiment analysis** -- Enrichment on top of working mention detection.
14. **DF-3: Contextual mention analysis** -- Advanced enrichment.
15. **DF-7: Multi-brand for agencies** -- After product-market fit is validated.
16. **DF-8: Source attribution tracking** -- Nice enrichment for Perplexity/Bing responses.
17. **DF-10: Prompt variation testing** -- Advanced feature for power users.
18. **DF-4: AI content gap identification** -- Requires significant LLM analysis, defer until unit economics are understood.
19. **DF-9: Content-level recommendations** -- Most expensive and complex feature. Defer until the audit loop is proven.

### Defer Indefinitely

All anti-features (AF-1 through AF-8) unless explicitly reconsidered.

---

## Cost Considerations Affecting Feature Prioritization

AI engine API costs directly constrain feature scope:

| Feature | Cost Impact | Mitigation |
|---------|-------------|------------|
| TS-1 Multi-engine querying | ~$0.01-0.05 per query per engine (3 engines x N queries) | Cache responses aggressively. Batch queries where API allows. |
| TS-4 Competitor comparison | Multiplies query cost by number of competitors (typically 3-5) | Limit free tier to 2 competitors. Run competitor queries less frequently. |
| DF-6 Auto query generation | One-time LLM call to generate queries from crawled content (~$0.02-0.10) | Cache generated queries. Only regenerate on explicit request or re-crawl. |
| DF-2/DF-3 Sentiment/context analysis | Additional LLM call per response for classification (~$0.01-0.03 each) | Can use smaller/cheaper models for classification. Batch process. |
| DF-9 Content-level recommendations | Expensive: analyzing user content + AI responses + generating recommendations (~$0.10-0.50 per audit) | Defer to paid tier. Rate limit. Cache recommendation templates. |

**Estimated cost per full audit (MVP):** $0.15-0.50 depending on query count and competitor count. At scale, this means the product needs to charge or aggressively cache to avoid losing money on free audits.

---

## Sources and Confidence Notes

- Competitor feature analysis is based on training data knowledge (pre-May 2025) and general understanding of the GEO monitoring space. **MEDIUM confidence.** Features and pricing may have changed. Verify against current competitor websites before making final product decisions.
- Feature complexity estimates are based on the existing codebase capabilities documented in PROJECT.md and CLAUDE.md. **HIGH confidence** for estimates involving existing infrastructure, **MEDIUM confidence** for net-new capabilities.
- Cost estimates are approximate based on published API pricing for OpenAI, Anthropic, and Perplexity as of early 2025. **MEDIUM confidence** -- verify current pricing.
- The recommendation to lead with URL-first instant audit as the primary differentiator is **HIGH confidence** -- this aligns with the project vision and addresses a genuine gap in competitor offerings observed across training data.
