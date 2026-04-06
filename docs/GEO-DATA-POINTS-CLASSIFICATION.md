# Classification et Spécifications des 109 Data Points GEO

> **Document :** Analyse complète des 109 points de mesure d'Endexa
> **Date :** Mars 2026
> **Objectif :** Définir le rôle, l'impact GEO et l'implémentation exacte de chaque point dans le système Endexa
> **Référence architecture :** `geo_data_points/measurements/` + `backend/app/services/`

---

## Conventions

### Format de retour universel

Chaque script `measure()` doit retourner :
```python
{
    "score": int,          # 0-100
    "comment": str,        # Phrase lisible, affichée dans l'UI
    "metadata": dict       # Données brutes pour debug/export
}
```

### Signature obligatoire
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
```

### Kwargs disponibles selon le contexte
```python
kwargs.get("rendered_html")   # HTML après rendu JS (Playwright)
kwargs.get("raw_html")        # HTML brut sans JS
kwargs.get("domain")          # Domaine extrait de l'URL
kwargs.get("brand_name")      # Nom de la marque auditée
kwargs.get("keywords")        # Mots-clés fournis par l'utilisateur
kwargs.get("competitors")     # Liste des domaines concurrents
```

### Barème de score
| Score | Signification |
|-------|--------------|
| 90-100 | Excellent — aucune action requise |
| 70-89 | Bon — améliorations mineures |
| 50-69 | Moyen — corrections recommandées |
| 30-49 | Faible — problèmes importants |
| 0-29 | Critique — bloque la visibilité AI |

### Priorités
| Priorité | Label | Signification |
|----------|-------|---------------|
| P0 | 🔴 Critique | Bloque directement la visibilité AI si absent |
| P1 | 🟠 Important | Impact fort et direct sur les citations LLM |
| P2 | 🟡 Utile | SEO classique avec bénéfice GEO indirect |
| P3 | 🟢 Conditionnel | Nécessite accès analytics externe |
| P4 | ⚪ Externe | Nécessite API tierce payante |
| P5 | ⛔ Marginal | À déprécier — impact GEO non prouvé |

---

## Table des matières

1. [Module WI — Infrastructure Web (35 points)](#module-wi--infrastructure-web)
2. [Module CNT — Contenu (23 points)](#module-cnt--contenu)
3. [Module BV — Visibilité de Marque (15 points)](#module-bv--visibilité-de-marque)
4. [Module SEO — Référencement (13 points)](#module-seo--référencement)
5. [Module UX — Expérience Utilisateur (7 points)](#module-ux--expérience-utilisateur)
6. [Module COMP — Compétitif (10 points)](#module-comp--compétitif)
7. [Module LEG — Légal (6 points)](#module-leg--légal)
8. [Synthèse et roadmap d'implémentation](#synthèse-et-roadmap)

---

## Module WI — Infrastructure Web

> 35 data points | Mesure la capacité technique du site à être crawlé et compris par les robots IA.

---

### WI-001 — Robots.txt GPTBot
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie si le fichier `robots.txt` autorise l'accès au crawler d'OpenAI (`GPTBot`). GPTBot est utilisé pour entraîner les modèles GPT et alimenter ChatGPT Search.

**Impact GEO :** Si GPTBot est bloqué, OpenAI ne peut pas indexer le contenu du site. Le site sera absent des réponses de ChatGPT pour toutes les requêtes où il serait pertinent. Aucune autre optimisation ne compensera ce blocage.

**Implémentation Endexa :**
```python
import urllib.robotparser
import aiohttp

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    robots_url = url.rstrip('/') + '/robots.txt'
    rp = urllib.robotparser.RobotFileParser()
    # Fetch robots.txt asynchronously
    async with aiohttp.ClientSession() as session:
        async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            content = await resp.text()
    rp.parse(content.splitlines())
    allowed = rp.can_fetch("GPTBot", url)
    score = 100 if allowed else 0
    return {
        "score": score,
        "comment": f"GPTBot {'autorisé' if allowed else 'bloqué'} dans robots.txt",
        "metadata": {"bot": "GPTBot", "robots_url": robots_url, "allowed": allowed}
    }
```

---

### WI-002 — Robots.txt ClaudeBot
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie si `ClaudeBot` (Anthropic) est autorisé dans `robots.txt`. Utilisé pour alimenter Claude.ai.

**Impact GEO :** Identique à GPTBot mais pour l'écosystème Anthropic/Claude. Avec l'adoption croissante de Claude en entreprise, ce signal prend de l'importance.

**Implémentation Endexa :** Identique à WI-001, remplacer `"GPTBot"` par `"ClaudeBot"`.

---

### WI-003 — Robots.txt PerplexityBot
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie l'accès de `PerplexityBot`. Perplexity est l'un des moteurs génératifs les plus actifs en crawl web, avec un modèle RAG (Retrieval-Augmented Generation) qui cite systématiquement ses sources.

**Impact GEO :** Perplexity cite les sources dans 100% de ses réponses par design architectural. Bloquer PerplexityBot = zéro citation sur Perplexity.

**Implémentation Endexa :** Identique à WI-001, remplacer par `"PerplexityBot"`.

---

### WI-004 — Robots.txt CCBot
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie l'accès de `CCBot` (Common Crawl). Common Crawl est le dataset d'entraînement utilisé par la majorité des LLMs open-source et commerciaux.

**Impact GEO :** Common Crawl alimente LLaMA, Mistral, Falcon et de nombreux modèles. Bloquer CCBot signifie être absent des modèles entraînés sur ces données — un impact différé mais structurel sur la notoriété de marque dans les LLMs.

**Implémentation Endexa :** Identique à WI-001, remplacer par `"CCBot"`.

---

### WI-005 — Robots.txt Google-Extended
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Vérifie l'accès de `Google-Extended`, le crawler de Google pour ses produits IA (Gemini, AI Overviews dans Search).

**Impact GEO :** Google AI Overviews (anciennement SGE) utilise `Google-Extended` séparément de Googlebot. Un site peut être indexé dans Google Search mais exclu de Google AI.

**Implémentation Endexa :** Identique à WI-001, remplacer par `"Google-Extended"`.

---

### WI-006 — Sitemap Lastmod
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Vérifie la présence et la qualité des balises `<lastmod>` dans le sitemap XML. `Lastmod` indique aux crawlers la date de dernière modification de chaque page.

**Impact GEO :** Les LLMs priorisent le contenu frais. Un sitemap avec `lastmod` récents signale au crawler AI que le site est actif et maintenu, augmentant la fréquence d'indexation.

**Implémentation Endexa :**
```python
import aiohttp
from xml.etree import ElementTree as ET
from datetime import datetime, timezone

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    sitemap_url = url.rstrip('/') + '/sitemap.xml'
    async with aiohttp.ClientSession() as session:
        async with session.get(sitemap_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return {"score": 0, "comment": "Sitemap introuvable", "metadata": {}}
            content = await resp.text()
    root = ET.fromstring(content)
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = root.findall('.//sm:url', ns)
    lastmods = [u.find('sm:lastmod', ns) for u in urls]
    lastmods = [l.text for l in lastmods if l is not None]
    coverage = len(lastmods) / max(len(urls), 1)
    # Check freshness: % of lastmods within 90 days
    now = datetime.now(timezone.utc)
    fresh = sum(1 for l in lastmods if (now - datetime.fromisoformat(l.replace('Z','+00:00'))).days <= 90)
    freshness_ratio = fresh / max(len(lastmods), 1)
    score = int((coverage * 0.5 + freshness_ratio * 0.5) * 100)
    return {
        "score": score,
        "comment": f"{len(lastmods)}/{len(urls)} URLs avec lastmod, {fresh} récentes (<90j)",
        "metadata": {"total_urls": len(urls), "with_lastmod": len(lastmods), "fresh_count": fresh}
    }
```

---

### WI-007 — Status Code 200
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie que l'URL principale retourne un HTTP 200. Détecte les erreurs 4xx/5xx, redirections en boucle, ou pages qui retournent 200 avec contenu d'erreur.

**Impact GEO :** Un crawler AI qui reçoit un code non-200 abandonne la page immédiatement. Les LLMs ne peuvent pas citer une page inaccessible.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15),
                               allow_redirects=True) as resp:
            status = resp.status
            final_url = str(resp.url)
    redirect_count = 0  # count via history
    score = 100 if status == 200 else (50 if status in [301, 302] else 0)
    return {
        "score": score,
        "comment": f"HTTP {status}",
        "metadata": {"status_code": status, "final_url": final_url}
    }
```

---

### WI-008 — Response Time (TTFB)
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Mesure le Time To First Byte (TTFB) — délai entre la requête et le premier octet de réponse. Déjà implémenté (WI-004 dans l'ancien système).

**Impact GEO :** Les crawlers AI ont des timeouts stricts (souvent 5-10s). Un TTFB > 3s risque un timeout, surtout lors de crawls en masse. Les agents AI autonomes sont encore plus sensibles à la latence.

**Implémentation Endexa :**
```python
import time

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    start = time.monotonic()
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            ttfb = time.monotonic() - start
            await resp.read()
    if ttfb < 0.8:
        score = 100
    elif ttfb < 1.5:
        score = 80
    elif ttfb < 3.0:
        score = 50
    else:
        score = max(0, int(100 - ttfb * 15))
    return {
        "score": score,
        "comment": f"TTFB : {ttfb:.2f}s",
        "metadata": {"ttfb_seconds": round(ttfb, 3)}
    }
```

---

### WI-009 — JS Dependency
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Détecte si le contenu principal de la page dépend de JavaScript pour être rendu (SPA React/Vue/Angular sans SSR). Compare la quantité de texte dans le HTML brut vs le HTML rendu.

**Impact GEO :** C'est **le problème le plus courant et le plus dévastateur**. GPTBot, ClaudeBot, et la majorité des crawlers AI ne sont pas des navigateurs — ils ne peuvent pas exécuter du JavaScript. Une SPA sans SSR affiche un `<div id="root"></div>` vide aux crawlers. Le contenu est invisible, même si le site fonctionne parfaitement pour les utilisateurs.

**Implémentation Endexa :**
```python
from bs4 import BeautifulSoup

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    raw_html = kwargs.get("raw_html", "")
    rendered_html = kwargs.get("rendered_html", "")
    # Extract visible text from both
    raw_text = BeautifulSoup(raw_html, 'lxml').get_text(separator=' ', strip=True)
    rendered_text = BeautifulSoup(rendered_html, 'lxml').get_text(separator=' ', strip=True) if rendered_html else raw_text
    raw_words = len(raw_text.split())
    rendered_words = len(rendered_text.split())
    ratio = raw_words / max(rendered_words, 1)
    # If raw has < 30% of rendered content, heavy JS dependency
    if ratio >= 0.8:
        score = 100
    elif ratio >= 0.5:
        score = 60
    elif ratio >= 0.3:
        score = 20
    else:
        score = 0
    return {
        "score": score,
        "comment": f"Contenu HTML brut : {raw_words} mots / rendu JS : {rendered_words} mots",
        "metadata": {"raw_words": raw_words, "rendered_words": rendered_words, "ratio": round(ratio, 2)}
    }
```
> **Note Endexa :** Le `rendered_html` est produit par `PlaywrightCrawler` dans `crawler_service.py`. S'assurer que les deux variants sont passés en `kwargs` depuis `audit_service.py`.

---

### WI-010 — Dynamic Rendering
**Priorité :** 🔴 P0 Critique | **Automation :** Semi

**Rôle :** Vérifie si le site implémente une solution de pre-rendering ou SSR pour les bots (ex : Prerender.io, Next.js SSR, Nuxt SSR, Vite SSG).

**Impact GEO :** Complément de WI-009. Un site peut avoir du contenu JS-dépendant mais l'exposer correctement via dynamic rendering. Ce point récompense les solutions de contournement.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    raw_html = kwargs.get("raw_html", "")
    soup = BeautifulSoup(raw_html, 'lxml')
    signals = {
        "next_data": bool(soup.find(id='__NEXT_DATA__')),
        "nuxt_data": '__NUXT__' in raw_html or 'data-n-head' in raw_html,
        "prerender_header": False,  # check X-Prerender header
        "ssr_meta": bool(soup.find('meta', attrs={'name': 'generator'})),
        "full_content": len(soup.get_text().split()) > 200,
    }
    score_map = {"next_data": 30, "nuxt_data": 30, "prerender_header": 25, "full_content": 40, "ssr_meta": 5}
    score = min(100, sum(v for k, v in score_map.items() if signals.get(k)))
    return {
        "score": score,
        "comment": f"Dynamic rendering détecté : {[k for k,v in signals.items() if v]}",
        "metadata": signals
    }
```

---

### WI-011 — Schema.org Organization
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie la présence et la qualité d'un JSON-LD `@type: Organization` avec les propriétés minimales : `name`, `url`, `logo`, `sameAs`. Déjà implémenté (WI-003).

**Impact GEO :** BrightEdge démontre que les pages avec `Organization` schema ont 2.3-2.5x plus de chances d'apparaître dans les AI Overviews Google. Les LLMs utilisent ce schema pour identifier et désambiguïser les entités.

**Implémentation Endexa :**
```python
import json
from bs4 import BeautifulSoup

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    scripts = soup.find_all('script', type='application/ld+json')
    org_schemas = []
    for s in scripts:
        try:
            data = json.loads(s.string or '{}')
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') in ['Organization', 'Corporation', 'LocalBusiness']:
                        org_schemas.append(item)
            elif data.get('@type') in ['Organization', 'Corporation', 'LocalBusiness']:
                org_schemas.append(data)
        except (json.JSONDecodeError, AttributeError):
            pass
    if not org_schemas:
        return {"score": 0, "comment": "Aucun schema Organization trouvé", "metadata": {}}
    org = org_schemas[0]
    fields = {"name": 10, "url": 10, "logo": 15, "sameAs": 25, "description": 10, "contactPoint": 10, "address": 10, "foundingDate": 10}
    score = sum(v for k, v in fields.items() if org.get(k))
    return {
        "score": min(score, 100),
        "comment": f"Organization schema présent, champs : {[k for k in fields if org.get(k)]}",
        "metadata": {"schema_found": True, "fields_present": [k for k in fields if org.get(k)]}
    }
```

---

### WI-012 — Schema.org sameAs
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Vérifie la présence et la qualité des liens `sameAs` dans les schemas JSON-LD, notamment vers Wikipedia, Wikidata, LinkedIn, Twitter/X, GitHub.

**Impact GEO :** `sameAs` crée le lien entre l'entité schema et ses représentations externes. Les LLMs utilisent ces liens pour résoudre l'identité d'une marque et réduire les hallucinations. Un `sameAs` vers Wikipedia multiplie les chances d'apparaître dans le Knowledge Graph Google.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    same_as_links = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
            if isinstance(data, dict) and 'sameAs' in data:
                same_as_links.extend(data['sameAs'] if isinstance(data['sameAs'], list) else [data['sameAs']])
        except (json.JSONDecodeError, AttributeError):
            pass
    high_value = ['wikipedia.org', 'wikidata.org', 'linkedin.com', 'twitter.com', 'x.com']
    matched = [h for h in high_value if any(h in link for link in same_as_links)]
    score = min(100, len(same_as_links) * 15 + len(matched) * 10)
    return {
        "score": score,
        "comment": f"{len(same_as_links)} liens sameAs dont {len(matched)} haute valeur",
        "metadata": {"same_as_links": same_as_links, "high_value_matched": matched}
    }
```

---

### WI-013 — Schema JSON-LD Nesting
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Évalue la profondeur et la cohérence des schemas JSON-LD (relations entre entités, `@graph`, types imbriqués).

**Impact GEO :** Un JSON-LD bien structuré avec des entités liées (ex: `WebPage` → `author` → `Person` → `Organization`) permet aux LLMs de construire un graphe de connaissances complet sur le site.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    schemas = []
    for s in soup.find_all('script', type='application/ld+json'):
        try:
            schemas.append(json.loads(s.string or '{}'))
        except (json.JSONDecodeError, AttributeError):
            pass
    if not schemas:
        return {"score": 0, "comment": "Aucun JSON-LD trouvé", "metadata": {}}
    def count_depth(obj, depth=0):
        if isinstance(obj, dict):
            return max((count_depth(v, depth+1) for v in obj.values()), default=depth)
        elif isinstance(obj, list):
            return max((count_depth(i, depth) for i in obj), default=depth)
        return depth
    max_depth = max(count_depth(s) for s in schemas)
    type_count = len(schemas)
    has_graph = any('@graph' in s for s in schemas)
    score = min(100, type_count * 15 + max_depth * 10 + (20 if has_graph else 0))
    return {
        "score": score,
        "comment": f"{type_count} schemas JSON-LD, profondeur max {max_depth}",
        "metadata": {"schema_count": type_count, "max_depth": max_depth, "has_graph": has_graph}
    }
```

---

### WI-014 — Common Crawl Presence
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Vérifie si le domaine est présent dans l'index Common Crawl via l'API publique `index.commoncrawl.org`. Common Crawl archive le web depuis 2008 et est la source d'entraînement de la majorité des LLMs.

**Impact GEO :** Un domaine absent de Common Crawl n'existe pas dans les datasets d'entraînement. Impact direct sur la connaissance que les LLMs ont de la marque.

**Implémentation Endexa :**
```python
from urllib.parse import urlparse

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    domain = urlparse(url).netloc
    cc_index_url = f"https://index.commoncrawl.org/CC-MAIN-2024-51-index?url={domain}/*&output=json&limit=5"
    async with aiohttp.ClientSession() as session:
        async with session.get(cc_index_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            content = await resp.text()
    lines = [l for l in content.strip().split('\n') if l]
    found = len(lines) > 0
    score = 100 if found else 0
    return {
        "score": score,
        "comment": f"Domaine {'présent' if found else 'absent'} dans Common Crawl",
        "metadata": {"domain": domain, "records_found": len(lines)}
    }
```

---

### WI-015 — H-Tag Hierarchy
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Analyse la hiérarchie des balises de titre (H1-H6) : unicité du H1, structure séquentielle, ratio headings/contenu.

**Impact GEO :** Les LLMs extraient la structure des pages principalement via les headings. Une hiérarchie H1 → H2 → H3 bien construite facilite l'extraction de faits et augmente la probabilité d'être cité comme source structurée.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    h1s = soup.find_all('h1')
    h2s = soup.find_all('h2')
    h3s = soup.find_all('h3')
    issues = []
    score = 100
    if len(h1s) == 0:
        issues.append("H1 manquant"); score -= 40
    elif len(h1s) > 1:
        issues.append(f"{len(h1s)} H1 (doit être unique)"); score -= 20
    if len(h2s) == 0:
        issues.append("Aucun H2"); score -= 20
    if len(h3s) > 0 and len(h2s) == 0:
        issues.append("H3 sans H2 parent"); score -= 10
    return {
        "score": max(0, score),
        "comment": f"H1:{len(h1s)}, H2:{len(h2s)}, H3:{len(h3s)}. {'; '.join(issues) if issues else 'Hiérarchie correcte'}",
        "metadata": {"h1_count": len(h1s), "h2_count": len(h2s), "h3_count": len(h3s), "issues": issues}
    }
```

---

### WI-016 — Alt Text Coverage
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Calcule le pourcentage d'images avec un attribut `alt` non vide.

**Impact GEO :** Les LLMs multimodaux (GPT-4V, Gemini) utilisent les `alt` pour comprendre le contexte visuel. Les `alt` enrichissent le contexte sémantique de la page pour les crawlers textuels.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    imgs = soup.find_all('img')
    if not imgs:
        return {"score": 100, "comment": "Aucune image trouvée", "metadata": {"images": 0}}
    with_alt = sum(1 for img in imgs if img.get('alt', '').strip())
    coverage = with_alt / len(imgs)
    score = int(coverage * 100)
    return {
        "score": score,
        "comment": f"{with_alt}/{len(imgs)} images avec alt text ({score}%)",
        "metadata": {"total_images": len(imgs), "with_alt": with_alt, "coverage_pct": score}
    }
```

---

### WI-017 — WCAG Compliance
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Évalue la conformité WCAG basique : contrastes, aria-labels, rôles sémantiques, navigation au clavier.

**Impact GEO :** L'accessibilité force une sémantique HTML propre. Les pages WCAG-conformes ont généralement un HTML plus structuré, facilitant l'extraction de contenu par les crawlers AI.

**Implémentation Endexa :** Utiliser `axe-core` via Playwright (headless) ou vérifications manuelles des signaux ARIA. Score composite sur 5 critères : `lang` attribute, aria-labels sur les forms, skip links, rôles ARIA sur la nav, images alt.

---

### WI-018 — SSL/HTTPS
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Vérifie que le site utilise HTTPS avec un certificat valide et non expiré.

**Impact GEO :** Les crawlers AI refusent les connexions HTTP non sécurisées ou avec certificats invalides. Signal E-E-A-T (trustworthiness).

**Implémentation Endexa :**
```python
import ssl, socket

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    from urllib.parse import urlparse
    from datetime import datetime
    hostname = urlparse(url).hostname
    ctx = ssl.create_default_context()
    conn = ctx.wrap_socket(socket.socket(), server_hostname=hostname)
    conn.settimeout(10)
    conn.connect((hostname, 443))
    cert = conn.getpeercert()
    conn.close()
    expire_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
    days_remaining = (expire_date - datetime.utcnow()).days
    score = 100 if days_remaining > 30 else (50 if days_remaining > 0 else 0)
    return {
        "score": score,
        "comment": f"HTTPS valide, certificat expire dans {days_remaining} jours",
        "metadata": {"days_remaining": days_remaining, "issuer": str(cert.get('issuer'))}
    }
```

---

### WI-019 — Click Depth
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Mesure la profondeur de clic depuis la homepage pour atteindre les pages importantes (combien de clics depuis `/` jusqu'aux pages de contenu).

**Impact GEO :** Les crawlers AI, comme Googlebot, limitent leur profondeur de crawl. Une page à 4+ clics de la homepage risque de ne jamais être indexée.

**Implémentation Endexa :** BFS (Breadth-First Search) sur les liens internes depuis la homepage. Retourner la profondeur moyenne et le % de pages accessibles en ≤ 3 clics.

---

### WI-020 — Orphan Pages
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Détecte les pages sans aucun lien interne entrant (pages orphelines), visibles uniquement via le sitemap.

**Impact GEO :** Les crawlers AI suivent les liens. Une page orpheline ne sera jamais crawlée via le graph de liens, même si elle est dans le sitemap.

**Implémentation Endexa :** Croiser les URLs du sitemap avec le graph des liens internes construits lors du crawl.

---

### WI-021 — Internal Link Score
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Analyse la qualité du maillage interne : nombre de liens internes par page, distribution de l'autorité de page, anchor texts descriptifs.

**Impact GEO :** Un bon maillage interne permet aux crawlers AI d'explorer l'ensemble du site en partant de la homepage. Les anchor texts descriptifs aident les LLMs à comprendre le sujet de chaque page liée.

**Implémentation Endexa :** Extraire tous les `<a href>` internes, évaluer : nombre moyen de liens par page, % avec anchor text non générique ("cliquez ici" = négatif), présence de liens vers les pages importantes.

---

### WI-022 — Broken Links (404)
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Détecte les liens internes renvoyant vers des pages 404.

**Impact GEO :** Les crawlers qui tombent sur des 404 interrompent leur exploration. Signal négatif d'autorité et de maintenance du site.

**Implémentation Endexa :** Vérifier les status HTTP de chaque lien interne trouvé lors du crawl. Score = 100 - (nb_404 / total_links * 100).

---

### WI-023 — Redirect Chains
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Détecte les chaînes de redirections (A→B→C) et les boucles de redirections.

**Impact GEO :** Chaque redirection ajoute de la latence. Une chaîne de 3+ redirections peut faire timeout un crawler AI.

**Implémentation Endexa :** Analyser `resp.history` d'aiohttp pour compter les redirections. Score basé sur la longueur max des chaînes.

---

### WI-024 — Canonical Tags
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Vérifie la présence et la cohérence des balises `<link rel="canonical">`.

**Impact GEO :** Sans canonical, les LLMs peuvent indexer plusieurs versions d'une même page (avec/sans www, avec/sans trailing slash) et diluer l'autorité. Évite le contenu dupliqué perçu.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    canonical = soup.find('link', rel='canonical')
    if not canonical:
        return {"score": 0, "comment": "Balise canonical manquante", "metadata": {}}
    href = canonical.get('href', '')
    self_referencing = url.rstrip('/') == href.rstrip('/')
    score = 100 if self_referencing else 60
    return {
        "score": score,
        "comment": f"Canonical : {href} ({'auto-référençant' if self_referencing else 'externe'})",
        "metadata": {"canonical_url": href, "self_referencing": self_referencing}
    }
```

---

### WI-025 — Hreflang Tags
**Priorité :** ⛔ P5 Marginal | **Automation :** Full

**Rôle :** Vérifie la présence des balises `hreflang` pour les sites multilingues.

**Impact GEO :** Pertinent uniquement pour les sites multilingues. Impact GEO faible — les LLMs ne différencient pas les variantes linguistiques de la même façon que Google Search.

**Implémentation Endexa :** Mesure simple : présence/absence de tags hreflang + cohérence des URLs déclarées.

---

### WI-026 — PDF Accessibility
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Détecte la présence de PDFs liés sur le site et vérifie s'ils sont accessibles (non protégés par mot de passe).

**Impact GEO :** Les crawlers AI peuvent indexer les PDFs. Des PDFs avec un contenu de qualité (whitepapers, études) sont d'excellentes sources de citation si accessibles.

**Implémentation Endexa :** Identifier les liens vers `.pdf` dans le HTML. Tenter une requête HEAD sur les PDFs. Signaler les PDFs inaccessibles.

---

### WI-027 à WI-035 — Signaux techniques (Favicon, Crawl Depth, DOM Size, Console Errors, Resource Blockage, Redirect Loops, Text-to-HTML Ratio, Data Localization, Breadcrumb Schema)
**Priorité :** ⛔ P5 Marginal (sauf Breadcrumb Schema : 🟡 P2)

**Rôle :**
- **Favicon** : Présence d'un favicon. Impact GEO nul.
- **Crawl Depth** : Nombre de pages crawlées depuis la homepage. Utile pour les audits de site.
- **DOM Size** : Taille du DOM rendu. Un DOM > 1500 nœuds ralentit le rendu.
- **Console Errors** : Erreurs JS dans la console. Symptôme de problèmes de rendu.
- **Resource Blockage** : Ressources (JS/CSS) bloquées par robots.txt.
- **Redirect Loops** : Boucles de redirection infinies. Bloquant.
- **Text-to-HTML Ratio** : % de texte vs HTML. Indicateur de contenu dilué.
- **Data Localization** : Utilisation de CDNs locaux selon la région.
- **Breadcrumb Schema** : JSON-LD `BreadcrumbList`.

**Breadcrumb Schema (P2) :** Aide les LLMs à comprendre l'arborescence du site. Implémentation identique à WI-011 mais pour `@type: BreadcrumbList`.

---

## Module CNT — Contenu

> 23 data points | Mesure la qualité et la structure du contenu pour la compréhension et la citation par les LLMs.

---

### CNT-001 — Schema FAQPage
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie la présence d'un JSON-LD `FAQPage` avec des questions/réponses structurées.

**Impact GEO :** BrightEdge mesure **3.2x** de taux de citation pour les pages avec FAQPage schema. Les LLMs extraient directement les paires Q/R pour composer leurs réponses. C'est le signal contenu le plus impactant individuellement.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    faqs = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
            if data.get('@type') == 'FAQPage':
                faqs = data.get('mainEntity', [])
        except (json.JSONDecodeError, AttributeError):
            pass
    if not faqs:
        return {"score": 0, "comment": "Aucun schema FAQPage trouvé", "metadata": {}}
    valid = [q for q in faqs if q.get('name') and q.get('acceptedAnswer', {}).get('text')]
    score = min(100, 30 + len(valid) * 10)  # 30 pts pour présence, +10 par Q/R valide
    return {
        "score": score,
        "comment": f"FAQPage présent : {len(valid)} questions valides",
        "metadata": {"faq_count": len(valid), "questions": [q.get('name','') for q in valid[:5]]}
    }
```

---

### CNT-002 — Information Gain Score
**Priorité :** 🟠 P1 Important | **Automation :** Semi

**Rôle :** Mesure si le contenu apporte des informations uniques non disponibles dans le top 5 des résultats de recherche sur le même sujet.

**Impact GEO :** Les LLMs évitent de citer du contenu générique. Un contenu qui apporte des données originales, des études primaires, ou des points de vue distinctifs a significativement plus de chances d'être référencé.

**Implémentation Endexa :** Utiliser l'embedding OpenAI `text-embedding-3-small` pour vectoriser le contenu de la page, puis calculer la distance cosinus avec les embeddings des pages concurrentes stockées en pgvector. Score = distance moyenne (plus elle est grande, plus le contenu est unique).

```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    # Requires: competitor page embeddings in pgvector
    content = kwargs.get("page_content", "")
    competitor_embeddings = kwargs.get("competitor_embeddings", [])  # List[List[float]]
    if not content or not competitor_embeddings:
        return {"score": 50, "comment": "Données insuffisantes pour calcul", "metadata": {}}
    # Get embedding for this page (use cached if available)
    from openai import AsyncOpenAI
    client = AsyncOpenAI()
    resp = await client.embeddings.create(model="text-embedding-3-small", input=content[:8000])
    page_embedding = resp.data[0].embedding
    # Cosine distances
    import numpy as np
    similarities = [np.dot(page_embedding, ce) / (np.linalg.norm(page_embedding) * np.linalg.norm(ce))
                    for ce in competitor_embeddings]
    avg_similarity = sum(similarities) / len(similarities)
    # Higher distance = more unique
    uniqueness = 1 - avg_similarity
    score = int(uniqueness * 100)
    return {
        "score": score,
        "comment": f"Unicité sémantique : {score}% (similarité moy. concurrents : {avg_similarity:.2f})",
        "metadata": {"avg_similarity": round(avg_similarity, 3), "uniqueness_score": score}
    }
```

---

### CNT-003 — Entity Density
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Mesure la densité d'entités nommées (personnes, organisations, lieux, dates, produits) dans le contenu, via spaCy NER.

**Impact GEO :** Les LLMs construisent leur compréhension du monde à partir d'entités. Un contenu riche en entités bien définies est plus facilement indexé dans la base de connaissances implicite des modèles. Recherche Princeton : +25-40% de visibilité pour les contenus avec données factuelles.

**Implémentation Endexa :**
```python
import spacy

nlp = spacy.load("en_core_web_sm")  # ou fr_core_news_sm selon la langue

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    content = kwargs.get("page_content", "")
    if not content:
        return {"score": 0, "comment": "Contenu vide", "metadata": {}}
    doc = nlp(content[:10000])
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    word_count = len(content.split())
    entity_density = len(entities) / max(word_count / 100, 1)  # entités par 100 mots
    unique_entities = len(set(e[0] for e in entities))
    # Target: 3-8 entities per 100 words
    if 3 <= entity_density <= 8:
        score = 100
    elif entity_density < 1:
        score = int(entity_density * 33)
    else:
        score = min(100, int(entity_density * 15))
    return {
        "score": score,
        "comment": f"{len(entities)} entités ({unique_entities} uniques), densité {entity_density:.1f}/100 mots",
        "metadata": {"entity_count": len(entities), "unique_count": unique_entities,
                     "density": round(entity_density, 2), "types": list(set(e[1] for e in entities))}
    }
```

---

### CNT-004 — Vector Similarity
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Mesure la similarité sémantique entre le contenu de la page et les requêtes utilisateurs cibles (keywords fournis lors de l'audit).

**Impact GEO :** Contrairement au SEO classique, les LLMs ne matchent pas sur des mots-clés exacts mais sur la proximité sémantique. Ce score mesure si la page "répond" réellement aux requêtes cibles en termes de sens.

**Implémentation Endexa :** Vectoriser le contenu de la page et les keywords via OpenAI embeddings. Calculer la similarité cosinus. Utiliser pgvector pour stocker les résultats.

---

### CNT-005 — Perplexity Score
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Calcule la "perplexité" du texte — mesure statistique de la complexité du vocabulaire et de la fluidité.

**Impact GEO :** Les LLMs préfèrent les textes avec une perplexité modérée : ni trop simples (peu informatifs) ni trop complexes (difficiles à extraire). Proxy de la lisibilité pour les modèles.

**Implémentation Endexa :** Utiliser `textstat` pour calculer un score composite. Alternativement, appeler l'API OpenAI avec `logprobs=True` sur un extrait.

---

### CNT-006 — Flesch-Kincaid
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Score de lisibilité Flesch-Kincaid (0-100). Score 60-70 = texte facile à lire.

**Impact GEO :** La recherche Princeton montre que les textes fluides et clairs ont +15-30% de visibilité dans les LLMs. Un score trop bas (jargon technique) ou trop haut (contenu simpliste) est pénalisant.

**Implémentation Endexa :**
```python
import textstat

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    content = kwargs.get("page_content", "")
    if not content or len(content.split()) < 50:
        return {"score": 50, "comment": "Contenu insuffisant pour analyse", "metadata": {}}
    fk_score = textstat.flesch_reading_ease(content)
    fk_grade = textstat.flesch_kincaid_grade(content)
    # Target: 40-70 (professional but readable)
    if 40 <= fk_score <= 70:
        score = 100
    elif 20 <= fk_score < 40:
        score = 70
    elif 70 < fk_score <= 90:
        score = 80
    else:
        score = 40
    return {
        "score": score,
        "comment": f"Flesch {fk_score:.0f}/100 (niveau {fk_grade:.1f})",
        "metadata": {"flesch_score": round(fk_score, 1), "grade_level": round(fk_grade, 1)}
    }
```

---

### CNT-007 — Content Freshness
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Détecte et évalue la fraîcheur du contenu : dates dans le texte, balises `dateModified` en schema, header `Last-Modified`.

**Impact GEO :** Les LLMs, surtout pour des requêtes factuelles, préfèrent les sources récentes. Perplexity affiche explicitement la date des sources citées. Un contenu sans date signale un manque de maintenance.

**Implémentation Endexa :**
```python
import re
from datetime import datetime, timezone

async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    signals = {}
    # 1. Schema dateModified
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
            if 'dateModified' in data:
                signals['schema_date'] = data['dateModified']
            elif 'datePublished' in data:
                signals['schema_date'] = data['datePublished']
        except (json.JSONDecodeError, AttributeError):
            pass
    # 2. Time element
    time_el = soup.find('time', attrs={'datetime': True})
    if time_el:
        signals['html_time'] = time_el.get('datetime')
    # Parse most recent date found
    best_date = signals.get('schema_date') or signals.get('html_time')
    if best_date:
        try:
            dt = datetime.fromisoformat(best_date.replace('Z', '+00:00'))
            days_old = (datetime.now(timezone.utc) - dt).days
            if days_old <= 90: score = 100
            elif days_old <= 365: score = 75
            elif days_old <= 730: score = 50
            else: score = 25
            comment = f"Contenu mis à jour il y a {days_old} jours"
        except ValueError:
            score, comment = 50, "Date détectée mais non parseable"
    else:
        score, comment = 20, "Aucune date de publication trouvée"
    return {"score": score, "comment": comment, "metadata": signals}
```

---

### CNT-008 — Citation Ratio
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Mesure le ratio de liens externes vers des sources autoritaires (Wikipedia, sites académiques, études, publications) par rapport au volume total de contenu.

**Impact GEO :** La recherche Princeton GEO démontre que **citer des sources est le facteur #1** d'amélioration de la visibilité dans les moteurs génératifs (+30-40%). Les LLMs font confiance au contenu qui lui-même cite des sources vérifiables.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    word_count = len(soup.get_text().split())
    external_links = [a.get('href','') for a in soup.find_all('a', href=True)
                      if a.get('href','').startswith('http') and urlparse(url).netloc not in a.get('href','')]
    authority_domains = ['wikipedia.org', 'scholar.google', 'ncbi.nlm.nih.gov', 'arxiv.org',
                         'pubmed', '.gov', '.edu', 'nature.com', 'science.org', 'statista.com']
    authority_links = [l for l in external_links if any(d in l for d in authority_domains)]
    citation_density = len(external_links) / max(word_count / 500, 1)  # citations per 500 words
    authority_ratio = len(authority_links) / max(len(external_links), 1)
    score = min(100, int(citation_density * 30 + authority_ratio * 70))
    return {
        "score": score,
        "comment": f"{len(external_links)} liens ext. ({len(authority_links)} sources autoritaires)",
        "metadata": {"external_links": len(external_links), "authority_links": len(authority_links),
                     "citation_density": round(citation_density, 2)}
    }
```

---

### CNT-009 — List/Table Density
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Mesure la présence et la densité de listes `<ul>/<ol>` et tableaux `<table>` par rapport au volume de contenu.

**Impact GEO :** Surfer SEO (analyse 46M pages) : les pages avec tableaux de données ont **4.1x** plus de citations AI. Les listes facilitent l'extraction de faits discrets par les LLMs. Les tableaux comparatifs sont particulièrement prisés.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    lists = len(soup.find_all(['ul', 'ol']))
    tables = len(soup.find_all('table'))
    list_items = len(soup.find_all('li'))
    word_count = len(soup.get_text().split())
    density = (lists + tables * 3) / max(word_count / 200, 1)  # tables worth 3x
    score = min(100, int(density * 40) + (20 if tables > 0 else 0) + (20 if lists > 0 else 0))
    return {
        "score": max(0, score),
        "comment": f"{lists} listes ({list_items} items), {tables} tableaux",
        "metadata": {"lists": lists, "tables": tables, "list_items": list_items}
    }
```

---

### CNT-010 — Informational Intent
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Détecte si le contenu répond à une intention informationnelle (questions "qu'est-ce que", "comment", "pourquoi", définitions, guides).

**Impact GEO :** Les LLMs sont massivement interrogés sur des requêtes informationnelles. Un contenu structuré autour de questions/réponses explicites est systématiquement préféré pour les citations.

**Implémentation Endexa :** NLP via spaCy pour détecter les structures interrogatives, la présence de définitions ("X est...", "X désigne..."), l'utilisation de titres en forme de question.

---

### CNT-011 — Commercial Intent
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Mesure la présence de signaux commerciaux (prix, CTA, comparatifs produits).

**Impact GEO :** Les requêtes commerciales dans les LLMs ("meilleur outil pour X", "prix de Y") génèrent des citations vers des pages avec des informations concrètes : tarifs, features, comparatifs.

**Implémentation Endexa :** Détecter : présence de balises `Offer` schema, symboles de prix, tableaux de comparaison, CTAs.

---

### CNT-012 — Video Content
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Détecte la présence de vidéos (YouTube, Vimeo, vidéos natives) avec metadata.

**Impact GEO :** Les LLMs multimodaux commencent à citer du contenu vidéo. Le schema `VideoObject` permet aux moteurs génératifs de comprendre le contenu vidéo sans le voir.

**Implémentation Endexa :** Détecter `<iframe>` YouTube/Vimeo, `<video>` HTML5, et schema `VideoObject`. Score basé sur la présence de titre, description, transcription.

---

### CNT-013 — Image Uniqueness
**Priorité :** ⛔ P5 Marginal | **Automation :** Semi

**Rôle :** Vérifie si les images sont originales (pas de stock photos génériques).

**Impact GEO :** Impact GEO non prouvé. Difficile à automatiser sans reverse image search à grande échelle.

---

### CNT-014 — YouTube Transcripts
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Vérifie si les vidéos YouTube embarquées ont des transcriptions disponibles.

**Impact GEO :** Les transcriptions sont du contenu textuel indexable. Elles multiplient la surface d'extraction pour les LLMs.

**Implémentation Endexa :** Extraire les IDs YouTube des iframes, interroger l'API YouTube Data (`captions.list`) pour vérifier la disponibilité des sous-titres/transcriptions.

---

### CNT-015 — Visual Hierarchy
**Priorité :** ⛔ P5 Marginal | **Automation :** Full

**Rôle :** Évalue la cohérence visuelle de la page (tailles de titres, espacement).

**Impact GEO :** Signal CSS, non pertinent pour les crawlers AI textuels.

---

### CNT-016 — Fact Check Schema
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Vérifie la présence de schema `ClaimReview` pour les contenus éditoriaux de fact-checking.

**Impact GEO :** Signal d'autorité E-E-A-T. Les LLMs accordent plus de crédibilité aux sources qui vérifient leurs affirmations.

**Implémentation Endexa :** Détecter `@type: ClaimReview` dans les JSON-LD. Pertinent pour les sites médias et d'actualité.

---

### CNT-017 — HowTo Schema
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Vérifie la présence de schema `HowTo` avec des étapes structurées.

**Impact GEO :** Les requêtes "comment faire X" sont parmi les plus fréquentes dans les LLMs. Le schema `HowTo` permet une extraction directe des étapes par les moteurs génératifs, augmentant massivement la probabilité de citation.

**Implémentation Endexa :** Identique à CNT-001 mais pour `@type: HowTo`. Évaluer : présence des `step`, présence de `name` et `text` dans chaque step.

---

### CNT-018 — Content Length
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Mesure le nombre de mots du contenu principal (hors navigation/footer).

**Impact GEO :** Les LLMs citent préférentiellement du contenu substantiel. En dessous de 300 mots, une page est rarement citée. Au-dessus de 1500 mots, elle contient suffisamment de substance pour couvrir plusieurs questions.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    content = kwargs.get("page_content", "")  # Extracted main content, not full HTML
    words = len(content.split())
    if words >= 1500: score = 100
    elif words >= 800: score = 80
    elif words >= 400: score = 60
    elif words >= 200: score = 40
    else: score = int(words / 200 * 40)
    return {
        "score": score,
        "comment": f"{words} mots de contenu principal",
        "metadata": {"word_count": words}
    }
```

---

### CNT-019 — Sentence Length
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Mesure la longueur moyenne et la variance des phrases.

**Impact GEO :** Princeton GEO paper : les phrases courtes (<20 mots en moyenne) avec variation de longueur sont plus facilement extraites par les LLMs. Les phrases trop longues peuvent être tronquées lors de l'extraction.

**Implémentation Endexa :** `textstat.avg_sentence_length()` + calcul de variance.

---

### CNT-020 — Paragraph Length
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Mesure la longueur moyenne des paragraphes en mots.

**Impact GEO :** Les LLMs extraient les faits paragraphe par paragraphe. Des paragraphes de 60-120 mots sont optimaux — assez longs pour être informatifs, assez courts pour être auto-contenus.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().split()) > 10]
    if not paragraphs:
        return {"score": 0, "comment": "Aucun paragraphe substantiel", "metadata": {}}
    lengths = [len(p.split()) for p in paragraphs]
    avg_length = sum(lengths) / len(lengths)
    # Optimal: 60-120 words
    if 60 <= avg_length <= 120: score = 100
    elif 40 <= avg_length < 60: score = 80
    elif 120 < avg_length <= 180: score = 70
    else: score = 40
    return {
        "score": score,
        "comment": f"Longueur moyenne des paragraphes : {avg_length:.0f} mots",
        "metadata": {"avg_paragraph_length": round(avg_length, 1), "paragraph_count": len(paragraphs)}
    }
```

---

### CNT-021 — Active Voice %
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Estime le pourcentage de phrases à la voix active vs passive.

**Impact GEO :** La voix active est plus directe et plus facilement extraite par les LLMs. Les phrases passives complexes créent de l'ambiguïté dans l'extraction de sujets/objets.

**Implémentation Endexa :** Heuristiques NLP via spaCy : détecter les constructions "be + past participle" pour identifier la voix passive.

---

### CNT-022 — Unique Named Entities
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Compte le nombre d'entités nommées uniques et leur diversité de types (PERSON, ORG, GPE, DATE, MONEY).

**Impact GEO :** Un contenu qui mentionne des personnes réelles (auteurs, experts), des organisations, des chiffres datés crée un réseau de faits vérifiables que les LLMs peuvent croiser avec leur base de connaissances.

**Implémentation Endexa :** Extension de CNT-003 avec focus sur la diversité des types d'entités.

---

### CNT-023 — Duplicate Content
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Détecte le contenu dupliqué entre les pages du même site via similarité cosinus des embeddings.

**Impact GEO :** Les LLMs déprioritisent les sources avec contenu redondant. Des pages quasi-identiques divisent l'autorité et créent de la confusion dans l'indexation.

**Implémentation Endexa :** Comparer les embeddings de toutes les pages auditées via pgvector. Signaler les pairs avec similarité > 0.85.

---

## Module BV — Visibilité de Marque

> 15 data points | Mesure la présence et la réputation de la marque dans les sources utilisées pour entraîner et alimenter les LLMs.

---

### BV-001 — Knowledge Graph ID
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie si l'entité dispose d'un Knowledge Graph ID Google (via l'API Knowledge Graph Search).

**Impact GEO :** Le Knowledge Graph de Google est une source primaire pour de nombreux LLMs. Une entité avec un KG ID est désambiguïsée et a une "fiche d'identité" que les modèles peuvent consulter. Sans KG ID, la marque risque d'être confondue avec d'autres entités similaires.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    brand_name = kwargs.get("brand_name", "")
    if not brand_name:
        return {"score": 0, "comment": "Nom de marque non fourni", "metadata": {}}
    kg_api_key = settings.GOOGLE_KG_API_KEY
    api_url = f"https://kgsearch.googleapis.com/v1/entities:search?query={brand_name}&key={kg_api_key}&limit=3&types=Organization"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            data = await resp.json()
    items = data.get('itemListElement', [])
    if not items:
        return {"score": 0, "comment": f"'{brand_name}' absent du Knowledge Graph Google", "metadata": {}}
    best = items[0]
    result_score = best.get('resultScore', 0)
    kg_id = best.get('result', {}).get('@id', '')
    score = min(100, int(result_score * 10))
    return {
        "score": max(40, score) if kg_id else 0,
        "comment": f"KG ID trouvé : {kg_id} (score {result_score:.1f})",
        "metadata": {"kg_id": kg_id, "result_score": result_score}
    }
```
> **Note :** Nécessite `GOOGLE_KG_API_KEY` dans `.env`. L'API Knowledge Graph est gratuite jusqu'à 100K requêtes/jour.

---

### BV-002 — KG Confidence Score
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Mesure le score de confiance de l'entité dans le Knowledge Graph (de 0 à ~10+).

**Impact GEO :** Un score KG élevé indique que Google considère l'entité comme bien établie et fiable. Corrèle avec la fréquence de mention dans les AI Overviews.

**Implémentation Endexa :** Extension de BV-001, extraire `resultScore` et le normaliser sur 100.

---

### BV-003 — Wikidata Item
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie si la marque a une entrée Wikidata (Q-item) avec les propriétés essentielles.

**Impact GEO :** Wikidata est le graph de connaissances structuré utilisé par Wikipedia et de nombreux LLMs comme source de vérité pour les entités. Une entrée Wikidata complète réduit drastiquement les hallucinations des LLMs sur la marque.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    domain = urlparse(url).netloc.replace('www.', '')
    # Search Wikidata by official website URL
    sparql_query = f"""
    SELECT ?item ?itemLabel WHERE {{
      ?item wdt:P856 <https://{domain}> .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" }}
    }} LIMIT 1
    """
    wikidata_url = "https://query.wikidata.org/sparql"
    async with aiohttp.ClientSession() as session:
        async with session.get(wikidata_url, params={"query": sparql_query, "format": "json"},
                               headers={"User-Agent": "Endexa/1.0"}) as resp:
            data = await resp.json()
    results = data.get('results', {}).get('bindings', [])
    if not results:
        return {"score": 0, "comment": "Aucun item Wikidata trouvé pour ce domaine", "metadata": {}}
    item_id = results[0].get('item', {}).get('value', '').split('/')[-1]
    label = results[0].get('itemLabel', {}).get('value', '')
    return {
        "score": 100,
        "comment": f"Wikidata item : {item_id} ({label})",
        "metadata": {"wikidata_id": item_id, "label": label}
    }
```

---

### BV-004 — Wikipedia Backlinks
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Compte le nombre de pages Wikipedia qui lient vers la marque.

**Impact GEO :** Wikipedia est la source la plus citée par tous les LLMs. Des backlinks Wikipedia signalent que la marque est mentionnée dans des articles thématiques, augmentant sa notoriété implicite dans les modèles.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    brand_name = kwargs.get("brand_name", "")
    wiki_api = f"https://fr.wikipedia.org/w/api.php?action=query&list=search&srsearch={brand_name}&format=json&srlimit=5"
    async with aiohttp.ClientSession() as session:
        async with session.get(wiki_api) as resp:
            data = await resp.json()
    results = data.get('query', {}).get('search', [])
    score = min(100, len(results) * 20)
    return {
        "score": score,
        "comment": f"{len(results)} articles Wikipedia mentionnant '{brand_name}'",
        "metadata": {"wiki_results": len(results), "articles": [r.get('title') for r in results]}
    }
```

---

### BV-005 — Wikipedia Page
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie si la marque dispose de sa propre page Wikipedia.

**Impact GEO :** Avoir une page Wikipedia dédiée est le signal d'autorité le plus fort pour les LLMs. Wikipedia est dans le top 3 des sources les plus citées par ChatGPT, Claude et Gemini.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    brand_name = kwargs.get("brand_name", "")
    wiki_url = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{brand_name.replace(' ', '_')}"
    async with aiohttp.ClientSession() as session:
        async with session.get(wiki_url) as resp:
            exists = resp.status == 200
            data = await resp.json() if exists else {}
    score = 100 if exists else 0
    return {
        "score": score,
        "comment": f"Page Wikipedia {'trouvée' if exists else 'inexistante'} pour '{brand_name}'",
        "metadata": {"exists": exists, "wiki_title": data.get('title'), "extract": data.get('extract', '')[:200]}
    }
```

---

### BV-006 — Hallucination Rate
**Priorité :** 🟠 P1 Important | **Automation :** Semi

**Rôle :** Mesure le taux d'informations incorrectes que les LLMs génèrent sur la marque en interrogeant directement plusieurs modèles.

**Impact GEO :** Un taux d'hallucination élevé indique que les LLMs n'ont pas assez d'informations fiables sur la marque, ou que les informations disponibles sont contradictoires. C'est un indicateur inversé de la qualité de la présence GEO.

**Implémentation Endexa :** Via `dispatch_service.py`, envoyer des questions factuelles sur la marque aux LLMs configurés. Comparer les réponses avec les données fournies par l'utilisateur lors de l'audit (founding date, CEO name, products). Calculer le % de faits corrects.

> **Note :** Nécessite que l'utilisateur fournisse des "faits vérifiables" lors de la configuration de l'audit.

---

### BV-007 — Sentiment Analysis
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Analyse le sentiment des mentions de la marque dans les réponses des LLMs.

**Impact GEO :** Les LLMs amplifient le sentiment existant sur une marque. Un sentiment négatif persistant dans les réponses des LLMs peut influencer les décisions d'achat des utilisateurs finaux.

**Implémentation Endexa :** Déjà partiellement implémenté via `sentiment_service.py`. Intégrer les résultats dans le score BV-007.

---

### BV-008 — Brand Search Volume
**Priorité :** ⚪ P4 Externe | **Automation :** Full

**Rôle :** Volume de recherche mensuel pour le nom de marque sur Google.

**Impact GEO :** Corrèle avec la notoriété de marque, mais nécessite l'API Google Keyword Planner (non publique) ou Semrush/Ahrefs.

**Implémentation Endexa :** Marquer comme "requires_external_api: semrush|ahrefs". Retourner score 50 (neutre) si non disponible, avec message "Connectez votre compte Semrush pour cette mesure."

---

### BV-009 — Author Authority
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Évalue l'autorité des auteurs du contenu via leur profil (LinkedIn, Google Scholar, Wikipedia, bio page).

**Impact GEO :** Signal E-E-A-T (Expertise, Experience, Authoritativeness, Trustworthiness). Les LLMs pondèrent la crédibilité des sources par l'autorité des auteurs. Un article signé par un expert avec un profil vérifiable a plus de chances d'être cité.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    html = kwargs.get("rendered_html") or kwargs.get("raw_html", "")
    soup = BeautifulSoup(html, 'lxml')
    signals = {}
    # 1. Schema Person or author
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
            author = data.get('author') or (data.get('@graph') and next(
                (x for x in data['@graph'] if x.get('@type') == 'Person'), None))
            if author:
                signals['schema_author'] = author.get('name')
                signals['author_url'] = author.get('url', '')
        except (json.JSONDecodeError, AttributeError):
            pass
    # 2. Byline text
    byline = soup.find(class_=lambda c: c and 'author' in c.lower())
    if byline:
        signals['byline_text'] = byline.get_text().strip()[:100]
    # 3. Links to LinkedIn/scholar in author section
    author_section = soup.find(class_=lambda c: c and 'author' in c.lower())
    if author_section:
        auth_links = [a.get('href','') for a in author_section.find_all('a', href=True)]
        signals['linkedin_link'] = any('linkedin.com' in l for l in auth_links)
    score = (30 if signals.get('schema_author') else 0) + \
            (20 if signals.get('author_url') else 0) + \
            (30 if signals.get('byline_text') else 0) + \
            (20 if signals.get('linkedin_link') else 0)
    return {
        "score": score,
        "comment": f"Auteur : {signals.get('schema_author', 'non identifié')}",
        "metadata": signals
    }
```

---

### BV-010 — E-E-A-T Score
**Priorité :** 🟠 P1 Important | **Automation :** Semi

**Rôle :** Score composite d'Expertise, Experience, Authoritativeness et Trustworthiness.

**Impact GEO :** Les LLMs intègrent implicitement les signaux E-E-A-T lors de l'évaluation des sources. Google AI Overviews est explicitement documenté comme utilisant E-E-A-T pour sélectionner les sources citées.

**Implémentation Endexa :** Score composite de 4 sous-scores : BV-009 (Expertise/Experience), WI-012 sameAs vers Wikipedia/LinkedIn (Authoritativeness), WI-018 SSL + BV-001 KG (Trustworthiness), BV-016 reviews (Experience).

---

### BV-011 — Review Rating / Review Volume
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Récupère les notes moyennes et le volume d'avis sur Google My Business, Trustpilot, G2, Capterra.

**Impact GEO :** Les LLMs citent les avis clients pour les requêtes de type "avis sur X" ou "X est-il fiable ?". Une note élevée et un volume important d'avis sont des signaux d'autorité sociale.

**Implémentation Endexa :** Schema `AggregateRating` dans le HTML ou requête vers l'API Google My Business si disponible. Scraping respectueux des pages Trustpilot/G2 avec parsing des données structurées.

---

### BV-012 à BV-015 — Podcast Mentions, Influencer Mentions, Mention Velocity
**Priorité :** ⚪ P4 Externe

**Rôle :** Mesures de présence dans les médias alternatifs et vélocité des mentions.

**Impact GEO :** Pertinents mais très difficiles à mesurer sans APIs tierces (Mention.com, Brand24, BuzzSumo).

**Implémentation Endexa :** Marquer comme `requires_external_api: mention|brand24`. Optionnellement, implémenter une recherche Google News simple pour `Mention Velocity`.

---

## Module SEO — Référencement

> 13 data points | Signaux SEO classiques avec impact GEO indirect.

---

### SEO-001 — Reddit Mention Volume
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Compte le nombre de mentions de la marque sur Reddit dans les 90 derniers jours.

**Impact GEO :** Reddit est **massivement surreprésenté** dans les données d'entraînement des LLMs (OpenAI a payé pour l'accès à l'API Reddit). Les discussions Reddit où la marque est mentionnée positivement constituent une source directe d'influence sur la connaissance des LLMs.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    brand_name = kwargs.get("brand_name", "")
    reddit_url = f"https://www.reddit.com/search.json?q={brand_name}&sort=relevance&t=year&limit=25"
    async with aiohttp.ClientSession() as session:
        async with session.get(reddit_url, headers={"User-Agent": "Endexa/1.0"}) as resp:
            data = await resp.json()
    posts = data.get('data', {}).get('children', [])
    total_posts = len(posts)
    total_upvotes = sum(p.get('data', {}).get('ups', 0) for p in posts)
    score = min(100, total_posts * 4 + (20 if total_upvotes > 1000 else 0))
    return {
        "score": score,
        "comment": f"{total_posts} posts Reddit sur '{brand_name}' ({total_upvotes} upvotes)",
        "metadata": {"reddit_posts": total_posts, "total_upvotes": total_upvotes}
    }
```

---

### SEO-002 — Social Signal (X/Twitter)
**Priorité :** ⛔ P5 Marginal | **Automation :** Full

**Rôle :** Volume de mentions sur X (Twitter).

**Impact GEO :** Impact GEO faible. X n'est plus une source primaire pour les LLMs depuis les restrictions d'accès API en 2023.

---

### SEO-003 — Backlink Profile
**Priorité :** ⚪ P4 Externe | **Automation :** Full

**Rôle :** Qualité et quantité des domaines référents.

**Impact GEO :** Signal indirect d'autorité de domaine. Nécessite Ahrefs/Moz API.

**Implémentation Endexa :** Via l'API Ahrefs (si configurée). Alternative gratuite limitée : Common Crawl backlink data.

---

### SEO-004 — Referring Domains
**Priorité :** ⚪ P4 Externe | **Automation :** Full

**Implémentation Endexa :** Identique à SEO-003.

---

### SEO-005 — Navigational Intent
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Évalue si la page est bien positionnée pour les requêtes navigationnelles (brand name + "login", "pricing", "docs").

**Implémentation Endexa :** Vérifier la présence de pages `/login`, `/pricing`, `/docs` et leur accessibilité depuis la homepage.

---

### SEO-006 à SEO-009 — Zero-Click %, Forum Presence, Local SEO, Map Embeds
**Priorité :** Mixte (P2 pour Local SEO, ⛔ pour Forum Presence)

**Local SEO (NAP) :** Vérifier la cohérence Name/Address/Phone dans les schemas et le footer. Pertinent pour les business locaux.

**Map Embeds :** Détecter les iframes Google Maps. Signal local SEO.

**Zero-Click % :** Nécessite Google Search Console — ⚪ P4 Externe.

**Forum Presence :** Semi-automatisable via Google Search `site:quora.com OR site:stackexchange.com "{brand_name}"`. Impact GEO faible.

---

### SEO-010 à SEO-013 — OG Tags, Twitter Cards, Brand/Non-Brand Ratio, Link Velocity
**Priorité :** ⛔ P5 Marginal (sauf OG Tags : 🟡 P2)

**OG Tags :** Pertinent car les partages sur réseaux sociaux créent des URLs crawlables. Vérifier `og:title`, `og:description`, `og:image`, `og:url`.

**Twitter Cards / Brand Ratio / Link Velocity :** Impact GEO très faible ou nécessitent des APIs externes.

---

## Module UX — Expérience Utilisateur

> 7 data points | Métriques de performance et d'engagement.

---

### UX-001 — Core Web Vitals LCP
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Largest Contentful Paint — temps d'affichage du plus grand élément visible.

**Impact GEO :** Les agents AI autonomes (browsing agents) ont des timeouts. Un LCP > 4s peut provoquer l'abandon du crawl. Signal de qualité technique indirect.

**Implémentation Endexa :** Via l'API Google PageSpeed Insights (gratuite, clé optionnelle) :
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    psi_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile"
    async with aiohttp.ClientSession() as session:
        async with session.get(psi_url) as resp:
            data = await resp.json()
    lcp = data.get('lighthouseResult', {}).get('audits', {}).get('largest-contentful-paint', {})
    lcp_value = lcp.get('numericValue', 0) / 1000  # Convert ms to seconds
    if lcp_value <= 2.5: score = 100
    elif lcp_value <= 4.0: score = 60
    else: score = max(0, int(100 - lcp_value * 15))
    return {
        "score": score,
        "comment": f"LCP : {lcp_value:.1f}s ({'bon' if lcp_value <= 2.5 else 'à améliorer'})",
        "metadata": {"lcp_seconds": round(lcp_value, 2)}
    }
```

---

### UX-002 — Core Web Vitals CLS
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Cumulative Layout Shift — stabilité visuelle de la page.

**Impact GEO :** Signal de qualité technique. Un CLS élevé indique un HTML instable qui peut perturber l'extraction de contenu par les crawlers.

**Implémentation Endexa :** Via PageSpeed Insights API — extraire `cumulative-layout-shift`.

---

### UX-003 — Mobile Friendliness
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Vérifie si la page est responsive et utilisable sur mobile.

**Impact GEO :** Google indexe en mobile-first. Les crawlers AI de Google utilisent le même agent. Un site non-responsive peut être sous-indexé.

**Implémentation Endexa :** Via PageSpeed Insights API — score mobile. Alternativement, vérifier le viewport meta tag et les media queries CSS.

---

### UX-004 à UX-007 — Dwell Time, Bounce Rate, Scroll Depth, Interaction Rate
**Priorité :** 🟢 P3 Conditionnel

**Rôle :** Métriques comportementales d'engagement.

**Impact GEO :** Corrèlent avec la qualité du contenu mais ne sont **pas directement mesurables** sans Google Analytics ou équivalent.

**Implémentation Endexa :** Ces 4 points ne peuvent être mesurés qu'avec une intégration analytics. Ajouter dans l'UI un bouton "Connecter Google Analytics" et récupérer via l'API GA4 :
- Dwell Time → `averageSessionDuration`
- Bounce Rate → `bounceRate`
- Scroll Depth → via événements personnalisés GA4
- Interaction Rate → `engagementRate`

Retourner score 50 (neutre) avec message explicatif si analytics non connecté.

---

## Module COMP — Compétitif

> 10 data points | Mesure la position relative de la marque face aux concurrents dans les LLMs.

---

### COMP-001 — Share of Model (GPT)
**Priorité :** 🔴 P0 Critique | **Automation :** Semi

**Rôle :** Mesure le pourcentage de fois où la marque est citée par GPT-4/GPT-4o sur les requêtes cibles du secteur.

**Impact GEO :** C'est **la métrique GEO fondamentale** — équivalent du "Share of Voice" en marketing traditionnel, mais pour les LLMs. Un Share of Model de 60% signifie que sur 10 questions sectorielles posées à ChatGPT, la marque est mentionnée 6 fois.

**Implémentation Endexa :** Déjà partiellement implémenté via `dispatch_service.py` et `mention_detector.py`. Formaliser :
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    # Requires: audit queries already dispatched and mentions stored
    audit_id = kwargs.get("audit_id")
    db = kwargs.get("db")
    # Query mentions from DB
    from app.models.brand_mention import BrandMention
    from app.models.engine_response import EngineResponse
    from app.models.audit_query import AuditQuery
    gpt_responses = (db.query(EngineResponse)
        .join(AuditQuery).filter(AuditQuery.audit_id == audit_id,
                                  EngineResponse.engine == "openai").all())
    if not gpt_responses:
        return {"score": 0, "comment": "Aucune réponse GPT disponible", "metadata": {}}
    responses_with_mention = sum(1 for r in gpt_responses
        if db.query(BrandMention).filter(BrandMention.engine_response_id == r.id).count() > 0)
    som = responses_with_mention / len(gpt_responses) * 100
    score = int(som)
    return {
        "score": score,
        "comment": f"Share of Model GPT : {som:.0f}% ({responses_with_mention}/{len(gpt_responses)} requêtes)",
        "metadata": {"som_pct": round(som, 1), "queries_tested": len(gpt_responses),
                     "queries_with_mention": responses_with_mention}
    }
```

---

### COMP-002 — Share of Model (Claude)
**Priorité :** 🔴 P0 Critique | **Automation :** Semi

**Rôle :** Share of Model sur Claude (Anthropic).

**Implémentation Endexa :** Identique à COMP-001, filtrer sur `engine == "anthropic"`.

---

### COMP-003 — Share of Model (Perplexity)
**Priorité :** 🔴 P0 Critique | **Automation :** Semi

**Rôle :** Share of Model sur Perplexity.

**Implémentation Endexa :** Identique à COMP-001, filtrer sur `engine == "perplexity"`.

---

### COMP-004 — Competitor SoM
**Priorité :** 🔴 P0 Critique | **Automation :** Semi

**Rôle :** Compare le Share of Model de la marque auditée avec celui des concurrents détectés sur les mêmes requêtes.

**Impact GEO :** Donne le contexte compétitif réel. Un SoM de 20% peut être excellent (si le leader est à 25%) ou désastreux (si le leader est à 80%).

**Implémentation Endexa :** Via `competitor_service.py` — croiser les mentions des concurrents découverts sur les mêmes `AuditQuery` records.

---

### COMP-005 — Competitor Content Volume
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Compare le volume de contenu indexé (nombre de pages) entre la marque et ses concurrents.

**Implémentation Endexa :** Utiliser le paramètre `site:domaine.com` dans une requête Google Custom Search API pour estimer le nombre de pages indexées.

---

### COMP-006 — Competitor Schema Coverage
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Compare la couverture schema.org (types et propriétés) entre la marque et ses concurrents.

**Implémentation Endexa :** Crawler les pages principales des concurrents (via `competitor_service.py`) et parser leurs JSON-LD.

---

### COMP-007 — Keyword Gap
**Priorité :** ⚪ P4 Externe | **Automation :** Full

**Rôle :** Identifie les mots-clés sur lesquels les concurrents se positionnent mais pas la marque.

**Implémentation Endexa :** Nécessite Semrush/Ahrefs API.

---

### COMP-008 — Entity Gap
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Identifie les entités (topics, concepts) présentes dans le contenu des concurrents mais absentes du contenu de la marque.

**Impact GEO :** Les "entity gaps" correspondent exactement aux sujets sur lesquels les LLMs mentionneront les concurrents mais pas la marque.

**Implémentation Endexa :** Extraire les entités (spaCy NER) des pages principales de la marque et des concurrents. Calculer les entités présentes chez les concurrents mais absentes chez la marque.

---

### COMP-009 — Vector Distance Gap
**Priorité :** 🟠 P1 Important | **Automation :** Full

**Rôle :** Mesure la distance sémantique entre le contenu de la marque et les requêtes cibles vs la distance entre les concurrents et ces mêmes requêtes.

**Impact GEO :** Un concurrent sémantiquement plus proche des requêtes cibles sera systématiquement préféré par les LLMs RAG (Perplexity, ChatGPT avec browsing).

**Implémentation Endexa :** Via pgvector — calculer la distance cosinus entre les embeddings de la marque et des concurrents par rapport aux embeddings des keywords cibles.

---

### COMP-010 — Brand Sentiment Gap
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Compare le sentiment des mentions de la marque vs les concurrents dans les réponses LLMs.

**Implémentation Endexa :** Extension de `sentiment_service.py` — calculer le sentiment pour les mentions de chaque concurrent et comparer avec la marque.

---

## Module LEG — Légal

> 6 data points | Signaux légaux et de conformité pour l'accès au contenu par les IA.

---

### LEG-001 — TDM Reservation
**Priorité :** 🔴 P0 Critique | **Automation :** Full

**Rôle :** Vérifie si le site a une déclaration TDM (Text and Data Mining) permettant explicitement l'utilisation du contenu par des IA.

**Impact GEO :** La directive européenne sur le droit d'auteur (article 4, DSM 2019) permet aux IA de miner du contenu pour entraînement **sauf si le site réserve ce droit**. Un fichier `ai.txt` ou `llms.txt` avec des permissions TDM explicites signale aux IA qu'elles peuvent utiliser le contenu librement.

**Implémentation Endexa :**
```python
async def measure(url: str, **kwargs) -> Dict[str, Any]:
    signals = {}
    # 1. Check /llms.txt
    async with aiohttp.ClientSession() as session:
        for path in ['/llms.txt', '/ai.txt', '/robots.txt']:
            try:
                async with session.get(url.rstrip('/') + path, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        signals[path] = content[:500]
            except Exception:
                pass
    # 2. Check for TDM reservation in robots.txt
    tdm_blocked = False
    if '/robots.txt' in signals:
        tdm_blocked = 'TDMRep' in signals['/robots.txt'] and 'disallow' in signals['/robots.txt'].lower()
    llms_txt_exists = '/llms.txt' in signals
    ai_txt_exists = '/ai.txt' in signals
    score = (60 if llms_txt_exists else 0) + (20 if ai_txt_exists else 0) + (20 if not tdm_blocked else -20)
    return {
        "score": max(0, min(100, score)),
        "comment": f"llms.txt : {'✓' if llms_txt_exists else '✗'}, TDM bloqué : {'oui' if tdm_blocked else 'non'}",
        "metadata": {"llms_txt": llms_txt_exists, "ai_txt": ai_txt_exists, "tdm_blocked": tdm_blocked}
    }
```

---

### LEG-002 — Privacy Policy Page
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Vérifie la présence d'une page de politique de confidentialité accessible.

**Impact GEO :** Signal de légitimité. Les LLMs, notamment dans les réponses à des requêtes sur des marques inconnues, peuvent mentionner l'absence de politique de confidentialité comme un signal négatif.

**Implémentation Endexa :** Détecter les liens vers `/privacy`, `/privacy-policy`, `/politique-confidentialite` dans le footer.

---

### LEG-003 — Terms of Service
**Priorité :** ⛔ P5 Marginal | **Automation :** Full

**Implémentation Endexa :** Détecter un lien vers les CGU/Terms dans le footer.

---

### LEG-004 — TDM Policy URL
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Vérifie si le site déclare une URL de politique TDM dans le header HTTP `TDMRep`.

**Implémentation Endexa :** Vérifier le header HTTP `TDMRep` dans la réponse du serveur.

---

### LEG-005 — GDPR Compliance
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Vérifie les signaux basiques de conformité RGPD : bandeau cookies, politique de confidentialité, opt-out.

**Implémentation Endexa :** Détecter les bandeaux de consentement (OneTrust, Axeptio, Cookiebot) via des sélecteurs CSS connus. Vérifier la présence de la mention "RGPD" ou "GDPR" sur le site.

---

### LEG-006 — CCPA Compliance
**Priorité :** 🟡 P2 Utile | **Automation :** Full

**Rôle :** Vérifie la conformité California Consumer Privacy Act pour les sites visant le marché américain.

**Implémentation Endexa :** Détecter les mentions "Do Not Sell My Personal Information" ou "CCPA" sur le site.

---

## Synthèse et Roadmap

### Répartition par priorité

| Priorité | Nombre | Description |
|----------|--------|-------------|
| 🔴 P0 Critique | 14 | Bloquants directs — implémenter en premier |
| 🟠 P1 Important | 24 | Impact fort prouvé — Vague 2 |
| 🟡 P2 Utile | 30 | SEO/GEO indirect — Vague 3 |
| 🟢 P3 Conditionnel | 4 | Nécessitent analytics connecté |
| ⚪ P4 Externe | 8 | Nécessitent API tierce |
| ⛔ P5 Marginal | 9 | À déprécier ou impact non prouvé |

**Total actionnable sans API externe : 72/109 points**

---

### Points P0 — À implémenter en priorité absolue

| Code | Nom | Module |
|------|-----|--------|
| WI-001 | Robots.txt GPTBot | WI |
| WI-002 | Robots.txt ClaudeBot | WI |
| WI-003 | Robots.txt PerplexityBot | WI |
| WI-004 | Robots.txt CCBot | WI |
| WI-009 | JS Dependency (SPA sans SSR) | WI |
| WI-010 | Dynamic Rendering | WI |
| WI-011 | Schema Organization | WI |
| WI-007 | Status Code 200 | WI |
| CNT-001 | Schema FAQPage | CNT |
| BV-001 | Knowledge Graph ID | BV |
| BV-003 | Wikidata Item | BV |
| BV-005 | Wikipedia Page | BV |
| LEG-001 | TDM Reservation / llms.txt | LEG |
| COMP-001/002/003 | Share of Model (GPT/Claude/Perplexity) | COMP |

---

### Points nécessitant des kwargs supplémentaires

Pour être compatibles avec le système Endexa, certains points nécessitent des données passées via `kwargs` depuis `audit_service.py` :

| Kwarg | Points concernés | Source |
|-------|-----------------|--------|
| `rendered_html` | WI-009, WI-010, WI-015, CNT-020... | `PlaywrightCrawler` |
| `raw_html` | WI-007, WI-011, WI-015... | `requests/aiohttp` |
| `page_content` | CNT-018, CNT-006, CNT-003... | `html_parser.py` |
| `brand_name` | BV-001 à BV-008, COMP-001... | `Audit.brand_name` |
| `keywords` | CNT-004, COMP-009... | `Audit.keywords` |
| `competitor_embeddings` | CNT-002, COMP-009... | pgvector |
| `audit_id` + `db` | COMP-001 à COMP-004 | Contexte audit |

---

### Points P3/P4 — Intégrations suggérées

| Intégration | Points débloqués | Priorité |
|-------------|-----------------|----------|
| Google PageSpeed Insights API (gratuit) | UX-001, UX-002, UX-003 | Rapide |
| Google Knowledge Graph API (gratuit) | BV-001, BV-002 | Rapide |
| Wikidata SPARQL (gratuit) | BV-003, BV-004 | Rapide |
| Reddit API (gratuit) | SEO-001 | Rapide |
| Google Analytics 4 (nécessite OAuth) | UX-004 à UX-007 | Phase 2 |
| Ahrefs/Semrush (payant) | SEO-003, SEO-004, COMP-007, BV-008 | Phase 3 |

---

### Points à déprécier (P5 — ne pas implémenter)

Ces 9 points ont un impact GEO non prouvé et coûtent en complexité de maintenance :

`WI-025` Hreflang (sauf sites multilingues), `WI-027` Favicon, `WI-035` Text-to-HTML Ratio, `CNT-013` Image Uniqueness, `CNT-015` Visual Hierarchy, `SEO-002` Social Signal X, `SEO-006` Forum Presence, `SEO-010` OG Tags, `SEO-011` Twitter Cards

**Recommandation :** Les retirer du scoring global ou les regrouper dans une catégorie "Signaux secondaires" avec un poids nul.

---

*Document généré pour le projet Endexa GEO Platform MVP — Mars 2026*
