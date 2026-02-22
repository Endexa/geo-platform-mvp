# Phase 6: Site AI-Readiness Scoring - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Score each crawled page against 53 research-backed SEO+GEO criteria with purpose-built scoring services, producing per-page and per-category scores that roll up into an Optimization Score (0-100) displayed alongside the existing Visibility Score. The formula, weights, and criteria are defined in the roadmap. This phase builds the scoring engine and integrates it into the audit pipeline — it does NOT add premium tiers, page selection UI, or user-facing comparison features.

</domain>

<decisions>
## Implementation Decisions

### Page scope & crawl cap
- Score ALL crawled pages, not just the homepage — AI engines cite individual content pages, not homepages
- Default crawl cap of 25 pages per audit — small sites get scored fully, large sites get the most important pages
- Page selection heuristic: homepage always included, remaining pages selected by internal link count (most linked = most important)
- Be transparent in the UI about which pages were scored and which were discovered but not scored

### Score aggregation
- Weakest link model: the lowest-scoring page pulls the overall Optimization Score down disproportionately
- This encourages fixing the worst pages first, which aligns with the research (one bad page can tank AI perception of the whole site)

### Grading strictness
- Strict/realistic scoring — most sites should score 30-60, only well-optimized sites hit 80+
- Shows the real gap between current state and AI-optimized state, motivating action

### Scoring mode per criterion
- Mixed: binary (0 or 100) for truly yes/no criteria (SSL exists, robots.txt allows GPTBot, etc.)
- Gradient (0-100) for spectrum criteria (content length, readability, schema completeness, heading quality, etc.)
- Each criterion type (binary vs gradient) determined by the nature of what's being measured

### Criterion feedback tone
- Friendly summary by default ("AI crawlers can't read your site — you're blocking GPTBot in robots.txt")
- Expandable technical details ("GPTBot: BLOCKED via robots.txt line 12. Disallow: /")
- Each criterion result includes both a human-readable explanation and the raw evidence

### Backlink data
- Use free alternatives for backlink criteria (S9, S10) — do NOT require paid APIs (Ahrefs, Moz)
- Researcher should investigate: Common Crawl index, OpenLinkProfiler, Bing Webmaster API, or other free backlink data sources
- If no viable free source exists, use proxy signals (internal link quality, social profiles, external link patterns)

### Missing data handling
- All 53 criteria should be scorable — use free APIs where external data is needed:
  - Core Web Vitals: Google PageSpeed Insights API (free)
  - Knowledge Graph: Google Knowledge Graph Search API (free)
  - Wikipedia/Wikidata: Wikimedia APIs (free)
- If a criterion truly can't be checked, exclude from score calculation and show "Not checked" (don't score as 0)

### Claude's Discretion
- Exact weakest-link formula (how much the lowest page drags down the average)
- Binary vs gradient classification for each of the 53 criteria
- Internal link count heuristic for page importance ranking
- Which free backlink data source to use (based on research findings)
- Score display visualization (gauges, bars, colors) — whatever works best for the data
- Loading/progress UX during scoring stage
- Error handling for external API failures (PageSpeed, Knowledge Graph, etc.)

</decisions>

<specifics>
## Specific Ideas

- User wants full transparency: show which pages were scored, which were discovered but not scored, and why
- User envisions future premium tier where customers pay to score more than 25 pages — not in Phase 6 scope but influences architecture (make the cap configurable)
- User wants customers to eventually be able to choose which pages to score from discovered routes — future feature, but score storage should be per-page to support this
- "We should be able to score everything" — user expects all 53 criteria to be functional, not stubs

</specifics>

<deferred>
## Deferred Ideas

- Premium tier with higher/unlimited page cap — future monetization phase
- Page selection UI (let users pick which discovered routes to score) — future UX enhancement
- Benchmarked scoring with percentiles ("better than 60% of sites") — requires audit history data (Phase 9)
- Full backlink integration via paid API (Ahrefs/Moz) — when there's revenue to justify the cost

</deferred>

---

*Phase: 06-site-ai-readiness-scoring*
*Context gathered: 2026-02-22*
