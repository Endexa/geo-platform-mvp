---
phase: 09-stripe-pricing-fix
plan: "06"
subsystem: frontend
tags: [design-system, branding, ux, tailwind, nuxt]
dependency_graph:
  requires: [09-04, 09-05]
  provides: [consistent-slate-design-system, endexa-branding, page-titles]
  affects: [dashboard-layout, all-app-pages]
tech_stack:
  added: []
  patterns: [slate-* color tokens, useHead page titles]
key_files:
  created: []
  modified:
    - frontend/layouts/dashboard.vue
    - frontend/pages/dashboard.vue
    - frontend/pages/audit.vue
    - frontend/pages/competitors.vue
    - frontend/pages/recommendations.vue
    - frontend/pages/analyze.vue
    - frontend/pages/brands.vue
    - frontend/nuxt.config.ts
decisions:
  - "slate-* replaces gray-* across all 7 target files — zero raw gray tokens remain in class attributes"
  - "Endexa sidebar logo uses font-mono + text-primary-800 to match the data-dense dashboard style"
  - "useHead titles use em dash (—) as separator per Endexa format"
metrics:
  duration: ~15 minutes
  completed: "2026-02-26"
  tasks_completed: 1
  files_modified: 8
---

# Phase 09 Plan 06: Design System Token Sweep + Endexa Branding + Page Titles Summary

Design system coherence pass — replaced all raw gray-* Tailwind class tokens with slate-* equivalents across the entire dashboard layout and 6 app pages, rebranded sidebar from 'GEO Platform' to 'Endexa' with font-mono styling, and added useHead() page titles to all app pages.

## What Was Built

### Token Replacement (7 files, 0 gray tokens remaining)

Replaced all `gray-*` Tailwind class tokens with `slate-*` equivalents in:
- `frontend/layouts/dashboard.vue` — sidebar background, borders, nav inactive state, breadcrumbs, user menu
- `frontend/pages/dashboard.vue` — headers, skeletons, empty states, score cards, progress bars, engine breakdown
- `frontend/pages/audit.vue` — headers, competitor preview, recommendation preview, error states
- `frontend/pages/competitors.vue` — headers, loading skeletons, empty states, crawl trigger panel
- `frontend/pages/recommendations.vue` — headers, loading skeletons, empty states, tabs, filter dropdowns, page group buttons
- `frontend/pages/analyze.vue` — headers, form labels, progress stepper, error states
- `frontend/pages/brands.vue` — headers, form inputs/textareas, loading skeletons, empty states

**Exception respected:** CSS variables and `<style>` blocks were not touched. Only class attribute tokens were replaced.

### Endexa Branding (dashboard.vue layout)

Before:
```html
<h1 class="text-2xl font-bold text-primary-600">GEO Platform</h1>
<p class="text-sm text-gray-500">Optimization Suite</p>
```

After:
```html
<h1 class="text-2xl font-bold font-mono text-primary-800">Endexa</h1>
<p class="text-sm text-slate-500">GEO Optimization Suite</p>
```

### Page Titles (useHead added to 6 pages)

| Page | Title |
|------|-------|
| dashboard.vue | Dashboard — Endexa |
| audit.vue | New Audit — Endexa |
| competitors.vue | Competitors — Endexa |
| recommendations.vue | Recommendations — Endexa |
| analyze.vue | Code Analysis — Endexa |
| brands.vue | Brands — Endexa |

### nuxt.config.ts App Head

```typescript
title: 'Endexa — AI Search Optimization Platform',
meta: [{ name: 'description', content: 'Endexa analyzes 61 criteria across crawlability, content structure, schema, and authority to optimize your presence in AI search engines.' }]
```

## Verification Results

All plan verification checks passed:

```
frontend/layouts/dashboard.vue: 0 gray tokens remaining
frontend/pages/dashboard.vue:   0 gray tokens remaining
frontend/pages/recommendations.vue: 0 gray tokens remaining

Endexa in sidebar: OK
Old branding removed: OK
useHead in dashboard: OK
useHead in audit: OK
```

Frontend build: clean — 1325 modules transformed, 0 errors.

## Commits

- `bcefa669` — Replace gray-* tokens with slate-*, update Endexa branding, add page titles

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- All 7 target files have 0 remaining gray-* class tokens
- Sidebar shows 'Endexa' with font-mono and text-primary-800
- All 6 app pages have useHead() with '— Endexa' title format
- nuxt.config.ts title and description both reference Endexa
- `npm run build` passes cleanly (commit bcefa669)
