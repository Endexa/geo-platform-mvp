# Test Report — SomScorer (Share of Model) + Live Scoring Pipeline

**Date :** 2026-04-06
**Branche :** `measureGEO_implementation`
**Site de test :** `http://localhost:9999` (Acme Analytics — site statique local)

---

## Resume

| Suite de tests | Resultat | Details |
|----------------|----------|---------|
| SomScorer unit tests | 25/25 | `tests/test_som_scorer.py` |
| Orchestrator unit tests | 15/15 | `tests/test_scoring_orchestrator.py` |
| Live scoring (site de test) | 32/32 | `tests/test_live_scoring.py` |
| **Total** | **72/72** | |

---

## Ce qui a ete teste

### 1. SomScorer — Unit Tests (25 tests)

Testent le scorer en isolation, sans crawl ni DB.

| Categorie | Tests | Ce qui est verifie |
|-----------|-------|--------------------|
| Structure | 4 | Import, heritage BaseScorer, constructeur sans args, methode score_page |
| Critere COMP1 | 5 | Retourne exactement 1 resultat, criterion_id="COMP1", bon type, nom descriptif, pourcentage dans summary |
| Calcul SoM | 7 | score=0 si vide, score=100 si parfait, score=0 si 0 mentions, score=50 si moitie, moyenne multi-engine, queries inegales, score clamp 0-100 |
| Edge cases | 4 | Ancien format flat skip, queries_sent=0 pas de division par zero, cle manquante, entree non-dict |
| Evidence | 2 | Evidence non-null, contient per_engine_som |
| Integration BaseScorer | 2 | compute_category_score correspond au score du critere |

### 2. Orchestrator — Unit Tests (15 tests)

Testent l'aggregation et la decouverte de liens.

| Categorie | Tests | Ce qui est verifie |
|-----------|-------|--------------------|
| Weakest-link | 6 | 1 page, multi-page, vide, categories manquantes, clamp, scores parfaits |
| Link discovery | 4 | Extraction liens, filtrage externe, skip non-content, HTML vide |
| Category weights | 5 | ai_visibility present, poids=0.15, somme=1.0, 5 categories, optimization_score exclut ai_visibility |

### 3. Live Scoring — Tests sur le site de test (32 tests)

Crawlent le vrai site `http://localhost:9999` et executent les scorers.

| Categorie | Tests | Ce qui est verifie |
|-----------|-------|--------------------|
| Crawler | 5 | HTML retourne, titre extrait, contenu texte, domaine, cles requises |
| CrawlabilityScorer | 7 | 12 criteres, scores valides, GPTBot/ClaudeBot/PerplexityBot autorises, HTTP 200, score categorie > 0 |
| ContentStructureScorer | 5 | 13 criteres, heading hierarchy, content length, FAQ detecte, score > 0 |
| StructuredDataScorer | 6 | 13 criteres, Organization detecte, FAQPage detecte, Article detecte, llms.txt (note SSL), score > 0 |
| SomScorer | 4 | COMP1 retourne, score correspond aux donnees simulees (52%), evidence 5 engines, pourcentage dans summary |
| Pipeline complet | 5 | 4 categories presentes, tous scores >= 0, 39 criteres total, COMP1 avec score=57, scorecard imprime |

### 4. Scorecard du site de test

```
CRAWLABILITY:       100.0/100  (11/12 checked — C9 SSR skip car Playwright non installe)
CONTENT_STRUCTURE:   69.2/100  (13/13 checked)
STRUCTURED_DATA:     37.7/100  (13/13 checked)
AI_VISIBILITY:       57.0/100  (1/1 checked — donnees de visibilite simulees)
```

**39 criteres evalues** sur le site de test, dont 38 avec des scores reels.

---

## Ce qui n'a PAS ete teste (et pourquoi)

### 1. AuthorityScorer (A1-A8 + S1-S15)

**Raison :** Appelle des APIs externes (Google Knowledge Graph, Wikidata SPARQL, Wikipedia REST, PageSpeed Insights) qui necessitent `GOOGLE_API_KEY` et une connexion internet fiable. Le scorer fonctionne en "graceful degradation" (retourne `_not_checked` si l'API echoue), mais les tests live ne valident pas les vrais scores.

**Pour tester :** Ajouter `GOOGLE_API_KEY` au `.env` et lancer sur un vrai domaine HTTPS.

### 2. Pipeline d'audit complet (8 stages Celery)

**Raison :** Necessite :
- `DATABASE_URL` Supabase (pas de base locale configuree)
- Cles API LLM (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`) pour les stages 2 (query gen), 3 (dispatch), 7 (sentiment)
- Celery worker connecte a Redis + DB

**Ce qui manque specifiquement :**
- Stage 1 (CRAWLING) : crawl OK en isolation, mais pas teste via Celery
- Stage 2 (GENERATING_QUERIES) : necessite OpenAI API key
- Stage 3 (DISPATCHING) : necessite toutes les cles LLM
- Stage 4 (ANALYZING) : necessite DB pour stocker BrandMention/EngineResponse
- Stage 5 (SCORING) : **teste en isolation** (sans DB), pas teste via le pipeline Celery
- Stage 6 (DISCOVERING_COMPETITORS) : necessite DB + spaCy NER
- Stage 7 (RECOMMENDING) : necessite DB + Mistral API key
- Stage 8 (COMPLETED) : necessite DB

**Pour tester :** Configurer `DATABASE_URL` (Supabase) et au moins `OPENAI_API_KEY` + `MISTRAL_API_KEY` dans `backend/.env`.

### 3. SomScorer dans le pipeline reel

**Raison :** Le branchement dans `audit_tasks.py` (extraction `visibility_score_data` + registration SomScorer + passage au orchestrator) n'est pas teste end-to-end car il necessite une base de donnees pour persister les `CriterionResult` et un `VisibilityScore` reel.

**Ce qui EST teste :** Le scorer lui-meme (25 unit tests), l'injection des donnees dans l'orchestrator (modification validee par les tests orchestrator), le scoring live avec donnees simulees (4 tests).

**Pour tester le branchement reel :** Lancer un audit complet via `POST /api/v1/audit/` avec DB + API keys configurees, puis verifier que COMP1 apparait dans `SELECT * FROM criterion_results WHERE criterion_id = 'COMP1'`.

### 4. C9 — Server-Side Rendering (Playwright)

**Raison :** Playwright browsers non installes sur cette machine (`playwright install` necessaire). Le critere retourne `_not_checked` (non penalisant).

**Pour tester :** `playwright install` puis relancer les tests.

### 5. SD12/SD13 — llms.txt / llms-full.txt

**Raison :** Le scorer cherche `https://{domain}/llms.txt` (HTTPS) mais le site de test est en HTTP sur localhost. Le handshake SSL echoue. En production sur un vrai domaine HTTPS, ca fonctionne correctement.

**Pour tester :** Lancer sur un vrai domaine HTTPS qui a un fichier llms.txt.

### 6. Frontend

**Raison :** Hors scope de ce changement (backend only). Le frontend consomme les resultats via l'API — le critere COMP1 sera automatiquement affiche dans CriterionDrilldown si le pipeline complet tourne.

---

## Fichiers modifies/crees

| Fichier | Action | Lignes |
|---------|--------|--------|
| `backend/app/services/scoring/som_scorer.py` | CREE | 73 |
| `backend/app/services/scoring/scoring_orchestrator.py` | MODIFIE | +6 lignes (kwarg + injection) |
| `backend/app/tasks/audit_tasks.py` | MODIFIE | +10 lignes (extraction + registration + passage) |
| `backend/app/services/scoring/__init__.py` | MODIFIE | +2 lignes (export) |
| `backend/tests/test_live_scoring.py` | CREE | 280 |
| `test-site/` | CREE | Site de test (4 fichiers HTML/txt) |

---

## Commande pour reproduire les tests

```bash
# Prerequis : lancer le site de test
cd test-site && python3 -m http.server 9999 &

# Tests unitaires SomScorer
cd backend && source venv/bin/activate
pytest tests/test_som_scorer.py -v

# Tests orchestrator (pas de regression)
pytest tests/test_scoring_orchestrator.py -v

# Tests live sur le site de test
pytest tests/test_live_scoring.py -v -s

# Tout ensemble
pytest tests/test_som_scorer.py tests/test_scoring_orchestrator.py tests/test_live_scoring.py -v
```
