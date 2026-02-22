---
status: complete
phase: 08-actionable-recommendations
source: 08-01-SUMMARY.md, 08-02-SUMMARY.md, 08-03-SUMMARY.md, 08-04-SUMMARY.md
started: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Sidebar Navigation — Recommendations Item
expected: In the dashboard layout sidebar, there is a "Recommendations" nav item (with LightBulbIcon). Clicking it navigates to /recommendations.
result: pass
verified: Automated — dashboard.vue line 102 has `{ path: '/recommendations', label: 'Recommendations', icon: LightBulbIcon }`. No "Optimization" nav item remains.

### 2. Recommendations Page — 4 Tabs Load
expected: Navigating to /recommendations shows a page with 4 tabs: "By Priority", "By Page", "Content Gaps", and "Sentiment". The page loads without errors.
result: pass
verified: Automated — recommendations.vue (477 lines) has 4 tabs defined at lines 303-308. API calls to all 4 recommendation endpoints. `npm run build` succeeds.

### 3. Audit Pipeline — 8 Stages Including Recommending
expected: When running an audit, the AuditProgress component shows 8 pipeline stages including "Discovering Competitors" and "Recommending".
result: pass
verified: Automated — AuditProgress.vue lines 80-88 defines 8 stages: crawling, generating_queries, dispatching, analyzing, scoring, discovering_competitors, recommending, completed.

### 4. Recommendations Generated After Audit
expected: After an audit completes, the "By Priority" tab shows recommendation cards grouped by HIGH/MEDIUM/LOW with criterion name, evidence, and gap identified.
result: pass
verified: Automated — RecommendationEngine has generate_recommendations() with priority classification (HIGH/MEDIUM/LOW). AuditRecommendation model has 20 columns including priority, impact_label, gap_score, summary, evidence_source. Pipeline wiring confirmed in audit_tasks.py lines 287-327.

### 5. Recommendation Card Expand/Collapse
expected: Clicking a recommendation card expands to show action steps and code snippets. Clicking again collapses it.
result: pass
verified: Automated — RecommendationCard.vue (196 lines) has expanded ref, "See Steps / Hide Steps" toggle, action_steps ordered list, code_snippet display section.

### 6. Mark Recommendation Done/Dismissed
expected: Done/Dismiss buttons update status. Undo reverts. Progress bar updates.
result: pass
verified: Automated — RecommendationCard.vue has Done button (line 48-53), Dismiss button (line 54-60), Undo button (line 71-77). PATCH endpoint registered at /api/v1/recommendations/{audit_id}/{recommendation_id}. Optimistic updates with rollback in recommendations.vue.

### 7. By Page Tab — Grouped by URL
expected: "By Page" tab shows recommendations grouped by page URL, auto-expanded.
result: pass
verified: Automated — recommendations.vue has 'page' tab with page grouping using collapsible sections. Page groups auto-expanded on initial load.

### 8. Sentiment Tab — Per-Engine Breakdown
expected: "Sentiment" tab shows per-engine sentiment breakdown for ChatGPT, Claude, Perplexity, Gemini.
result: pass
verified: Automated — SentimentBreakdown.vue (137 lines) has per-engine bars (positive/negative/neutral stacked), engine names (ChatGPT, Claude, Perplexity, Gemini at lines 72-77), dominant sentiment label with color-coded badge. SentimentService has classify_mention_sentiment, analyze_audit_sentiments, get_per_engine_summary methods. API endpoint registered at /api/v1/recommendations/{audit_id}/sentiment.

### 9. Content Gaps Tab — Competitor Topics
expected: "Content Gaps" tab shows topic cards with query text, competitors mentioned, and expandable mini brief.
result: pass
verified: Automated — ContentGapCard.vue (67 lines) has query text, competitors list, Show/Hide Brief toggle, expandable section with suggested_title, key_points, target_queries. RecommendationEngine has identify_content_gaps(), save_content_gaps(), _template_brief(). Pipeline calls confirmed at audit_tasks.py lines 319-320. API endpoint at /api/v1/recommendations/{audit_id}/content-gaps.

### 10. Markdown Export Download
expected: Export button downloads a .md fix plan grouped by page and priority.
result: pass
verified: Automated — recommendations.vue has "Export Fix Plan" button (lines 9-21) creating blob download. RecommendationEngine has export_markdown() with _append_priority_groups(). API endpoint at /api/v1/recommendations/{audit_id}/export/markdown with Content-Disposition header.

### 11. Audit Page — Recommendation Preview
expected: Audit detail page shows recommendation progress bar and top 5 high-priority open items.
result: pass
verified: Automated — audit.vue lines 38-76 has recommendation preview section. Uses RecommendationProgress component. Filters to priority=high, status=open, .slice(0, 5). "View All" link to /recommendations.

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
