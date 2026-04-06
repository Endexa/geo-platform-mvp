# Redwane — Next Direction

> **Date :** Mars 2026
> **Contexte :** Les phases 1-9 sont complètes. Le pipeline fonctionne de bout en bout.
> Ce document identifie les 5 axes prioritaires pour faire d'Endexa un outil GEO honnête et différenciant,
> avec pour chaque axe : le problème exact, ce qui existe déjà, ce qu'il faut coder, et une estimation réaliste.

---

## Diagnostic rapide

| Ce qui existe | Ce qui manque |
|--------------|---------------|
| Pipeline complet 8 étapes | Visibilité et préparation technique mélangées en 1 score |
| 61 critères techniques (crawl/content/schema/authority) | Zéro mesure de Share of Model réelle dans le score affiché |
| LLM dispatch vers 5 moteurs | Le vrai signal GEO (VisibilityScore) ne pèse que 15% du score final |
| Competitor discovery + scoring | Brand Signature Layers 2 et 4 manquantes |
| Recommendations avec code snippets | Aucun suivi de progression dans le temps (score delta entre audits) |
| Sentiment analysis des mentions | UI score unique = confusant pour l'utilisateur |

---

## Axe 1 — Refactoriser l'architecture du score

### Problème
Le score affiché dans l'UI (`optimization_score × 0.85 + visibility_score × 0.15`) mélange deux choses fondamentalement différentes :
- **Visibility Score** = "les LLMs te citent-ils ?" — c'est le vrai GEO
- **Optimization Score** = "ton site est-il préparé pour être crawlé ?" — c'est de la préparation technique

Un site bien connu avec du HTML sale peut avoir 8/100 en Optimization mais dominer tous les LLMs. Endexa l'afficherait comme mauvais. C'est un problème de crédibilité produit.

### Ce qui existe déjà
- `VisibilityScore` calculé et stocké en DB (Stage 4)
- `OptimizationScore` calculé et stocké en DB (Stage 5)
- Les deux sont déjà retournés séparément dans `AuditDetailResponse`
- Le frontend a déjà deux composants distincts pour les afficher

### Ce qu'il faut coder

**Backend — `scoring_orchestrator.py`**
Supprimer la ligne :
```python
# Actuellement (ligne ~180 du scoring_orchestrator.py) :
displayed = final_score * 0.85 + visibility_score * 0.15
```
Stocker les deux scores séparément sans les blender. `Audit.optimization_score` reste le score technique. `Audit.visibility_score` (via VisibilityScore table) reste le score GEO réel.

**Backend — `audit.py` (schéma)**
Remplacer `overall_score` par deux champs explicites dans `AuditDetailResponse` :
```python
geo_visibility_score: int      # 0-100 — "Les LLMs te citent"
geo_readiness_score: int       # 0-100 — "Ton site est prêt"
geo_combined_score: int        # 0-100 — moyenne simple des deux pour un KPI unique
```

**Frontend — `audit/[id].vue`**
Afficher deux jauges côte à côte avec des labels clairs :
- **Visibilité IA** (étoile) — "Cité dans X% des réponses LLM"
- **Préparation technique** (engrenage) — "X/61 critères validés"
- Un score combiné optionnel en titre de page

### Estimation
- Backend : **2-3h** (refactoring schéma + suppression du blend)
- Frontend : **3-4h** (composant dual-gauge + labels)
- **Total : 1 jour**

---

## Axe 2 — Share of Model comme KPI central

### Problème
Le Share of Model (SoM) — "sur 12 questions posées à ChatGPT sur mon secteur, combien de fois mon nom apparaît ?" — est **la** métrique GEO fondamentale. Elle existe partiellement dans le code (les données sont là dans la DB) mais n'est pas exposée comme KPI de premier plan.

Actuellement le `VisibilityScore` calcule un score composite (40% rate + 30% position + 30% prominence) qui noie l'information brute. L'utilisateur veut voir : "**GPT te mentionne dans 7/12 requêtes (58%). Perplexity : 10/12 (83%). Claude : 3/12 (25%).**"

### Ce qui existe déjà
- `EngineResponse` en DB avec `engine` et `response_text`
- `BrandMention` en DB avec `engine_response_id`
- `AuditQuery` en DB avec `audit_id`
- Le calcul `responses_with_mention / total_responses` est faisable avec une query SQL simple
- `per_engine_scores` dans `VisibilityScore` stocke déjà `queries_sent` et `queries_with_mentions`

### Ce qu'il faut coder

**Backend — nouveau endpoint ou enrichissement de `GET /audit/{id}`**
```python
# Dans AuditDetailResponse, ajouter :
share_of_model: {
    "openai":     {"queries_tested": 12, "mentions": 7,  "som_pct": 58.3},
    "anthropic":  {"queries_tested": 12, "mentions": 3,  "som_pct": 25.0},
    "perplexity": {"queries_tested": 12, "mentions": 10, "som_pct": 83.3},
    "gemini":     {"queries_tested": 12, "mentions": 5,  "som_pct": 41.7},
}
```
Le calcul est déjà fait dans `ScoringService.compute_audit_score()` — il suffit d'exposer les données brutes `queries_with_mentions` et `queries_sent` qui sont déjà dans `per_engine_scores`.

**Frontend — composant `ShareOfModelCard.vue`**
Un tableau simple : moteur | requêtes testées | fois cité | SoM % | barre de progression colorée (rouge < 30%, orange 30-60%, vert > 60%).

**Backend — `GET /dashboard/overview`**
Ajouter `avg_som_per_engine` sur les 30 derniers jours pour voir la progression dans le temps.

### Estimation
- Backend : **3-4h** (exposition des données existantes, calcul SoM dans dashboard)
- Frontend : **4-5h** (composant + intégration dashboard)
- **Total : 1.5 jours**

---

## Axe 3 — Score Delta entre audits (progression dans le temps)

### Problème
Un utilisateur qui lance un 2ème audit après avoir corrigé ses schemas JSON-LD ne peut pas voir si son score a progressé. Il n'y a aucune comparaison audit N vs audit N-1. C'est un problème de rétention majeur — sans progression visible, l'utilisateur n'a pas de raison de relancer un audit.

### Ce qui existe déjà
- `Audit` table avec `user_id`, `domain`, `optimization_score`, `created_at`
- `VisibilityScore` table liée à chaque audit
- `TrendChart` dans le dashboard affiche déjà une courbe de score dans le temps
- `DashboardService` agrège déjà des historiques

### Ce qu'il faut coder

**Backend — `GET /audit/{id}` enrichissement**
Avant de retourner les résultats, chercher l'audit précédent du même domaine/user et calculer les deltas :
```python
prev_audit = db.query(Audit)\
    .filter(Audit.user_id == user_id, Audit.domain == domain, Audit.id != audit_id)\
    .order_by(Audit.created_at.desc()).first()

score_delta = {
    "optimization": current.optimization_score - prev.optimization_score,
    "visibility": current_visibility - prev_visibility,
    "prev_audit_id": str(prev_audit.id),
    "prev_audit_date": prev_audit.created_at,
}
```

**Backend — enrichissement des `AuditRecommendation`**
Lors de `RecommendationEngine.generate_recommendations()`, vérifier si ce critère avait déjà une recommandation dans l'audit précédent et s'il a été marqué `done`. Ajouter `was_fixed_since_last_audit: bool` sur chaque recommandation.

**Frontend — `AuditResults.vue`**
Afficher un badge "+12 pts" en vert ou "-5 pts" en rouge à côté de chaque score. Section "Progrès depuis le dernier audit" en haut des recommandations.

### Estimation
- Backend : **4-5h** (delta calculation + enrichissement reco)
- Frontend : **3-4h** (badges delta + section progrès)
- **Total : 1.5 jours**

---

## Axe 4 — Brand Signature Engine : Layers 2 et 4

### Problème
Le Brand Signature Engine est le module le plus différenciant d'Endexa — il n'existe nulle part ailleurs sur le marché. Actuellement seules les Layers 1 (règles) et 3 (pgvector cosine) fonctionnent. Les Layers 2 et 4 sont documentées mais pas codées.

### Ce qui existe déjà
```
Layer 1 : RULES ENGINE        ✅ brand_voice.py — forbidden words, required phrases, regex
Layer 2 : STATISTICAL         ❌ manquante
Layer 3 : SEMANTIC            ✅ brand_voice.py — pgvector cosine similarity (OpenAI text-embedding-3-small)
Layer 4 : LLM DEEP ANALYSIS   ❌ manquante
```
- `BrandVoiceConfig`, `VoiceVector`, `VoiceRule` models en DB
- `BrandVoiceService.process_knowledge_base()` chunke et vectorise le corpus de marque
- `BrandVoiceService.check_voice()` appelle layers 1 et 3
- Score formula actuellement : `rules×0.2 + stats×0.3 + semantic×0.5` (stats = 0 car layer 2 absente)

### Ce qu'il faut coder

**Layer 2 — Statistical Fingerprint (`brand_voice.py`)**
```python
def _check_statistical_layer(self, text: str, config: BrandVoiceConfig) -> float:
    """Compare statistical fingerprint of text vs brand corpus baseline."""
    import textstat
    import statistics

    # Metrics to compare
    metrics = {
        "avg_sentence_length": textstat.avg_sentence_length(text),
        "flesch_score": textstat.flesch_reading_ease(text),
        "syllable_ratio": textstat.syllable_count(text) / max(len(text.split()), 1),
        "type_token_ratio": len(set(text.lower().split())) / max(len(text.split()), 1),
    }

    # Compare against stored baseline in BrandVoiceConfig.statistical_baseline (JSONB)
    baseline = config.statistical_baseline or {}
    if not baseline:
        return 0.5  # No baseline yet

    deviations = []
    for key, value in metrics.items():
        if key in baseline:
            base_val = baseline[key]
            deviation = abs(value - base_val) / max(base_val, 0.001)
            deviations.append(min(deviation, 1.0))

    avg_deviation = statistics.mean(deviations) if deviations else 0.5
    return 1.0 - avg_deviation  # Higher = more similar to brand voice
```
Nécessite : ajouter `statistical_baseline JSONB` sur `BrandVoiceConfig`. Calculer le baseline lors du `process_knowledge_base()`.

**Layer 4 — LLM Deep Analysis (`brand_voice.py`)**
```python
async def _check_llm_layer(self, text: str, config: BrandVoiceConfig,
                             layer3_score: float) -> dict:
    """On-demand LLM analysis — only called when layer3_score is ambiguous (0.35-0.65)."""
    if not settings.OPENAI_API_KEY:
        return {"score": layer3_score, "explanation": None, "examples": []}

    # Retrieve top 3 brand examples from pgvector
    examples = await self._get_similar_chunks(text, config_id=config.id, top_k=3)

    prompt = f"""You are a brand voice consistency expert.
Brand voice description: {config.description or "Not provided"}
Brand examples:
{chr(10).join(f'- "{e}"' for e in examples)}

Submitted text:
"{text[:1000]}"

Rate how well the submitted text matches the brand voice on a scale of 0-100.
Return JSON: {{"score": int, "explanation": str, "matches": [str], "mismatches": [str]}}"""

    response = litellm.completion(
        model="openai/gpt-4o-mini",
        api_key=settings.OPENAI_API_KEY,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    result = json.loads(response.choices[0].message.content)
    return {"score": result["score"] / 100, "explanation": result["explanation"],
            "matches": result.get("matches", []), "mismatches": result.get("mismatches", [])}
```

**Score formula finale :**
```python
# Fast mode (layers 1-3):
score = rules×0.2 + stats×0.3 + semantic×0.5

# Deep mode (all 4, only when semantic is ambiguous):
if 0.35 <= semantic_score <= 0.65:
    llm = await _check_llm_layer(...)
    score = rules×0.15 + stats×0.20 + semantic×0.35 + llm×0.30
```

### Estimation
- Layer 2 (statistical) : **4-5h** (calcul baseline, migration DB, intégration)
- Layer 4 (LLM) : **5-6h** (prompt engineering, conditional trigger, UI explanation)
- **Total : 2-2.5 jours**

---

## Axe 5 — Compléter les 3 modules GEO absents du scoring

### Problème
Le scoring actuel couvre uniquement ce qu'on peut mesurer en crawlant le site (technique + contenu + schema + autorité de base). Il manque complètement :
- **BV — Brand Visibility** : est-ce que la marque existe dans les sources que les LLMs connaissent (KG, Wikidata, Reddit, Wikipedia) ?
- **COMP — Competitive** : Share of Model par moteur (données en DB mais pas dans le score)
- **UX** : Core Web Vitals réels (PageSpeed API existe dans `authority_scorer.py` mais limité au LCP)

Ces trois modules représentent les signaux les plus directement liés à la visibilité GEO réelle.

### Ce qui existe déjà
- `AuthorityScorer._check_knowledge_graph()` appelle déjà l'API KG Google (A3)
- `AuthorityScorer._check_wikidata()` appelle déjà l'API Wikidata SPARQL (A4)
- `AuthorityScorer._check_wikipedia()` appelle déjà l'API Wikipedia (A5)
- `AuthorityScorer._check_cwv()` appelle déjà PageSpeed Insights (S11, LCP uniquement)
- `VisibilityScore.per_engine_scores` contient déjà les données SoM brutes
- `DiscoveredCompetitor.queries_mentioned_in` contient le SoM concurrentiel

### Ce qu'il faut coder

**Module BV — 5 points prioritaires à ajouter dans `AuthorityScorer`**

Les critères A3/A4/A5 existent mais ne sont pas pondérés de façon adéquate. Il faut ajouter :

| Critère | Ce qui manque | Implémentation |
|---------|---------------|----------------|
| `BV-Reddit` | Volume de mentions Reddit sur 90j | `GET https://www.reddit.com/search.json?q={brand}&t=year` — déjà accessible sans API key |
| `BV-ReviewVolume` | Présence sur G2/Trustpilot/Capterra | Checker les sameAs links + HEAD request sur `g2.com/products/{slug}` |
| `BV-MentionVelocity` | Trend de mentions récentes | Comparer Common Crawl index dates sur le domaine (API publique) |

**Module COMP — Score de Share of Model dans l'optimization score**

Ajouter un nouveau scorer `SomScorer` qui lit les données déjà calculées :
```python
class SomScorer(BaseScorer):
    """Converts VisibilityScore data into a COMP category score (0-100)."""

    async def score_page(self, page_data: dict) -> list[ScoringCriterionResult]:
        audit_id = page_data.get("audit_id")
        visibility_data = page_data.get("visibility_score_data", {})

        # Extract per-engine SoM percentages
        per_engine = visibility_data.get("per_engine_scores", {})
        som_scores = []
        for engine, data in per_engine.items():
            if isinstance(data, dict) and "queries_with_mentions" in data:
                som = data["queries_with_mentions"] / max(data["queries_sent"], 1)
                som_scores.append(som)

        avg_som = sum(som_scores) / len(som_scores) if som_scores else 0
        score = int(avg_som * 100)

        return [ScoringCriterionResult(
            criterion_id="COMP1",
            criterion_name="Average Share of Model across AI engines",
            score=score,
            human_summary=f"Brand cited in {score}% of AI responses on average",
            evidence={"per_engine_som": per_engine},
        )]
```

Ajouter `"comp": 0.15` dans `CATEGORY_WEIGHTS` et réduire `authority` de 0.15 à 0.10 pour garder la somme à 1.0.

**Module UX — CLS et FCP dans PageSpeed**

Dans `authority_scorer.py._check_cwv()`, actuellement seul LCP est extrait. Étendre :
```python
# Ajouter CLS et FCP
cls_value = audits.get("cumulative-layout-shift", {}).get("numericValue", 0)
fcp_ms = audits.get("first-contentful-paint", {}).get("numericValue", 0)
# CLS < 0.1 = bon, > 0.25 = mauvais
# FCP < 1800ms = bon, > 3000ms = mauvais
```

### Estimation
- BV additions (Reddit + Review + Velocity) : **5-6h**
- SomScorer COMP : **4h** (nouveau scorer + reconfiguration poids)
- UX CLS/FCP : **2h** (extension de l'appel PageSpeed existant)
- **Total : 2.5-3 jours**

---

## Récapitulatif et ordre d'exécution

| Axe | Impact produit | Effort | Ordre |
|-----|---------------|--------|-------|
| **Axe 1** — Découpler les deux scores | 🔴 Critique — crédibilité produit | 1 jour | **1er** |
| **Axe 2** — Share of Model comme KPI | 🔴 Critique — valeur principale | 1.5 jours | **2ème** |
| **Axe 3** — Delta de progression | 🟠 Important — rétention | 1.5 jours | **3ème** |
| **Axe 5** — Modules BV/COMP/UX | 🟠 Important — profondeur GEO | 2.5 jours | **4ème** |
| **Axe 4** — Brand Signature L2/L4 | 🟡 Différenciant — feature unique | 2.5 jours | **5ème** |

**Total estimé : ~9 jours de développement**

---

## Ce que ça donnera à la fin

```
AVANT (aujourd'hui)
  Score : 43/100
  (mélange incompréhensible de technique + visibilité)

APRÈS (axes 1-3 implémentés)
  ┌─────────────────────────────────────────────────┐
  │  Visibilité IA        43/100   (+8 vs dernier)  │
  │  ChatGPT    58%  ████████░░                     │
  │  Perplexity 83%  █████████████                  │
  │  Claude     25%  ████░░░░░░░                    │
  │                                                 │
  │  Préparation technique  61/100  (+12 vs dernier)│
  │  Crawlabilité    72%   ████████████             │
  │  Contenu         38%   ██████░░░░               │
  │  Données struct. 71%   ████████████             │
  │  Autorité        55%   █████████░░              │
  └─────────────────────────────────────────────────┘
```

C'est la différence entre un outil de diagnostic technique et un vrai outil GEO.

---

## Fichiers clés à modifier par axe

| Axe | Fichiers backend | Fichiers frontend |
|-----|-----------------|-------------------|
| Axe 1 | `scoring_orchestrator.py`, `schemas/audit.py`, `api/audit.py` | `pages/audit/[id].vue`, `components/AuditResults.vue` |
| Axe 2 | `scoring_service.py`, `schemas/audit.py`, `api/dashboard.py` | `components/ShareOfModelCard.vue`, `pages/dashboard.vue` |
| Axe 3 | `api/audit.py`, `services/recommendation_engine.py`, `models/audit.py` | `components/AuditResults.vue`, `components/RecommendationCard.vue` |
| Axe 4 | `services/brand_voice.py`, `models/brand_voice.py`, migration | `pages/brand-voice.vue`, `components/BrandVoiceResult.vue` |
| Axe 5 | `scoring/authority_scorer.py`, nouveau `scoring/som_scorer.py`, `scoring_orchestrator.py` | `components/CategoryBreakdown.vue` |
