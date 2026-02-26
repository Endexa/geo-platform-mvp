---
phase: 09-stripe-pricing-fix
plan: 03
subsystem: ui
tags: [nuxt, vue, tailwind, heroicons, landing-page, marketing, layout, intersectionobserver]

requires:
  - phase: 07-dashboard-frontend-polish
    provides: dashboard layout and useAuth composable pattern

provides:
  - Landing layout (layouts/landing.vue) — sticky navbar with no sidebar for marketing pages
  - useScrollFadeIn composable — IntersectionObserver-based scroll animations without animation libraries
  - LandingHero section — headline, CTAs, stats bar
  - LandingFeatures section — 6-card bento grid with Heroicons
  - LandingHowItWorks section — 3 numbered steps with desktop connecting lines
  - index.vue replaced — marketing landing page using 'landing' layout, redirects logged-in users to /dashboard

affects: [09-04, 09-05, landing-page-completion]

tech-stack:
  added: []
  patterns:
    - useScrollFadeIn composable pattern — IntersectionObserver at 0.1 threshold, fires once and unobserves
    - transition-all duration-300 with opacity-0/100 + translate-y-0/6 for scroll entrance animations
    - Landing layout isolation — marketing pages use layouts/landing.vue (no sidebar), dashboard pages keep layouts/dashboard.vue
    - Heroicons from @heroicons/vue/24/outline used as dynamic :is components in feature cards

key-files:
  created:
    - frontend/layouts/landing.vue
    - frontend/composables/useScrollFadeIn.ts
    - frontend/components/landing/LandingHero.vue
    - frontend/components/landing/LandingFeatures.vue
    - frontend/components/landing/LandingHowItWorks.vue
  modified:
    - frontend/pages/index.vue

key-decisions:
  - "Footer in landing.vue is inline placeholder — plan 05 creates LandingFooter component"
  - "duration-300 used for all animations (max per CLAUDE.md anti-patterns rule)"
  - "useScrollFadeIn fires once then unobserves to avoid re-triggering on scroll up"
  - "Connecting lines in HowItWorks use absolute positioning within relative step containers — spans left-[calc(50%+24px)] to right-[-50%]"

patterns-established:
  - "Landing components live in frontend/components/landing/ subdirectory"
  - "Each landing section uses useScrollFadeIn for entrance — import and destructure { el, visible }"
  - "Amber (#F59E0B / bg-amber-500) is the CTA color throughout landing; primary-800 for brand/text accents"

requirements-completed: [LAND-01, LAND-07]

duration: 8min
completed: 2026-02-26
---

# Phase 9 Plan 03: Landing Layout + Hero, Features, How It Works Summary

**Landing layout isolation with sticky glass navbar, IntersectionObserver scroll animations, and three marketing sections (Hero, Features, HowItWorks) replacing the old dashboard stub on index.vue**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-26T00:00:00Z
- **Completed:** 2026-02-26T00:08:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created `layouts/landing.vue` — standalone marketing layout with sticky glass navbar (backdrop-blur-sm, bg-white/90), logo, nav links (Features, Pricing, FAQ), Sign In / Get Started Free CTAs — no sidebar
- Created `useScrollFadeIn.ts` composable — IntersectionObserver at 0.1 threshold, fires once per element then unobserves; uses duration-300 CSS transitions only
- Replaced `index.vue` — now uses `layout: 'landing'`, redirects logged-in users to `/dashboard`, sets SEO head meta
- Created `LandingHero.vue` — dot-grid background, headline with amber underline accent on "visible to AI?", two CTAs (amber button + text link), stats bar (61 criteria / 4 categories / 4 AI engines)
- Created `LandingFeatures.vue` — 6-card bento grid with Heroicons (ShieldCheckIcon, DocumentTextIcon, CodeBracketIcon, StarIcon, EyeIcon, LightBulbIcon), hover:border-primary-200 + hover:shadow-md transitions
- Created `LandingHowItWorks.vue` — 3 numbered steps in primary-800 circles with desktop connecting lines via absolute positioning, trailing amber CTA

## Task Commits

1. **Task 1: Create landing layout and useScrollFadeIn composable** - `f5c6bba7` (feat)
2. **Task 2: Replace index.vue and build Hero, Features, HowItWorks sections** - `d400ec68` (feat)

## Files Created/Modified

- `frontend/layouts/landing.vue` — Marketing layout, sticky glass navbar, slot, inline footer placeholder
- `frontend/composables/useScrollFadeIn.ts` — IntersectionObserver composable for scroll fade animations
- `frontend/pages/index.vue` — Landing page root (replaced dashboard stub), landing layout, auth redirect
- `frontend/components/landing/LandingHero.vue` — Hero section with headline, CTAs, stats bar
- `frontend/components/landing/LandingFeatures.vue` — 6-card bento grid with Heroicons and descriptions
- `frontend/components/landing/LandingHowItWorks.vue` — 3-step process section with connecting lines and CTA

## Decisions Made

- Footer in `landing.vue` is a minimal inline placeholder (`<footer>` with copyright text) — the full `LandingFooter` component is created in plan 05
- All animations use `duration-300` (300ms) per CLAUDE.md anti-pattern rule: "No `duration-1000` transitions — cap at 300ms"
- `useScrollFadeIn` unobserves after first intersection to avoid re-triggering on scroll back up
- Connecting lines in `LandingHowItWorks` use `left-[calc(50%+24px)] right-[-50%]` to span from step center to next step

## Deviations from Plan

None — plan executed exactly as written. Build passes with `npm run build`.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Landing layout and three sections are complete
- Plan 04 can add Testimonials, Pricing, FAQ, and Trust sections using the same component pattern
- Plan 05 will create the full LandingFooter component to replace the inline footer placeholder
- All section components follow established pattern: `useScrollFadeIn` + `duration-300` transitions + `components/landing/` directory

---
*Phase: 09-stripe-pricing-fix*
*Completed: 2026-02-26*
