---
phase: 09-stripe-pricing-fix
plan: 05
subsystem: ui
tags: [nuxt, vue, tailwind, heroicons, landing-page, marketing, pricing, faq, testimonials, trust, footer]

requires:
  - phase: 09-stripe-pricing-fix
    plan: 03
    provides: landing layout, useScrollFadeIn, LandingHero, LandingFeatures, LandingHowItWorks

provides:
  - LandingTestimonials — 3 testimonial cards with initials avatars
  - LandingFAQ — 7-question accordion with openIndex state (no library)
  - LandingTrust — 4-section security credibility grid with CheckCircleIcon checklists
  - LandingFooter — dark bg-slate-900 5-column footer with brand, product, features, company, legal
  - LandingPricing — 3-tier pricing section using runtime-config price ID + useStripe checkout
  - index.vue — all 8 landing sections wired in sequence
  - landing.vue — real LandingFooter replaces inline placeholder footer

affects: [LAND-01, LAND-02, LAND-07, landing-page-completion]

tech-stack:
  added: []
  patterns:
    - FAQ accordion with openIndex ref — v-show + ChevronDownIcon rotate on expand (no library)
    - Trust section dynamic :is component for icons within a sections array
    - LandingPricing reads config.public.stripePriceProMonthly from useRuntimeConfig (never hardcoded)
    - Footer as layout component — Nuxt 3 auto-imports LandingFooter from components/landing/ directory

key-files:
  created:
    - frontend/components/landing/LandingTestimonials.vue
    - frontend/components/landing/LandingFAQ.vue
    - frontend/components/landing/LandingTrust.vue
    - frontend/components/landing/LandingFooter.vue
    - frontend/components/landing/LandingPricing.vue
  modified:
    - frontend/pages/index.vue
    - frontend/layouts/landing.vue

key-decisions:
  - "LandingFooter placed in layouts/landing.vue (not index.vue) so it appears on all landing-layout pages"
  - "Footer has Company + Legal merged into one column to keep the 5-column grid with col-span-2 brand on md"
  - "LandingPricing uses CheckIcon + XMarkIcon from heroicons (consistent with codebase) not unicode checkmarks"
  - "duration-300 maintained throughout — all transitions cap at 300ms per CLAUDE.md anti-patterns rule"

metrics:
  duration: 10min
  tasks: 2
  files: 7
  completed: 2026-02-26
---

# Phase 9 Plan 05: Remaining Landing Sections + Footer Summary

**Complete landing page: 5 new components (Testimonials, Pricing, FAQ, Trust, Footer), all 8 sections wired into index.vue, real footer component replaces inline placeholder in landing layout**

## Performance

- **Duration:** 10 min
- **Completed:** 2026-02-26
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

- Created `LandingTestimonials.vue` — 3 testimonial cards in a 3-column grid with initials-based avatar circles (amber/primary/slate color scheme), decorative quote mark, name and role display; uses useScrollFadeIn entrance
- Created `LandingFAQ.vue` — 7 FAQ questions using a pure Vue openIndex ref accordion; ChevronDownIcon rotates 180deg on open; v-show for smooth native show/hide; no animation library required
- Created `LandingTrust.vue` — Security credibility section with inline badge (ShieldCheckIcon + "Security & Trust"), 2x2 grid of trust cards using dynamic `:is` for icons (LockClosedIcon, ShieldCheckIcon, EyeSlashIcon, ServerIcon), CheckCircleIcon checklists per card; E-E-A-T signal for LAND-07
- Created `LandingFooter.vue` — Dark footer (bg-slate-900), 5-column grid with col-span-2 brand column, product/features/company+legal columns; bottom copyright bar with border-t border-slate-800
- Created `LandingPricing.vue` — Inline landing pricing section with same 3-tier layout as pricing.vue; reads `config.public.stripePriceProMonthly` from useRuntimeConfig; Pro tier uses `handleSubscribe` with loading/error state; Free uses NuxtLink, Enterprise uses mailto
- Updated `index.vue` — All 7 section components now present in correct order (Hero, Features, HowItWorks, Testimonials, Pricing, FAQ, Trust); LandingFooter lives in layout
- Updated `landing.vue` — Inline footer placeholder replaced with `<LandingFooter />` auto-imported component

## Task Commits

1. **Task 1: Build LandingTestimonials, LandingFAQ, LandingTrust, LandingFooter** - `9bad096e` (feat)
2. **Task 2: Build LandingPricing, update index.vue and landing.vue** - `b1ba88ad` (feat)

## Files Created/Modified

- `frontend/components/landing/LandingTestimonials.vue` — 73 lines, 3 testimonial cards
- `frontend/components/landing/LandingFAQ.vue` — 80 lines, 7 questions accordion
- `frontend/components/landing/LandingTrust.vue` — 100 lines, 4 security sections
- `frontend/components/landing/LandingFooter.vue` — 55 lines, 5-column dark footer
- `frontend/components/landing/LandingPricing.vue` — 164 lines, 3-tier pricing section
- `frontend/pages/index.vue` — updated to include all 7 section components
- `frontend/layouts/landing.vue` — LandingFooter replaces inline footer placeholder

## Decisions Made

- `LandingFooter` placed in `layouts/landing.vue` (not `index.vue`) so it's global to all landing-layout pages
- Company and Legal columns merged into a single 5th column to maintain the 5-column grid while keeping col-span-2 for the brand on md breakpoint
- `LandingPricing` uses `CheckIcon` and `XMarkIcon` from `@heroicons/vue/24/outline` for included/excluded features — consistent with codebase heroicons usage
- All transitions use `duration-300` — cap enforced per CLAUDE.md anti-pattern: "No `duration-1000` transitions"

## Deviations from Plan

None — plan executed exactly as written. All 5 verification checks pass.

## Self-Check

### Files exist

- `frontend/components/landing/LandingTestimonials.vue` — FOUND
- `frontend/components/landing/LandingFAQ.vue` — FOUND
- `frontend/components/landing/LandingTrust.vue` — FOUND
- `frontend/components/landing/LandingFooter.vue` — FOUND
- `frontend/components/landing/LandingPricing.vue` — FOUND
- `frontend/pages/index.vue` (modified) — FOUND
- `frontend/layouts/landing.vue` (modified) — FOUND

### Commits exist

- `9bad096e` — FOUND
- `b1ba88ad` — FOUND

## Self-Check: PASSED

---
*Phase: 09-stripe-pricing-fix*
*Completed: 2026-02-26*
