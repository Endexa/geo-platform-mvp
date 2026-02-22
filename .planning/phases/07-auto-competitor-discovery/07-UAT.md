---
status: complete
phase: 07-auto-competitor-discovery
source: 07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md
started: 2026-02-22T22:00:00Z
updated: 2026-02-22T22:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Sidebar Competitors Navigation
expected: Dashboard sidebar shows a "Competitors" navigation item with an icon, positioned after "AI Audit". Clicking it navigates to the competitors page.
result: pass

### 2. Audit Pipeline Includes Competitor Discovery Stage
expected: When running a full audit, the status progresses through DISCOVERING_COMPETITORS before reaching COMPLETED. The audit finishes successfully with competitors extracted.
result: pass

### 3. Competitor Leaderboard Preview on Audit Page
expected: After audit completion, the audit detail page shows a top-5 competitor preview section with brand names, SOV percentages, and a "View All Competitors" link.
result: pass

### 4. Source Citations Display on Audit Page
expected: Audit page shows a Source Citations section with per-engine URL groupings (ChatGPT, Claude, Perplexity, Gemini). Each citation is a clickable URL with domain extraction.
result: pass

### 5. Full Competitors Page
expected: Navigating to /competitors shows a full leaderboard table with competitor names, SOV percentage bars, engine badges (color-coded), and crawl status badges (Scored/Pending/No URL). Your brand is highlighted.
result: pass

### 6. Competitor Score Comparison
expected: On the competitors page, selecting a competitor shows side-by-side category scores (Crawlability, Content Structure, Structured Data, Authority) with directional arrows and color coding. Score gaps summary is sorted by largest deficit first.
result: pass

### 7. Score Competitors Crawl Trigger
expected: Clicking "Score Competitors" button triggers competitor crawling with a loading spinner. After completion, leaderboard updates with scored competitors showing per-category averages.
result: pass

### 8. Add Custom Query
expected: On the audit page, a QueryEditor section allows adding a custom query by typing text and selecting a category. Custom queries appear with amber background and dashed border, sorted above auto-generated queries.
result: pass

### 9. Edit Custom Query
expected: Clicking edit on a custom query enables inline editing of text and category. Saving updates the query. Auto-generated queries cannot be edited.
result: pass

### 10. Delete Custom Query
expected: Clicking delete on a custom query shows a confirmation dialog. Confirming removes it. Dispatched queries (with engine responses) cannot be deleted (shows 409 error).
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
