---
phase: 06-site-ai-readiness-scoring
plan: 04
subsystem: scoring
tags: [structured-data, schema-org, json-ld, faqpage, llms-txt, sameAs]

# Dependency graph
requires:
  - phase: 06-site-ai-readiness-scoring
    plan: 01
    provides: BaseScorer ABC, ScoringOrchestrator, PageScore/CriterionResult models
provides:
  - StructuredDataScorer implementing 13 structured data criteria
  - Tiered schema type detection (Foundation/Content/Supplementary)
  - JSON-LD syntax and completeness validation per schema type
  - FAQPage bonus weight recognition (3.2x citation rate)
  - llms.txt and llms-full.txt presence and format validation
  - sameAs link detection
  - Coverage breadth scoring
affects: [06-05, 09-dashboard]
---

# 06-04 Summary: StructuredDataScorer

## What was built
StructuredDataScorer service (1113 lines) implementing 13 criteria checking schema.org quality and coverage. This is 20% of the Optimization Score. JSON-LD is 2.3-2.5x more likely to appear in AI Overviews (BrightEdge). FAQPage schema gives +28% AI citations (Frase.io).

## Key files

### key-files.created
- `backend/app/services/scoring/structured_data_scorer.py` — StructuredDataScorer with 13 criteria

### key-files.modified
- `backend/app/tasks/audit_tasks.py` — Registered StructuredDataScorer in scoring pipeline

## Criteria implemented
1. Organization schema presence and completeness
2. WebSite schema presence
3. BreadcrumbList schema presence
4. Article schema presence and completeness
5. FAQPage schema (bonus weighted — 3.2x citation rate)
6. HowTo schema presence
7. Product schema presence
8. Person schema presence
9. ClaimReview schema presence
10. JSON-LD validation (syntax + required fields)
11. Coverage breadth (number of distinct schema types)
12. sameAs links presence
13. llms.txt presence and format

## Decisions
- Three-tier schema classification: Foundation (Organization/WebSite/BreadcrumbList), Content (Article/FAQPage/HowTo/Product), Supplementary (Person/ClaimReview/Review)
- FAQPage gets bonus weight in scoring due to 3.2x citation rate evidence
- llms.txt checked but scored conservatively (no AI provider confirmed reading it)

## Self-Check: PASSED
