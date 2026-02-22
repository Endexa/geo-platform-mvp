# Backlog & Roadmap

> **Priority order. Work top-down unless the user says otherwise.**

---

## Priority 1 — Recommendation Engine (Core Value Prop)

The platform analyzes websites but can't yet tell users *what to fix*. This is the main differentiator.

- [ ] Integrate LiteLLM or direct OpenAI API in `backend/app/services/optimizer.py`
- [ ] Build prompt template: given analysis scores + crawled content, identify 3 gaps with action plans
- [ ] Return structured JSON: `{category, severity, issue, action_plan, impact_score}`
- [ ] Store recommendations in DB (model exists: `backend/app/models/recommendation.py`)
- [ ] Wire up `/optimization` frontend page to display recommendations
- [ ] Add "Create Jira Ticket" button per recommendation (Jira integration already scaffolded)
- [ ] Test with 5-10 real websites

**Acceptance criteria:** User analyzes URL → clicks "Generate Recommendations" → sees 3 actionable items with severity and impact scores.

---

## Priority 2 — Implement Critical GEO Data Points (~30 high-value scripts)

Currently 5/108 scripts return real data. Focus on the ones that provide the most value:

### Web Infrastructure (high impact)
- [ ] WI-006: Robots.txt PerplexityBot Access
- [ ] WI-007: Robots.txt CCBot Access
- [ ] WI-008: Robots.txt Google-Extended Access
- [ ] WI-011: Schema.org FAQPage
- [ ] WI-012: Schema.org HowTo
- [ ] WI-013: Schema.org BreadcrumbList
- [ ] WI-015: Internal Linking Structure
- [ ] WI-021: XML Sitemap Presence

### Content (high impact)
- [ ] CNT-001: Entity Density
- [ ] CNT-002: Flesch Reading Ease
- [ ] CNT-003: Content Freshness
- [ ] CNT-005: Heading Hierarchy
- [ ] CNT-006: Word Count
- [ ] CNT-012: Keyword Density

### Brand Visibility (high impact)
- [ ] BV-001: Knowledge Graph Presence
- [ ] BV-002: Wikidata QID

### UX (high impact)
- [ ] UX-001: Core Web Vitals LCP
- [ ] UX-003: Core Web Vitals CLS

### Legal
- [ ] LEG-001: Privacy Policy Presence
- [ ] LEG-002: GDPR Cookie Consent

**Acceptance criteria:** `orchestrator/run_all.py` returns real (non-zero) scores for these data points when analyzing any URL.

**Template pattern:** Copy an existing working script (e.g., `wi_001_gptbot.py`), adapt the measurement logic.

---

## Priority 3 — Brand Signature Engine (4-Layer Architecture)

Layers 1 (rules) and 3 (pgvector similarity) already work. Build the missing layers.

### Layer 2: Statistical Fingerprint (NEW)
- [ ] On knowledge base upload: extract brand profile stats (avg sentence length, vocabulary richness/TTR, Flesch-Kincaid range, passive voice ratio, question frequency, formality score)
- [ ] Store brand profile as JSON in `brand_voice_configs` table (add `stats_profile JSONB` column)
- [ ] On check: compute same stats for new content, compare against profile (z-score deviation)
- [ ] Return per-stat deviation scores

### Layer 4: LLM Deep Analysis (NEW)
- [ ] Add "Explain" endpoint: `POST /api/v1/voice/explain`
- [ ] Retrieve top-5 similar brand passages via pgvector
- [ ] Build LLM prompt: compare new content vs retrieved brand examples
- [ ] Return structured response: tone mismatches, vocabulary drift, missing messages, specific suggestions with brand excerpts

### Composite Scoring
- [ ] Update `check_voice()` to combine all available layers with proper weights
- [ ] Fast mode (layers 1-3): `rules×0.2 + stats×0.3 + semantic×0.5`
- [ ] Deep mode (all 4): `rules×0.15 + stats×0.2 + semantic×0.35 + llm×0.3`

### Frontend
- [ ] Complete file upload UI on `/brand-voice` (PDF/TXT parsing)
- [ ] Add rule creation UI (forbidden words, required phrases, tone directives)
- [ ] Display composite score breakdown (per-layer scores)
- [ ] Add "Explain" button that triggers Layer 4 and shows detailed analysis

### Polish
- [ ] Add brand centroid calculation (average of all embeddings) for distance-from-center metric
- [ ] Test full flow: upload KB → check content → see composite score → click Explain → see detailed analysis

**Acceptance criteria:** User uploads brand content → checks new text → sees instant composite score (layers 1-3) → clicks "Explain" → gets LLM-powered analysis with brand examples.

---

## ~~Priority 4 — Enable Authentication~~ DONE (Phase 1)

Auth fully enabled via GSD Phase 1 (Foundation & Safety):
- PyJWT + pwdlib replace python-jose + passlib
- Register/login/me endpoints at `/api/v1/auth/*`
- All protected endpoints require `Depends(get_current_active_user)` — returns 401 for unauthenticated requests
- AuditCostLedger model + CostTrackingService with $1.00/audit budget cap
- Redis AI response cache (24h TTL, fail-open)
- Outbound rate limiter per AI provider (asyncio semaphore + token bucket)
- Celery app initialized with Redis broker
- Alembic migrations infrastructure with 2 migrations
- Remaining: `org_id` scoping for queries, frontend login/signup flow

---

## ~~Priority 5 — Clean Up Dead Code~~ DONE

RAG dead code removed (rag.py, rag_system.py, mongodb_client.py, qdrant_client.py, requirements_rag.txt, RAG_INTEGRATION_SUMMARY.md, .env.example cleaned). Brand signature uses pgvector only.

---

## Priority 5 — Complete Integrations

- [ ] Test Stripe webhook with real/test payment
- [ ] Test Jira ticket creation with real recommendations
- [ ] Set up proper environment variables for external services

---

## Open Bugs

| # | Severity | Description | File |
|---|----------|-------------|------|
| — | — | No known bugs yet | — |

---

## Agent-Suggested Tasks

<!-- Agents: add discovered improvements here with [Agent Suggested] prefix -->

---

## Post-MVP Scope (Won't Build Now)

- Scheduled monitoring / recurring analysis
- Email notifications / weekly digest
- Real-time WebSocket updates
- Multi-tenant organization management
- Advanced analytics / trend comparison
- PDF report export
