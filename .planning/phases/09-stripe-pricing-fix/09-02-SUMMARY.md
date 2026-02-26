---
phase: 09-stripe-pricing-fix
plan: 02
subsystem: ui
tags: [nuxt, vue, stripe, pricing, tailwind]

# Dependency graph
requires:
  - phase: 04-payments-freemium-gating
    provides: "useStripe composable and stripePriceProMonthly runtime config key"
provides:
  - "3-tier pricing page (Free / Pro / Enterprise) with no yearly toggle"
  - "handleSubscribe reads price ID from config.public.stripePriceProMonthly"
  - "Enterprise contact-us mailto link to hello@endexa.com"
affects: [09-stripe-pricing-fix, landing-page, frontend-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useRuntimeConfig() for Stripe price IDs — never hardcode Stripe IDs in source"
    - "definePageMeta({ layout: 'dashboard' }) on in-app pages"

key-files:
  created: []
  modified:
    - frontend/pages/pricing.vue

key-decisions:
  - "Monthly-only pricing: yearly toggle removed entirely — requirements explicitly forbid it"
  - "Enterprise tier CTA is mailto:hello@endexa.com — no Stripe session, custom deal flow"
  - "Pro card badge changed from 'Recommended' to 'Most Popular' per spec"
  - "Free CTA is NuxtLink to /audit (not a disabled button) — reduces friction for free users"
  - "Added definePageMeta dashboard layout — pricing page is in-app, not a landing page"

patterns-established:
  - "Pricing page pattern: 3-column md:grid-cols-3 with relative Pro card for badge positioning"
  - "Stripe price ID pattern: always read from config.public.stripePriceProMonthly, never hardcode"

requirements-completed: [LAND-02, LAND-03]

# Metrics
duration: 4min
completed: 2026-02-26
---

# Phase 9 Plan 02: Pricing Page Rewrite Summary

**3-tier pricing page (Free / Pro $29/mo / Enterprise) with yearly toggle removed, price ID from runtime config, and Enterprise mailto contact tier**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-02-26T00:00:00Z
- **Completed:** 2026-02-26T00:04:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Rewrote pricing.vue from 2-tier + yearly toggle to clean 3-tier monthly-only layout
- Fixed hardcoded `'price_pro_monthly'` string — Pro CTA now reads from `config.public.stripePriceProMonthly`
- Added Enterprise tier with custom pricing copy and `mailto:hello@endexa.com` contact CTA
- Pro card has `border-2 border-primary-800`, `shadow-lg`, and "Most Popular" badge
- Free tier CTA is a NuxtLink to `/audit` rather than a disabled button
- Added `definePageMeta({ layout: 'dashboard' })` — pricing page is an in-app page

## Task Commits

1. **Task 1: Rewrite pricing.vue — 3 tiers, no toggle, env-var price ID** - `9bf62e88` (feat)

## Files Created/Modified

- `frontend/pages/pricing.vue` — Full rewrite: 3-tier grid, no yearly toggle, env-var price ID, Enterprise mailto tier

## Decisions Made

- Monthly-only pricing: requirements explicitly forbid a yearly toggle — removed entirely.
- Enterprise tier uses mailto contact flow rather than Stripe — enterprise deals need human touch.
- Pro badge text changed from "Recommended" to "Most Popular" to match spec exactly.
- Free CTA upgraded from disabled "Current Plan" button to active NuxtLink — reduces friction for free-tier users.
- Added `definePageMeta({ layout: 'dashboard' })` since this page is accessed inside the app, not from the landing page.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The `NUXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY` env var was already wired in nuxt.config.ts from Phase 4.

## Next Phase Readiness

- Pricing page is production-ready as soon as `NUXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY` is set to a real Stripe price ID
- Enterprise tier contact link is immediately functional
- Remaining Phase 9 plans can proceed (landing page, Stripe webhook hardening, etc.)

---
*Phase: 09-stripe-pricing-fix*
*Completed: 2026-02-26*
