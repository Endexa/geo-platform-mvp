# Phase 5: Audit Experience - Research

**Researched:** 2026-02-22
**Domain:** Full-stack audit UX -- Nuxt 3 frontend + FastAPI backend integration
**Confidence:** HIGH

## Summary

Phase 5 is the first frontend-heavy phase in this project. All prior phases built backend pipeline stages (crawl, query gen, dispatch, analysis, scoring). Phase 5 connects the user to that pipeline: a URL input triggers a complete audit, progress updates stream to the frontend, and results are displayed with drill-down into individual AI responses with highlighted brand mentions.

The backend is almost entirely done. The `POST /api/v1/audit/` endpoint creates audits, the Celery pipeline runs 5 stages (CRAWLING -> GENERATING_QUERIES -> DISPATCHING -> ANALYZING -> COMPLETED), and the `GET /api/v1/audit/{id}` endpoint returns full details including queries, engine responses, brand mentions, and visibility scores. The main work is: (1) build frontend auth so the protected audit endpoints work, (2) build the audit trigger + progress polling UI, (3) build the results display with score cards and per-query drill-down, and (4) build the AI response viewer with highlighted brand mentions.

**Primary recommendation:** Build a `useAuth` composable and `useApiFetch` wrapper first (auth token in cookie, auto-injected Authorization header), then build the audit page as a single-page flow with URL input -> progress stepper -> results -> drill-down. Use `useIntervalFn` from @vueuse/core for polling. Build a custom `<HighlightMentions>` component using BrandMention `char_offset` data rather than string matching, since the backend already provides precise offsets.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIT-01 | User can enter a URL and trigger a complete AI brand visibility audit | Backend `POST /api/v1/audit/` already exists. Frontend needs: auth composable, audit page with URL input form, API call wiring. The audit trigger is one API call returning 202 + audit ID. |
| AUDIT-07 | User can drill down into each query to see the full AI response with mentions highlighted | Backend `GET /api/v1/audit/{id}` returns full `AuditDetailResponse` including `queries[].engine_responses[].mentions[]` with `char_offset` and `context_quote`. Frontend needs: expandable query list, AI response viewer, custom highlight component using offset data. |
</phase_requirements>

## Standard Stack

### Core (Already in project -- no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Nuxt 3 | ^3.9.0 | Frontend framework | Already installed, SPA mode |
| @vueuse/core | ^10.7.0 | `useIntervalFn` for polling, `useCookie` available but Nuxt built-in preferred | Already installed |
| @heroicons/vue | ^2.0.18 | Icons for progress steps, status indicators | Already installed |
| Tailwind CSS | ^3.4.0 | Styling | Already installed |
| Pinia | ^2.1.7 | Auth state store | Already installed |

### Supporting (No new npm packages needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Nuxt `useCookie` | built-in | JWT token storage (SSR-safe) | Auth composable for persisting access_token |
| Nuxt `useFetch` / `$fetch` | built-in | API calls with auth headers | All API communication |
| @headlessui/vue | ^1.7.16 | Disclosure/accordion for drill-down | Query expansion UI |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `useApiFetch` | @nuxtjs/supabase auth | Supabase module is already in nuxt.config but auth moved to self-managed JWT in Phase 1. Remove Supabase module to avoid conflicts. |
| Custom `<HighlightMentions>` | vue-word-highlighter | vue-word-highlighter only supports string-based matching, not character-offset highlighting. Backend provides precise `char_offset` values -- using them is more accurate than re-matching strings. |
| `useIntervalFn` polling | WebSocket/SSE | Polling is simpler, audit takes 30-90s total, and the status endpoint is already built. WebSockets add infrastructure complexity for minimal benefit at this scale. |
| Pinia auth store | useCookie + composable only | Pinia provides reactive state across components (nav bar, auth guards). Worth it since layout needs auth state for user display. |

**Installation:**
```bash
# No new packages needed. Everything required is already installed.
# However, @nuxtjs/supabase should be REMOVED from nuxt.config.ts modules
# since auth is now self-managed JWT (Phase 1 decision).
```

## Architecture Patterns

### Recommended Project Structure (New files for Phase 5)

```
frontend/
├── composables/
│   ├── useAuth.ts              # Auth state: login/logout/token/user
│   └── useApiFetch.ts          # $fetch wrapper with auto Authorization header
├── middleware/
│   └── auth.ts                 # Route guard: redirect to /login if no token
├── stores/
│   └── auth.ts                 # Pinia store for auth state (reactive across components)
├── components/
│   ├── AuditForm.vue           # URL input + submit button
│   ├── AuditProgress.vue       # Multi-step progress stepper with status mapping
│   ├── AuditResults.vue        # Score cards + per-engine breakdown
│   ├── QueryList.vue           # Expandable list of audit queries
│   ├── QueryDetail.vue         # Single query with engine responses
│   ├── EngineResponseCard.vue  # Individual AI response with highlighted mentions
│   └── HighlightMentions.vue   # Custom component: renders text with highlighted spans at char_offsets
├── pages/
│   ├── login.vue               # REWRITE: actual login/register form
│   └── audit.vue               # NEW: main audit page (form + progress + results)
└── layouts/
    └── dashboard.vue           # UPDATE: auth-aware nav (user info, logout)
```

### Pattern 1: Auth Composable + Cookie Token Storage

**What:** Store JWT access_token in a cookie using Nuxt's `useCookie`, provide a `useAuth` composable wrapping login/logout/user state, and a `useApiFetch` that auto-injects the Authorization header.

**When to use:** Every API call to the backend (all audit endpoints require JWT auth).

**Example:**
```typescript
// composables/useApiFetch.ts
export const useApiFetch = (url: string, opts: any = {}) => {
  const config = useRuntimeConfig()
  const token = useCookie('access_token')

  return $fetch(url, {
    baseURL: config.public.apiUrl + '/api/v1',
    headers: {
      ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
    },
    ...opts,
  })
}
```

```typescript
// composables/useAuth.ts
export const useAuth = () => {
  const token = useCookie('access_token')
  const user = useState<User | null>('auth_user', () => null)
  const isLoggedIn = computed(() => !!token.value)

  const login = async (email: string, password: string) => {
    const data = await useApiFetch('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    token.value = data.access_token
    // Fetch user info
    const me = await useApiFetch('/auth/me')
    user.value = me
  }

  const logout = () => {
    token.value = null
    user.value = null
    navigateTo('/login')
  }

  return { token, user, isLoggedIn, login, logout }
}
```

### Pattern 2: Status-Driven Progress Polling

**What:** After creating an audit, poll `GET /audit/{id}` every 2-3 seconds using `useIntervalFn`. Map `AuditStatus` enum values to progress stepper steps. Stop polling when status is `completed` or `failed`.

**When to use:** Between audit creation (202) and completion.

**Example:**
```typescript
// In audit.vue or AuditProgress.vue
const STAGE_ORDER = ['pending', 'crawling', 'generating_queries', 'dispatching', 'analyzing', 'completed']

const STAGE_LABELS: Record<string, string> = {
  pending: 'Starting audit...',
  crawling: 'Crawling website...',
  generating_queries: 'Generating AI queries...',
  dispatching: 'Querying AI engines...',
  analyzing: 'Analyzing mentions & scoring...',
  completed: 'Audit complete!',
}

const currentStage = computed(() => {
  return STAGE_ORDER.indexOf(audit.value?.status ?? 'pending')
})

const { pause } = useIntervalFn(async () => {
  const data = await useApiFetch(`/audit/${auditId.value}`)
  audit.value = data
  if (data.status === 'completed' || data.status === 'failed') {
    pause()
  }
}, 3000)
```

### Pattern 3: Offset-Based Mention Highlighting

**What:** Given `response_text` and an array of `BrandMention` objects (each with `char_offset`, `matched_text`, `confidence`), render the response text with `<mark>` tags at the precise offsets.

**When to use:** EngineResponseCard drill-down view.

**Example:**
```typescript
// components/HighlightMentions.vue logic
function buildHighlightedSegments(text: string, mentions: Mention[]): Segment[] {
  // Sort mentions by char_offset ascending
  const sorted = [...mentions].sort((a, b) => a.char_offset - b.char_offset)
  const segments: Segment[] = []
  let cursor = 0

  for (const mention of sorted) {
    // Text before this mention
    if (mention.char_offset > cursor) {
      segments.push({ text: text.slice(cursor, mention.char_offset), highlight: false })
    }
    // The mention itself
    segments.push({
      text: text.slice(mention.char_offset, mention.char_offset + mention.matched_text.length),
      highlight: true,
      mention,
    })
    cursor = mention.char_offset + mention.matched_text.length
  }
  // Remaining text after last mention
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), highlight: false })
  }
  return segments
}
```

### Anti-Patterns to Avoid

- **String re-matching for highlights:** The backend already computed `char_offset` values. Do NOT use regex or string search to find mentions in the frontend -- use the offsets directly. String matching could miss fuzzy matches or highlight wrong occurrences.
- **Polling without cleanup:** Always call `pause()` from `useIntervalFn` when polling is no longer needed (component unmount, audit complete, or audit failed). Orphaned intervals cause memory leaks and unnecessary API calls.
- **Storing JWT in localStorage:** Use `useCookie` instead. Cookies work with SSR (if ever enabled), are automatically sent with requests, and can be configured with httpOnly in production.
- **Fetching full audit detail for progress checks:** The `GET /audit/{id}` endpoint eager-loads all queries, engine responses, and mentions. For progress polling, consider adding a lightweight status endpoint OR use the existing endpoint but only use the `status` field during polling, then fetch full details once on completion. For MVP, the existing endpoint is fine since data only grows to full size after completion anyway.
- **Hardcoding API URL:** Use `useRuntimeConfig().public.apiUrl` consistently. The existing `analyze.vue` hardcodes fetch URLs -- don't repeat this pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Polling interval management | Manual setInterval + onUnmounted cleanup | `useIntervalFn` from @vueuse/core | Handles lifecycle cleanup automatically, provides pause/resume controls |
| Cookie-safe token storage | Manual document.cookie parsing | Nuxt `useCookie` composable | SSR-safe, reactive, auto-serialization |
| Expandable/collapsible query list | Custom toggle logic | `<Disclosure>` from @headlessui/vue | Accessible, animated, keyboard-navigable out of the box |
| Icon library | SVG inline strings | @heroicons/vue components | Already installed, consistent with existing layout |
| Route auth guard | Per-page auth checks | Nuxt route middleware (`defineNuxtRouteMiddleware`) | Centralized, runs before navigation, works with SSR |

**Key insight:** This phase has zero new npm dependencies needed. Everything required is already installed. The work is wiring existing tools together and building Vue components.

## Common Pitfalls

### Pitfall 1: Supabase Module Conflict
**What goes wrong:** The existing `nuxt.config.ts` includes `@nuxtjs/supabase` as a module, which adds its own auth middleware and redirect logic. This conflicts with the self-managed JWT auth built in Phase 1.
**Why it happens:** The project was originally built with Supabase auth, then Phase 1 migrated to self-managed JWT. The frontend module was never removed.
**How to avoid:** Remove `@nuxtjs/supabase` from `nuxt.config.ts` modules array and remove the `supabase` config block. Remove `@nuxtjs/supabase` from package.json dependencies.
**Warning signs:** Unexpected redirects, auth-related console errors from Supabase client, double auth token handling.

### Pitfall 2: Polling Continues After Navigation
**What goes wrong:** User starts an audit, navigates away, but the polling interval keeps firing, causing console errors or stale state updates.
**Why it happens:** `useIntervalFn` auto-cleans up on component unmount in Vue 3, but only if it's called in the setup function. If called in an async callback or after await, cleanup may not bind correctly.
**How to avoid:** Call `useIntervalFn` at the top level of `<script setup>`, not inside async functions. Control start/stop with `pause()` and `resume()`. Use a `watch` on the audit status to pause when complete.
**Warning signs:** Console errors after navigating away from audit page, API calls to audits that no longer exist.

### Pitfall 3: AuditStatus Enum Mismatch
**What goes wrong:** Frontend progress stepper doesn't match backend statuses, showing wrong step or getting stuck.
**Why it happens:** Backend uses snake_case enum values (`generating_queries`, `completed`). Frontend might map these incorrectly or miss a stage.
**How to avoid:** Define the status-to-step mapping as a single constant (see Pattern 2 above). The backend `AuditStatus` enum values are: `pending`, `crawling`, `generating_queries`, `dispatching`, `analyzing`, `completed`, `failed`.
**Warning signs:** Progress stepper shows "unknown" stage, stepper jumps backwards, stepper doesn't advance.

### Pitfall 4: N+1 Rendering in Query Drill-Down
**What goes wrong:** Rendering all 10-15 queries with all their engine responses and mentions at once causes UI jank.
**Why it happens:** Each query has 3 engine responses, each response has potentially many mentions with full text. Rendering all at once = 30-45 large text blocks.
**How to avoid:** Use accordion/disclosure pattern -- only render the expanded query's engine responses. Lazy-render AI response text only when the user expands that specific query.
**Warning signs:** Slow page rendering after audit completion, scroll jank.

### Pitfall 5: Auth Token Expiry During Long Audit
**What goes wrong:** Access token expires while the audit is still running (token TTL is 30 minutes, audit could take 2-5 minutes, but user might leave tab open). Subsequent poll requests return 401.
**Why it happens:** JWT has 30-minute expiry (`ACCESS_TOKEN_EXPIRE_MINUTES = 30` in config). No refresh token flow is implemented in the frontend yet.
**How to avoid:** For MVP, the 30-minute window is likely sufficient. Add error handling in the polling function to detect 401 and redirect to login. For a better UX, implement refresh token rotation (backend already supports `create_refresh_token`).
**Warning signs:** Polling suddenly returns 401 errors, user gets kicked to login mid-audit.

### Pitfall 6: Frontend Login Page is a Bypass
**What goes wrong:** The current `login.vue` is a "Continue to Dashboard" button with no actual auth. If we add auth middleware, every page redirects to login, but login doesn't actually authenticate.
**Why it happens:** login.vue was built for MVP demo mode before Phase 1 added real auth.
**How to avoid:** Rewrite login.vue with actual register/login forms that call `POST /api/v1/auth/register` and `POST /api/v1/auth/login`. Use the `useAuth` composable.
**Warning signs:** Auth middleware creates infinite redirect loop (login requires auth which redirects to login).

## Code Examples

### Audit Status to Progress Mapping
```typescript
// types/audit.ts
interface AuditStatus {
  status: 'pending' | 'crawling' | 'generating_queries' | 'dispatching' | 'analyzing' | 'completed' | 'failed'
}

const PROGRESS_STEPS = [
  { key: 'crawling', label: 'Crawling website', icon: 'GlobeAltIcon' },
  { key: 'generating_queries', label: 'Generating queries', icon: 'SparklesIcon' },
  { key: 'dispatching', label: 'Querying AI engines', icon: 'PaperAirplaneIcon' },
  { key: 'analyzing', label: 'Analyzing mentions', icon: 'MagnifyingGlassIcon' },
  { key: 'completed', label: 'Audit complete', icon: 'CheckCircleIcon' },
]

function getStepIndex(status: string): number {
  const idx = PROGRESS_STEPS.findIndex(s => s.key === status)
  return idx === -1 ? 0 : idx
}
```

### Audit Page Flow
```vue
<!-- pages/audit.vue -->
<template>
  <NuxtLayout name="dashboard">
    <!-- Phase 1: URL Input -->
    <AuditForm v-if="!auditId" @submit="startAudit" />

    <!-- Phase 2: Progress -->
    <AuditProgress v-else-if="isRunning" :audit="audit" />

    <!-- Phase 3: Results -->
    <AuditResults v-else-if="isCompleted" :audit="audit" />

    <!-- Error State -->
    <AuditError v-else-if="isFailed" :audit="audit" @retry="resetAudit" />
  </NuxtLayout>
</template>
```

### Auth-Protected API Fetch
```typescript
// composables/useApiFetch.ts
export function useApiFetch<T>(path: string, opts: any = {}): Promise<T> {
  const config = useRuntimeConfig()
  const token = useCookie('access_token')

  return $fetch<T>(path, {
    baseURL: `${config.public.apiUrl}/api/v1`,
    headers: {
      ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
      ...opts.headers,
    },
    onResponseError({ response }) {
      if (response.status === 401) {
        token.value = null
        navigateTo('/login')
      }
    },
    ...opts,
  })
}
```

### Mention Highlighting Component
```vue
<!-- components/HighlightMentions.vue -->
<template>
  <div class="whitespace-pre-wrap text-sm leading-relaxed">
    <template v-for="(segment, i) in segments" :key="i">
      <mark
        v-if="segment.highlight"
        class="bg-warning-200 text-warning-900 rounded px-0.5"
        :title="`${segment.mention.match_type} match (${segment.mention.confidence}% confidence)`"
      >{{ segment.text }}</mark>
      <span v-else>{{ segment.text }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
interface Mention {
  char_offset: number
  matched_text: string
  match_type: string
  confidence: number
}
interface Segment {
  text: string
  highlight: boolean
  mention?: Mention
}

const props = defineProps<{
  text: string
  mentions: Mention[]
}>()

const segments = computed<Segment[]>(() => {
  if (!props.mentions.length) return [{ text: props.text, highlight: false }]
  const sorted = [...props.mentions].sort((a, b) => a.char_offset - b.char_offset)
  const result: Segment[] = []
  let cursor = 0
  for (const m of sorted) {
    if (m.char_offset > cursor) {
      result.push({ text: props.text.slice(cursor, m.char_offset), highlight: false })
    }
    const end = m.char_offset + m.matched_text.length
    result.push({
      text: props.text.slice(m.char_offset, end),
      highlight: true,
      mention: m,
    })
    cursor = end
  }
  if (cursor < props.text.length) {
    result.push({ text: props.text.slice(cursor), highlight: false })
  }
  return result
})
</script>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| @nuxtjs/supabase for auth | Self-managed JWT (Phase 1) | Phase 1 (2026-02-22) | Must remove Supabase module from frontend |
| `setInterval` + `onUnmounted` | `useIntervalFn` from @vueuse/core | VueUse 10.x (2024) | Cleaner polling with auto-cleanup |
| `pollEvery` built into useFetch | Rejected from Nuxt core | PR #29566 (2024) | Use @vueuse/core `useIntervalFn` instead |
| vue-word-highlighter for text highlighting | Custom offset-based component | N/A (project-specific) | Backend provides `char_offset` -- more accurate than string re-matching |
| analyze.vue (old analysis API) | audit.vue (new audit API) | Phase 5 | Old page talks to `/api/v1/analysis/analyze`, new page talks to `/api/v1/audit/` |

**Deprecated/outdated in this project:**
- `@nuxtjs/supabase` module: Remove from nuxt.config.ts and package.json. Auth is self-managed JWT.
- `frontend/pages/analyze.vue`: The old analysis page. Keep for backward compat but the new audit flow should be on `/audit`.
- `frontend/pages/login.vue`: Currently a bypass button. Must be rewritten with real register/login forms.

## Open Questions

1. **Should analyze.vue be repurposed or kept separate?**
   - What we know: `analyze.vue` talks to the old `/analysis/analyze` endpoint (108-point scoring). The new audit is on `/audit/`.
   - What's unclear: Should we replace `analyze.vue` with the new audit flow, or keep both? The old analysis is a different feature (website scoring) vs. new audit (AI brand visibility).
   - Recommendation: Keep `analyze.vue` as-is for now. Create new `audit.vue` page. Update sidebar nav to include "AI Audit" link. The two features serve different purposes.

2. **Lightweight status endpoint for polling?**
   - What we know: `GET /audit/{id}` eager-loads all queries, responses, and mentions. During polling, we only need the `status` field.
   - What's unclear: Does the eager loading cause measurable overhead before the audit is complete? During crawling/generating stages, the queries list is empty or short.
   - Recommendation: Use the existing endpoint for MVP. The eager loading only returns substantial data when the audit is complete (when polling stops). Optimize later if needed.

3. **Refresh token flow?**
   - What we know: Backend supports `create_refresh_token` (7-day expiry). Frontend currently has no refresh token logic.
   - What's unclear: Is 30-minute access token sufficient for the audit use case?
   - Recommendation: For Phase 5, store only the access_token. Add 401 error handling that redirects to login. Defer refresh token rotation to a later phase. The 30-minute window is generous for a 2-5 minute audit.

4. **Design system alignment?**
   - What we know: MASTER.md specifies Fira Code/Fira Sans fonts, specific color palette (#1E40AF primary, #F59E0B CTA), and Data-Dense Dashboard style. No page-specific design file for audit page exists.
   - What's unclear: Should the design system fonts be implemented in this phase?
   - Recommendation: Use the existing Tailwind color configuration (already close to design system colors). Font implementation can be deferred to a dedicated UI polish phase. Focus on functional UX.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `backend/app/api/audit.py`, `backend/app/tasks/audit_tasks.py`, `backend/app/schemas/audit.py` -- backend API and pipeline are fully built
- Codebase analysis: `backend/app/models/audit.py` (AuditStatus enum), `backend/app/models/brand_mention.py` (char_offset field)
- Codebase analysis: `backend/app/core/security.py`, `backend/app/api/auth.py` -- JWT auth endpoints exist
- Codebase analysis: `frontend/nuxt.config.ts`, `frontend/package.json` -- @vueuse/core, @headlessui/vue already installed
- [Nuxt pollEvery PR #29566 -- CLOSED](https://github.com/nuxt/nuxt/pull/29566) -- pollEvery rejected, use useIntervalFn instead

### Secondary (MEDIUM confidence)
- [VueUse useIntervalFn docs](https://vueuse.org/shared/useintervalfn/) -- standard polling composable
- [vue-word-highlighter GitHub](https://github.com/kawamataryo/vue-word-highlighter) -- confirmed no offset-based highlighting
- [Mastering Nuxt JWT auth](https://masteringnuxt.com/blog/building-a-custom-authentication-system-with-jwt-in-nuxt-3) -- useCookie + composable pattern
- [FastAPI + Celery polling pattern](https://testdriven.io/blog/fastapi-and-celery/) -- 202 + poll status endpoint

### Tertiary (LOW confidence)
- [Nuxt UI Stepper component](https://ui.nuxt.com/docs/components/stepper) -- design reference only (Nuxt UI is NOT installed and should NOT be added)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed, no new dependencies
- Architecture: HIGH -- backend API already built, frontend patterns well-established in Nuxt 3 ecosystem
- Pitfalls: HIGH -- identified from direct codebase analysis (Supabase conflict, login bypass, enum mismatch)
- Auth integration: MEDIUM -- composable pattern is well-documented but needs careful implementation to avoid Supabase module conflicts

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable -- no fast-moving dependencies)
