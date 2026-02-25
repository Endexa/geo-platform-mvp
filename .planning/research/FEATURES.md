# Feature Research: GEO/SEO Audit Platform

**Domain:** Generative Engine Optimization + SEO audit SaaS
**Researched:** 2026-02-25
**Confidence:** HIGH (based on competitor product pages, G2 reviews, pricing pages, market research reports, and existing internal research)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any GEO/SEO audit tool in 2026. Missing any of these = users bounce to a competitor within minutes.

| # | Feature | Why Expected | Complexity | Notes |
|---|---------|--------------|------------|-------|
| TS-1 | **URL-based audit with score** | Every competitor offers this (Geoptie free, HubSpot free, SevenSEO free). Users expect to enter a URL and get a score immediately. | MEDIUM | Already partially built (61 criteria framework exists but returns zeros). Must produce real, meaningful scores on first use. |
| TS-2 | **Multi-engine AI visibility tracking** | Otterly ($29/mo), AthenaHQ ($95/mo), Profound ($99/mo) all track across ChatGPT + Perplexity + Gemini minimum. 3+ engines is floor. | HIGH | Already built: 4 engines (OpenAI, Anthropic, Perplexity, Gemini). Must show per-engine breakdown with mention counts, sentiment, citations. |
| TS-3 | **Overall GEO readiness score (0-100)** | Geoptie uses 0-100 across 6 dimensions. Otterly has visibility score. Profound has brand visibility metrics. Users need a single number to anchor understanding. | MEDIUM | Dual-score architecture exists (Visibility + Optimization). Scoring formula researched. Need the scores to actually work. |
| TS-4 | **Category breakdown scores** | Geoptie breaks into 6 dimensions (citation readiness, answer alignment, content structure, factual density, authority, technical). Users expect to see where they're strong/weak. | MEDIUM | 4 categories exist (Crawlability, Content Structure, Structured Data, Authority). Weights researched. Must produce real numbers. |
| TS-5 | **Competitor comparison** | Every tool from Otterly ($29/mo) to Profound ($99/mo+) shows "how you compare to competitors." Users need context for their score. | HIGH | Auto-competitor discovery planned (NER from AI responses). Must show side-by-side scores. |
| TS-6 | **Actionable recommendations list** | Geoptie, Frase, and Profound all provide specific "do this next" items. A score without actions is worthless. Users leave tools that show problems but not solutions. | HIGH | Recommendation engine is a stub. This is the #1 feature gap. Must produce prioritized, specific, implementable suggestions. |
| TS-7 | **PDF/HTML audit report export** | SEOptimer, Semrush, and every agency-facing tool exports reports. Agencies need to send reports to clients. In-house teams share with stakeholders. | MEDIUM | Not built. Standard feature -- templated HTML -> PDF conversion. |
| TS-8 | **Dashboard with history/trends** | Otterly shows weekly tracking with position changes over time. SE Ranking shows Health Score progress. Users need to see improvement. | MEDIUM | Dashboard exists but shows fake data. Needs real metrics + trend lines. |
| TS-9 | **Freemium entry point** | HubSpot Grader is fully free. Geoptie offers free audit. SevenSEO free audit. Insites free. Users expect to try before paying. | LOW | Planned: free partial audit (crawlability). Smart gate -- show enough value to convert. |
| TS-10 | **Authentication + saved audits** | Users expect to create an account, run multiple audits, and see their history. | LOW | Already built (JWT auth, register/login/me). Need to wire audit history to user accounts properly. |

### Differentiators (Competitive Advantage)

Features that no or few competitors offer. These are where Endexa competes.

| # | Feature | Value Proposition | Complexity | Notes |
|---|---------|-------------------|------------|-------|
| D-1 | **SEO + GEO combined audit** | Frase.io is the only competitor doing dual SEO+GEO scoring ($39/mo+), but their focus is content optimization, not technical audit. No one offers a combined technical SEO + GEO audit with unified scoring. Most tools are GEO-only (Profound, Otterly, AthenaHQ) or SEO-only (Semrush, Ahrefs, SE Ranking adding GEO as afterthought). | HIGH | The 61 criteria already span both domains (Crawlability = SEO, Content Structure = GEO, Structured Data = both, Authority = both). This is the architectural differentiator. |
| D-2 | **Code analysis flow** | Zero competitors offer this. Every GEO/SEO tool is crawl-only. Enterprise teams with React/Next.js SPAs have hidden SEO/GEO problems that crawlers cannot detect (client-side rendering, meta tag generation logic, build pipeline issues). Endexa generates prompts -> user runs on their codebase -> uploads results -> deeper analysis. | HIGH | Novel feature. No market validation yet, but the crawl-only vs code-analysis gap is documented in market research. High complexity but high differentiation. |
| D-3 | **Jira/task export with structured stories** | Siteimprove has basic Jira integration. Semrush exports CSV. No GEO tool exports recommendations as structured Jira stories with epics, priorities, and acceptance criteria. SEO teams using Jira need to manually convert audit findings into tickets -- this automates it. | MEDIUM | Jira service is a stub. CSV export is simple. Customizable grouping (by category, priority, page) adds value. |
| D-4 | **Affordable pricing targeting SMBs/agencies** | Profound starts at $99/mo but real value is $399/mo+. AthenaHQ starts at $95/mo (intro) then $295/mo. Goodie AI starts at $495/mo. Otterly at $29/mo is closest but only monitors (no audit/recommendations). Gap: full audit + recommendations + competitor benchmarking under $50/mo. | LOW | Pricing decision, not feature complexity. Freemium + $29-49/mo starter tier undercuts every competitor offering comparable depth. |
| D-5 | **Priority-ordered recommendations with impact estimates** | Most tools give a flat list of issues. SE Ranking shows how much each fix improves your Health Score. Endexa should go further: "Fix this and your score improves by ~X points" with effort estimates (quick win / moderate / project). | MEDIUM | Requires scoring system to be fully working first. Then calculate delta: "if this criterion scored 100 instead of current, overall score changes by X." |
| D-6 | **Chat assistant for audit results** | Novel for GEO tools. Profound has AI agents but for content creation, not audit Q&A. Users should be able to ask "Why did I score low on structured data?" and get a contextual, evidence-based answer. | MEDIUM | LLM integration needed. Feed audit results as context -> let user ask questions. Not complex technically but powerful UX. |
| D-7 | **Per-page drill-down** | Crawl multiple pages, score each independently. Show which pages drag the overall score down. Competitors typically score the domain, not individual pages. | MEDIUM | Crawl pipeline exists. Need per-page scoring + rollup with weakest-link aggregation (already designed: 0.6*mean + 0.4*min). |
| D-8 | **Multi-site management for agencies** | Agencies manage 10-50+ client sites. Otterly offers this at higher tiers. Profound has it for enterprise. A clean multi-site dashboard with cross-client reporting is valuable for agency tier. | MEDIUM | Database already supports multiple audits. Need site grouping, client labels, cross-site comparison views. |

### Anti-Features (Deliberately NOT Building)

Features that seem valuable but create problems for Endexa's positioning, cost structure, or development velocity.

| # | Anti-Feature | Why Requested | Why Problematic | What to Do Instead |
|---|--------------|---------------|-----------------|-------------------|
| AF-1 | **Real-time continuous monitoring** | Otterly and Profound offer "always-on" monitoring with alerts. Seems essential. | Massively expensive in AI API costs. Each monitoring check across 4 engines for 100 prompts = $4-10/run. Daily monitoring for 1000 users = $4K-10K/day in API costs. Endexa is audit-first (on-demand), not monitoring-first. | Offer scheduled re-audits (weekly/monthly) instead of continuous. Users trigger audits when ready. Much cheaper, still shows trends. |
| AF-2 | **AI content generation/writing** | Profound creates AI-optimized content. Frase writes content. Goodie AI has a content writer. | Content generation is a different product category (competes with Jasper, Writer, ChatGPT itself). Dilutes audit focus. Massive LLM cost per generation. Quality control is hard. | Provide recommendations that tell users WHAT to write/change, not generate the content itself. Users already have AI writing tools. |
| AF-3 | **10+ AI engine coverage** | Profound covers 10+ engines. Seems like more = better. | Diminishing returns past 4-5 engines. ChatGPT + Perplexity + Gemini + Claude cover 90%+ of AI search traffic. Adding DeepSeek, Copilot, You.com etc. adds cost but minimal insight. Each engine needs its own API integration, prompt tuning, response parsing. | Cover 4 engines well (already built). Add DeepSeek/Copilot in v3 only if user demand proves it. |
| AF-4 | **White-label reports** | Agencies want to rebrand reports with their logo. Seems like easy upsell. | White-label adds significant UI complexity (custom logos, colors, domains, email templates). Delays core product. Enterprise feature that distracts from SMB focus. | Offer clean PDF export with Endexa branding. White-label in v3 for enterprise tier only. |
| AF-5 | **Direct repository access / GitHub integration** | Could auto-analyze code instead of prompt-based flow. | Security nightmare (accessing customer codebases). Massive complexity (parsing every framework). Trust barrier ("give us access to your repo"). | Use the prompt-based code analysis flow (D-2). User runs prompts locally, uploads results. Zero trust/security concerns. |
| AF-6 | **Real-time prompt volume data** | Profound shows what millions of users ask AI. AthenaHQ tracks prompt volumes. | Requires access to AI platform data or massive query sampling infrastructure. No public API for prompt volume data. Would need to build/buy query intelligence, which is Profound's core moat ($96M raised). | Focus on query generation (already built: query_generator.py creates relevant prompts) and actual AI responses. Don't try to measure "what people ask" -- measure "what AI says." |
| AF-7 | **Brand Signature Engine** | Comparing content against established brand voice. Interesting for consistency. | pgvector embeddings complexity. Deferred to v3 per project decision. Would delay audit core. | Focus v2 on audit + recommendations. Brand voice analysis in v3 when core is solid. |
| AF-8 | **CRM integrations (Salesforce, HubSpot, Marketo)** | Enterprise SEO tools have them. Connects SEO to pipeline metrics. | Enterprise complexity. Each CRM integration is 2-4 weeks of development. Most SMBs/agencies don't need this. | Offer webhook API + Zapier-compatible CSV exports. Let users connect to their CRM via Zapier. Native CRM integrations in v3 enterprise tier. |

## Feature Dependencies

```
[TS-1] URL-based audit with score
    |-- requires --> Working scoring pipeline (all 61 criteria produce real measurements)
    |-- requires --> Crawl service (already built)
    |-- enables --> [TS-3] Overall GEO readiness score
    |-- enables --> [TS-4] Category breakdown scores
    |-- enables --> [D-7] Per-page drill-down

[TS-3] Overall GEO readiness score
    |-- requires --> [TS-1] URL-based audit with score
    |-- enables --> [TS-5] Competitor comparison (need scores to compare)
    |-- enables --> [TS-8] Dashboard with history (need scores to trend)

[TS-2] Multi-engine AI visibility tracking
    |-- requires --> LLM dispatch (already built)
    |-- requires --> Mention detection (already built)
    |-- requires --> Query generator (already built)
    |-- enables --> [TS-5] Competitor comparison (competitor mentions)
    |-- enables --> [D-5] Impact estimates (AI visibility component)

[TS-5] Competitor comparison
    |-- requires --> [TS-3] Overall GEO readiness score (for site score comparison)
    |-- requires --> [TS-2] Multi-engine AI visibility tracking (for mention comparison)
    |-- requires --> Auto-competitor discovery (NER from AI responses, partially built)

[TS-6] Actionable recommendations
    |-- requires --> [TS-1] URL-based audit with score (need scores to generate recs)
    |-- requires --> [TS-4] Category breakdown (need to know weak areas)
    |-- enables --> [D-3] Jira export (need recommendations to export)
    |-- enables --> [D-5] Priority-ordered with impact (need recs + scoring)
    |-- enables --> [D-6] Chat assistant (need recs as context)

[D-1] SEO + GEO combined audit
    |-- requires --> [TS-1] URL-based audit (must work for both SEO and GEO criteria)
    |-- enhances --> [TS-6] Actionable recommendations (broader recommendation surface)

[D-2] Code analysis flow
    |-- independent of --> [TS-1] (can be built separately)
    |-- enhances --> [TS-6] Actionable recommendations (deeper, code-level recs)
    |-- enhances --> [D-7] Per-page drill-down (code context per page)

[D-3] Jira export
    |-- requires --> [TS-6] Actionable recommendations (must have recs to export)

[D-6] Chat assistant
    |-- requires --> [TS-1] URL-based audit (need audit context)
    |-- requires --> [TS-6] Recommendations (need recs as context)
    |-- enhances --> user engagement and understanding

[D-8] Multi-site management
    |-- requires --> [TS-1] URL-based audit (must work per site)
    |-- requires --> [TS-10] Authentication (sites belong to users)
    |-- enhances --> [TS-8] Dashboard (cross-site views)

[TS-7] PDF/HTML report export
    |-- requires --> [TS-1] URL-based audit (need audit data)
    |-- requires --> [TS-6] Recommendations (reports need recs)
    |-- independent of --> [D-3] Jira export (different output format)

[TS-9] Freemium entry point
    |-- requires --> [TS-1] URL-based audit (must show partial audit free)
    |-- conflicts with --> giving away too much (gate must be carefully positioned)
```

### Dependency Notes

- **[TS-1] is the critical path root.** Nothing else works until the scoring pipeline produces real numbers. This must be Phase 1 of any rebuild.
- **[TS-6] Recommendations is the second critical dependency.** Jira export, chat assistant, PDF reports, and impact estimates all depend on having real recommendations. This is Phase 2.
- **[TS-5] Competitor comparison needs both scoring AND AI visibility working.** This is Phase 3 at earliest.
- **[D-2] Code analysis flow is independent.** Can be built in parallel with other features. No dependency on scoring pipeline.
- **[D-8] Multi-site is an overlay.** Works once single-site audit works. Defer until core is solid.

## MVP Definition

### Launch With (v2.0) -- Get to "Minimum Lovable Product"

- [x] [TS-1] **Working URL-based audit** -- The core product. All 61 criteria must produce real, meaningful measurements. Without this, nothing else matters.
- [x] [TS-3] **Overall GEO readiness score** -- Single number users can track. Dual-score (Visibility + Optimization) with research-backed formula.
- [x] [TS-4] **Category breakdown** -- 4 categories with individual scores. Shows where to focus.
- [x] [TS-2] **Multi-engine AI visibility** -- Run queries across 4 engines, show mention counts and sentiment per engine.
- [x] [TS-6] **Actionable recommendations** -- Priority-ordered list of specific fixes. This is what converts free to paid.
- [x] [TS-9] **Freemium gate** -- Free crawlability audit. Paid unlocks full audit + recommendations.
- [x] [TS-10] **Auth + saved audits** -- Already built. Wire audit history properly.

### Add After Validation (v2.x) -- Prove Conversion, Then Expand

- [ ] [TS-5] **Competitor comparison** -- Add when users ask "how do I compare?" Auto-discover competitors from AI responses. Side-by-side scores.
- [ ] [D-5] **Impact estimates on recommendations** -- "Fix this = +X points." Calculated from scoring model. Adds urgency to recommendations.
- [ ] [TS-7] **PDF/HTML report export** -- Essential for agencies. Template-based generation from audit data.
- [ ] [D-3] **Jira/CSV export** -- Convert recommendations into structured tasks. Customizable grouping.
- [ ] [TS-8] **Dashboard with trends** -- Show score history over time. Requires multiple audits per site.
- [ ] [D-7] **Per-page drill-down** -- Crawl multiple pages, score each. Show weakest pages.

### Future Consideration (v3+) -- After Product-Market Fit

- [ ] [D-2] **Code analysis flow** -- Novel but unvalidated. Build only after confirming demand from developer personas.
- [ ] [D-6] **Chat assistant** -- Nice UX but not critical for conversion. Add when audit+recs are polished.
- [ ] [D-8] **Multi-site management** -- Agency tier feature. Build when agency adoption proves demand.
- [ ] [AF-4] White-label reports -- Enterprise only. v3.
- [ ] [AF-8] CRM integrations -- Enterprise only. v3.
- [ ] Brand Signature Engine -- Deferred per project decision. v3.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Phase |
|---------|------------|---------------------|----------|-------|
| [TS-1] Working scoring pipeline | HIGH | HIGH (61 criteria) | P1 | v2.0 |
| [TS-3] Overall GEO score | HIGH | LOW (aggregation) | P1 | v2.0 |
| [TS-4] Category breakdown | HIGH | LOW (sub-aggregation) | P1 | v2.0 |
| [TS-2] Multi-engine AI visibility | HIGH | MEDIUM (already built, needs polish) | P1 | v2.0 |
| [TS-6] Recommendations engine | HIGH | HIGH (LLM-powered) | P1 | v2.0 |
| [TS-9] Freemium gate | HIGH | LOW (access control) | P1 | v2.0 |
| [D-1] SEO+GEO combined | HIGH | LOW (architectural, already designed) | P1 | v2.0 |
| [D-5] Impact estimates | HIGH | MEDIUM (delta calculation) | P2 | v2.x |
| [TS-5] Competitor comparison | HIGH | HIGH (auto-discovery + benchmarking) | P2 | v2.x |
| [TS-7] PDF/HTML export | MEDIUM | MEDIUM (templating) | P2 | v2.x |
| [D-3] Jira/CSV export | MEDIUM | MEDIUM (structured export) | P2 | v2.x |
| [TS-8] Dashboard trends | MEDIUM | MEDIUM (charting + history) | P2 | v2.x |
| [D-7] Per-page drill-down | MEDIUM | MEDIUM (multi-page crawl) | P2 | v2.x |
| [D-6] Chat assistant | MEDIUM | MEDIUM (LLM + context) | P3 | v3 |
| [D-2] Code analysis flow | MEDIUM | HIGH (novel, unvalidated) | P3 | v3 |
| [D-8] Multi-site management | LOW-MEDIUM | MEDIUM (UI + data model) | P3 | v3 |

**Priority key:**
- P1: Must have for v2.0 launch. Without these, product is not viable.
- P2: Should have. Add within 1-2 months of launch. Drives retention and agency adoption.
- P3: Nice to have. Build based on user demand signals.

## Competitor Feature Analysis

| Feature | Profound ($99-399/mo+) | Otterly ($29-989/mo) | AthenaHQ ($95-2K/mo) | Frase.io ($39/mo+) | Geoptie (Free+) | **Endexa (Planned)** |
|---------|----------------------|---------------------|---------------------|-------------------|----------------|---------------------|
| GEO readiness score | Visibility metrics | Visibility score | GEO Score | SEO+GEO dual score | 0-100 across 6 dims | **Dual score: Visibility + Optimization** |
| AI engine coverage | 10+ engines | 3-4 engines | 5+ engines | 4 engines | 4+ engines | **4 engines (sufficient)** |
| Competitor benchmarking | Yes (enterprise) | Yes (basic) | Yes (detailed) | Yes (SERP-based) | Yes (vs. competitors) | **Yes (auto-discovered from AI responses)** |
| Actionable recommendations | AI-powered content recs | No (monitoring only) | Limited insights | Content optimization recs | Recs per dimension | **Priority-ordered, impact-estimated recs** |
| SEO + GEO combined | No (GEO only) | No (GEO only) | No (GEO only) | Yes (content focus) | No (GEO only) | **Yes (technical audit, 61 criteria)** |
| Code analysis | No | No | No | No | No | **Yes (prompt-based flow)** |
| Jira export | No | No | No | No | No | **Yes (structured stories)** |
| PDF report | Custom dashboards | Weekly reports | Custom reports | Content briefs | Audit report | **Yes (branded PDF)** |
| Content generation | Yes (one-click) | No | No | Yes (AI writer) | No | **No (deliberate -- recs only)** |
| Freemium | No (paid only) | Free trial (7 days) | Intro pricing ($95) | 7-day free trial | Free audit tool | **Free crawlability audit (permanent)** |
| Pricing accessibility | $99/mo starter | $29/mo starter | $95 intro/$295 standard | $39/mo all features | Free + paid tiers | **Free + $29-49/mo target** |
| Chat assistant | No | No | No | No | No | **Planned (v3)** |
| Multi-site | Enterprise tier | Higher tiers | Enterprise | Unlimited in all plans | Per-audit | **Planned (v2.x+)** |

### Key Competitive Observations

1. **The recommendation gap is real.** Otterly (monitoring only), AthenaHQ (limited insights), and Geoptie (basic recs) leave a massive gap. Only Profound and Frase offer deep actionable recommendations, and Profound costs $399/mo+ for real value. This is where Endexa wins.

2. **SEO+GEO combined is nearly uncontested.** Frase.io does dual scoring but for content optimization only (not technical audit). No tool audits both traditional SEO signals AND GEO signals in a unified technical audit. This is Endexa's structural advantage.

3. **Code analysis is a blue ocean.** Zero competitors offer any form of codebase analysis. Every tool is crawl-only. This is risky (unvalidated) but potentially a category-defining feature.

4. **Jira export is unique.** Siteimprove has basic Jira integration for accessibility issues. No GEO/SEO tool exports structured Jira stories from audit recommendations. Developer/agency teams will value this.

5. **Price positioning is favorable.** The market has a gap between "free but shallow" (Geoptie, HubSpot, SevenSEO) and "deep but expensive" (Profound $399/mo, AthenaHQ $295/mo, Goodie $495/mo). Endexa at $29-49/mo with deep audit + recommendations fills this gap.

## What Users Actually Pay For (Conversion Drivers)

Based on competitor pricing tiers and G2/review analysis:

1. **Actionable recommendations** -- The #1 conversion driver. Free tools show problems; paid tools tell you how to fix them. "If the tool doesn't shorten the path between insight and execution, you'll end up with another shiny dashboard your team ignores by week two." (Search Engine Land)

2. **Ongoing tracking/trending** -- Users pay to see improvement over time. "Did my changes help?" requires historical data. Free = snapshot, paid = trajectory.

3. **Competitor intelligence** -- Users pay to know "am I winning or losing vs. competitors?" Competitive benchmarking is consistently behind paywalls.

4. **Export/reporting** -- Agencies pay for professional reports they can send to clients. In-house teams pay for exports they can share with stakeholders.

5. **Volume (more queries, more pages, more engines)** -- Metered usage is the standard SaaS gating mechanism. Otterly gates on "search prompts" (15 free, 100 at $189/mo). AthenaHQ gates on "credits."

### Freemium Gate Recommendation

**Free tier (Crawlability Audit):**
- Crawlability category score (C1-C12): robots.txt, SSR detection, TTFB, HTTP status, sitemap
- Overall score (but with categories grayed out)
- Top 3 recommendations (out of full list)
- No AI visibility queries (too expensive for free tier)
- No competitor comparison

**Paid tier ($29-49/mo, Full Audit):**
- All 4 category scores + all 61 criteria
- Full AI visibility queries across 4 engines
- Complete recommendation list with priorities and impact estimates
- Competitor auto-discovery and benchmarking
- PDF report export
- Audit history and trending
- Jira/CSV export

**Rationale:** Crawlability is cheap to compute (no LLM calls), provides immediate value, and naturally reveals problems that require the full audit to solve. "Your robots.txt blocks AI crawlers" makes users want to know what ELSE is wrong.

## Sources

### Competitor Pricing & Features (verified Feb 2026)
- [Profound pricing & features](https://www.tryprofound.com/pricing) -- $99/mo starter, $399/mo growth, custom enterprise
- [Profound $96M raise (Fortune, Feb 2026)](https://fortune.com/2026/02/24/exclusive-as-ai-threatens-search-profound-raises-96-million-to-help-brands-stay-visible/)
- [Profound review (Rankability)](https://www.rankability.com/blog/profound-ai-review/)
- [Otterly.AI pricing](https://otterly.ai/pricing) -- $29/mo lite, $189/mo standard, $989/mo pro
- [Otterly.AI features](https://otterly.ai/features)
- [AthenaHQ pricing](https://athenahq.ai/plans) -- $95 intro, $295/mo standard, $2K+ enterprise
- [AthenaHQ review (Rankability)](https://www.rankability.com/blog/athenahq-ai-review/)
- [Goodie AI review (Bermawy)](https://bermawy.com/blog/goodie-ai-geo-platform-review) -- $495/mo+
- [Frase.io pricing](https://www.frase.io/pricing) -- $39/mo all features
- [Frase.io GEO features](https://www.frase.io/features/geo-content-optimization)
- [Geoptie free GEO audit](https://geoptie.com/free-geo-audit) -- 6 dimensions, 0-100 score

### Market Research
- [AI SEO Tracking Tools 2026 Comparative Analysis (Search Influence)](https://www.searchinfluence.com/blog/ai-seo-tracking-tools-2026-analysis-platforms/)
- [Best GEO Tools 2026 (Nick Lafferty)](https://nicklafferty.com/blog/best-generative-engine-optimization-tools-2025/)
- [Best GEO Software 2026 (Alex Birkett)](https://www.alexbirkett.com/generative-engine-optimization-software/)
- [NoGood GEO Tools 2026](https://nogood.io/blog/generative-engine-optimization-tools/)
- [SE Ranking GEO Tools Review 2026](https://visible.seranking.com/blog/best-generative-engine-optimization-tools-2026/)

### Internal Research
- [Endexa SEO-GEO Market Research](endexa-audit-review-2/SEO-GEO-MARKET-RESEARCH.md) -- Princeton GEO findings, enterprise challenges, market consolidation
- [Endexa GEO Tools Comparison Chart](endexa-audit-review-2/GEO-TOOLS-COMPARISON-CHART.md) -- Tier-based competitor analysis

### SEO Audit & Workflow
- [Siteimprove Jira integration](https://www.siteimprove.com/integrations/connectors/jira/)
- [Semrush SEO audit tools](https://www.semrush.com/blog/seo-audit-tools/)
- [Search Engine Land: Why your website needs a GEO audit now](https://searchengineland.com/why-your-website-needs-a-geo-audit-now-460056)

---
*Feature research for: GEO/SEO Audit Platform (Endexa v2)*
*Researched: 2026-02-25*
