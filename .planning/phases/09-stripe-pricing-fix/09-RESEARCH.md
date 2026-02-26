# Phase 9: Landing Page + Frontend Overhaul + Stripe Production - Research

**Researched:** 2026-02-26
**Domain:** Marketing landing page (Nuxt 3 / Tailwind CSS), Stripe production wiring, design system coherence
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LAND-01 | Professional landing page with Hero, Features, How It Works, Pricing, FAQ, Security/Trust, Footer sections | Meridiane reference patterns identified; Nuxt layout separation pattern confirmed |
| LAND-02 | Pricing page with 3 tiers: Free, Pro $29/mo (Stripe checkout), Enterprise (contact form) — no yearly toggle | Current pricing.vue has yearly toggle — must be removed; 3-column grid pattern from reference project |
| LAND-03 | Stripe checkout works end-to-end — real price ID from env vars, webhook processes subscription | Backend fully built (stripe_service.py + payments.py); frontend wiring broken (hardcoded fallback price_id); env vars missing from .env.example |
| LAND-04 | Coherent UI/UX across all app pages — consistent design system (typography, colors, spacing, components) | Index.vue uses gray-900 text vs primary-800; design tokens mismatch between landing and app pages documented |
| LAND-05 | Paywall hardened — server-side gating, frontend upgrade prompts, subscription status rehydration on refresh | Backend require_tier() works; frontend useSubscription derives tier from audit response (weak); needs dedicated /payments/subscription-status endpoint |
| LAND-06 | Settings page has Manage Subscription button (Stripe Customer Portal) for Pro users | redirectToPortal() composable exists but settings.vue has no portal button for Pro users |
| LAND-07 | Landing page content establishes credibility — about, security, trust signals (E-E-A-T) | Trust page pattern from Meridiane reference; security section pattern with icon+checklist documented |
| LAND-08 | All .env.example files document Stripe vars, frontend builds clean | Backend .env.example missing STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_PRO_MONTHLY, STRIPE_PORTAL_CONFIG_ID; frontend .env.example missing Stripe vars entirely |
</phase_requirements>

---

## Summary

Phase 9 is the final phase — it transforms a feature-complete but marketing-incomplete product into something users can discover, evaluate, and purchase. The work splits into four distinct streams: (1) a new marketing landing page built as a Nuxt layout-isolated page, (2) hardening Stripe checkout to use real env-var price IDs, (3) adding subscription status rehydration and a Customer Portal button, and (4) unifying the design system across all app pages.

The backend is already production-ready for Stripe. `stripe_service.py` uses the StripeClient instance pattern (SDK v14+), `payments.py` has checkout sessions, Customer Portal, webhook handling with idempotency, and `dependencies.py` has server-side `require_tier()` gating on all pro endpoints. The only gap is the frontend: `pricing.vue` has a yearly toggle that must be removed and the price ID is hardcoded to `'price_pro_monthly'` instead of reading from `config.public.stripePriceProMonthly`. The `useSubscription` composable derives tier from audit response (fragile on page refresh) and needs a dedicated `/payments/subscription-status` endpoint to rehydrate on load. Settings page has no "Manage Subscription" button for Pro users despite `redirectToPortal()` existing.

The reference project `~/Informatique/Perso/quick-launch-page-craft` uses React with Framer Motion animations, which cannot be copied directly, but its visual patterns (asymmetric bento grids, eyebrow text, staggered fade-ins, dot-grid textures, avatar initials for testimonials, 5-column trust grid) are directly adaptable to Vue 3 + Tailwind CSS using simple CSS transitions. The Endexa design system is already well-defined: `#1E40AF` primary, `#F59E0B` CTA/amber, Fira Code headings + Fira Sans body. The inconsistency is that app pages use `text-gray-900` and `bg-gray-50` while the design system spec says `#F8FAFC` background and `#1E3A8A` text — a small but noticeable token drift.

**Primary recommendation:** Build the landing page as a new `layouts/landing.vue` (no sidebar/header) with `pages/landing.vue` pointing to it. Keep all sections in a single long-scroll page. Use Vue's built-in `Transition` + `IntersectionObserver` for fade-in animations (no Framer Motion). Fix the Stripe price ID wiring to read from `config.public.stripePriceProMonthly`. Add a `GET /payments/subscription-status` endpoint that returns tier, and call it from `useSubscription` on mount.

---

## Current State Audit (Critical Context)

### What Works

| Component | Status | Notes |
|-----------|--------|-------|
| `stripe_service.py` | Working | StripeClient instance pattern, async methods, checkout + portal + webhook verify |
| `payments.py` | Working | All 5 endpoints registered, webhook handles 5 event types, idempotency via WebhookEvent table |
| `dependencies.py` | Working | `require_tier()` factory used on all pro endpoints (recommendations, chat, reports, code_analysis) |
| `useStripe.ts` | Working | `redirectToCheckout(priceId)` and `redirectToPortal()` both implemented |
| `checkout/success.vue` | Working | Polls `session-status` for 5 attempts, sets tier on success |
| `checkout/cancel.vue` | Exists | |
| `stripe_service.py` portal | Working | `STRIPE_PORTAL_CONFIG_ID` optional, returns to `/settings` |

### What Is Broken / Missing

| Gap | Location | Fix Required |
|-----|----------|-------------|
| Yearly billing toggle | `pricing.vue` lines 12-41 | Requirements say "no yearly toggle" — remove it |
| Hardcoded price ID | `pricing.vue` line 187 | `'price_pro_monthly'` literal — must read from `config.public.stripePriceProMonthly` |
| Subscription rehydration | `useSubscription.ts` | Derives tier from `is_limited` in audit response only — not rehydrated on page refresh |
| Missing subscription endpoint | Backend | No `GET /payments/subscription-status` endpoint that returns current user's tier |
| No portal button in settings | `settings.vue` | Shows "Upgrade to Pro" for free users but no "Manage Subscription" for Pro users |
| Backend .env.example | `.env.example` | Missing `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PORTAL_CONFIG_ID`, `FRONTEND_URL` |
| Frontend .env.example | `frontend/.env.example` | Missing all Stripe vars: `NUXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`, `NUXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY` |
| Landing page | None exists | `index.vue` is currently a dashboard widget, not a marketing page |
| No marketing layout | `layouts/` | Only `layouts/dashboard.vue` exists; need `layouts/landing.vue` |
| Design token drift | All app pages | `text-gray-900` used instead of `text-primary-900`; `bg-gray-50` used instead of design system `#F8FAFC` |

---

## Standard Stack

### Core (already installed — no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Nuxt 3 | ^3.x | Framework | Already in use |
| Vue 3 | ^3.x | UI reactivity | Already in use |
| Tailwind CSS | ^3.x | Styling | Already in use |
| Heroicons Vue | ^2.x | Icons | Already in use |
| Lucide Vue | ^0.x | Icons | Already in use |
| Stripe SDK (Python) | ^14.x | Backend | Already in use (StripeClient pattern) |

### No New Frontend Dependencies Required

The landing page can be built entirely with:
- Native Vue `Transition` component for enter animations
- `IntersectionObserver` API (built-in browser) for scroll-triggered fade-ins
- Existing Tailwind classes for layout (no additional CSS frameworks)
- Existing Heroicons/Lucide for icons
- CSS `@keyframes` for marquee animation (already defined in `main.css` for shimmer)

Do NOT add Framer Motion, GSAP, AOS, or any animation library. The reference project uses Framer Motion (React), but the equivalent is simple CSS transitions + IntersectionObserver in Vue.

**Installation:**
```bash
# No new packages needed
```

---

## Architecture Patterns

### Recommended Project Structure Changes

```
frontend/
├── layouts/
│   ├── dashboard.vue     # EXISTS — keep as-is
│   └── landing.vue       # NEW — navbar + footer only, no sidebar
├── pages/
│   ├── index.vue         # REPLACE — becomes landing page (definePageMeta layout: 'landing')
│   ├── landing/          # Consider: or keep everything in index.vue
│   │   └── sections/     # Optional: split into sub-components if too long
│   ├── pricing.vue       # MODIFY — remove yearly toggle, fix price ID
│   ├── settings.vue      # MODIFY — add portal button for Pro users
│   └── dashboard.vue     # MODIFY — redirect / to /dashboard if logged in
├── components/
│   └── landing/          # NEW — landing-specific section components
│       ├── LandingHero.vue
│       ├── LandingFeatures.vue
│       ├── LandingHowItWorks.vue
│       ├── LandingPricing.vue
│       ├── LandingTestimonials.vue
│       ├── LandingFAQ.vue
│       ├── LandingTrust.vue
│       └── LandingFooter.vue
└── composables/
    └── useSubscription.ts  # MODIFY — add fetchTierOnMount()
```

### Pattern 1: Landing Page Layout Isolation

**What:** A separate `landing.vue` layout that has only a top navbar and footer — no sidebar, no auth guards.
**When to use:** Any public marketing page (landing, pricing, about).

```vue
<!-- layouts/landing.vue -->
<template>
  <div class="min-h-screen bg-white">
    <!-- Minimal top nav: logo + Sign In + Get Started -->
    <header class="sticky top-0 z-50 border-b border-slate-100 bg-white/90 backdrop-blur-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <NuxtLink to="/" class="font-mono text-xl font-bold text-primary-800">Endexa</NuxtLink>
        <nav class="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
          <a href="#features" class="hover:text-primary-800 transition-colors">Features</a>
          <a href="#pricing" class="hover:text-primary-800 transition-colors">Pricing</a>
          <a href="#faq" class="hover:text-primary-800 transition-colors">FAQ</a>
        </nav>
        <div class="flex items-center gap-3">
          <NuxtLink v-if="!isLoggedIn" to="/login" class="text-sm text-slate-600 hover:text-primary-800">Sign In</NuxtLink>
          <NuxtLink to="/audit" class="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold transition-colors cursor-pointer">
            Get Started Free
          </NuxtLink>
        </div>
      </div>
    </header>
    <slot />
    <!-- Footer component -->
    <LandingFooter />
  </div>
</template>
```

```vue
<!-- pages/index.vue - becomes the landing page -->
<script setup lang="ts">
definePageMeta({ layout: 'landing' })
// If user is logged in, redirect to dashboard
const { isLoggedIn } = useAuth()
onMounted(() => {
  if (isLoggedIn.value) navigateTo('/dashboard')
})
</script>
```

### Pattern 2: Landing Sections as Scroll Targets

**What:** Each section has an `id` attribute for anchor navigation. Sections fade in using IntersectionObserver.
**When to use:** All landing page sections.

```vue
<!-- composables/useScrollFadeIn.ts -->
export function useScrollFadeIn() {
  const el = ref<HTMLElement | null>(null)
  const visible = ref(false)

  onMounted(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) visible.value = true },
      { threshold: 0.1 }
    )
    if (el.value) observer.observe(el.value)
  })

  return { el, visible }
}
```

```vue
<!-- Usage in any section component -->
<div ref="el" :class="['transition-all duration-700', visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6']">
```

### Pattern 3: Subscription Status Rehydration

**What:** A dedicated backend endpoint returns the current user's tier. Frontend calls it on mount.
**When to use:** On every page load while logged in.

```python
# backend/app/api/payments.py — new endpoint
@router.get("/subscription-status")
async def subscription_status(
    current_user: Profile = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return current user's subscription tier for frontend rehydration."""
    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(["active", "trialing"]),
        )
        .first()
    )
    tier = "pro" if sub else "free"
    return {"tier": tier, "status": sub.status if sub else None}
```

```typescript
// composables/useSubscription.ts — enhanced
export const useSubscription = () => {
  const tier = useState<string>('subscription_tier', () => 'free')
  const isProUser = computed(() => tier.value === 'pro')

  const fetchTierOnMount = async () => {
    try {
      const data = await useApiFetch<{ tier: string }>('/payments/subscription-status')
      tier.value = data.tier
    } catch {
      // Silently fail — defaults to 'free'
    }
  }

  // ... existing methods
  return { tier, isProUser, updateTierFromAudit, setTier, fetchTierOnMount }
}
```

```typescript
// layouts/dashboard.vue — call on mount
const { fetchTierOnMount } = useSubscription()
onMounted(async () => {
  // ... existing auth check
  await fetchTierOnMount()
})
```

### Pattern 4: Stripe Price ID from Env Vars

**What:** Read price ID from runtime config, not hardcoded string.

```typescript
// pricing.vue — corrected handleSubscribe
const handleSubscribe = async () => {
  const priceId = config.public.stripePriceProMonthly
  if (!priceId) {
    error.value = 'Pricing not configured. Contact support@endexa.com'
    return
  }
  loading.value = true
  try {
    await redirectToCheckout(priceId)
  } catch (err: any) {
    error.value = err?.data?.detail || 'Failed to start checkout. Please try again.'
    loading.value = false
  }
}
```

### Pattern 5: Hero Section for GEO/SEO Tool

**What:** Clear problem/solution headline, URL input CTA, stats bar.
**Based on:** Reference project patterns + SaaS landing page research.

```
Structure:
- Eyebrow: "AI-powered GEO analysis" (all caps, tracked)
- H1: "Is your site visible to AI search?" (large, Fira Code, tracking-tight)
- Subheadline: "Endexa analyzes 61 criteria across crawlability, content structure, schema, and authority — then tells you exactly what to fix."
- Primary CTA: "Analyze my site" (amber button, large)
- Secondary CTA: "See a sample audit →" (link style)
- Stats bar: "61 criteria | 4 categories | Real measurements"
- Hero visual: score card mockup or dashboard screenshot
```

### Pattern 6: Pricing Section (3-Tier, No Yearly Toggle)

**What:** 3-column grid, Pro card highlighted with ring-2, no billing toggle.
**Requirements say:** No yearly toggle — monthly only at $29/mo.

```
Free:
  - $0/mo
  - Crawlability analysis (12 criteria)
  - Overall optimization score
  - Top 3 recommendations
  - CTA: "Get started free" → /audit (no checkout)

Pro: $29/mo [HIGHLIGHTED with ring + "Most Popular" badge]
  - All 4 categories (61 criteria)
  - Full recommendations + fix guides
  - Competitor benchmarking + SOV
  - AI visibility breakdown (ChatGPT, Claude, Perplexity, Gemini)
  - PDF/HTML reports + Jira CSV export
  - AI chat assistant
  - Code analysis prompts
  - CTA: "Subscribe to Pro" → Stripe checkout

Enterprise: Custom pricing
  - Everything in Pro
  - Multi-site management (unlimited brands)
  - Priority support
  - Custom integrations
  - CTA: "Contact us" → mailto or contact form modal
```

### Anti-Patterns to Avoid

- **Monthly/yearly toggle in pricing:** Requirements explicitly say no yearly toggle. Remove the existing one in pricing.vue.
- **Hardcoded price IDs in frontend:** Must use `config.public.stripePriceProMonthly` from runtime config.
- **Deriving tier only from audit response:** Breaks on page refresh. Need dedicated subscription-status endpoint.
- **Emoji in UI:** CLAUDE.md prohibits emoji — use Heroicons/Lucide SVG only.
- **z-[9999]:** Use defined z-index scale (z-10, z-20, z-30, z-50).
- **Animations over 300ms:** Cap at duration-300 per CLAUDE.md anti-patterns.
- **Landing page in dashboard layout:** Must use separate `landing` layout (no sidebar).
- **Stripe webhook endpoint without raw body:** Must use `await request.body()` (already correct in payments.py — do not change).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stripe Customer Portal | Custom subscription management UI | `redirectToPortal()` + Stripe hosted portal | Handles cancellation, plan changes, invoice history, payment method updates — massive scope |
| Payment form | Custom card input | Stripe Checkout (hosted) | PCI compliance, fraud detection, 3DS, ApplePay/GooglePay built-in |
| Subscription status webhook logic | Custom deduplication | Existing `WebhookEvent` table + upsert pattern | Already implemented and tested in payments.py |
| Scroll animations | JavaScript animation library | CSS transitions + IntersectionObserver | Zero bundle cost, sufficient for fade-in effects |
| FAQ accordion | Custom JS toggle | Nuxt's `<details>`/`<summary>` or simple `v-show` | No library needed for basic accordion |
| Trust/security content | Custom icons | Heroicons/Lucide Shield, Lock, CheckCircle | Already installed |

**Key insight:** The backend payment infrastructure is complete. The planner should focus on frontend wiring and new UI components, not backend changes (except the subscription-status endpoint).

---

## Common Pitfalls

### Pitfall 1: Landing Page Using Dashboard Layout

**What goes wrong:** The current `index.vue` uses `definePageMeta({ layout: 'dashboard' })` — this means users hit the sidebar when visiting the landing page.
**Why it happens:** The dashboard layout was set up first; no marketing page was planned.
**How to avoid:** Create `layouts/landing.vue` with no sidebar. The new `index.vue` should use `definePageMeta({ layout: 'landing' })`.
**Warning signs:** If `/` shows a sidebar to logged-out users, the layout is wrong.

### Pitfall 2: Stripe Price ID Not Configured Causes Silent Failure

**What goes wrong:** `pricing.vue` currently falls back to empty string `''` if no price ID is set, which fails at the Stripe API with an unclear error.
**Why it happens:** The config guard checks `stripePublishableKey` (not `stripePriceProMonthly`) to decide the price ID.
**How to avoid:** Read `config.public.stripePriceProMonthly` directly. Show a clear error message if empty.
**Warning signs:** Checkout button shows spinner then "Failed to start checkout" with no helpful context.

### Pitfall 3: Subscription Status Not Rehydrated on Refresh

**What goes wrong:** User subscribes, `setTier('pro')` is called on success page. On next page refresh, `useState` resets to 'free' (default). The Pro user sees Free UI.
**Why it happens:** `useState` is server-side rendered — it reinitializes on each full page load. The current `updateTierFromAudit()` only runs when an audit response arrives.
**How to avoid:** Add `fetchTierOnMount()` called from `layouts/dashboard.vue` `onMounted`. This calls `GET /payments/subscription-status` and sets the tier from the DB.
**Warning signs:** After subscribing, browser refresh shows "Upgrade to Pro" CTA again.

### Pitfall 4: Webhook Receives `request.body()` After Framework Parses It

**What goes wrong:** Stripe webhook signature verification requires the raw, un-parsed request body. If FastAPI reads the body as JSON before verification, the signature check fails.
**Why it happens:** Using `Body()` or Pydantic schema in the webhook handler causes FastAPI to parse and re-serialize the body, changing byte layout.
**How to avoid:** The existing `payments.py` already uses `payload = await request.body()` correctly. Do NOT change the webhook handler pattern.
**Warning signs:** `SignatureVerificationError` in logs even with correct webhook secret.

### Pitfall 5: Stripe Customer Portal Not Configured in Dashboard

**What goes wrong:** `redirectToPortal()` creates a portal session, but the portal shows nothing useful if not configured in Stripe Dashboard.
**Why it happens:** Portal configuration (what actions are allowed) must be done in Stripe Dashboard under "Customer portal" settings before it works.
**How to avoid:** Document in PLAN.md that the Stripe Dashboard portal configuration must be done manually before testing. The `STRIPE_PORTAL_CONFIG_ID` env var is optional but recommended to pin a specific configuration.
**Warning signs:** Portal page loads but shows empty or "no subscriptions found".

### Pitfall 6: Design System Token Inconsistency

**What goes wrong:** App pages use raw Tailwind colors (`text-gray-900`, `bg-gray-50`) while the design system spec defines `#1E3A8A` for text and `#F8FAFC` for background. These are actually the same or very close values, but a few places use `bg-white` vs design system `#F8FAFC`, creating a subtle difference.
**Why it happens:** Developers use Tailwind defaults without checking the design system.
**How to avoid:** The Tailwind config already has `primary` color scale correctly mapped. Replace `text-gray-900` with `text-slate-900` or `text-primary-900` (both are dark enough). Background should be `bg-slate-50` (= #F8FAFC close enough). The key is consistency, not perfection.
**Warning signs:** Dashboard cards look visually "off" compared to landing page sections.

### Pitfall 7: Missing `NUXT_PUBLIC_API_URL` vs `NUXT_PUBLIC_API_BASE` Mismatch

**What goes wrong:** `nuxt.config.ts` maps `NUXT_PUBLIC_API_URL` → `apiUrl`, but `useApiFetch.ts` uses `config.public.apiBase`. The `.env.example` documents `NUXT_PUBLIC_API_BASE`.
**Why it happens:** Both variable names exist; the config key changed at some point.
**How to avoid:** When updating `.env.example` for Stripe vars, verify the existing API URL var name is consistent throughout.

---

## Code Examples

### Landing Page Hero Section (Vue 3 + Tailwind)

```vue
<!-- components/landing/LandingHero.vue -->
<template>
  <section class="relative min-h-screen flex flex-col items-center justify-center overflow-hidden pt-24 pb-16 px-4">
    <!-- Subtle dot grid background -->
    <div
      aria-hidden="true"
      class="pointer-events-none absolute inset-0"
      style="background-image: radial-gradient(circle, rgba(30,64,175,0.04) 1px, transparent 1px); background-size: 24px 24px;"
    />

    <div class="relative z-10 max-w-4xl mx-auto text-center">
      <!-- Eyebrow -->
      <p class="text-xs uppercase tracking-[0.2em] font-semibold text-primary-600 mb-6">
        AI Search Optimization Platform
      </p>

      <!-- H1 -->
      <h1 class="font-mono font-bold tracking-tight leading-[1.05] text-slate-900
                 text-4xl sm:text-5xl md:text-6xl lg:text-7xl mb-6">
        Is your site
        <span class="relative inline-block text-primary-800">
          visible to AI?
          <span aria-hidden="true" class="absolute -bottom-1 left-0 right-0 h-1 rounded-full bg-amber-400/60" />
        </span>
      </h1>

      <!-- Subheadline -->
      <p class="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto mb-10">
        Endexa analyzes 61 criteria across crawlability, content structure, schema, and authority —
        then tells you exactly what to fix to get cited by ChatGPT, Claude, and Perplexity.
      </p>

      <!-- CTAs -->
      <div class="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
        <NuxtLink
          to="/audit"
          class="px-8 py-3 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2"
        >
          Analyze my site free
        </NuxtLink>
        <a
          href="#features"
          class="text-sm text-slate-600 hover:text-primary-800 transition-colors duration-150"
        >
          See what we measure &rarr;
        </a>
      </div>

      <!-- Stats bar -->
      <div class="flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-12 text-sm text-slate-500">
        <span><strong class="text-slate-900 font-mono">61</strong> criteria measured</span>
        <span class="hidden sm:inline text-slate-300">|</span>
        <span><strong class="text-slate-900 font-mono">4</strong> categories analyzed</span>
        <span class="hidden sm:inline text-slate-300">|</span>
        <span><strong class="text-slate-900 font-mono">4</strong> AI engines tracked</span>
      </div>
    </div>
  </section>
</template>
```

### Pricing Section (3-Tier, No Toggle)

```vue
<!-- Pricing card structure — Pro highlighted -->
<div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
  <!-- Free -->
  <div class="rounded-xl border border-slate-200 p-6 flex flex-col bg-white">
    <!-- ... -->
    <NuxtLink to="/audit" class="w-full py-3 text-center rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition-colors cursor-pointer">
      Get started free
    </NuxtLink>
  </div>

  <!-- Pro — highlighted -->
  <div class="relative rounded-xl border-2 border-primary-800 p-6 flex flex-col bg-white shadow-lg">
    <span class="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-primary-800 text-white text-xs font-semibold px-3 py-1 rounded-full">
      Most Popular
    </span>
    <!-- ... -->
    <button @click="handleCheckout" class="w-full py-3 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2">
      Subscribe to Pro — $29/mo
    </button>
  </div>

  <!-- Enterprise -->
  <div class="rounded-xl border border-slate-200 p-6 flex flex-col bg-white">
    <!-- ... -->
    <a href="mailto:hello@endexa.com" class="w-full py-3 text-center rounded-lg border border-primary-800 text-primary-800 text-sm font-medium hover:bg-primary-50 transition-colors cursor-pointer">
      Contact us
    </a>
  </div>
</div>
```

### Settings — Manage Subscription Button

```vue
<!-- settings.vue — Subscription section -->
<div class="card">
  <h2 class="text-xl font-bold text-slate-900 mb-4">Subscription</h2>
  <div class="flex items-center justify-between p-4 bg-gradient-to-r from-primary-50 to-primary-100 rounded-lg">
    <div>
      <p class="text-sm text-slate-600 mb-1">Current Plan</p>
      <p class="text-2xl font-bold font-mono text-primary-700">{{ isProUser ? 'Pro' : 'Free' }}</p>
    </div>
    <!-- Pro: Manage Subscription button -->
    <button
      v-if="isProUser"
      @click="handlePortal"
      :disabled="portalLoading"
      class="px-4 py-2 rounded-lg border border-primary-300 text-primary-800 text-sm font-medium hover:bg-primary-50 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
    >
      {{ portalLoading ? 'Opening...' : 'Manage Subscription' }}
    </button>
    <!-- Free: Upgrade link -->
    <NuxtLink v-else to="/pricing" class="btn-primary cursor-pointer">
      Upgrade to Pro
    </NuxtLink>
  </div>
</div>

<script setup lang="ts">
const { isProUser } = useSubscription()
const { redirectToPortal } = useStripe()
const portalLoading = ref(false)

const handlePortal = async () => {
  portalLoading.value = true
  try {
    await redirectToPortal()
  } catch {
    // Show error
    portalLoading.value = false
  }
}
</script>
```

### Backend: Subscription Status Endpoint

```python
# backend/app/api/payments.py — add this endpoint

class SubscriptionStatusResponse(BaseModel):
    tier: str
    status: Optional[str] = None

@router.get("/subscription-status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: Profile = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return current user's subscription tier for frontend rehydration on page load."""
    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(["active", "trialing"]),
        )
        .first()
    )
    return SubscriptionStatusResponse(
        tier="pro" if sub else "free",
        status=sub.status if sub else None,
    )
```

### Trust/Security Section Pattern

```vue
<!-- components/landing/LandingTrust.vue -->
<!-- Based on Meridiane reference project Trust.tsx -->
<template>
  <section id="security" class="py-20 bg-slate-50 border-t border-slate-200">
    <div class="max-w-4xl mx-auto px-4">
      <div class="text-center mb-12">
        <div class="inline-flex items-center gap-2 bg-primary-50 border border-primary-100 text-primary-700 px-4 py-1.5 rounded-full text-sm font-medium mb-6">
          <ShieldCheckIcon class="w-4 h-4" />
          Security & Trust
        </div>
        <h2 class="font-mono text-3xl font-bold text-slate-900 mb-3">Built for your data security</h2>
        <p class="text-slate-600 max-w-xl mx-auto">Your audit data and API keys are handled with enterprise-grade security practices.</p>
      </div>
      <div class="grid md:grid-cols-2 gap-4">
        <div v-for="section in trustSections" :key="section.title" class="bg-white border border-slate-200 rounded-xl p-6">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-9 h-9 bg-primary-50 rounded-lg flex items-center justify-center shrink-0">
              <component :is="section.icon" class="w-4 h-4 text-primary-700" />
            </div>
            <h3 class="font-semibold text-slate-900">{{ section.title }}</h3>
          </div>
          <ul class="space-y-2">
            <li v-for="item in section.items" :key="item" class="flex items-start gap-2 text-sm text-slate-600">
              <CheckCircleIcon class="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
              {{ item }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
```

### FAQ Accordion Pattern

```vue
<!-- Simple FAQ with v-show, no library needed -->
<div class="divide-y divide-slate-200">
  <div v-for="(faq, i) in faqs" :key="i" class="py-4">
    <button
      @click="openIndex = openIndex === i ? null : i"
      class="flex items-center justify-between w-full text-left cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded"
    >
      <span class="font-medium text-slate-900">{{ faq.q }}</span>
      <ChevronDownIcon
        class="w-5 h-5 text-slate-400 transition-transform duration-200 shrink-0"
        :class="openIndex === i ? 'rotate-180' : ''"
      />
    </button>
    <div v-show="openIndex === i" class="mt-3 text-sm text-slate-600 leading-relaxed">
      {{ faq.a }}
    </div>
  </div>
</div>
```

---

## Competitor Landing Page Analysis

### Key GEO Tool Competitor Patterns (Research: Feb 2026)

**Confirmed patterns from Surfer SEO, Ahrefs, Otterly.AI, Profound:**

1. **Hero section always includes**: Headline (problem-focused), 1-line value prop, primary CTA (free trial/get started), secondary CTA (demo/sample), social proof element (customer count or logos)

2. **Features section**: Icon grid or bento-style cards (2-col or 5-col asymmetric). Tag each feature with a category label (like the reference project's "Crawlability", "Schema", "Authority").

3. **How It Works**: 3-step numbered process with connecting line. Steps: Enter URL → Get Score → Fix Issues.

4. **Social Proof/Testimonials**: 3 testimonials. Asymmetric layout (1 large + 2 smaller). Use initials avatars with color coding (amber/blue/zinc — like Meridiane reference). No real photos needed for MVP.

5. **Pricing**: 3-tier card grid. Free | Pro ($29/mo) | Enterprise (contact). Pro card highlighted with ring/border. No yearly toggle (per requirements).

6. **FAQ**: 5-8 questions. Common GEO tool FAQs: "What is GEO?", "How is this different from SEO?", "How long does an audit take?", "What AI engines do you track?", "What does the free tier include?"

7. **Trust/Security section**: Critical for SaaS. Sections: Data encryption, Auth & access control, Privacy & data handling, Infrastructure, Audit logging, GDPR compliance. Use CheckCircle icons.

8. **Footer**: 4-5 column grid. Brand (logo + tagline) | Product (Pricing, Dashboard, Audit) | Company (About, Security) | Legal (Privacy, Terms) | Contact (email).

9. **Pricing market context**: GEO tools price $20-$500/mo. At $29/mo Endexa is competitive with Otterly.AI ($29) and Rankscale ($20). This should be referenced in messaging ("affordable" angle).

### Messaging That Works for GEO Tools

- **Problem-first headline**: "Is your site invisible to AI search?" (fear-based, specific)
- **Authority signal**: "61 criteria. 4 categories. Real measurements." (specificity builds trust)
- **Differentiation**: SEO + GEO combined (most tools are one or the other)
- **Actionability**: "Tells you exactly what to fix" (not just "gives you a score")
- **Affordability angle**: $29/mo vs. $495/mo enterprise tools

---

## Design System Coherence Plan

### Current State (Documented)

| Element | App Pages Currently | Design System Spec | Action |
|---------|--------------------|--------------------|--------|
| Body background | `bg-gray-50` | `#F8FAFC` (slate-50) | Minor: change to `bg-slate-50` |
| Body text | `text-gray-900` | `#1E3A8A` (primary-900) | Change headings to `text-primary-900`, body to `text-slate-700` |
| Primary button | `bg-primary-600` (#2563eb) | CTA = `#F59E0B` (amber) | CTA buttons should be amber (btn-primary needs update) |
| Card background | `bg-white` with `shadow-md` | White + shadow-md | Correct — keep |
| H1 font | Fira Code (correct) | Fira Code | Correct — keep |
| Body font | Fira Sans (correct) | Fira Sans | Correct — keep |

**Key insight:** The design system says CTA buttons = amber (#F59E0B). Currently `btn-primary` is blue (`bg-primary-600`). For the landing page, use amber for CTAs (`bg-amber-500`). For app pages, the blue primary buttons are acceptable within the dashboard context (they're navigation/action buttons, not conversion CTAs).

### Coherence Tasks (Not a Full Redesign)

The requirements say "coherent design system" — not a full visual redesign. The targeted fixes:
1. Make navbar and landing page look premium (new landing layout)
2. Ensure settings, pricing pages use `slate-*` not `gray-*` for color naming consistency
3. Ensure CTAs on all pages use amber, not blue
4. Ensure all pages have proper page titles (`useHead`)

---

## Environment Variables Documentation

### Backend `.env.example` — Missing Stripe Vars

```env
# ========== Stripe Payments ==========
# Get from Stripe Dashboard > Developers > API keys
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Get from Stripe Dashboard > Products > Prices
STRIPE_PRICE_PRO_MONTHLY=price_...

# Optional: Stripe Customer Portal configuration ID
# Get from Stripe Dashboard > Customer portal > Configurations
STRIPE_PORTAL_CONFIG_ID=bpc_...

# URL for Stripe success/cancel redirect
FRONTEND_URL=http://localhost:3000
```

### Frontend `.env.example` — Missing Stripe Vars

```env
# Stripe (publishable key only — never use secret key in frontend)
NUXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NUXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY=price_...
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Yearly billing toggle in pricing | No toggle — monthly only (per requirements) | Simplifies UX, removes confusion |
| Hardcoded `'price_pro_monthly'` | `config.public.stripePriceProMonthly` from env | Enables real Stripe wiring |
| Tier derived from audit `is_limited` | Dedicated subscription-status endpoint | Survives page refresh |
| No landing page (dashboard is first page) | Full landing page at `/` with redirect for logged-in users | Enables public marketing |
| `stripe.api_key` global (deprecated) | `StripeClient` instance (already correct) | Already on current SDK pattern |

**Deprecated/outdated already handled:**
- Legacy `stripe.api_key` global pattern: already replaced with `StripeClient(settings.STRIPE_SECRET_KEY)` in `stripe_service.py`
- Yearly billing toggle: will be removed

---

## Open Questions

1. **Enterprise contact form vs email link**
   - What we know: Requirements say "Enterprise (contact form)"
   - What's unclear: Does this mean a modal with a form, or just `mailto:` link?
   - Recommendation: Use `mailto:hello@endexa.com` for MVP — a full contact form (with Supabase storage or email sending) is out of scope. Mark as "Enterprise — Contact us" with email link.

2. **Testimonials — real or placeholder**
   - What we know: Product is in MVP phase, may not have real customers yet
   - What's unclear: Should we use placeholder testimonials with made-up names?
   - Recommendation: Use 3 testimonials with generic roles ("SEO Manager at an e-commerce agency", "In-house SEO specialist", "Digital marketing consultant") and realistic but anonymized quotes. Clearly label as "Early Access Users" to avoid credibility issues.

3. **Landing page URL routing**
   - What we know: `/` currently shows old dashboard widget page
   - What's unclear: Should logged-in users see landing page or redirect to dashboard?
   - Recommendation: Redirect logged-in users to `/dashboard` on mount. Anonymous users see landing page. This is the standard SaaS pattern.

4. **Stripe webhook endpoint in production**
   - What we know: Webhook endpoint exists at `/api/v1/payments/webhook`
   - What's unclear: Whether the webhook is registered in Stripe Dashboard (test vs production)
   - Recommendation: Document in PLAN.md that webhook registration is a manual step. Planner should add a verification task: "Confirm webhook endpoint registered in Stripe Dashboard (test mode) with correct events: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted, invoice.paid, invoice.payment_failed"

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `frontend/composables/useStripe.ts`, `useSubscription.ts` — current state documented from source
- Direct code inspection: `backend/app/api/payments.py`, `backend/app/services/stripe_service.py` — complete implementation verified
- Direct code inspection: `backend/app/core/dependencies.py` — `require_tier()` pattern verified
- Direct code inspection: `frontend/pages/pricing.vue` — hardcoded price ID bug verified at line 187
- Direct code inspection: `frontend/layouts/dashboard.vue` — no subscription rehydration on mount confirmed
- Direct code inspection: `frontend/pages/settings.vue` — no portal button for Pro users confirmed
- Direct code inspection: `frontend/tailwind.config.js` — design tokens verified
- Direct code inspection: `frontend/nuxt.config.ts` — runtime config structure verified
- Direct code inspection: `design-system/endexa-geo-platform/MASTER.md` — design system spec
- Direct code inspection: `quick-launch-page-craft` — Hero, Pricing, Features, Testimonials, Trust patterns
- Stripe Official Docs: https://docs.stripe.com/customer-management/integrate-customer-portal — Customer Portal integration confirmed

### Secondary (MEDIUM confidence)
- WebSearch + Stripe docs: Stripe Customer Portal requires manual Dashboard configuration before use
- WebSearch: GEO tool pricing context ($20-$500/mo range; $29/mo is competitive)
- WebSearch: SaaS landing page section order (hero → features → how it works → testimonials → pricing → FAQ → trust → footer)
- Nuxt official docs: `definePageMeta({ layout: 'landing' })` for layout isolation

### Tertiary (LOW confidence)
- Competitor landing page patterns (Surfer, Clearscope, Frase) inferred from WebSearch summaries — not directly verified by visiting their sites

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — No new libraries needed; all tools already installed
- Architecture: HIGH — Directly verified from codebase (specific line references)
- Stripe wiring: HIGH — Both backend (complete) and frontend (broken) verified from source
- Landing page patterns: MEDIUM — Reference project examined directly; competitor patterns from search
- Pitfalls: HIGH — All pitfalls verified against actual code

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (30 days — stable domain)
