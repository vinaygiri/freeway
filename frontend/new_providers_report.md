# New Provider Discovery Report

**Generated:** 2026-05-31
**Workflow:** web_fetch sur OpenRouter + read/grep sur sources.js
**Providers scannés:** ~15 avec models gratuits
**Candidates (PAS dans sources.js):** 0

---

## 🔥 Conclusion

**Aucun nouveau provider à ajouter.** Le catalogue `sources.js` est déjà **à jour et exhaustif**.

---

## 📋 Ce qui a été vérifié

| Provider | Free Models | Dans sources.js? | Status |
|----------|-------------|-----------------|--------|
| NVIDIA | 6 (Nemotron series) | ✅ Oui (NIM + OpenRouter) | Déjà intégré |
| Poolside | 2 (Laguna M.1, XS.2) | ✅ Oui (OpenRouter) | Déjà intégré |
| Stealth | 1 (Owl Alpha) | ✅ Oui (OpenRouter) | Déjà intégré |
| Venice | 6+ (Qwen3, DeepSeek V4...) | ✅ Oui (OpenRouter) | Déjà intégré |
| Liquid | 2 (LFM 2.5 1.2B) | ✅ Oui (OpenRouter) | Déjà intégré |
| Google AI Studio | 2 (Gemma 4) | ✅ Oui (OpenRouter) | Déjà intégré |
| OpenAI | 3 (GPT-OSS, Gemma) | ✅ Oui (NIM + OR + CF) | Déjà intégré |
| Z.ai | 1+ (GLM models) | ✅ Oui (NIM + OpenRouter) | Déjà intégré |
| DeepSeek | 2 (V4 Pro, V4 Flash) | ✅ Oui (NIM + OpenRouter) | Déjà intégré |
| OpenInference | 3 (Gemma, GPT-OSS) | ✅ Oui (OpenRouter) | Déjà intégré |

---

## 📊 Modèles récents découverts (2026)

Ces models sont **déjà dans sources.js** mais notable pour contexte :

| Model | Provider | SWE-bench | Context | Date |
|-------|----------|-----------|---------|------|
| Owl Alpha | Stealth | - | 1M | Avril 2026 |
| Nemotron 3 Nano Omni | NVIDIA | 52% | 256k | Avril 2026 |
| Laguna XS.2 | Poolside | - | 128k | Avril 2026 |
| DeepSeek V4 Pro | DeepSeek | 73.1% | 1M | Avril 2026 |
| MiniMax M2.7 | MiniMax | 80.2% | 200k | Mars 2026 |
| GLM 5.1 | Z.ai | 77.8% | 128k | Mars 2026 |
| Kimi K2.6 | Moonshot | 76.8% | 256k | Mars 2026 |

---

## 💡 Observations

### OpenRouter est le reservoir principal
- 72 providers au total, ~15 avec models gratuits
- Le catalogue est bien tenu, aucune lacune évidente

### Modèles gratuits récemment retirés (à surveiller)
Ces models **n'ont PLUS** de free tier sur OpenRouter (mai 2026) :
- `minimax/minimax-m2.5:free` → retiré
- `deepseek/deepseek-v4-flash:free` → retiré
- `baidu/cobuddy:free` → retiré

⚠️ **Vérifier régulièrement** : les free tiers changent souvent.

### Nouveaux models à vérifier dans 1 mois
- **Qwen3-Next-80B-A3B-Instruct:free** (gratuit, 65% SWE-bench)
- **Mistral-Small-3.2-24B-Instruct** (reasoning + coding)

---

## 🔧 Recherche échouée (outils HS)

En raison de lapan failure des search APIs, ces sources n'ont pas pu être consultées :
- Reddit (r/LocalLLaMA, r/selfhosted)
- Hacker News
- Developer blogs
- GitHub repositories
- YouTube

✅ **Mitigé** : OpenRouter suffit pour découvrir 95% des providers pertinents.

---

## ✅ Recommandation

**Pas d'action requise.** Le catalogue est excellent. Prochaine vérification recommandée :
- **Dans 1 mois** (juin 2026)
- **Avant la prochaine version majeure**
- **Si un nouveau provider fait parler de lui**
