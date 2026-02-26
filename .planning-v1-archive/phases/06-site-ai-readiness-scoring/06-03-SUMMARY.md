---
phase: 06-site-ai-readiness-scoring
plan: 03
subsystem: scoring
tags: [content-structure, readability, heading-hierarchy, answer-first, faq, textstat, nltk]

# Dependency graph
requires:
  - phase: 06-site-ai-readiness-scoring
    plan: 01
    provides: BaseScorer ABC, ScoringOrchestrator, PageScore/CriterionResult models
provides:
  - ContentStructureScorer implementing 13 content structure criteria
  - Heading hierarchy quality analysis (H1>H2>H3 with skip-level detection)
  - Answer-first format detection for question-style headings
  - Data density measurement (tables, lists, statistics)
  - FAQ section detection by heading patterns and Q&A structure
  - Readability scoring via Flesch-Kincaid (textstat)
  - Content freshness, citations, quotations, entity density analysis
affects: [06-05, 09-dashboard]
---

# 06-03 Summary: ContentStructureScorer

## What was built
ContentStructureScorer service (1360 lines) implementing 13 criteria that analyze whether page content is structured for AI extraction. This is 25% of the Optimization Score. Research shows answer-first format yields +40% citations (Princeton GEO paper).

## Key files

### key-files.created
- `backend/app/services/scoring/content_structure_scorer.py` — ContentStructureScorer with 13 criteria

### key-files.modified
- `backend/app/tasks/audit_tasks.py` — Registered ContentStructureScorer in scoring pipeline
- `backend/requirements.txt` — Added nltk>=3.8.0 for NLP analysis

## Criteria implemented
1. Heading hierarchy quality (H1>H2>H3, skip-level penalties)
2. Answer-first format detection
3. Paragraph length analysis
4. Data density (tables, ordered/unordered lists, statistics)
5. FAQ section presence
6. Content length adequacy
7. Readability (Flesch-Kincaid grade 8-10 target)
8. Citation/source presence
9. Content freshness (date detection)
10. Statistics density
11. Quotation presence
12. Entity density
13. Sentence variety

## Decisions
- Used textstat for Flesch-Kincaid readability scoring
- Added nltk for entity/sentence analysis
- Target readability grade 8-10 for optimal AI comprehension

## Self-Check: PASSED
