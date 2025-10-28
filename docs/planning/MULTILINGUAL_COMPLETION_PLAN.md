# Plan de Complétion Multilingue - Intelia Expert

**Date**: 2025-10-28
**Objectif**: Aligner les 4 services (frontend, backend, rag, llm) sur les 16 langues i18n
**Status**: 🔴 8/16 langues complètes (50%)

---

## 📊 État Actuel

### Langues par Service

| Service | Langues | Taux |
|---------|---------|------|
| **Frontend** | 16/16 | 100% ✅ |
| **Backend** | 16/16 | 100% ✅ |
| **RAG (ai-service)** | 9/16 | 56% ⚠️ |
| **LLM** | 12/16 | 75% ⚠️ |

### Langues Complètes (4 services)

**8/16 langues fonctionnelles** (50%):
- ✅ de (German)
- ✅ en (English)
- ✅ es (Spanish)
- ✅ fr (French)
- ✅ it (Italian)
- ✅ pt (Portuguese)
- ✅ th (Thai)
- ✅ zh (Chinese)

---

## 🔴 Problèmes Identifiés

### Problème 1: RAG - 4 langues bloquées (CRITIQUE)

**Langues manquantes:**
- ❌ ar (Arabic) - Dictionnaire manquant
- ❌ ja (Japanese) - Dictionnaire manquant
- ❌ tr (Turkish) - Dictionnaire manquant
- ❌ vi (Vietnamese) - Dictionnaire manquant

**Fichier affecté:**
- `rag/config/config.py` lignes 44-61

**Impact:**
- 🔴 Utilisateurs ne peuvent PAS utiliser RAG dans ces langues
- 🔴 Questions non traduites correctement
- 🔴 Résultats de recherche bloqués

**Code actuel:**
```python
SUPPORTED_LANGUAGES = {
    # "ar",  # Arabe - dictionnaire manquant
    "de",  # Allemand
    "en",  # Anglais
    "es",  # Espagnol
    "fr",  # Français
    "hi",  # Hindi
    "id",  # Indonésien
    "it",  # Italien
    # "ja",  # Japonais - dictionnaire manquant
    "nl",  # Néerlandais
    "pl",  # Polonais
    "pt",  # Portugais
    "th",  # Thaï
    # "tr",  # Turc - dictionnaire manquant
    # "vi",  # Vietnamien - dictionnaire manquant
    "zh",  # Chinois
}
```

---

### Problème 2: LLM - 5 langues non optimisées

**Langues manquantes:**
- ❌ hi (Hindi)
- ❌ id (Indonesian)
- ❌ nl (Dutch)
- ❌ pl (Polish)
- ❌ tr (Turkish)

**Fichier affecté:**
- `llm/app/domain_config/domains/aviculture/system_prompts.json` ligne 6

**Impact:**
- ⚠️ Génération pas optimale (pas de prompt système spécifique)
- ⚠️ Qualité réduite pour ces langues
- ⚠️ Expérience utilisateur dégradée

**Code actuel:**
```json
"languages_supported": ["fr", "en", "es", "de", "it", "pt", "ar", "zh", "ja", "ko", "th", "vi"]
```

**Langues présentes mais pas dans Frontend:**
- ✅ ko (Korean) - À SUPPRIMER ou ajouter au Frontend

---

### Problème 3: Korean (ko) orphelin

**Incohérence:**
- LLM supporte Korean (ko)
- Frontend/Backend n'ont PAS de locale Korean
- Impossible à sélectionner dans l'UI

**Impact:** Fonctionnalité inutilisée

**Action:** Supprimer Korean du LLM (ou ajouter au Frontend si besoin business)

---

## 🎯 Plan d'Action

### Phase 1: RAG - Activer 4 langues manquantes (PRIORITÉ CRITIQUE)

**Durée estimée:** 2-3 heures

#### Étape 1.1: Vérifier disponibilité des dictionnaires

**Tâche:** Identifier si les dictionnaires existent ou peuvent être générés

**Actions:**
1. Vérifier `rag/config/` pour dictionnaires existants
2. Rechercher dictionnaires open-source pour ar, ja, tr, vi
3. Vérifier service Google Translate comme fallback

**Fichiers à vérifier:**
- `rag/config/universal_dict.json` (si existant)
- `rag/utils/translation_service.py` - Service de traduction hybride
- `rag/utils/translation_utils.py` - Utilitaires

**Décision:**
- **Option A** (RECOMMANDÉ): Activer Google Translate fallback pour ces langues
- **Option B**: Créer dictionnaires manuellement (long)
- **Option C**: Utiliser traduction LLM (coûteux)

---

#### Étape 1.2: Activer les langues dans RAG config

**Fichier:** `rag/config/config.py`

**Modifications:**
```python
# AVANT (9 langues)
SUPPORTED_LANGUAGES = {
    # "ar",  # Arabe - dictionnaire manquant
    "de",  # Allemand
    "en",  # Anglais
    "es",  # Espagnol
    "fr",  # Français
    "hi",  # Hindi
    "id",  # Indonésien
    "it",  # Italien
    # "ja",  # Japonais - dictionnaire manquant
    "nl",  # Néerlandais
    "pl",  # Polonais
    "pt",  # Portugais
    "th",  # Thaï
    # "tr",  # Turc - dictionnaire manquant
    # "vi",  # Vietnamien - dictionnaire manquant
    "zh",  # Chinois
}

# APRÈS (13 langues)
SUPPORTED_LANGUAGES = {
    "ar",  # Arabe - Google Translate fallback
    "de",  # Allemand
    "en",  # Anglais
    "es",  # Espagnol
    "fr",  # Français
    "hi",  # Hindi
    "id",  # Indonésien
    "it",  # Italien
    "ja",  # Japonais - Google Translate fallback
    "nl",  # Néerlandais
    "pl",  # Polonais
    "pt",  # Portugais
    "th",  # Thaï
    "tr",  # Turc - Google Translate fallback
    "vi",  # Vietnamien - Google Translate fallback
    "zh",  # Chinois
}
```

---

#### Étape 1.3: Activer Google Translate fallback

**Fichier:** `rag/config/config.py`

**Vérifier configuration:**
```python
# Google Translation API
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
ENABLE_GOOGLE_TRANSLATE_FALLBACK = (
    os.getenv("ENABLE_GOOGLE_TRANSLATE_FALLBACK", "false").lower() == "true"
)
```

**Action:**
1. Vérifier si `GOOGLE_TRANSLATE_API_KEY` est configuré
2. Si OUI → Mettre `ENABLE_GOOGLE_TRANSLATE_FALLBACK=true`
3. Si NON → Configurer Google Cloud Translation API

**Variables d'environnement à ajouter:**
```bash
GOOGLE_TRANSLATE_API_KEY=your-api-key-here
ENABLE_GOOGLE_TRANSLATE_FALLBACK=true
```

---

#### Étape 1.4: Tester les 4 nouvelles langues

**Tests à effectuer:**
1. Question en arabe → RAG doit traduire et chercher
2. Question en japonais → RAG doit traduire et chercher
3. Question en turc → RAG doit traduire et chercher
4. Question en vietnamien → RAG doit traduire et chercher

**Endpoints de test:**
```bash
# Test Arabic
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "ما هو أفضل علف للدجاج؟", "language": "ar"}'

# Test Japanese
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "鶏に最適な飼料は何ですか？", "language": "ja"}'

# Test Turkish
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Tavuklar için en iyi yem nedir?", "language": "tr"}'

# Test Vietnamese
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Thức ăn tốt nhất cho gà là gì?", "language": "vi"}'
```

---

### Phase 2: LLM - Ajouter 5 langues manquantes

**Durée estimée:** 1-2 heures

#### Étape 2.1: Ajouter langues au system_prompts.json

**Fichier:** `llm/app/domain_config/domains/aviculture/system_prompts.json`

**Modifications:**
```json
// AVANT (12 langues)
"languages_supported": ["fr", "en", "es", "de", "it", "pt", "ar", "zh", "ja", "ko", "th", "vi"]

// APRÈS (16 langues)
"languages_supported": ["ar", "de", "en", "es", "fr", "hi", "id", "it", "ja", "nl", "pl", "pt", "th", "tr", "vi", "zh"]
```

**Note:** Suppression de "ko" (Korean) car pas dans Frontend

---

#### Étape 2.2: Ajouter mappings de noms de langues

**Fichier:** `llm/app/domain_config/domains/aviculture/config.py`

**Lignes ~290-304:**
```python
# AVANT
language_names = {
    "fr": "French",
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ar": "Arabic",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",  # ← À SUPPRIMER
    "th": "Thai",
    "vi": "Vietnamese",
}

# APRÈS (16 langues triées alphabétiquement)
language_names = {
    "ar": "Arabic",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hi": "Hindi",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "th": "Thai",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "zh": "Chinese",
}
```

---

#### Étape 2.3: Vérifier prompts système pour nouvelles langues

**Fichier:** `llm/app/domain_config/domains/aviculture/system_prompts.json`

**Vérifier que TOUS les prompts incluent:**
```
CRITICAL: Respond EXCLUSIVELY in {language_name}
```

**Prompts à vérifier:**
- standard_query
- calculation
- comparison
- general_poultry
- clarification_needed
- data_quality_check
- etc.

**Action:** S'assurer que la variable `{language_name}` est bien injectée pour toutes les langues

---

#### Étape 2.4: Tester les 5 nouvelles langues

**Tests LLM:**
```bash
# Test Hindi
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "मुर्गियों के लिए सबसे अच्छा चारा क्या है?", "language": "hi"}'

# Test Indonesian
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "Apa pakan terbaik untuk ayam?", "language": "id"}'

# Test Dutch
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "Wat is het beste voer voor kippen?", "language": "nl"}'

# Test Polish
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "Jaka jest najlepsza karma dla kur?", "language": "pl"}'

# Test Turkish
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "Tavuklar için en iyi yem nedir?", "language": "tr"}'
```

---

### Phase 3: Nettoyage Korean (ko)

**Durée estimée:** 15 minutes

#### Option A: Supprimer Korean (RECOMMANDÉ)

**Raison:** Pas de demande business, pas de locale Frontend/Backend

**Fichiers à modifier:**

1. **`llm/app/domain_config/domains/aviculture/system_prompts.json`**
   - Supprimer "ko" de `languages_supported`

2. **`llm/app/domain_config/domains/aviculture/config.py`**
   - Supprimer ligne `"ko": "Korean"` du dictionnaire `language_names`

3. **`llm/config/aviculture/system_prompts.json`** (si existant)
   - Supprimer "ko" de `languages_supported`

---

#### Option B: Ajouter Korean au Frontend/Backend

**Si besoin business pour marché coréen:**

**Fichiers à créer:**
1. `frontend/public/locales/ko.json` - Traductions coréennes
2. `backend/app/locales/ko.json` - Traductions backend

**Fichiers à modifier:**
1. `frontend/lib/languages/config.ts` - Ajouter config Korean
2. `backend/app/utils/i18n.py` - Ajouter 'ko' à SUPPORTED_LANGUAGES
3. `rag/config/config.py` - Ajouter "ko" à SUPPORTED_LANGUAGES

**Recommandation:** Option A (supprimer) sauf si besoin business

---

## 📝 Checklist de Complétion

### Phase 1: RAG (CRITIQUE)

- [ ] **1.1** Vérifier disponibilité dictionnaires (ar, ja, tr, vi)
- [ ] **1.2** Activer 4 langues dans `rag/config/config.py`
- [ ] **1.3** Configurer Google Translate fallback
  - [ ] Vérifier `GOOGLE_TRANSLATE_API_KEY` dans env
  - [ ] Activer `ENABLE_GOOGLE_TRANSLATE_FALLBACK=true`
- [ ] **1.4** Tester RAG pour 4 nouvelles langues
  - [ ] Test Arabic (ar)
  - [ ] Test Japanese (ja)
  - [ ] Test Turkish (tr)
  - [ ] Test Vietnamese (vi)

### Phase 2: LLM

- [ ] **2.1** Ajouter 5 langues à `system_prompts.json`
  - [ ] hi (Hindi)
  - [ ] id (Indonesian)
  - [ ] nl (Dutch)
  - [ ] pl (Polish)
  - [ ] tr (Turkish)
- [ ] **2.2** Mettre à jour `language_names` mapping
- [ ] **2.3** Vérifier prompts système
- [ ] **2.4** Tester LLM pour 5 nouvelles langues
  - [ ] Test Hindi (hi)
  - [ ] Test Indonesian (id)
  - [ ] Test Dutch (nl)
  - [ ] Test Polish (pl)
  - [ ] Test Turkish (tr)

### Phase 3: Nettoyage Korean

- [ ] **3.1** DÉCISION: Supprimer ou Ajouter Korean?
  - [ ] Option A: Supprimer de LLM
  - [ ] Option B: Ajouter à Frontend/Backend
- [ ] **3.2** Appliquer la décision choisie

### Phase 4: Validation Finale

- [ ] **4.1** Exécuter tests end-to-end pour TOUTES les 16 langues
- [ ] **4.2** Vérifier cohérence des 4 services
- [ ] **4.3** Mettre à jour documentation
- [ ] **4.4** Créer commit git avec changements

---

## 🧪 Plan de Tests

### Test 1: RAG pour chaque langue

**Script de test:**
```python
# test_rag_all_languages.py
import requests

LANGUAGES = [
    ("ar", "ما هو أفضل علف للدجاج؟"),
    ("de", "Was ist das beste Futter für Hühner?"),
    ("en", "What is the best feed for chickens?"),
    ("es", "¿Cuál es el mejor alimento para pollos?"),
    ("fr", "Quelle est la meilleure alimentation pour les poulets?"),
    ("hi", "मुर्गियों के लिए सबसे अच्छा चारा क्या है?"),
    ("id", "Apa pakan terbaik untuk ayam?"),
    ("it", "Qual è il miglior mangime per i polli?"),
    ("ja", "鶏に最適な飼料は何ですか？"),
    ("nl", "Wat is het beste voer voor kippen?"),
    ("pl", "Jaka jest najlepsza karma dla kur?"),
    ("pt", "Qual é a melhor ração para frangos?"),
    ("th", "อาหารที่ดีที่สุดสำหรับไก่คืออะไร?"),
    ("tr", "Tavuklar için en iyi yem nedir?"),
    ("vi", "Thức ăn tốt nhất cho gà là gì?"),
    ("zh", "鸡的最佳饲料是什么？"),
]

for lang_code, query in LANGUAGES:
    print(f"\n🧪 Testing {lang_code}...")
    response = requests.post(
        "http://localhost:8000/api/v1/chat",
        json={"query": query, "language": lang_code}
    )
    if response.status_code == 200:
        print(f"✅ {lang_code}: SUCCESS")
    else:
        print(f"❌ {lang_code}: FAILED - {response.status_code}")
```

---

### Test 2: LLM pour chaque langue

**Script de test:**
```python
# test_llm_all_languages.py
import requests

LANGUAGES = [
    ("ar", "ما هو أفضل علف للدجاج؟"),
    ("de", "Was ist das beste Futter für Hühner?"),
    ("en", "What is the best feed for chickens?"),
    ("es", "¿Cuál es el mejor alimento para pollos?"),
    ("fr", "Quelle est la meilleure alimentation pour les poulets?"),
    ("hi", "मुर्गियों के लिए सबसे अच्छा चारा क्या है?"),
    ("id", "Apa pakan terbaik untuk ayam?"),
    ("it", "Qual è il miglior mangime per i polli?"),
    ("ja", "鶏に最適な飼料は何ですか？"),
    ("nl", "Wat is het beste voer voor kippen?"),
    ("pl", "Jaka jest najlepsza karma dla kur?"),
    ("pt", "Qual é a melhor ração para frangos?"),
    ("th", "อาหารที่ดีที่สุดสำหรับไก่คืออะไร?"),
    ("tr", "Tavuklar için en iyi yem nedir?"),
    ("vi", "Thức ăn tốt nhất cho gà là gì?"),
    ("zh", "鸡的最佳饲料是什么？"),
]

for lang_code, query in LANGUAGES:
    print(f"\n🧪 Testing LLM {lang_code}...")
    response = requests.post(
        "http://localhost:8001/generate",
        json={"query": query, "language": lang_code}
    )
    if response.status_code == 200:
        result = response.json()
        # Vérifier que la réponse est dans la bonne langue
        print(f"✅ {lang_code}: SUCCESS")
        print(f"   Response preview: {result['response'][:100]}...")
    else:
        print(f"❌ {lang_code}: FAILED - {response.status_code}")
```

---

### Test 3: End-to-End pour chaque langue

**Flow complet:**
1. Utilisateur sélectionne langue dans Frontend
2. Envoie question via API
3. RAG traduit et cherche documents
4. LLM génère réponse dans la langue
5. Frontend affiche réponse traduite

**Script de test:**
```bash
# test_e2e_languages.sh
#!/bin/bash

LANGUAGES=("ar" "de" "en" "es" "fr" "hi" "id" "it" "ja" "nl" "pl" "pt" "th" "tr" "vi" "zh")

for lang in "${LANGUAGES[@]}"; do
    echo "🧪 Testing E2E for $lang..."

    # Test Frontend i18n
    if [ -f "frontend/public/locales/$lang.json" ]; then
        echo "  ✅ Frontend locale exists"
    else
        echo "  ❌ Frontend locale missing"
    fi

    # Test Backend i18n
    if [ -f "backend/app/locales/$lang.json" ]; then
        echo "  ✅ Backend locale exists"
    else
        echo "  ❌ Backend locale missing"
    fi

    # Test RAG support (check config)
    if grep -q "\"$lang\"" rag/config/config.py; then
        echo "  ✅ RAG supports language"
    else
        echo "  ❌ RAG missing language"
    fi

    # Test LLM support (check system_prompts)
    if grep -q "\"$lang\"" llm/app/domain_config/domains/aviculture/system_prompts.json; then
        echo "  ✅ LLM supports language"
    else
        echo "  ❌ LLM missing language"
    fi

    echo ""
done
```

---

## 📊 Métriques de Succès

### Objectif: 16/16 langues complètes

**Cibles:**
- ✅ Frontend: 16/16 (100%) - **DÉJÀ ATTEINT**
- ✅ Backend: 16/16 (100%) - **DÉJÀ ATTEINT**
- 🎯 RAG: 16/16 (100%) - **ACTUELLEMENT 9/16 (56%)**
- 🎯 LLM: 16/16 (100%) - **ACTUELLEMENT 12/16 (75%)**

### KPIs

1. **Couverture linguistique:** 16/16 langues (100%)
2. **Tests passants:** 16/16 langues testées avec succès
3. **Latence traduction:** < 200ms pour Google Translate fallback
4. **Qualité réponses:** Score RAGAS > 0.8 pour toutes langues

---

## 🚀 Déploiement

### Pré-requis

1. **Google Cloud Translation API configurée**
   - Créer projet Google Cloud
   - Activer Cloud Translation API
   - Créer clé API
   - Ajouter `GOOGLE_TRANSLATE_API_KEY` aux variables d'environnement

2. **Tests locaux réussis**
   - Tous les tests Phase 1-3 passés
   - Validation end-to-end OK

3. **Documentation à jour**
   - README mis à jour avec 16 langues
   - Guide utilisateur traduit

### Ordre de déploiement

1. **RAG service** (CRITIQUE - Phase 1)
   - Deploy config changes
   - Activer Google Translate fallback
   - Monitoring traduction

2. **LLM service** (Phase 2)
   - Deploy config changes
   - Update system prompts
   - Tester génération multilingue

3. **Frontend/Backend** (Déjà OK)
   - Aucun changement nécessaire
   - Vérification finale

### Rollback plan

**Si problème avec nouvelles langues:**
1. Réactiver commentaires dans `rag/config/config.py`
2. Retour aux 9 langues RAG stables
3. Désactiver Google Translate fallback
4. Investiguer logs

---

## 📚 Documentation à Mettre à Jour

### Fichiers à modifier

1. **README.md principal**
   - Section langues supportées
   - Mettre à jour de 9 → 16 langues

2. **docs/README.md**
   - Ajouter référence à ce plan

3. **docs/guides/COMPLETE_SYSTEM_DOCUMENTATION.md**
   - Section multilingue
   - Architecture traduction

4. **docs/frontend/FRONTEND_ARCHITECTURE.md** (si existant)
   - i18n system complet

5. **docs/backend/BACKEND_ARCHITECTURE.md** (si existant)
   - Translation service

---

## ⏱️ Estimation Temps Total

| Phase | Tâche | Durée |
|-------|-------|-------|
| Phase 1 | RAG - 4 langues | 2-3h |
| Phase 2 | LLM - 5 langues | 1-2h |
| Phase 3 | Nettoyage Korean | 15min |
| Phase 4 | Tests E2E | 1h |
| Phase 5 | Documentation | 30min |
| **TOTAL** | | **5-7h** |

**Recommandation:** Sprint de 1 journée pour tout compléter

---

## 🎯 Priorités

### 🔴 URGENT (Phase 1)

**RAG - 4 langues bloquées:**
- ar (Arabic)
- ja (Japanese)
- tr (Turkish)
- vi (Vietnamese)

**Raison:** Ces utilisateurs ne peuvent PAS utiliser la plateforme correctement

---

### 🟡 IMPORTANT (Phase 2)

**LLM - 5 langues non optimisées:**
- hi (Hindi)
- id (Indonesian)
- nl (Dutch)
- pl (Polish)
- tr (Turkish)

**Raison:** Fonctionnalité dégradée mais utilisable

---

### 🟢 OPTIONNEL (Phase 3)

**Korean cleanup:**
- Décision business nécessaire
- Pas d'impact utilisateur actuel

---

## 📝 Notes

### Note 1: Ancien nom "ai-service"

Le service RAG se nommait auparavant `ai-service/`.
**Nouveau nom:** `rag/`

**Fichiers à vérifier:**
- ✅ Documentation mise à jour
- ⚠️ Vérifier imports/paths dans code
- ⚠️ Vérifier docker-compose.yml
- ⚠️ Vérifier variables d'environnement

---

### Note 2: Google Translate Coûts

**Pricing Google Cloud Translation API:**
- $20 par million de caractères
- Estimation mensuelle pour 4 langues: ~$50-100/mois
- Peut être réduit avec cache intelligent

**Alternative:** Traduction LLM (plus coûteux mais meilleure qualité)

---

### Note 3: Dictionnaires vs Google Translate

**Avantages dictionnaires:**
- ✅ Gratuit
- ✅ Rapide (pas d'API call)
- ✅ Terminology spécifique aviculture

**Avantages Google Translate:**
- ✅ Pas de maintenance
- ✅ Support toutes langues
- ✅ Traduction contexte

**Recommandation:** Hybride
- Dictionnaires pour langues principales (9 actuelles)
- Google Translate fallback pour 4 nouvelles langues

---

## ✅ Validation Finale

### Critères de succès

- [ ] Les 16 langues sont activées dans RAG config
- [ ] Les 16 langues sont activées dans LLM config
- [ ] Google Translate fallback fonctionne pour ar, ja, tr, vi
- [ ] Tests E2E passent pour 16/16 langues
- [ ] Aucune régression sur 8 langues existantes
- [ ] Documentation à jour
- [ ] Korean supprimé (ou ajouté partout)
- [ ] Monitoring activé pour nouvelles langues

---

**Prêt à démarrer l'implémentation!** 🚀

Prochaine étape: Phase 1.1 - Vérifier disponibilité des dictionnaires
