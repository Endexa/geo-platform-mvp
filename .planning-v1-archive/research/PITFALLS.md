# Domain Pitfalls: AI Brand Visibility Auditing

**Domain:** AI Brand Visibility Auditing Platform (querying ChatGPT, Claude, Perplexity for brand mentions)
**Project:** GEO Platform MVP
**Researched:** 2026-02-21
**Confidence:** MEDIUM (based on training data knowledge of API policies, pricing, and common patterns in LLM-integrated products; web verification tools were unavailable during research -- API terms and pricing MUST be verified against current official documentation before implementation)

---

## Critical Pitfalls

Mistakes that cause rewrites, legal exposure, or unsustainable economics.

---

### C-1: API Cost Explosion -- Querying 3+ AI Engines Per Audit Without Cost Controls

**What goes wrong:** Each audit queries ChatGPT, Claude, and Perplexity with multiple prompts (industry questions, brand-specific queries, competitor comparisons). A single audit easily generates 10-20 API calls across three providers. At $0.01-0.03 per query (GPT-4o-mini input+output for a typical brand monitoring prompt) and $0.03-0.15 for more capable models, a single audit costs $0.30-3.00. With user experimentation, re-runs, and custom queries, costs spiral before any revenue is collected.

**Why it happens:**
- Developers test with small volumes and never model per-audit unit economics
- "Just query all three engines with all the questions" seems obvious but is expensive at scale
- No cost ceiling per audit means a single user can generate $50+ in API costs by adding many custom queries
- Free tier users generate costs with no revenue offset

**Consequences:**
- A product that costs more per audit than it can charge, especially at the free/trial tier
- Discovering the unit economics problem after launch, when usage patterns are already established
- Having to retroactively add restrictions that degrade the user experience

**Warning signs:**
- No per-audit cost estimate in the design documents
- No hard cap on number of queries per audit
- No differentiation between free/paid tier query budgets
- Testing only with 1-2 queries rather than realistic 10-20 query workloads

**Prevention:**
1. **Model unit economics before writing any AI query code.** Calculate: (queries per audit) x (avg tokens per query) x (cost per token) x (3 engines) = cost per audit. Compare against target price point.
2. **Implement a query budget per audit** -- hard cap of N queries per engine, enforced at the service layer, not just the UI.
3. **Start with GPT-4o-mini and Claude 3.5 Haiku** (or cheapest available tiers). Resist the temptation to use flagship models for monitoring queries.
4. **Cache aggressively.** If a user audits "best CRM software" today, the same query to the same engine tomorrow will produce a similar answer. Cache AI responses with a configurable TTL (24-72 hours for MVP).
5. **Implement cost tracking from day one.** Log the estimated cost of every API call. Build a `/admin/costs` dashboard before building the user-facing one.
6. **Use the existing Redis cache** in the stack. Store AI responses keyed by `hash(engine + prompt + date_bucket)`.

**Detection:** Track `cost_per_audit` metric. If it exceeds your target price point / 3 (leaving room for infrastructure + margin), you have a problem.

**Phase mapping:** Must be addressed in the AI engine querying milestone, before any user-facing feature is shipped. This is a design constraint, not an afterthought.

**Confidence:** HIGH -- this is fundamental unit economics, not speculative.

---

### C-2: Terms of Service Violations -- Scraping AI Engine UIs Instead of Using Official APIs

**What goes wrong:** Teams build scrapers that automate the ChatGPT web UI, Perplexity web interface, or Claude.ai to extract responses, because "it's cheaper than the API" or "the API doesn't have web search." This violates every major AI provider's Terms of Service, which explicitly prohibit automated access to their consumer-facing products.

**Why it happens:**
- The API versions of these models behave differently from the web UI versions (especially Perplexity, which has real-time web search in the UI but a different behavior in the API)
- Scraping is perceived as free, while APIs have clear per-token costs
- Some features (like ChatGPT's Browse with Bing or Perplexity's web citations) are not directly available via the API in the same form
- Developers confuse "I can technically do this" with "I am allowed to do this"

**Consequences:**
- Account termination and potential legal action
- IP blocking, CAPTCHA walls, and detection mechanisms that break the product unpredictably
- Building on a foundation that can disappear overnight with no recourse
- Inability to raise funding or sell the product (legal due diligence will catch this)

**Warning signs:**
- Any code using Playwright/Selenium/Puppeteer to interact with chat.openai.com, claude.ai, or perplexity.ai
- References to "headless browser" in the context of querying AI engines (as opposed to crawling the user's own website, which is legitimate)
- Storing session cookies or auth tokens for AI provider consumer accounts
- The existing Playwright dependency in the stack is fine for crawling user-submitted URLs, but must NOT be repurposed for AI engine scraping

**Prevention:**
1. **Use only official APIs.** OpenAI API, Anthropic API, Perplexity API. No exceptions.
2. **Document the API access method** for each engine in the architecture. Make it explicit that scraping is prohibited.
3. **Review each provider's current Terms of Service and Acceptable Use Policy** before implementation. Flag this as a mandatory pre-implementation task. (Note: I was unable to verify current TOS documents during this research -- this MUST be done before coding begins.)
4. **Accept that API responses differ from web UI responses.** The product's value proposition must be built on what the APIs provide, not what the web UIs show.
5. **For Perplexity specifically:** The Perplexity API (pplx-api) provides a Sonar model with online search capabilities. Use this rather than trying to replicate the web UI experience.

**Detection:** Code review. Any `playwright.goto("https://chat.openai.com")` or similar is an immediate red flag.

**Phase mapping:** Architecture decision that must be locked in before any AI engine integration code is written. First task of the AI querying milestone.

**Confidence:** HIGH -- TOS violations are well-documented across all three providers. MEDIUM on specific current API capabilities (verify before implementation).

---

### C-3: Building Monitoring Before Nailing the One-Time Audit

**What goes wrong:** The team starts building scheduled re-checks, trend tracking, alert systems, and dashboards for monitoring brand visibility over time -- before the single one-time audit produces reliable, valuable results. The monitoring layer adds enormous complexity (scheduling, diff detection, notification systems, historical data storage, trend visualization) while the core audit is still unreliable or hard to interpret.

**Why it happens:**
- Monitoring is the "premium feature" and feels like the path to revenue
- It is more technically interesting than perfecting a single audit
- Stakeholders push for "recurring value" before validating "one-time value"
- The PROJECT.md already lists monitoring as a paid upgrade path, which creates pressure to build toward it

**Consequences:**
- A monitoring system that faithfully tracks unreliable data (garbage in, garbage out)
- Premature complexity in the database schema (time-series storage, diff tables, alert configs) that constrains future changes to the audit format
- User confusion: "Why did my score drop from 72 to 45 overnight?" when the real answer is "AI responses are non-deterministic"
- Engineering time spent on scheduling infrastructure instead of audit quality

**Warning signs:**
- Database schema includes `scheduled_audits`, `audit_history`, or `alert_configs` tables before the single audit flow is validated with real users
- Celery beat or cron-based scheduling code exists before the one-time audit is reliable
- More code in the monitoring/scheduling layer than in the audit/analysis layer
- User feedback on the single audit is not yet collected

**Prevention:**
1. **Enforce a strict milestone gate:** The one-time audit must be validated (real users, real feedback, real value) before any monitoring code is written.
2. **Design the audit data model to be monitoring-compatible** (timestamps, versioning, immutable results) without building the monitoring layer itself.
3. **The PROJECT.md already gets this right** -- "MVP is one-time audit, monitoring as upgrade." Enforce this boundary ruthlessly during implementation.
4. **Track the temptation explicitly.** When someone says "while we're here, we could also add scheduling," the answer is "that's Phase N+1."

**Detection:** If the Celery beat scheduler is configured before 10 real users have completed a one-time audit, you have jumped ahead.

**Phase mapping:** Monitoring is a separate milestone that should NOT begin until the one-time audit milestone is complete and validated. The one-time audit milestone should explicitly include a "no monitoring" boundary in its scope.

**Confidence:** HIGH -- this is a well-known product development anti-pattern, and the PROJECT.md already identifies the correct sequencing.

---

### C-4: Storing AI Responses Without Data Handling Strategy -- Privacy and Legal Exposure

**What goes wrong:** The platform stores verbatim AI engine responses in the database without considering: (a) whether the AI provider's terms allow storing and re-displaying their outputs, (b) whether the responses contain copyrighted material that the platform is now redistributing, (c) GDPR/privacy implications if AI responses mention real people, and (d) data retention policies.

**Why it happens:**
- "We need to show the user what the AI said" seems like an obvious requirement
- Storing the raw response is the simplest implementation
- Legal review is deferred because "we're just an MVP"
- The distinction between "using AI output internally" and "displaying AI output as a product feature" is not considered

**Consequences:**
- Potential violation of AI provider terms (some providers restrict how their outputs can be displayed, especially in competitive/benchmarking contexts)
- Copyright liability if AI responses reproduce copyrighted content and the platform serves it to users
- GDPR data subject access requests becoming nightmarish (AI responses may reference individuals)
- Data storage costs growing unbounded as every audit stores full AI transcripts

**Warning signs:**
- No `data_retention_policy` field or cleanup job for old AI responses
- AI responses stored as raw text blobs with no metadata about source, version, or expiration
- No legal review of "can we show users what ChatGPT said about their brand?"
- No consideration of the distinction between "we queried the AI" (API usage) and "we are redistributing the AI's output" (content licensing)

**Prevention:**
1. **Review each provider's API terms regarding output storage and redistribution.** OpenAI's terms generally allow commercial use of API outputs. Anthropic's terms allow commercial use of API outputs. Perplexity's terms need specific review. (MEDIUM confidence -- verify current terms before implementation.)
2. **Store structured extracts, not raw transcripts.** Extract: brand_mentioned (bool), mention_context (excerpt), sentiment, position_in_response. This is more useful for scoring AND avoids storing full copyrighted AI outputs.
3. **Implement data retention from day one.** AI responses older than N days should be summarized and the raw text purged. Keep the scores and metadata, delete the verbatim text.
4. **Add attribution.** When showing AI quotes to users, attribute them clearly: "Source: ChatGPT API response, [date]." This is both legally safer and more transparent.
5. **Flag personal data in AI responses.** If an AI response mentions a real person by name, that is potentially PII under GDPR. Implement detection (even basic NER) and handling.

**Detection:** If the `ai_responses` table is growing without bounds and has no `expires_at` column, this pitfall is active.

**Phase mapping:** Data handling strategy must be defined in the architecture phase of the AI querying milestone, before the first API response is stored. Schema design should include retention fields.

**Confidence:** MEDIUM -- specific provider terms need current verification. The general principle of needing a data handling strategy is HIGH confidence.

---

## High Pitfalls

Mistakes that cause significant rework or degrade product quality.

---

### H-1: Treating AI Responses as Deterministic -- The Reproducibility Problem

**What goes wrong:** The team builds scoring and comparison logic that assumes querying the same prompt to the same engine twice will produce the same result. In reality, LLM outputs are non-deterministic even with temperature=0 (due to floating-point non-determinism in GPU operations, model updates, system prompt changes, and A/B testing by providers). A brand's "visibility score" can fluctuate 10-30% between runs with identical inputs.

**Why it happens:**
- Developers test once, see a result, and assume it is stable
- The scoring algorithm treats each data point as a fixed measurement, like a page speed test
- Temperature=0 is assumed to mean "deterministic" (it does not, it means "greedy decoding," which is still non-deterministic across hardware)
- AI providers silently update models, system prompts, and safety filters

**Consequences:**
- Users lose trust when their score changes without any change to their website
- Trend data (for future monitoring) becomes meaningless noise
- Support burden: "Why did my score drop?" when the answer is "AI randomness"
- Comparing audits across time becomes unreliable

**Warning signs:**
- No `temperature` parameter set in API calls (relying on provider defaults)
- No mention of "variance," "confidence interval," or "stability" in the scoring design
- Score displayed as a single number (72) rather than a range (68-76)
- No mechanism to run multiple queries and aggregate

**Prevention:**
1. **Set temperature=0 on all monitoring queries.** This minimizes (but does not eliminate) variance.
2. **Run each query 2-3 times and aggregate.** Majority vote for binary questions (mentioned/not), median for numerical scores. This increases cost but dramatically improves reliability.
3. **Display confidence alongside scores.** "Visibility: 72 (confidence: high)" or "Visibility: 45-65 (variable)." Users need to understand the measurement has inherent uncertainty.
4. **Record the model version with each response.** OpenAI's API returns the model in the response. Anthropic's API returns the model. Track these to detect when a provider updates their model and scores shift.
5. **Design the scoring algorithm to be robust to individual query variance.** Weight binary signals (mentioned/not mentioned) higher than nuanced signals (sentiment, position in response) because they are more stable.
6. **Seed prompts where possible.** Use structured, specific prompts that constrain the response format, reducing variance in the parts you are scoring.

**Detection:** Run the same audit against the same URL twice within an hour. If scores differ by more than 15%, the scoring system is not handling non-determinism.

**Phase mapping:** Core architecture decision for the scoring system. Must be addressed in the audit design phase, before scoring logic is implemented.

**Confidence:** HIGH -- LLM non-determinism is a well-documented characteristic.

---

### H-2: Over-Engineering the Scoring Algorithm -- The "108 Data Points" Trap Revisited

**What goes wrong:** The team builds an elaborate, multi-dimensional scoring algorithm with weighted factors, sub-scores, normalization curves, and statistical models -- before validating that the scoring methodology correlates with actual brand visibility. The original 108-point system in this codebase is a concrete example of this exact pitfall: elaborate measurement infrastructure with questionable signal value.

**Why it happens:**
- More data points feels like more rigor
- Engineers enjoy building complex scoring systems
- The competitive landscape (SEO tools with "domain authority" scores) creates pressure to have a sophisticated-looking number
- The jump from "AI mentioned the brand" (binary, clear) to "AI mentioned the brand with positive sentiment in the top 3 sentences" (multi-factor, fuzzy) feels like added value

**Consequences:**
- Users do not trust or understand the score
- The score does not correlate with business outcomes (the user's brand being recommended by AI)
- Enormous engineering effort in calibration and tuning
- The existing codebase already has this problem: a 108-point system where 103 measurements return 0, random numbers, or crash

**Warning signs:**
- More than 5-7 scoring factors before validation with real users
- Score weights chosen by intuition rather than data
- No user research on "what number would make you take action?"
- Score algorithm documentation longer than the user-facing explanation of the score

**Prevention:**
1. **Start with the simplest meaningful score.** For v1: `visibility_score = (engines_that_mention_brand / total_engines_queried) * 100`. That is it. If ChatGPT mentions you but Claude and Perplexity do not, your score is 33.
2. **Layer complexity based on validated signals.** Only add a factor (sentiment, position in response, competitor comparison) when you have evidence it changes user behavior.
3. **Make the score explainable in one sentence.** "Your brand was mentioned by 2 out of 3 AI engines we tested." If you cannot explain it simply, it is too complex.
4. **Learn from the existing codebase's mistake.** The 108-point system was abandoned because it scored the site without checking what AI actually says. Do not repeat this by building an elaborate scoring system for what AI says without first validating that users find the raw data valuable.
5. **Separate the score from the data.** Show users the actual AI quotes and let them judge. The score is a summary, not the product.

**Detection:** If the scoring algorithm has more than 10 weighted factors and no user validation data, this pitfall is active.

**Phase mapping:** Scoring design should be a deliberate, constrained task in the audit milestone. Start simple, iterate based on user feedback. Resist the urge to design the "final" scoring system upfront.

**Confidence:** HIGH -- validated by the existing codebase's 108-point system being abandoned.

---

### H-3: Rate Limiting and API Quota Exhaustion -- Silent Failures at Scale

**What goes wrong:** The platform hits API rate limits during peak usage and either fails silently (returning partial results), crashes visibly, or blocks all users because rate limits are shared across the entire application rather than isolated per user/audit.

**Why it happens:**
- Each AI provider has different rate limiting models (RPM, TPM, concurrent requests)
- Rate limits are per-API-key, not per-user, so all platform users share the same quota
- Developers test with one user at a time and never encounter limits
- Error handling for 429 responses is an afterthought
- The existing rate limiter in the codebase limits inbound requests to the platform, but does NOT limit outbound requests to AI providers

**Consequences:**
- User A's audit causes User B's audit to fail
- Partial results with no indication of what is missing
- Automated retry loops that make the problem worse
- Provider-imposed cooldowns that affect the entire platform

**Specific rate limits to plan for (verify current values before implementation):**
- **OpenAI:** Tier-based. New accounts: ~500 RPM, 200K TPM. Tier 3+: 5000 RPM. These limits are per-organization, shared across all API keys.
- **Anthropic:** Tier-based. Varies by model. Claude 3.5 Haiku: ~100 RPM for lower tiers.
- **Perplexity:** The Sonar API has rate limits that vary by plan. Typically 20-50 RPM for standard plans.

**Warning signs:**
- No outbound rate limiter for AI API calls (the existing `rate_limiter.py` only handles inbound requests)
- No retry-with-backoff logic for 429 responses
- API keys stored as single env vars with no mention of quota management
- No circuit breaker pattern for when an engine is unavailable

**Prevention:**
1. **Build an outbound rate limiter.** Use Redis (already in the stack) to track API calls per provider per time window. Enforce limits below the provider's actual limits (80% of quota) to leave headroom.
2. **Implement exponential backoff with jitter** for 429 responses. Do not retry immediately.
3. **Queue audit queries through Celery** (already in the stack but not wired). This provides natural throttling and allows priority-based ordering.
4. **Isolate failures per engine.** If Perplexity is rate-limited, the audit should still complete with ChatGPT and Claude results. Partial results are better than no results.
5. **Monitor quota usage in real time.** Build a simple gauge: "OpenAI: 340/500 RPM used." Alert at 70% utilization.
6. **Consider per-engine API keys** if volume justifies it. Separate keys for different user tiers to isolate free-tier traffic from paid-tier traffic.
7. **Implement a circuit breaker.** If an engine returns 5 consecutive errors, stop querying it for 60 seconds rather than burning through retry budget.

**Detection:** Any 429 response from an AI provider in production logs. Any audit that completes with fewer engine results than expected without a clear error message to the user.

**Phase mapping:** Rate limiting and quota management must be built into the AI query service from the start. Not a "we'll add it later" concern.

**Confidence:** HIGH on the problem existing. MEDIUM on specific current rate limit numbers (verify with each provider's current documentation).

---

### H-4: Query Design That Produces Unreliable or Gameable Results

**What goes wrong:** The prompts used to query AI engines about a brand are either too generic ("Tell me about [brand]") producing inconsistent results, too leading ("Why is [brand] the best in [category]?") producing artificially positive results, or too narrow ("Is [brand] mentioned in your training data?") missing the actual use case of how real users query AI engines.

**Why it happens:**
- Prompt engineering for evaluation is harder than prompt engineering for generation
- The "auto-generated industry-relevant questions" feature (from PROJECT.md) requires understanding what questions real users would ask AI engines about this industry
- No ground truth exists for "correct" AI brand visibility
- Temptation to optimize prompts for the score rather than for realistic scenarios

**Consequences:**
- Scores that do not reflect real-world AI brand visibility
- Users discovering they can game their score by choosing favorable queries
- Inconsistent results across runs because vague prompts produce varied responses
- Competitive analysis that is misleading (competitor scores based on different query patterns)

**Warning signs:**
- Prompts that include the brand name as the primary subject (leading)
- No research on actual user queries in the target industry
- Auto-generated queries that are too generic ("best [category]") or too specific ("is [exact brand name] good at [exact service]?")
- No A/B testing of prompt variations

**Prevention:**
1. **Design queries around user intent, not brand names.** Instead of "Tell me about Acme Corp," use "What are the best [category] tools for [use case]?" The brand should appear (or not) naturally.
2. **Use a mix of query types:**
   - Category queries: "Best [industry] solutions for [use case]"
   - Problem queries: "How do I solve [problem the brand solves]?"
   - Comparison queries: "Compare top [category] providers"
   - Direct queries: "What do you know about [brand]?" (as one signal among many)
3. **Template queries with fill-in-the-blank fields** derived from crawling the user's website (industry, services, geography). The auto-generation should be structured, not free-form.
4. **Validate query effectiveness.** For a known brand (e.g., Salesforce for CRM), do the queries reliably surface that brand? If not, the queries are wrong, not the AI.
5. **Store and version queries.** Every audit records exactly which queries were used. This enables debugging and fair comparison over time.

**Detection:** Run the audit against a well-known brand (Apple, Salesforce, Nike). If the brand is not consistently detected across engines, the queries need work.

**Phase mapping:** Query template design is a critical sub-task of the AI querying milestone. It should be researched and validated before building the auto-generation feature.

**Confidence:** HIGH -- prompt design quality directly determines product quality.

---

## Moderate Pitfalls

Mistakes that cause delays, tech debt, or user experience issues.

---

### M-1: Treating All Three AI Engines as Interchangeable

**What goes wrong:** The code uses the same prompt format, the same parsing logic, and the same scoring criteria for ChatGPT, Claude, and Perplexity responses. In reality, these engines behave very differently: Perplexity includes citations and sources, ChatGPT may use web browsing (GPT-4o) or not (GPT-4o-mini), and Claude tends toward longer, more structured responses. A one-size-fits-all approach misses engine-specific signals and produces unreliable cross-engine comparisons.

**Why it happens:**
- LiteLLM (already in the stack) abstracts engine differences, making them look interchangeable
- "Query all three with the same prompt" is the simplest implementation
- Response parsing is hard enough for one format; handling three feels like over-engineering

**Consequences:**
- Missing Perplexity-specific value (citations, source links)
- Misinterpreting Claude's structured response format as "longer = better mention"
- Cross-engine scores that are not comparable (mentioned in a 3-paragraph Claude response vs. a 1-sentence ChatGPT response)

**Prevention:**
1. **Build an engine-specific adapter layer.** Each engine gets its own response parser that extracts standardized signals (brand_mentioned, context, sentiment) from engine-specific response formats.
2. **Tailor prompts per engine if needed.** Perplexity benefits from "with sources" instructions. ChatGPT may need different instructions for browsing-enabled vs. non-browsing models.
3. **Use LiteLLM for the API call abstraction** (it is already installed), but build custom parsers for the response content.
4. **Weight engines differently.** Perplexity with web search may be more relevant for "current brand visibility" than Claude's training-data-only knowledge.

**Detection:** If the same scoring function is called on raw `response.content` from all three engines without any engine-specific processing, this pitfall is active.

**Phase mapping:** Engine adapter design should be part of the AI querying milestone architecture.

**Confidence:** HIGH -- engine behavioral differences are well-documented.

---

### M-2: No Graceful Degradation When an AI Engine Is Unavailable

**What goes wrong:** If one of the three AI engines (ChatGPT, Claude, Perplexity) is down, rate-limited, or returns an error, the entire audit fails. Users see "Audit failed" when two out of three engines responded successfully.

**Why it happens:**
- Sequential query execution: if step 2 fails, step 3 never runs
- Error handling that propagates exceptions to the top level
- No concept of "partial results" in the data model

**Consequences:**
- Audit reliability is the product of three independent services' reliability (~99.9%^3 = 99.7%, meaning ~2.6 hours of expected downtime per year from engine unavailability alone, more realistically much worse)
- User frustration with intermittent failures
- Support tickets for problems outside your control

**Prevention:**
1. **Query all engines concurrently** (asyncio.gather with return_exceptions=True or Celery group tasks). One failure does not block others.
2. **Design the results schema to support partial results.** Each engine result is optional. The UI displays "ChatGPT: Mentioned, Claude: Unavailable, Perplexity: Not mentioned."
3. **Score based on available results.** If only 2 engines responded, score from 2. Clearly indicate the missing engine.
4. **Cache last-known-good results.** If Perplexity was queried yesterday and is down today, optionally show "Last checked: [date]" rather than blank.

**Detection:** Trigger an audit while one engine's API key is intentionally invalid. If the audit fails entirely, degradation is not graceful.

**Phase mapping:** Error handling strategy for the AI querying milestone.

**Confidence:** HIGH.

---

### M-3: Auto-Generated Queries That Expose Proprietary Information

**What goes wrong:** The auto-query-generation feature crawls the user's website and constructs AI engine queries that inadvertently include proprietary information (pricing, client lists, internal product names, strategy keywords) in the prompts sent to third-party AI APIs. These prompts may be logged by the providers, used for training (depending on plan), or exposed in API usage dashboards.

**Why it happens:**
- Crawling a website and extracting "keywords" for query generation is a blunt instrument
- No filtering between "public marketing keywords" and "sensitive business information"
- Users do not realize that auto-generated queries will be sent to external AI APIs

**Consequences:**
- User trust violation: "You sent my pricing strategy to OpenAI?"
- Potential data leakage if the AI provider uses API inputs for training (OpenAI API inputs are NOT used for training by default as of early 2025, but Perplexity's terms differ -- verify current policies)
- Enterprise customers (agencies) may have contractual obligations that prohibit sending client data to third-party AI APIs

**Prevention:**
1. **Show users the auto-generated queries before executing them.** Let users review, edit, and approve queries before they are sent to AI engines.
2. **Filter sensitive patterns from auto-generated queries.** Do not include: pricing, revenue, client names, internal product codenames, contact information.
3. **Add a clear disclosure:** "These queries will be sent to [list of AI providers]. Review and remove any sensitive information."
4. **For agency users managing client brands:** Make it clear that client brand names and industry keywords will be sent to third-party AI APIs. Some agencies will need client consent for this.
5. **Consider offering an option to use anonymized queries** ("best CRM tools for mid-market companies" instead of "is [client_name] a top CRM for mid-market?") for sensitive clients.

**Detection:** Review auto-generated queries for a real website. If they contain pricing, phone numbers, or internal terminology, the filtering is insufficient.

**Phase mapping:** Auto-query generation feature within the AI querying milestone. The review/approval UI is a required sub-task, not a nice-to-have.

**Confidence:** MEDIUM -- the severity depends on the specific auto-generation implementation and user base sensitivity.

---

### M-4: Database Schema Coupling Between Audit Results and Scoring Algorithm

**What goes wrong:** The audit results table stores computed scores as columns (like the existing `analyses` table with `visibility_score`, `readability_score`, `authority_score`). When the scoring algorithm changes (and it will, frequently, as the product evolves), historical results cannot be re-scored, and the schema must be migrated.

**Why it happens:**
- Storing computed scores as columns is the natural first implementation
- The existing codebase does this already (see the `analyses` model)
- "We'll just add a migration" seems easy until the 5th scoring change in 2 months

**Consequences:**
- Historical audits show scores from a different algorithm than current audits, making trends misleading
- Schema migrations for every scoring tweak
- Inability to re-score historical data when the algorithm improves

**Prevention:**
1. **Store raw AI responses and extracted signals separately from computed scores.** Raw data goes in an immutable `ai_responses` table. Computed scores go in a `scores` table that can be recomputed.
2. **Version the scoring algorithm.** Store `scoring_version: int` alongside every score. When the algorithm changes, increment the version.
3. **Build a re-scoring capability** from day one. Given raw AI responses, recompute scores. This is trivial if raw data is preserved and scored data is separate.
4. **Use JSONB for flexible raw data storage.** The existing schema already uses JSONB for `raw_data` on the `analyses` table. Extend this pattern.

**Detection:** If changing the score weighting formula requires a database migration, this pitfall is active.

**Phase mapping:** Database schema design within the AI querying milestone. The separation of raw data from scored data must be in the initial schema.

**Confidence:** HIGH -- this is a standard data modeling concern for any analytics product.

---

### M-5: Ignoring Model Version Drift and Silent Model Updates

**What goes wrong:** AI providers update their models without notice (or with minimal notice). OpenAI has historically updated GPT-4o-mini, GPT-4o, and other models in-place. Anthropic updates Claude Haiku/Sonnet/Opus. These updates can change how a brand is described, whether it appears in responses, and the overall response format. A brand's visibility score changes not because of anything the brand did, but because the AI provider updated the model.

**Why it happens:**
- "gpt-4o-mini" is treated as a stable identifier when it is actually a moving target
- No logging of model version per API call
- No baseline tests to detect when model behavior changes

**Consequences:**
- Score fluctuations that erode user trust
- Inability to distinguish "the brand's visibility changed" from "the model changed"
- Misleading trend data in the monitoring phase

**Prevention:**
1. **Pin specific model versions where available.** Use `gpt-4o-mini-2024-07-18` instead of `gpt-4o-mini`. Anthropic uses dated model IDs (e.g., `claude-3-5-haiku-20241022`).
2. **Log the model ID returned in every API response.** OpenAI's response includes `model` field. Anthropic's response includes `model` field.
3. **Run baseline queries daily.** A known-answer query (e.g., "What is the most popular CRM?") should return Salesforce consistently. If it stops doing so, something changed.
4. **Display model version in audit metadata.** Users should be able to see "This audit was performed using GPT-4o-mini-2024-07-18, Claude 3.5 Haiku 20241022, Perplexity Sonar."
5. **Alert when detected model versions change** from the last run.

**Detection:** Compare the `model` field in API responses across audits. If the model string changes between two runs that used the same configuration, model drift has occurred.

**Phase mapping:** Instrumentation task within the AI querying milestone. Model version logging is a required field in the AI response storage schema.

**Confidence:** HIGH -- model version drift is well-documented and ongoing.

---

## Minor Pitfalls

Issues that are easy to fix but often overlooked.

---

### L-1: Not Setting Appropriate Timeouts for AI API Calls

**What goes wrong:** AI API calls can take 5-30 seconds, especially for larger models or during high-traffic periods. Without explicit timeouts, an audit can hang indefinitely, blocking the Celery worker (or worse, a FastAPI background thread as the current codebase does).

**Prevention:**
1. Set explicit `timeout` on all AI API calls (15-30 seconds per call).
2. Set an overall audit timeout (2-3 minutes maximum).
3. Use asyncio or Celery task timeouts as a safety net.

**Phase mapping:** Basic implementation concern in the AI querying milestone.

**Confidence:** HIGH.

---

### L-2: Logging AI Prompts and Responses at DEBUG Level Without Sanitization

**What goes wrong:** Debug logging includes full AI prompts (which may contain user brand names, industry information) and full AI responses. These logs are stored in files, shipped to log aggregation services, and potentially accessible to support staff.

**Prevention:**
1. Log AI interactions at a separate log level or to a separate, access-controlled log sink.
2. Never log full prompts/responses at INFO level. Use truncated versions.
3. Implement log rotation and retention policies (the existing Loguru config has 10-day retention -- verify this is appropriate for AI response content).

**Phase mapping:** Logging configuration within the AI querying milestone.

**Confidence:** HIGH.

---

### L-3: Hardcoding Engine-Specific Prompt Templates in Service Code

**What goes wrong:** Prompt templates for each AI engine are embedded in Python service files. Changing a prompt requires a code change, redeployment, and potentially a review cycle. During rapid iteration on prompt quality, this creates unnecessary friction.

**Prevention:**
1. Store prompt templates in a configuration file (YAML or database table), not in Python code.
2. Version prompt templates independently from code.
3. Build an admin interface to edit and test prompt templates without redeployment.

**Phase mapping:** Architecture decision in the AI querying milestone. Simple YAML-based templates for v1.

**Confidence:** HIGH.

---

### L-4: Not Accounting for AI Engine Geographic and Language Variation

**What goes wrong:** AI responses vary by language settings, API region, and user locale. The platform queries from a single server location with English prompts, but the user's customers may experience different AI responses in different languages or regions.

**Prevention:**
1. Document that MVP results reflect English-language, US-region AI responses.
2. Add a `locale` parameter to audits for future multi-language support.
3. Do not claim "global" brand visibility based on single-locale queries.

**Phase mapping:** Scope limitation to document in the AI querying milestone. Not a v1 feature, but must be explicitly excluded.

**Confidence:** MEDIUM -- the degree of geographic variation in AI APIs is not well-documented.

---

## Phase-Specific Warnings

| Phase / Milestone Topic | Likely Pitfall | Mitigation | Priority |
|------------------------|---------------|------------|----------|
| AI Engine API Integration | C-1 (Cost explosion) | Model unit economics first; implement budgets and caching | CRITICAL |
| AI Engine API Integration | C-2 (TOS violations) | Official APIs only; review current TOS before coding | CRITICAL |
| AI Engine API Integration | H-3 (Rate limit exhaustion) | Outbound rate limiter + circuit breakers from day one | HIGH |
| AI Engine API Integration | H-1 (Non-determinism) | Temperature=0, multi-query aggregation, confidence display | HIGH |
| AI Engine API Integration | M-1 (Engines not interchangeable) | Engine-specific adapters for prompt and response handling | HIGH |
| Query Auto-Generation | H-4 (Query quality) | User-intent-based queries, not brand-name-based | HIGH |
| Query Auto-Generation | M-3 (Data leakage) | Show queries before execution, filter sensitive content | MEDIUM |
| Scoring Algorithm Design | H-2 (Over-engineering scores) | Start with simplest meaningful score, iterate on feedback | HIGH |
| Results Storage & Display | C-4 (Data handling) | Structured extracts, retention policies, provider TOS review | CRITICAL |
| Results Storage & Display | M-4 (Schema coupling) | Separate raw data from computed scores, version scoring | MEDIUM |
| Results Storage & Display | M-5 (Model version drift) | Pin model versions, log model IDs, baseline tests | MEDIUM |
| Monitoring (future phase) | C-3 (Premature monitoring) | Gate: one-time audit validated before monitoring begins | CRITICAL |

---

## Existing Codebase-Specific Warnings

These pitfalls are specific to building AI engine querying on top of the existing GEO Platform codebase.

| Existing Issue | Impact on AI Querying Milestone | Mitigation |
|---------------|-------------------------------|------------|
| BackgroundTasks used instead of Celery (M-22 in CONCERNS.md) | AI API calls will take 10-30 seconds per engine. Using FastAPI BackgroundTasks will block ASGI workers. | Wire Celery for AI audit tasks before building the query system. This is a prerequisite, not a nice-to-have. |
| Authentication disabled (H-11 in CONCERNS.md) | Without auth, any visitor can trigger expensive AI API calls. A bot could drain the entire API budget in minutes. | Enable authentication before exposing AI audit endpoints. At minimum, require an API key. |
| Rate limiter fails open on Redis outage (M-20 in CONCERNS.md) | If Redis goes down, there is no rate limiting on inbound requests AND no outbound rate limiting on AI API calls. | Change to fail-closed for the AI audit endpoint specifically. |
| `.env` committed with placeholder keys (M-23 in CONCERNS.md) | AI API keys (OpenAI, Anthropic, Perplexity) are high-value credentials that must not be committed. | Fix the `.gitignore` issue before adding new API keys. |
| Existing scoring uses random numbers (H-9 in CONCERNS.md) | If the AI audit scoring inherits the pattern of using `random.randint()` for missing data, scores will be unreliable. | Establish a clear "no random fallbacks" coding standard for the AI audit system. Missing data = explicit null, not a random number. |
| Dual ORM architecture (H-4 in CONCERNS.md) | New AI audit models should use ONE database access pattern. Do not create a third Base. | All new models for AI audit results must use the backend's existing SQLAlchemy Base and Alembic migrations. |

---

## Sources and Confidence Notes

- **API Terms of Service:** Based on training data knowledge of OpenAI, Anthropic, and Perplexity policies as of early 2025. MEDIUM confidence. These policies change frequently. **Action required:** Before implementation, read the current versions of:
  - OpenAI Usage Policies: https://openai.com/policies/usage-policies
  - OpenAI API Terms: https://openai.com/policies/terms-of-use
  - Anthropic Usage Policy: https://www.anthropic.com/aup
  - Anthropic API Terms: https://www.anthropic.com/api-terms
  - Perplexity API Terms: Check https://docs.perplexity.ai for current terms
- **API Pricing:** Based on training data knowledge of pricing as of early 2025. LOW confidence on exact numbers. Pricing changes frequently. **Action required:** Check current pricing pages before modeling unit economics.
- **API Rate Limits:** Based on training data knowledge of rate limit structures. MEDIUM confidence on general structure, LOW confidence on exact numbers. **Action required:** Verify current rate limits per provider tier.
- **Non-determinism characteristics:** HIGH confidence. This is a fundamental property of LLMs, not subject to policy changes.
- **Product development patterns (premature monitoring, over-engineering scores):** HIGH confidence. These are well-established anti-patterns observed across the industry.
- **Existing codebase concerns:** HIGH confidence. Based on direct analysis of CONCERNS.md and ARCHITECTURE.md from the codebase audit.
