# Phase 8: Actionable Recommendations - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate page-specific, evidence-based fix recommendations by comparing user site scores against competitor scores and research-backed best practices. Each recommendation shows the gap, the evidence, and the estimated impact. Includes sentiment analysis of AI mentions and content gap identification with briefs. Dashboard and PDF export belong in Phase 9.

</domain>

<decisions>
## Implementation Decisions

### Recommendation detail level
- Two tiers: **actionable guidance** as default view + **step-by-step with code snippets** expandable per recommendation
- Example default: "Add FAQPage schema to your pricing page — competitors have it, 3.2x citation rate (BrightEdge)"
- Example expanded: Full JSON-LD code snippet, placement instructions, validation steps
- Data structure must be export-friendly for Phase 9 PDF/CSV consumption

### Recommendation tracking
- Recommendations have a **done/dismissed state** with progress tracking
- Progress bar: "12/28 recommendations addressed"
- State persists across re-audits — when a recommendation is re-generated, previous done/dismissed status carries over if the recommendation matches

### Exportable fix plans
- Recommendations exportable as **machine-readable plan files** (Markdown format) that users can feed directly into a Claude Code / AI coding session to auto-fix their site
- Two export scopes available: **per-page** plan file and **combined full-site** plan file
- Format inspired by GSD PLAN.md structure — clear tasks, file paths, code changes, acceptance criteria

### Negative sentiment handling
- Negative AI mentions get **flagged with exact quote + a specific recommendation** to address the issue
- Example: "ChatGPT says 'Stripe's pricing is confusing' — improve pricing page clarity with comparison table and FAQ"

### Sentiment per engine
- Sentiment breakdown shown **per-engine**: "ChatGPT: mostly positive, Perplexity: mixed, Claude: not mentioned"
- Users can see which engines have issues and prioritize fixes per engine

### Content gap presentation
- Content gaps displayed as **topic cards** — visual and scannable
- Each card: topic name, which competitors get mentioned, user's coverage status, action needed
- Each gap includes a **mini content brief**: suggested title, 3-5 key points to cover, target keywords from AI queries

### Claude's Discretion
- Recommendation organization (priority-first, page-first, or category-first — or combination with tabs/filters)
- Navigation pattern between scoring page and recommendations (inline links, separate page, or both)
- Evidence display format (inline stats vs expandable detail)
- Competitor URL linking in content gap cards (show competitor pages or not)
- Sentiment classification granularity (3-way vs 5-level)
- Sentiment implementation method (LLM-based vs rule-based vs hybrid)
- Content brief generation method (LLM-generated vs template-based)
- Content recommendation depth (topic + rationale vs full content brief — user prefers briefs when possible)

</decisions>

<specifics>
## Specific Ideas

- "You might add a plan.md or md file that the user can directly give to their Claude session so it fixes it for him" — exportable fix plans inspired by GSD repo format
- Recommendations should be structured so an AI coding assistant can consume them as actionable instructions
- Both per-page and full-site export options for maximum flexibility
- Progress tracking persists across audits so users can see their improvement journey

</specifics>

<deferred>
## Deferred Ideas

- PDF/CSV export of recommendations — Phase 9 (Dashboard & Reporting)
- Recommendation trend tracking over time (how recommendations change between audits) — Phase 9

</deferred>

---

*Phase: 08-actionable-recommendations*
*Context gathered: 2026-02-22*
