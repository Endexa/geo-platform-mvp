---
phase: 06-site-ai-readiness-scoring
plan: 02
subsystem: scoring
tags: [crawlability, robots-txt, ssr-detection, ttfb, ai-bots, playwright]

# Dependency graph
requires:
  - phase: 06-site-ai-readiness-scoring
    plan: 01
    provides: BaseScorer ABC, ScoringOrchestrator, PageScore/CriterionResult models
provides:
  - CrawlabilityScorer implementing 12 crawlability criteria
  - Robots.txt checks for 8 AI bots (GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, Claude-SearchBot, Bingbot, CCBot, Google-Extended)
  - SSR detection via Playwright JS vs no-JS content comparison
  - TTFB measurement and scoring
  - HTTP status code verification for AI bot user-agents
  - Resource blockage detection (CSS/JS blocked in robots.txt)
affects: [06-05, 09-dashboard]
---

# 06-02 Summary: CrawlabilityScorer

## What was built
CrawlabilityScorer service (592 lines) implementing 12 criteria that evaluate whether AI crawlers can access and read page content. This is 25% of the Optimization Score — the most critical technical factor.

## Key files

### key-files.created
- `backend/app/services/scoring/crawlability_scorer.py` — CrawlabilityScorer with 12 criteria

### key-files.modified
- `backend/app/tasks/audit_tasks.py` — Registered CrawlabilityScorer in scoring pipeline

## Criteria implemented
1. GPTBot robots.txt access
2. ClaudeBot robots.txt access
3. PerplexityBot robots.txt access
4. OAI-SearchBot robots.txt access
5. Claude-SearchBot robots.txt access
6. Bingbot robots.txt access
7. CCBot robots.txt access
8. Google-Extended robots.txt access
9. SSR detection (JS vs no-JS content comparison)
10. TTFB measurement (good: <500ms, acceptable: <1500ms, poor: >1500ms)
11. HTTP status code for AI bot user-agent
12. Resource blockage detection

## Decisions
- Used Playwright for SSR detection (comparing JS-rendered vs no-JS content)
- 50% content threshold for JS-only flag
- Graceful degradation if Playwright unavailable (skip SSR criterion)

## Self-Check: PASSED
