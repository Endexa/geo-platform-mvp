---
phase: 09-stripe-pricing-fix
plan: 04
subsystem: frontend-subscription
tags: [nuxt, vue, stripe, subscription, composable, settings]

# Dependency graph
requires:
  - phase: 09-stripe-pricing-fix plan: 01
    provides: GET /payments/subscription-status endpoint

provides:
  - fetchTierOnMount() method in useSubscription composable
  - Subscription tier rehydration on every dashboard mount
  - Manage Subscription button in settings.vue for Pro users
  - slate-* design token consistency in settings.vue

affects: [frontend/composables/useSubscription.ts, frontend/layouts/dashboard.vue, frontend/pages/settings.vue]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subscription rehydration pattern: fetchTierOnMount() called in dashboard onMounted, silently fails to free tier on error"
    - "Portal button pattern: portalLoading ref disables button and shows 'Opening portal...' during redirect"
    - "Gray-to-slate migration: settings.vue now uses slate-* tokens uniformly"

key-files:
  created: []
  modified:
    - frontend/composables/useSubscription.ts
    - frontend/layouts/dashboard.vue
    - frontend/pages/settings.vue

key-decisions:
  - "fetchTierOnMount() silently fails (catch swallows error) so a network glitch doesn't break dashboard load — user defaults to Free UI"
  - "portalLoading never resets to false on success because redirectToPortal() navigates away — only reset on error"
  - "v-if/v-else on isProUser for the button vs NuxtLink — mutual exclusion guaranteed by Vue conditional directives"
  - "gray-* to slate-* migration scoped to settings.vue only (out-of-scope files untouched per deviation rules)"

# Metrics
duration: 8min
completed: 2026-02-26
---

# Phase 09-stripe-pricing-fix Plan 04: Subscription Rehydration + Settings Portal Button Summary

**Subscription tier rehydration via fetchTierOnMount() on dashboard mount, and conditional Manage Subscription / Upgrade to Pro buttons in settings.vue**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-02-26
- **Completed:** 2026-02-26
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

### Task 1: fetchTierOnMount + dashboard wiring

- Added `fetchTierOnMount()` async method to `useSubscription.ts` that calls `GET /payments/subscription-status` via `useApiFetch`, sets `tier.value` on success, and silently fails on error (defaulting to 'free')
- Updated return statement to export `fetchTierOnMount` alongside existing exports
- Updated `dashboard.vue` to destructure `fetchTierOnMount` from `useSubscription()` and call `await fetchTierOnMount()` at the end of `onMounted`, after auth check and `fetchUser()` — ensuring every dashboard page load rehydrates tier from the DB

### Task 2: Settings portal button + design token cleanup

- Updated Subscription card in `settings.vue` to conditionally render:
  - **Pro users:** `<button>` with `@click="handlePortal"`, `:disabled="portalLoading"`, and `{{ portalLoading ? 'Opening portal...' : 'Manage Subscription' }}`
  - **Free users:** `<NuxtLink to="/pricing">` — same "Upgrade to Pro" as before
- Replaced hardcoded "3 analyses remaining this month" with contextual per-tier status lines: "Full access to all features" (Pro) / "Crawlability analysis + top 3 recommendations" (Free)
- Added `const { redirectToPortal } = useStripe()`, `const portalLoading = ref(false)`, and `handlePortal()` async function to `<script setup>`
- Migrated all `gray-*` Tailwind tokens to `slate-*` throughout `settings.vue` — 9 instances replaced across labels, inputs, backgrounds, badges, and headings

## Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | fetchTierOnMount in useSubscription + dashboard.vue wiring | `75b6a96f` |
| 2 | Manage Subscription button + slate-* migration in settings.vue | `bf8ff65a` |

## Files Created/Modified

- `frontend/composables/useSubscription.ts` — Added `fetchTierOnMount()` method, updated return statement
- `frontend/layouts/dashboard.vue` — Added `fetchTierOnMount` to destructuring, added `await fetchTierOnMount()` in `onMounted`
- `frontend/pages/settings.vue` — Conditional Pro/Free buttons in Subscription card, handlePortal(), portalLoading, slate-* token migration

## Decisions Made

- `fetchTierOnMount()` uses a silent catch with no error display — a subscription status fetch failure is non-fatal and should not disrupt dashboard load; user simply sees Free UI until next successful load
- `portalLoading` is only reset to `false` in the catch block — on success, `redirectToPortal()` navigates the browser away, so the component unmounts and resetting the ref is unnecessary
- Mutual exclusion of the Pro/Free UI elements achieved with `v-if="isProUser"` / `v-else` directly on the button and NuxtLink

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

- [x] `frontend/composables/useSubscription.ts` — modified, contains `fetchTierOnMount` and `subscription-status`
- [x] `frontend/layouts/dashboard.vue` — modified, contains `fetchTierOnMount` call in `onMounted`
- [x] `frontend/pages/settings.vue` — modified, contains `Manage Subscription`, `handlePortal`, `redirectToPortal`, no `gray-*` tokens
- [x] Commit `75b6a96f` — Task 1
- [x] Commit `bf8ff65a` — Task 2

## Self-Check: PASSED

---
*Phase: 09-stripe-pricing-fix*
*Completed: 2026-02-26*
