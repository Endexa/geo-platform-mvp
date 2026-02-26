# Phase 7: Dashboard + Frontend Polish - Research

**Researched:** 2026-02-26
**Domain:** Frontend dashboard, data visualization, responsive UI, multi-site management
**Confidence:** HIGH

## Summary

Phase 7 is primarily a **frontend-heavy phase** that builds on substantial existing infrastructure. The backend already has working dashboard endpoints (`/dashboard/overview/{id}`, `/dashboard/history`), a complete brand CRUD API with multi-brand overview, and all the data models needed. The frontend has existing components for the dashboard (`DashboardHero`, `TrendChart`, `DeltaBadge`, `CategoryBreakdown`, `CompetitorRadar`), audit results (`AuditResults`, `OptimizationScore`, `CriterionDrilldown`), and brand management (`BrandCard`, `BrandComparison`). The charting stack (Chart.js v4 + vue-chartjs v5 + chartjs-adapter-date-fns) is already installed and functioning.

The work breaks into three domains: (1) **Dashboard data quality** -- ensuring the dashboard displays real data from completed audits, not mock numbers; the backend already supports this, the frontend already fetches real data, but needs verification and gap-filling. (2) **Multi-site management (DASH-05)** -- the Brand model exists with CRUD, overview endpoints, and brand-audit linking already built. The dashboard needs a brand selector and per-brand views. (3) **Frontend polish (UI-01 through UI-04)** -- applying the design system consistently (Fira Code/Fira Sans fonts, #1E40AF primary, Data-Dense Dashboard style), adding proper loading/error/empty states to all pages, and making the layout responsive for tablet.

**Primary recommendation:** Focus on wiring existing components together, applying the design system uniformly, and adding the responsive sidebar collapse for tablet. Do NOT rebuild components that already work -- enhance them.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | Real metrics dashboard showing audit history with actual data | Backend `DashboardService.get_overview()` and `get_audit_history()` already return real data. Frontend `dashboard.vue` fetches and displays it. Need to verify end-to-end with real audit data, ensure no mock/placeholder values remain. |
| DASH-02 | Score trend charts showing how scores evolve across audits over time | `TrendChart.vue` already implements this with overview/categories/engines tabs using Chart.js time scale. Backend `get_audit_history()` returns all completed audits with category averages. Need discrete data points annotation per Pitfall 13. |
| DASH-03 | Per-engine AI visibility breakdown (ChatGPT, Claude, Perplexity, Gemini) | Dashboard already shows per-engine horizontal bars. `AuditResults.vue` shows per-engine cards with confidence badges. TrendChart has "AI Engines" tab. All backed by real `VisibilityScore.per_engine_scores`. |
| DASH-04 | Per-category breakdown (Crawlability, Content, Schema, Authority) | `CategoryBreakdown.vue` exists and displays category scores with progress bars. TrendChart has "Categories" tab. `DashboardService._compute_category_averages()` provides the data. |
| DASH-05 | Multi-site management: agencies can manage multiple client sites from one account | `Brand` model exists with `user_id` FK. `BrandService` has full CRUD + overview. `brands.vue` page exists with create/edit/delete. Need brand-level dashboard view and brand selector in main dashboard. |
| UI-01 | Production-ready UI following design system (Data-Dense Dashboard style) | Design system defined in `MASTER.md`: Fira Code/Fira Sans fonts, #1E40AF/#3B82F6/#F59E0B colors, 4.5:1 contrast, no emojis, cursor-pointer on clickables. Tailwind config has primary/success/warning/danger palettes. Fonts NOT yet imported in nuxt.config or CSS. |
| UI-02 | Audit results page shows dual scores, category breakdowns, and recommendations | `AuditResults.vue` already shows dual scores via `OptimizationScore`, per-engine breakdown, summary stats, `CategoryBreakdown`, `CriterionDrilldown`, and queries. `audit.vue` shows competitor preview and recommendation preview. |
| UI-03 | Responsive layout works on desktop and tablet | Current sidebar layout is fixed at `w-64` with `ml-64` on content. No responsive breakpoint for tablet. Need collapsible sidebar at `lg:` breakpoint and hamburger toggle for tablet. |
| UI-04 | Loading states, error states, and empty states handled throughout | Dashboard has loading skeleton and empty state. Most pages have partial handling. Need systematic audit of ALL pages for consistent loading/error/empty patterns. |
</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| Chart.js | ^4.4.1 | Canvas-based charts | Installed, working |
| vue-chartjs | ^5.3.0 | Vue 3 wrapper for Chart.js | Installed, working |
| chartjs-adapter-date-fns | ^3.0.0 | Time scale for Chart.js | Installed, working |
| date-fns | ^4.1.0 | Date formatting | Installed |
| @heroicons/vue | ^2.0.18 | Icon library | Installed, used throughout |
| @headlessui/vue | ^1.7.16 | Accessible UI primitives | Installed |
| @vueuse/core | ^10.7.0 | Vue composables (useIntervalFn, etc.) | Installed, used |
| Tailwind CSS | ^3.4.0 | Utility-first styling | Installed, configured |
| lucide-vue-next | ^0.294.0 | Additional icons | Installed |

### Supporting (Nothing New Needed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pinia | ^2.1.7 | State management | Installed but not heavily used; consider for multi-brand state |
| vue-router | ^4.2.5 | Routing | Installed via Nuxt auto-routing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Chart.js | Apache ECharts | ECharts has more chart types but adds 1MB+ bundle; Chart.js is already working |
| Headless UI | Nuxt UI | Nuxt UI has dashboard-specific components but adds a full component library dependency; too late to switch |
| Custom sidebar collapse | VueUse useBreakpoints | VueUse is already installed; use `useMediaQuery` for responsive sidebar logic |

**Installation:** No new packages needed for Phase 7. Everything is already installed.

## Architecture Patterns

### Existing Project Structure (Relevant Files)
```
frontend/
  pages/
    dashboard.vue        # Main dashboard (DASH-01 through DASH-04)
    audit.vue            # Audit page with results (UI-02)
    brands.vue           # Multi-brand management (DASH-05)
    competitors.vue      # Competitor analysis page
    recommendations.vue  # Recommendations list
    pricing.vue          # Pricing/subscription page
  components/
    DashboardHero.vue    # Score hero with 3 score circles + deltas
    TrendChart.vue       # Line chart with overview/categories/engines tabs
    DeltaBadge.vue       # +/- score change badge
    CategoryBreakdown.vue # 4-category score display with clickable drilldown
    CompetitorRadar.vue  # Radar chart for competitive position
    AuditResults.vue     # Full audit results display
    OptimizationScore.vue # Dual-score display component
    CriterionDrilldown.vue # Per-criterion detail view
    ChatPanel.vue        # Chat assistant (Teleport to body)
    ExportActions.vue    # PDF/HTML/CSV export buttons
  layouts/
    dashboard.vue        # Sidebar + top bar + main content area
  composables/
    useApiFetch.ts       # Authenticated API fetching
    useAuth.ts           # Auth state management
    useChat.ts           # Chat panel logic
    useReports.ts        # Report download logic
    useStripe.ts         # Stripe checkout
    useSubscription.ts   # Tier checking
  middleware/
    auth.ts              # Route guard for authentication
  assets/css/
    main.css             # Tailwind imports + component classes + skeleton animation
```

### Backend Endpoints (Already Built)
```
GET  /api/v1/dashboard/overview/{audit_id}  -> DashboardOverviewResponse
GET  /api/v1/dashboard/history?domain=X     -> AuditHistoryResponse
GET  /api/v1/dashboard/{id}/export/pdf      -> PDF file download
GET  /api/v1/dashboard/{id}/export/csv      -> CSV file download
GET  /api/v1/brands/overview                -> MultiBrandOverviewResponse
POST /api/v1/brands/                        -> Create brand
GET  /api/v1/brands/{id}/audits             -> Paginated brand audit list
GET  /api/v1/audit                          -> User's audit list
GET  /api/v1/audit/{id}                     -> Full audit detail
```

### Pattern 1: Responsive Sidebar with Tailwind + VueUse
**What:** Collapsible sidebar that shows full on desktop (>=1024px), collapses to icon-only on tablet (768-1023px), and becomes an overlay drawer on mobile (<768px).
**When to use:** Dashboard layout (`layouts/dashboard.vue`).
**Example:**
```vue
<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'

const isDesktop = useMediaQuery('(min-width: 1024px)')
const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)')
const sidebarOpen = ref(true)

// Auto-collapse on tablet, auto-expand on desktop
watch(isDesktop, (desktop) => {
  sidebarOpen.value = desktop
})
</script>

<template>
  <!-- Sidebar -->
  <aside
    class="fixed inset-y-0 left-0 bg-white border-r border-gray-200 flex flex-col transition-all duration-200 z-30"
    :class="sidebarOpen ? 'w-64' : 'w-0 -translate-x-full lg:w-16 lg:translate-x-0'"
  >
    <!-- Navigation items show icon only when collapsed -->
  </aside>

  <!-- Mobile overlay -->
  <div
    v-if="!isDesktop && sidebarOpen"
    class="fixed inset-0 bg-black/50 z-20"
    @click="sidebarOpen = false"
  />

  <!-- Main content adjusts margin -->
  <div :class="sidebarOpen && isDesktop ? 'ml-64' : 'ml-0 lg:ml-16'">
    <!-- Top bar with hamburger toggle -->
  </div>
</template>
```

### Pattern 2: Consistent State Handling (Loading/Error/Empty)
**What:** Every data-fetching page follows the same three-state pattern.
**When to use:** All pages that fetch data from the API.
**Example:**
```vue
<template>
  <!-- Loading skeleton -->
  <div v-if="loading" class="animate-pulse">
    <!-- Skeleton matching the final layout structure -->
  </div>

  <!-- Error state -->
  <div v-else-if="error" class="bg-white rounded-xl border border-gray-200 p-12 text-center">
    <ExclamationTriangleIcon class="w-16 h-16 mx-auto text-amber-400" />
    <h2 class="text-lg font-semibold text-gray-700 mt-4">Something went wrong</h2>
    <p class="text-gray-500 mt-2 mb-6">{{ error }}</p>
    <button @click="retry" class="btn-primary cursor-pointer">Try Again</button>
  </div>

  <!-- Empty state -->
  <div v-else-if="isEmpty" class="bg-white rounded-xl border border-gray-200 p-12 text-center">
    <RelevantIcon class="w-16 h-16 mx-auto text-gray-300" />
    <h2 class="text-lg font-semibold text-gray-700 mt-4">{{ emptyTitle }}</h2>
    <p class="text-gray-500 mt-2 mb-6">{{ emptyMessage }}</p>
    <NuxtLink to="/action" class="btn-primary cursor-pointer">{{ emptyAction }}</NuxtLink>
  </div>

  <!-- Data state -->
  <template v-else>
    <!-- Actual content -->
  </template>
</template>
```

### Pattern 3: Brand-Level Dashboard Navigation
**What:** A brand selector in the dashboard that switches context between sites.
**When to use:** Dashboard page when user has multiple brands.
**Example:**
```vue
<!-- Brand selector in top bar or as sub-nav -->
<div v-if="brands.length > 1" class="flex items-center gap-2 border-b border-gray-200 pb-4 mb-4">
  <button
    v-for="brand in brands"
    :key="brand.brand_id"
    class="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors duration-200 cursor-pointer"
    :class="selectedBrand?.brand_id === brand.brand_id
      ? 'bg-[#1E40AF] text-white'
      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
    @click="selectBrand(brand)"
  >
    {{ brand.brand_name }}
  </button>
  <button class="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 cursor-pointer">
    All Sites
  </button>
</div>
```

### Anti-Patterns to Avoid
- **Hardcoding mock data in templates:** Every number displayed must come from the API response. No `42` or `69` literals.
- **Connected line charts for sparse data:** Per Pitfall 13, use discrete point markers with connecting lines only when audits are frequent. Annotate methodology changes.
- **Fixed sidebar without responsive breakpoint:** The current `w-64 ml-64` pattern breaks on tablet. Must add collapse behavior.
- **Inconsistent color usage:** Some components use `#1E40AF` directly, others use `text-primary-600`. Standardize on Tailwind config colors.
- **Missing cursor-pointer on clickable elements:** Design system anti-pattern. Audit all components.
- **z-index chaos:** Use Tailwind's z-10/z-20/z-30/z-50 scale. ChatPanel already uses Teleport to avoid stacking context issues.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Responsive detection | Custom window.resize listeners | `@vueuse/core` useMediaQuery | Already installed; handles cleanup, SSR safety |
| Chart rendering | Custom SVG/Canvas charts | vue-chartjs + Chart.js | Already installed and working; just configure |
| Skeleton loading | Custom CSS animation | Tailwind `animate-pulse` | Already used in dashboard.vue; consistent |
| Icon system | SVG files or emoji | @heroicons/vue + lucide-vue-next | Already installed; consistent sizing |
| Date formatting | Custom date logic | date-fns | Already installed; locale-aware |
| Accessible dropdowns/modals | Custom implementations | @headlessui/vue | Already installed; handles focus trap, escape key |

**Key insight:** Phase 7 requires zero new dependencies. Everything needed is already in package.json. The work is wiring, polishing, and systematizing.

## Common Pitfalls

### Pitfall 1: Dashboard Showing Stale or Misleading Trends (from PITFALLS.md #13)
**What goes wrong:** Trend charts imply continuous improvement between point-in-time audit snapshots. If scoring methodology changes between audits, old scores are not comparable to new scores on the same axis.
**Why it happens:** Line charts with `tension: 0.3` smooth between points, implying interpolation.
**How to avoid:**
- Display audit results as discrete data points (dots with `pointRadius: 5`) connected by thin lines
- Store scoring version with each audit (already have `algorithm_version` on VisibilityScore)
- If scoring version changes, add an annotation line on the chart: "Scoring v2 started here"
- Show "Last audited: [date]" prominently, not just in the chart tooltip
**Warning signs:** Score jumps of 20+ points between audits with no site changes (may be methodology change, not real improvement)

### Pitfall 2: Multi-Site Management Scaling
**What goes wrong:** Agency users with 50+ brands experience slow dashboard load because each brand triggers N+1 queries.
**Why it happens:** The existing `BrandService.get_multi_brand_overview()` already addresses this with a single aggregated query, but the dashboard overview endpoint fetches per-audit. If a user has many brands, switching between them can feel slow.
**How to avoid:**
- Use the existing `/brands/overview` endpoint which returns lightweight metrics
- Lazy-load detailed dashboard data only when a brand is selected
- Cache the brand list in Pinia store to avoid re-fetching on navigation
**Warning signs:** Dashboard page load time exceeding 2 seconds for users with 10+ brands

### Pitfall 3: Inconsistent Design System Application
**What goes wrong:** Some pages follow the design system, others use ad-hoc colors/fonts. The result feels like a patchwork rather than a cohesive product.
**Why it happens:** Components were built across multiple phases by different contexts. No design system audit has been done.
**How to avoid:**
- Add Fira Code and Fira Sans fonts to nuxt.config.ts head section (currently missing)
- Audit every page against the MASTER.md checklist: cursor-pointer, focus-visible:ring-2, 4.5:1 contrast, transitions 150-300ms
- Replace all inline hex colors (#1E40AF) with Tailwind config references (text-primary-800, bg-primary-800)
- Ensure all score displays use Fira Code (mono) and all body text uses Fira Sans
**Warning signs:** Visual inconsistency when navigating between pages (different blue shades, different card styles)

### Pitfall 4: Missing Error States on API Failures
**What goes wrong:** User sees a blank page or broken layout when an API call fails. Several pages only handle the happy path.
**Why it happens:** Error handling was added to some pages but not all during previous phases.
**How to avoid:**
- Audit every `useApiFetch` call for try/catch with user-visible error state
- Add a global error boundary pattern (or at minimum, per-page error ref + display)
- Network errors should show a retry button, not just a console.error
**Warning signs:** Console.error calls without corresponding UI feedback

### Pitfall 5: Chart.js Canvas Resizing Issues
**What goes wrong:** Charts don't resize correctly when sidebar collapses/expands, or overflow their container on tablet.
**Why it happens:** Chart.js v4 has known issues with responsive resizing when the container dimensions change after initial render. The `responsive` option relies on ResizeObserver which may not trigger on parent layout changes.
**How to avoid:**
- Set `responsive: true` and `maintainAspectRatio: false` (already done in TrendChart)
- When sidebar collapse changes layout, trigger chart resize with `nextTick` + chart instance `.resize()`
- Wrap charts in a container with explicit height (`h-64`, `h-72`) to prevent collapse
- Use `:key` prop on chart components to force re-render on significant layout changes (TrendChart already does this with `activeTab`)
**Warning signs:** Charts overlapping their containers, or shrinking to 0 height

## Code Examples

### Design System Font Integration (Currently Missing)
```typescript
// nuxt.config.ts -- add to app.head.link
link: [
  { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
  {
    rel: 'preconnect',
    href: 'https://fonts.googleapis.com'
  },
  {
    rel: 'preconnect',
    href: 'https://fonts.gstatic.com',
    crossorigin: ''
  },
  {
    rel: 'stylesheet',
    href: 'https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap'
  },
]
```

```javascript
// tailwind.config.js -- add fontFamily
theme: {
  extend: {
    fontFamily: {
      mono: ['"Fira Code"', 'monospace'],
      sans: ['"Fira Sans"', 'sans-serif'],
    },
    // ... existing colors
  },
},
```

### Skeleton Loading Pattern for Cards
```vue
<!-- Consistent skeleton for score cards -->
<div class="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
  <div class="h-4 bg-gray-200 rounded w-1/3 mb-4" />
  <div class="flex items-center justify-center">
    <div class="w-20 h-20 rounded-full bg-gray-200" />
  </div>
  <div class="h-3 bg-gray-200 rounded w-1/2 mx-auto mt-4" />
</div>
```

### Empty State Pattern
```vue
<!-- Reusable empty state -->
<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
  <component :is="icon" class="w-16 h-16 mx-auto text-gray-300" />
  <h2 class="text-lg font-semibold text-gray-700 mt-4">{{ title }}</h2>
  <p class="text-gray-500 mt-2 mb-6">{{ message }}</p>
  <NuxtLink
    v-if="actionPath"
    :to="actionPath"
    class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
  >
    {{ actionLabel }}
  </NuxtLink>
</div>
```

### Chart.js Time Scale Configuration (Already Working)
```typescript
// Source: frontend/components/TrendChart.vue -- verified working
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      type: 'time' as const,
      time: {
        unit: 'day' as const,
        displayFormats: { day: 'MMM d' },
      },
    },
    y: {
      min: 0,
      max: 100,
    },
  },
  plugins: {
    tooltip: {
      mode: 'index' as const,
      intersect: false,
    },
  },
}
```

### Brand Selector Composable Pattern
```typescript
// composables/useBrandSelector.ts
export function useBrandSelector() {
  const selectedBrandId = useState<string | null>('selectedBrandId', () => null)
  const brands = useState<BrandOverview[]>('brands', () => [])

  async function loadBrands() {
    const data = await useApiFetch<{ brands: BrandOverview[]; total_brands: number }>('/brands/overview')
    brands.value = data.brands
    if (!selectedBrandId.value && data.brands.length > 0) {
      selectedBrandId.value = data.brands[0].brand_id
    }
  }

  const selectedBrand = computed(() =>
    brands.value.find(b => b.brand_id === selectedBrandId.value)
  )

  return { selectedBrandId, brands, selectedBrand, loadBrands }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed sidebar always visible | Responsive sidebar with collapse | Tailwind v3+ | Required for tablet support |
| Placeholder/mock chart data | Real data from backend APIs | Phase 1-6 | Dashboard now backed by real audit data |
| Single audit view only | Multi-brand overview with brand switching | Phase 7 (this phase) | Agencies can manage multiple client sites |
| Inline hex colors | Tailwind config color tokens | Should be standardized this phase | Consistent theming, easier to change |
| System fonts | Fira Code + Fira Sans (design system) | Should be applied this phase | Professional, data-focused aesthetic |

**Deprecated/outdated:**
- `analyze.vue` page: Legacy analysis flow (URL + keywords). Should be kept but deprioritized in navigation in favor of `/audit` page.
- `brand-voice.vue` page: Brand Signature deferred to v3. Should remain in navigation but can be marked "Coming Soon."
- `optimization.vue` page: Placeholder page that appears to be unused. Can be removed from navigation.

## Gap Analysis: What Exists vs What's Needed

### DASH-01 (Real metrics dashboard)
- **Exists:** `dashboard.vue` fetches real data from `/dashboard/overview/{id}` and `/dashboard/history`. Displays DashboardHero, TrendChart, CompetitorRadar, Recommendation Progress.
- **Gap:** Dashboard is audit-centric (select an audit). Need a site-centric view (all audits for a domain). The audit selector dropdown already exists. Main gap is ensuring every displayed number traces to a real database value. Need to verify DashboardService populates all fields correctly.
- **Effort:** LOW -- verification + minor fixes

### DASH-02 (Score trend charts)
- **Exists:** `TrendChart.vue` with overview/categories/engines tabs using Chart.js time scale. Backend returns audit history with category averages and per-engine scores.
- **Gap:** Need to verify chart renders correctly with real multi-audit data. Add discrete point markers. Consider annotation for methodology version changes.
- **Effort:** LOW -- configuration tweaks

### DASH-03 (Per-engine AI visibility)
- **Exists:** Dashboard shows horizontal progress bars per engine. AuditResults shows per-engine cards with confidence badges. TrendChart has engines tab.
- **Gap:** Verify engine names display correctly (map openai->ChatGPT, etc.). Ensure "Not configured" state shows for engines without API keys.
- **Effort:** LOW -- already implemented

### DASH-04 (Per-category breakdown)
- **Exists:** `CategoryBreakdown.vue` shows 4 categories with scores, progress bars, and clickable drilldown to criterion level.
- **Gap:** Add to dashboard page (currently only on audit results page). Dashboard shows it as competitive position via radar chart but not as standalone category breakdown.
- **Effort:** LOW -- add CategoryBreakdown to dashboard

### DASH-05 (Multi-site management)
- **Exists:** Brand CRUD (create/edit/delete), BrandCard with overview metrics, BrandComparison for 2+ brands, backend `/brands/overview` endpoint.
- **Gap:** Dashboard lacks brand context switching. Need brand selector in dashboard header. Need per-brand dashboard view (filter audit list + history by brand domain). Need visual flow: Brands page -> click brand -> see brand's dashboard.
- **Effort:** MEDIUM -- composable + UI wiring

### UI-01 (Design system)
- **Exists:** Tailwind config has primary/success/warning/danger color scales. main.css has component classes. MASTER.md defines the design system.
- **Gap:** Fonts NOT imported (Fira Code/Fira Sans not in nuxt.config). Some components use inline hex instead of Tailwind classes. No font-family applied to headings or body. Missing `cursor-pointer` on some clickable elements.
- **Effort:** MEDIUM -- systematic audit + font import + class standardization

### UI-02 (Audit results page)
- **Exists:** Comprehensive audit results page with dual scores, per-engine cards, summary stats, category breakdown, criterion drilldown, competitor preview, recommendation preview, source citations, query editor, export actions, chat panel.
- **Gap:** Verify all sections render correctly with real data. Polish visual consistency with design system.
- **Effort:** LOW -- the page is already very complete

### UI-03 (Responsive layout)
- **Exists:** Fixed w-64 sidebar with ml-64 content. No responsive behavior.
- **Gap:** Sidebar must collapse on tablet (<1024px). Need hamburger toggle. Content area must expand when sidebar collapses. Charts must resize. Grid layouts must adapt.
- **Effort:** MEDIUM -- layout refactor in dashboard.vue layout

### UI-04 (Loading/error/empty states)
- **Exists:** Dashboard has loading skeleton and empty state. Brands page has loading skeleton and empty state. Some pages have error handling.
- **Gap:** Need systematic audit of all pages. Missing error states on several pages. Missing empty states on competitors.vue and recommendations.vue. Missing retry buttons on errors.
- **Effort:** MEDIUM -- systematic audit + additions per page

## Backend Readiness Assessment

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/dashboard/overview/{id}` | COMPLETE | Returns all fields needed for DashboardHero, top issues, competitive position, recommendation progress |
| `/dashboard/history?domain=X` | COMPLETE | Returns time-series with category averages and per-engine scores |
| `/dashboard/{id}/export/pdf` | COMPLETE | WeasyPrint rendering with Jinja2 template |
| `/dashboard/{id}/export/csv` | COMPLETE | Full CSV with scores, recommendations, competitors |
| `/brands/overview` | COMPLETE | Multi-brand metrics in single response |
| `/brands/{id}/audits` | COMPLETE | Paginated audit list per brand |
| `/audit` | COMPLETE | List user's audits with status filter |
| `/audit/{id}` | COMPLETE | Full audit detail with all relationships |
| `/recommendations/{audit_id}` | COMPLETE | Priority-ordered with progress tracking |
| `/competitors/{id}/leaderboard` | COMPLETE | SOV ranking with competitor audit summaries |
| **Per-brand dashboard** | NEEDED | No endpoint to get dashboard overview filtered by brand_id. Currently overview is per-audit, not per-brand. |

**Backend gap:** A `/dashboard/brand/{brand_id}` endpoint that returns the latest audit overview + audit history for a specific brand would simplify the frontend. Alternatively, the frontend can: (1) get brand detail to know the domain, (2) filter the audit list by domain, (3) pass the latest audit to `/dashboard/overview/{id}`. This 3-step approach works with existing endpoints but is chattier.

**Recommendation:** Add a convenience endpoint OR use existing endpoints with frontend composition. Given the backend is already mature, frontend composition (3 calls) is acceptable for v2. A dedicated endpoint can be added later if performance requires it.

## Migration Status

Latest Alembic migration: `014_add_chat_sessions.py`
Next migration number: `015`

**Migrations needed for Phase 7:** Likely NONE. All needed models (Brand, Audit, VisibilityScore, PageScore, AuditRecommendation, DiscoveredCompetitor, CompetitorAudit) already exist with the required columns. Multi-site management is handled by the existing Brand model with `user_id` FK and domain-based audit association.

## Open Questions

1. **Brand-level dashboard endpoint**
   - What we know: Frontend can compose existing endpoints to build a per-brand view
   - What's unclear: Whether a dedicated backend endpoint is needed for performance
   - Recommendation: Start with frontend composition; add endpoint only if load times exceed 1.5s

2. **Navigation cleanup**
   - What we know: Navigation has 8 items (Dashboard, Analyze, AI Audit, Competitors, Brands, Recommendations, Brand Voice, Settings). Some are legacy.
   - What's unclear: Which items should remain, be renamed, or be removed
   - Recommendation: Keep Analyze as secondary (legacy); keep Brand Voice with "Coming Soon" badge; remove optimization.vue (unused placeholder). Rename "AI Audit" to just "Audit" or "New Audit" for clarity.

3. **Design system font loading strategy**
   - What we know: Google Fonts URL for Fira Code + Fira Sans is specified in MASTER.md
   - What's unclear: Whether to use Google Fonts CDN or self-host
   - Recommendation: Google Fonts CDN via nuxt.config head link tags (simplest, CDN-cached globally). Self-hosting adds complexity without meaningful benefit for v2.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `frontend/pages/dashboard.vue`, `frontend/components/TrendChart.vue`, `frontend/components/DashboardHero.vue` -- direct code reading
- Existing codebase: `backend/app/services/dashboard_service.py`, `backend/app/api/dashboard.py` -- direct code reading
- Existing codebase: `backend/app/api/brands.py`, `backend/app/services/brand_service.py` -- direct code reading
- Existing codebase: `frontend/layouts/dashboard.vue`, `frontend/tailwind.config.js`, `frontend/nuxt.config.ts` -- direct code reading
- Design system: `design-system/endexa-geo-platform/MASTER.md` -- project-specific design system
- Project research: `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md` -- prior research documents

### Secondary (MEDIUM confidence)
- [vue-chartjs documentation](https://vue-chartjs.org/guide/) -- Chart.js integration patterns
- [Flowbite Tailwind sidebar](https://flowbite.com/docs/components/sidebar/) -- Responsive sidebar patterns
- [Carbon Design System loading patterns](https://carbondesignsystem.com/patterns/loading-pattern/) -- Skeleton loading best practices
- [Eleken empty state UX](https://www.eleken.co/blog-posts/empty-state-ux) -- Empty state design patterns
- [LogRocket skeleton design](https://blog.logrocket.com/ux-design/skeleton-loading-screen-design/) -- Skeleton loading screen design
- [Nuxt UI dashboard sidebar](https://ui.nuxt.com/docs/components/dashboard-sidebar) -- Reference patterns (not using Nuxt UI, but patterns are informative)

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and verified working
- Architecture: HIGH -- existing components and endpoints thoroughly examined
- Pitfalls: HIGH -- grounded in project-specific PITFALLS.md and codebase analysis
- Multi-site management: HIGH -- Brand model, service, and API already built
- Responsive layout: MEDIUM -- patterns are well-established but implementation requires careful testing across breakpoints
- Design system application: MEDIUM -- design system is defined but has never been systematically applied; gap audit needed

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable -- all technologies are mature)
