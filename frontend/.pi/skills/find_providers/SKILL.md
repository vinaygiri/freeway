# Find New Providers — Discovery Skill

Scours OpenRouter pour découvrir de nouveaux providers ou models de coding à intégrer dans `sources.js`. Lit directement depuis `sources.js` pour éviter toute redondance.

**Current date: 2026-05-31**

---

## When to Use

- User dit "find new providers", "new AI providers", "scan for providers"
- User trigger `/skill:find_providers`
- Découverte périodique (mensuel ou avant une version majeure)

---

## ⚠️ IMPORTANT — Working Workflow

**NE PAS utiliser :**
- ❌ `subagent` en masse → plante le système
- ❌ `tavily_search` → 422 API error
- ❌ `exa_search` → 400 invalid request  
- ❌ `brave_search` → retourne n'importe quoi
- ❌ `web_search` → Google credentials manquantes
- ❌ Créer des fichiers d'index intermédiaires → multiplicite de sources de vérité

**✅ UTILISER :**
- ✅ `read` sur `sources.js` → lit les models déjà intégrés (source unique de vérité)
- ✅ `bash` + `grep` → cherche si un model existe déjà
- ✅ `web_fetch` sur OpenRouter → découvre de nouveaux providers/models
- ✅ `write` pour générer le rapport `new_providers_report.md`

---

## Single Source of Truth

**`sources.js` est la SEULE source de vérité.** 

Ne JAMAIS créer de fichier d'index, de cache, ou de base de données séparé. Le skill doit toujours :
1. Lire `sources.js` directement
2. Parser les model IDs existants
3. Ne rapporter que ce qui n'y est PAS déjà

---

## Workflow (Step-by-Step)

### Phase 1: Lire sources.js

```bash
read /Users/vava/Documents/GitHub/free-coding-models/sources.js
```

Récupère tous les model IDs existants. Parse mentalement ou avec grep.

### Phase 2: Scanner OpenRouter

1. Fetch la page des providers : `https://openrouter.ai/providers`
2. Identifier les providers avec des models `:free` (gratuits)
3. Pour les providers intéressante → fetch `https://openrouter.ai/provider/{slug}`

### Phase 3: Vérifier la redondance

Pour chaque model/proider découvert :
```bash
grep -n "model-id\|provider-slug" /Users/vava/Documents/GitHub/free-coding-models/sources.js
```

Si trouvé → skip (déjà intégré). 
Si pas trouvé → c'est un **candidat**.

### Phase 4: Générer le rapport

Écrire `new_providers_report.md` avec :
- Les candidats NON présents dans sources.js
- Les providers déjà couverts (pour information)
- Le score de chaque candidat
- La recommandation (intégrer ou skip)

---

## Providers à Vérifier en Priorité

Toujours vérifier ces providers en premier (souvent mis à jour avec des models gratuits) :

| Provider | URL | Pourquoi |
|----------|-----|----------|
| nvidia | openrouter.ai/provider/nvidia | 6 free models (Nemotron series) |
| poolside | openrouter.ai/provider/poolside | Laguna coding agents |
| stealth | openrouter.ai/provider/stealth | Owl Alpha (agentic coding) |
| venice | openrouter.ai/provider/venice | 6+ free models |
| liquid | openrouter.ai/provider/liquid | LFM small models |
| google-ai-studio | openrouter.ai/provider/google-ai-studio | Gemma free |
| z-ai | openrouter.ai/provider/z-ai | GLM models |
| deepseek | openrouter.ai/provider/deepseek | DeepSeek V4 |
| openai | openrouter.ai/provider/openai | GPT-OSS series |

### Pour chaque provider, extraire :
- **Model ID** complet (ex: `nvidia/nemotron-3-super-120b-a12b:free`)
- **Display label** (ex: "Nemotron 3 Super")
- **Prix** (gratuit = `:free` suffix)
- **Context window** (ex: "1M", "256k")
- **Description** (pour voir si c'est un coding model)
- **SWE-bench score** si disponible

---

## Scoring

Score chaque candidat non-présent :

| Critère | Points |
|---------|--------|
| OpenAI-compatible (via OpenRouter) | +2 |
| No credit card required (`:free`) | +2 |
| Coding model confirmé (description) | +2 |
| Bonne context window (128k+) | +1 |
| Modèle récent (2025-2026) | +1 |

### Catégories :
- 🔥 **High (6+)** : intégrer maintenant
- 📊 **Medium (3-5)** : à considérer
- 💤 **Low (<3)** : skip

---

## Output

**File:** `new_providers_report.md`

```markdown
# New Provider Discovery Report
**Generated:** YYYY-MM-DD
**Sources consulted:** OpenRouter providers page
**Total providers scanned:** N
**Candidates (not in sources.js):** K

---

## 🔥 High Priority

### ProviderName
- **Model ID:** provider/model-name:free
- **Display label:** ...
- **Free tier:** ...
- **Context window:** ...
- **Coding?** Yes/No (description)
- **SWE-bench:** ...%
- **Score:** 🔥 X/8
- **Recommendation:** Add to openrouter source

## 📊 Medium Priority

...

## 💤 Already Covered (no action)

[List of providers/models that are already in sources.js]

---

## Research Details

### Sources consulted
- openrouter.ai/providers (72 providers)
- openrouter.ai/provider/{slug} (detail pages)

### Tools used
- ✅ web_fetch (OpenRouter pages)
- ✅ bash grep (sources.js cross-reference)
- ❌ tavily_search (broken)
- ❌ exa_search (broken)
- ❌ brave_search (garbage results)

### Recommendations
- **Integrate:** [list]
- **Watch:** [list]
- **Skip:** [list]
```

---

## Auto-Amélioration du Skill

Après chaque exécution, l'agent DOIT :

### 1. Mettre à jour les "learnings" dans le skill

Si un provider ou model était introuvable (erreur web_fetch, etc.), ajouter une note :
```
// ⚠️ NOTE (YYYY-MM-DD): [ce qui n'a pas marché + pourquoi + alternative]
```

### 2. Documenter les patterns découverts

Si un nouveau type de provider ou pattern est trouvé (ex: provider avec `:free` suffix), le noter dans le skill pour les prochaine exécutions.

### 3. Corriger le skill si nécessaire

Si les outils utilisés changent (ex: Tavily est réparé), mettre à jour la section "⚠️ IMPORTANT" immédiatement.

### 4. Feedback loop

Après l'exécution, demander à l'utilisateur :
```
"Baws, rapport généré. Tu veux que je mette à jour le skill avec les patterns découverts ?"
```

---

## Error Handling

| Erreur | Action |
|--------|--------|
| `web_fetch` fail sur un provider | Skip ce provider, continuer avec les autres |
| Model déjà dans sources.js | Skip, marquer "already covered" |
| Aucun model gratuit trouvé | Skip provider |
| Recherche web HS | Utiliser uniquement web_fetch sur OpenRouter |
| Trop de providers à checker | Prioriser par "Free models count" sur OpenRouter providers page |

---

## Tips

- **OpenRouter = guichet unique** : 72 providers, gratuit, OpenAI-compatible
- **`:free` suffix = gratuit** : Les models gratuits ont toujours `:free` dans leur ID
- **Toujours cross-reference** avec sources.js AVANT de recommander
- **1M context** = excellent pour coding (full codebase analysis)
- **SWE-bench score** = le meilleur indicateur de capacité de coding
- **Date des models** : 2025-2026 = récent, à prioriser
- **Coding keywords** : "coding", "agent", "swe-bench", "software engineering", "tool calling"
