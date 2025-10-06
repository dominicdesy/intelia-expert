# CHECKLIST COMPLÈTE DE VALIDATION DE FONDATION
## Système LLM Avicole - Préparation pour Expansion Massive de Données

**Date de création:** 2025-01-15
**Version:** 1.0
**Objectif:** Valider que le système est prêt pour l'ajout de centaines de documents et des dizaines de races supplémentaires

---

## CONTEXTE CRITIQUE

L'utilisateur a déclaré : *"En ce moment, les informations présentes dans la base de données PostgreSQL et Weaviate sont limitées. Je veux m'assurer que la fondation du LLM est très solide avant d'ajouter des centaines de documents."*

**Données actuelles identifiées dans le code:**
- PostgreSQL: Races détectées (Ross 308, Cobb 500, avec mapping vers "308/308 FF", "500")
- Weaviate: Volume exact inconnu, nécessite vérification
- Breeds registry: 51 races configurées (22 broilers, 18 layers, 2 breeders)
- Support de 12 langues (fr, en, es, de, it, pt, nl, pl, hi, id, th, zh)

---

## PARTIE 1: VALIDATION ARCHITECTURE & SCALABILITÉ

### 1.1 Test de Scalabilité Weaviate

**Fichier analysé:** `C:\intelia_gpt\intelia-expert\llm\core\rag_weaviate_core.py`

#### Tests à exécuter:

☐ **Test 1: Vérifier le volume actuel de documents**
```python
# Méthode: Exécuter dans la console Python
from llm.core.rag_weaviate_core import WeaviateCore
# Après initialisation:
# - Utiliser client.collections.list_all() pour lister les collections
# - Compter le nombre de documents par collection
# - Identifier les classes/collections existantes (PoultryDocument, PoultryKnowledge, etc.)
```
**Critères:**
- [ ] Nombre actuel de documents: _______ (à remplir)
- [ ] Collections existantes: _______ (à lister)
- [ ] Latence moyenne pour 1 query: _______ ms
- [ ] OBJECTIF: < 500ms pour queries simples

☐ **Test 2: Vérifier les index Weaviate**
```bash
# Connexion directe au cluster Weaviate
# URL: https://xmlc4jvtu6hfw9zrrmnw.c0.us-east1.gcp.weaviate.cloud
# Vérifier:
# - Présence d'index vectoriels (HNSW configuré)
# - Configuration de distance metric (cosine, dot, l2)
# - Paramètres HNSW: efConstruction, maxConnections
```
**Critères:**
- [ ] Index vectoriel actif: OUI / NON
- [ ] Distance metric: _______
- [ ] HNSW efConstruction: _______ (recommandé: 128-256)
- [ ] HNSW maxConnections: _______ (recommandé: 32-64)

☐ **Test 3: Batch import capacity**
```python
# Test d'import batch avec 100 documents factices
# Mesurer:
# - Temps d'import
# - Taux de succès
# - Erreurs éventuelles
```
**Critères:**
- [ ] Import de 100 docs réussit: OUI / NON
- [ ] Temps pour 100 docs: _______ secondes
- [ ] OBJECTIF: < 30 secondes pour 100 docs
- [ ] Projection pour 10,000 docs: _______ minutes

☐ **Test 4: Performance avec volume simulé**
**Action:** Charger 1000 documents de test et mesurer la latence de query
**Critères:**
- [ ] Latence P50: _______ ms (objectif: < 500ms)
- [ ] Latence P95: _______ ms (objectif: < 2000ms)
- [ ] Latence P99: _______ ms (objectif: < 5000ms)
- [ ] VERDICT: READY / NEEDS OPTIMIZATION

---

### 1.2 Test de Scalabilité PostgreSQL

**Fichier analysé:** `C:\intelia_gpt\intelia-expert\llm\core\rag_postgresql_retriever.py`

#### Tests à exécuter:

☐ **Test 1: Vérifier le schéma et les index actuels**
```sql
-- Se connecter à PostgreSQL et exécuter:
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Vérifier les tables critiques:
-- - companies, breeds, strains, documents, metrics, data_categories
```
**Critères:**
- [ ] Table `metrics` indexée sur: `age_min`, `age_max`, `metric_name`: OUI / NON
- [ ] Table `strains` indexée sur: `strain_name`, `species`: OUI / NON
- [ ] Table `documents` indexée sur: `sex`, `strain_id`: OUI / NON
- [ ] Index composites présents: OUI / NON (ex: `strain_id + age_min + sex`)

☐ **Test 2: Mesurer le volume actuel**
```sql
-- Compter les rows dans chaque table
SELECT
  'metrics' AS table_name, COUNT(*) AS row_count FROM metrics
UNION ALL
SELECT 'documents', COUNT(*) FROM documents
UNION ALL
SELECT 'strains', COUNT(*) FROM strains
UNION ALL
SELECT 'breeds', COUNT(*) FROM breeds;
```
**Résultats:**
- [ ] Metrics: _______ rows
- [ ] Documents: _______ rows
- [ ] Strains: _______ rows
- [ ] Breeds: _______ rows

☐ **Test 3: Performance des requêtes actuelles**
```sql
-- Test query: récupérer les métriques pour Ross 308 à 35 jours
EXPLAIN ANALYZE
SELECT m.metric_name, m.value_numeric, m.unit, m.age_min
FROM metrics m
JOIN documents d ON m.document_id = d.id
JOIN strains s ON d.strain_id = s.id
WHERE s.strain_name = '308/308 FF'
  AND m.age_min <= 35 AND m.age_max >= 35
  AND m.metric_name LIKE 'body_weight for %'
ORDER BY m.value_numeric DESC
LIMIT 10;
```
**Critères:**
- [ ] Temps d'exécution: _______ ms (objectif: < 100ms)
- [ ] Plan utilise Index Scan: OUI / NON
- [ ] Plan utilise Seq Scan: OUI / NON (MAUVAIS si OUI)
- [ ] VERDICT: OPTIMIZED / NEEDS INDEX

☐ **Test 4: Projection capacité pour expansion**
**Scénario:** 50 races × 20 métriques × 70 jours × 3 sexes = **210,000 rows**
```sql
-- Test avec EXPLAIN sur une requête simulée
-- Estimer le temps de query avec ce volume
```
**Critères:**
- [ ] Temps estimé pour query: _______ ms
- [ ] Acceptable (< 500ms): OUI / NON
- [ ] Partitioning nécessaire: OUI / NON
- [ ] VERDICT: READY / NEEDS PARTITIONING

---

### 1.3 Test de Robustesse Redis Cache

**Fichier analysé:** `C:\intelia_gpt\intelia-expert\llm\cache\cache_core.py`

#### Tests à exécuter:

☐ **Test 1: Vérifier la configuration actuelle**
```python
# Vérifier les limites configurées dans cache_core.py
# Ligne 52-54:
# max_value_bytes: 100_000 (100KB)
# max_keys_per_namespace: 1000
# total_memory_limit_mb: 100MB
```
**Configuration actuelle:**
- [ ] Max value size: 100 KB (ligne 52)
- [ ] Max keys per namespace: 1,000 (ligne 53)
- [ ] Total memory limit: 100 MB (ligne 54)
- [ ] Auto-purge enabled: True (ligne 62)
- [ ] Compression enabled: False (ligne 62)

☐ **Test 2: Tester le fallback si Redis DOWN**
```python
# Simuler Redis DOWN
# Vérifier que le système continue de fonctionner
# Code détecté dans cache_core.py:
# - _is_operational() retourne False si erreurs (ligne 292-301)
# - get() retourne None si non opérationnel (ligne 308-310)
# - set() retourne False si non opérationnel (ligne 356-359)
```
**Critères:**
- [ ] Système démarre sans Redis: OUI / NON
- [ ] Queries continuent (sans cache): OUI / NON
- [ ] Message log clair: OUI / NON
- [ ] Aucun crash: OUI / NON
- [ ] VERDICT: ROBUST / FRAGILE

☐ **Test 3: Vérifier les TTL par namespace**
```python
# Vérifier dans cache_core.py lignes 69-73:
# ttl_embeddings: 7200 (2h)
# ttl_search_results: 1800 (30min)
# ttl_responses: 3600 (1h)
# ttl_intent_results: 3600 (1h)
```
**Configuration TTL:**
- [ ] Embeddings: 2 heures (approprié pour données stables)
- [ ] Search results: 30 minutes (approprié pour résultats dynamiques)
- [ ] Responses: 1 heure (approprié pour réponses générées)
- [ ] TTL cohérents avec volatilité données: OUI / NON

☐ **Test 4: Test de limite mémoire**
```python
# Remplir Redis jusqu'à 85% de la limite (85 MB / 100 MB)
# Vérifier que auto-purge se déclenche (ligne 599-601)
# Méthode: _auto_purge_cache() ligne 644
```
**Critères:**
- [ ] Auto-purge se déclenche à 85%: OUI / NON
- [ ] Namespaces purgés dans l'ordre (searches → responses → embeddings): OUI / NON
- [ ] Mémoire redescend sous 70%: OUI / NON
- [ ] VERDICT: AUTO-SCALING WORKS / NEEDS FIX

---

### 1.4 Test Gestion des Erreurs (Cascade Fallbacks)

**Fichier analysé:** `C:\intelia_gpt\intelia-expert\llm\core\handlers\standard_handler.py`

#### Tests à exécuter:

☐ **Test 1: Si PostgreSQL échoue → Weaviate fallback**
```python
# Simuler échec PostgreSQL (timeout, erreur connexion)
# Vérifier code ligne 131-162 standard_handler.py:
# - PostgreSQL search_metrics() échoue
# - Log "PostgreSQL no results → Weaviate fallback" (ligne 161)
# - Weaviate search appelé (ligne 164-177)
```
**Critères:**
- [ ] PostgreSQL error logged: OUI / NON
- [ ] Weaviate appelé automatiquement: OUI / NON
- [ ] User reçoit une réponse (même si Weaviate): OUI / NON
- [ ] Temps total < 5s: OUI / NON
- [ ] VERDICT: RESILIENT / FRAGILE

☐ **Test 2: Si Weaviate échoue → Que se passe-t-il ?**
```python
# Simuler échec Weaviate (ligne 450-462 standard_handler.py)
# Vérifier:
# - Exception catchée
# - RAGResult avec source=ERROR
# - Message user-friendly
```
**Critères:**
- [ ] Exception catchée proprement: OUI / NON
- [ ] Message d'erreur clair pour l'utilisateur: OUI / NON
- [ ] Pas de crash système: OUI / NON
- [ ] VERDICT: GRACEFUL DEGRADATION / CRASH

☐ **Test 3: Si OpenAI rate limit → Retry logic**
```python
# Vérifier dans le code si retry logic existe
# Chercher: retry, backoff, rate_limit
# NOTE: Pas trouvé dans les fichiers analysés
```
**Critères:**
- [ ] Retry logic implémenté: OUI / NON
- [ ] Exponential backoff: OUI / NON
- [ ] Message user si échec final: OUI / NON
- [ ] **ACTION REQUISE:** Implémenter retry logic si absent

☐ **Test 4: Si PostgreSQL lent (timeout)**
```python
# Vérifier timeout configuré dans rag_postgresql_retriever.py
# Ligne 76: command_timeout=30 (30 secondes)
```
**Critères:**
- [ ] Timeout PostgreSQL: 30 secondes (ligne 76)
- [ ] Timeout approprié: OUI / NON (recommandé: 10-15s)
- [ ] **ACTION:** Réduire à 15s pour éviter attente longue

---

## PARTIE 2: VALIDATION QUALITÉ RÉPONSES

### 2.1 Test Anti-Hallucination sur Données Limitées

**Fichiers analysés:**
- `C:\intelia_gpt\intelia-expert\llm\security\guardrails\hallucination_detector.py`
- `C:\intelia_gpt\intelia-expert\llm\security\guardrails\core.py`

#### Tests à exécuter:

☐ **Test 1: Question sur race NON supportée (ISA Brown)**
```
Input: "Quel est le poids cible pour des ISA Brown à 30 semaines ?"
Expected Behavior:
1. Intent processor détecte "breed: isa brown"
2. PostgreSQL ne trouve AUCUN résultat (race layers, données limitées)
3. Weaviate ne trouve AUCUN document pertinent
4. SYSTÈME DOIT RÉPONDRE: "Je n'ai pas de données pour ISA Brown à 30 semaines"
5. NE DOIT PAS halluciner un poids
```
**Test réel:**
- [ ] Réponse obtenue: _______
- [ ] Contient "données indisponibles" ou équivalent: OUI / NON
- [ ] Contient un chiffre inventé: OUI / NON (ÉCHEC si OUI)
- [ ] Source mentionnée: OUI / NON
- [ ] VERDICT: SAFE / HALLUCINATION

☐ **Test 2: Question sur âge hors range (Ross 308 à 49 jours)**
```
Input: "Quel est le poids de Ross 308 mâles à 49 jours ?"
Context: Les données PostgreSQL vont typiquement jusqu'à 42 jours pour broilers
Expected Behavior:
1. PostgreSQL cherche age_min <= 49 AND age_max >= 49
2. Aucun résultat trouvé
3. SYSTÈME DOIT RÉPONDRE: "Mes données vont jusqu'à 42 jours pour Ross 308"
4. Peut proposer: "À 42 jours, le poids est de X grammes"
5. NE DOIT PAS extrapoler
```
**Test réel:**
- [ ] Réponse obtenue: _______
- [ ] Mentionne limite de données: OUI / NON
- [ ] Extrapolation détectée: OUI / NON (ÉCHEC si OUI)
- [ ] VERDICT: SAFE / HALLUCINATION

☐ **Test 3: Question sur métrique non applicable**
```
Input: "Quelle est la production d'œufs de Ross 308 à 25 semaines ?"
Context: Ross 308 = broiler, pas de données "egg production"
Expected Behavior:
1. Species filter détecte "broiler" (via breeds_registry)
2. Métrique "egg production" incompatible
3. SYSTÈME DOIT RÉPONDRE: "Ross 308 est une race de chair (broiler), la production d'œufs ne s'applique pas"
```
**Test réel:**
- [ ] Réponse obtenue: _______
- [ ] Détecte incompatibilité species: OUI / NON
- [ ] Invente des chiffres: OUI / NON (ÉCHEC si OUI)
- [ ] VERDICT: SAFE / HALLUCINATION

☐ **Test 4: Conflit PostgreSQL vs Weaviate**
```
Scenario: PostgreSQL dit "2190g" pour Ross 308 à 35j, Weaviate dit "2100g"
Expected Behavior:
1. Guardrails détectent inconsistency (core.py ligne 58-165)
2. Priorité à PostgreSQL (données structurées > documents)
3. Réponse mentionne la source: "Selon les données officielles Ross 308..."
```
**Test réel:**
- [ ] Source prioritaire: PostgreSQL / Weaviate / Mixte
- [ ] Source citée dans la réponse: OUI / NON
- [ ] Guardrail "consistency_checker" actif: OUI / NON
- [ ] VERDICT: CONSISTENT / CONFLICTING

---

### 2.2 Test Guardrails Complet

**Fichier analysé:** `C:\intelia_gpt\intelia-expert\llm\security\guardrails\core.py`

#### Guardrails détectés dans le code:

1. **Evidence Checker** (ligne 52, 96)
2. **Hallucination Detector** (ligne 53, 97-99)
3. **Thresholds configurables** (ligne 56, config.py)

☐ **Test 1: Evidence Checker**
```python
# Code: evidence_checker._check_evidence_support(response, context_docs)
# Ligne 96 de core.py
# Test: Réponse qui cite des documents vs réponse sans citation
```
**Tests:**
- [ ] **Test A:** Réponse avec citation directe → Score: _______ (attendu > 0.7)
- [ ] **Test B:** Réponse sans citation → Score: _______ (attendu < 0.3)
- [ ] **Test C:** Seuil de rejet: _______ (config dans config.py)
- [ ] Evidence checker rejette réponses non-sourcées: OUI / NON

☐ **Test 2: Hallucination Detector**
```python
# Code: hallucination_detector._detect_hallucination_risk(response, context_docs)
# Ligne 97-99 de core.py
```
**Tests:**
- [ ] **Test A:** Réponse avec chiffres PRÉSENTS dans docs → Risk: _______ (attendu < 0.3)
- [ ] **Test B:** Réponse avec chiffres ABSENTS des docs → Risk: _______ (attendu > 0.7)
- [ ] **Test C:** Réponse avec opinions ("je pense") → Risk: _______ (attendu > 0.8)
- [ ] Hallucination detector rejette spéculations: OUI / NON

☐ **Test 3: Thresholds de validation**
```python
# Vérifier config/guardrails_config.py (non trouvé, à chercher)
# Code core.py ligne 56: self.thresholds = get_thresholds(verification_level)
# Ligne 217-230: analyse des violations
```
**Configuration actuelle:**
- [ ] Evidence minimum: _______ (recommandé: 0.5-0.7)
- [ ] Hallucination maximum: _______ (recommandé: 0.3-0.5)
- [ ] Max violations: _______ (recommandé: 0)
- [ ] Max warnings: _______ (recommandé: 3)

☐ **Test 4: Quick verification (rapide)**
```python
# Code core.py ligne 167-194: quick_verify()
# Test de overlap entre réponse et documents
# Seuil: 30% overlap (ligne 190)
```
**Test:**
- [ ] Quick verify fonctionne: OUI / NON
- [ ] Seuil 30% approprié: OUI / NON
- [ ] Temps d'exécution: _______ ms (objectif < 100ms)

---

### 2.3 Test Multilingue (12 langues)

**Fichier analysé:** `C:\intelia_gpt\intelia-expert\llm\security\ood\detector.py`

#### Langues supportées identifiées (ligne 84-85):

1. **Traitement direct:** FR, EN
2. **Traduction service:** ES, DE, IT, PT, NL, PL, ID
3. **Non-Latin scripts:** HI, ZH, TH

☐ **Test 1: Détection de langue**
```python
# Code: detect_language_enhanced(query) - ligne 153
# Tester 12 langues avec même question: "Poids Ross 308 35 jours"
```

| Langue | Question | Detection | Confidence | Status |
|--------|----------|-----------|------------|--------|
| FR | "Poids Ross 308 35 jours" | fr | _____ | ☐ |
| EN | "Weight Ross 308 35 days" | en | _____ | ☐ |
| ES | "Peso Ross 308 35 días" | es | _____ | ☐ |
| DE | "Gewicht Ross 308 35 Tage" | de | _____ | ☐ |
| IT | "Peso Ross 308 35 giorni" | it | _____ | ☐ |
| PT | "Peso Ross 308 35 dias" | pt | _____ | ☐ |
| NL | "Gewicht Ross 308 35 dagen" | nl | _____ | ☐ |
| PL | "Waga Ross 308 35 dni" | pl | _____ | ☐ |
| HI | "रॉस 308 35 दिन वजन" | hi | _____ | ☐ |
| ID | "Berat Ross 308 35 hari" | id | _____ | ☐ |
| TH | "น้ำหนัก Ross 308 35 วัน" | th | _____ | ☐ |
| ZH | "罗斯308 35天体重" | zh | _____ | ☐ |

**Critères globaux:**
- [ ] 12/12 langues détectées correctement: OUI / NON
- [ ] Confidence moyenne > 0.80: OUI / NON
- [ ] Aucune confusion entre langues proches (es/pt, nl/de): OUI / NON

☐ **Test 2: Traduction préserve entités**
```python
# Code: translation_handler.translate_query() - detector.py ligne 406-408
# Vérifier que "Ross 308" et "35" sont préservés après traduction
```
**Tests:**
- [ ] **ES → FR:** "Ross 308 35 días" → contient "Ross 308" et "35": OUI / NON
- [ ] **DE → FR:** "Ross 308 35 Tage" → contient "Ross 308" et "35": OUI / NON
- [ ] **ZH → FR:** "罗斯308 35天" → contient "Ross 308" et "35": OUI / NON
- [ ] Entités numériques préservées: OUI / NON
- [ ] Noms de race préservés: OUI / NON

☐ **Test 3: Réponse dans langue originale**
```python
# Vérifier que la réponse finale est traduite dans la langue de la question
# (Nécessite vérification du response_generator)
```
**Tests:**
- [ ] Question EN → Réponse EN: OUI / NON
- [ ] Question ES → Réponse ES: OUI / NON
- [ ] Question ZH → Réponse ZH: OUI / NON
- [ ] Qualité traduction cohérente: OUI / NON

---

## PARTIE 3: VALIDATION DATA FLOW

### 3.1 Test Bout-en-Bout (10 Scénarios)

#### Scénario 1: Question Parfaite (Données disponibles)

```
Input: "Quel est le poids cible pour des mâles Ross 308 à 35 jours ?"
Language: FR
```

**Flow attendu:**

1. **OOD Detection** (detector.py ligne 134-174)
   - [ ] Langue détectée: `fr`
   - [ ] Score OOD: _______ (attendu > 0.30)
   - [ ] Décision: ACCEPTÉ / REJETÉ
   - [ ] Temps: _______ ms

2. **Intent Extraction** (intents.json ligne 1-100)
   - [ ] Breed: `ross 308` détecté
   - [ ] Age: `35` détecté
   - [ ] Sex: `male` détecté
   - [ ] Metric: `body_weight` détecté
   - [ ] Temps: _______ ms

3. **Routing** (standard_handler.py ligne 83-87)
   - [ ] Hint: `postgresql` (données structurées disponibles)
   - [ ] Filters: `{"species": "broiler"}` extraits
   - [ ] Temps: _______ ms

4. **PostgreSQL Query** (rag_postgresql_retriever.py ligne 161-357)
   - [ ] SQL généré avec: `strain_name = '308/308 FF'`, `age_min <= 35`, `sex = 'male'`
   - [ ] Résultats trouvés: _______ docs
   - [ ] Score pertinence: _______
   - [ ] Temps: _______ ms

5. **Response Generation**
   - [ ] Contexte docs passé au générateur
   - [ ] Réponse: "Le poids cible est de 2190 grammes pour des mâles Ross 308 à 35 jours."
   - [ ] Source citée: OUI / NON
   - [ ] Temps: _______ ms

6. **Guardrails** (core.py ligne 58-165)
   - [ ] Evidence support: _______ (attendu > 0.7)
   - [ ] Hallucination risk: _______ (attendu < 0.3)
   - [ ] Violations: _______ (attendu: 0)
   - [ ] Décision: PASS / FAIL
   - [ ] Temps: _______ ms

7. **Total**
   - [ ] Temps total: _______ ms (objectif: < 2000ms)
   - [ ] Réponse correcte: OUI / NON
   - [ ] VERDICT: SUCCESS / FAIL

---

#### Scénario 2: Question Vague (Clarification requise)

```
Input: "Quel aliment donner à mes poussins ?"
Language: FR
```

**Flow attendu:**

1. **OOD Detection**
   - [ ] Score OOD: _______ (attendu > 0.30, question avicole)
   - [ ] Décision: ACCEPTÉ / REJETÉ

2. **Intent Extraction**
   - [ ] Breed: `null` (MANQUANT)
   - [ ] Age: `null` (MANQUANT)
   - [ ] Metric: `feed` détecté
   - [ ] Status: INCOMPLET

3. **Routing**
   - [ ] Hint: `needs_clarification`
   - [ ] Missing fields: `["breed", "age_days"]`

4. **PostgreSQL Validator** (standard_handler.py ligne 206-249)
   - [ ] Validation status: `needs_fallback`
   - [ ] Helpful message généré: OUI / NON
   - [ ] Message: _______

5. **Response**
   - [ ] Contient demande de clarification: OUI / NON
   - [ ] Exemple: "Pour vous aider, pourriez-vous préciser la race et l'âge de vos poussins ?"
   - [ ] VERDICT: CLARIFICATION HANDLED / ECHEC

---

#### Scénario 3: Question Hors-Domaine

```
Input: "Quel temps fera-t-il demain ?"
Language: FR
```

**Flow attendu:**

1. **OOD Detection** (detector.py ligne 300-341)
   - [ ] Normalized query: "quel temps fera demain"
   - [ ] Domain words found: _______ (attendu: 0)
   - [ ] Score OOD: _______ (attendu < 0.30)
   - [ ] Threshold: 0.30 (ligne 343-344)
   - [ ] Décision: REJETÉ

2. **Response**
   - [ ] Source: `OOD_FILTERED`
   - [ ] Message: "Cette question ne concerne pas l'aviculture" (ou équivalent)
   - [ ] Pas de recherche PostgreSQL/Weaviate: CONFIRMÉ
   - [ ] VERDICT: OOD REJECTED CORRECTLY

---

#### Scénario 4: Question Multilingue (Espagnol)

```
Input: "¿Cuál es el peso de Ross 308 machos a 35 días?"
Language: ES
```

**Flow attendu:**

1. **Language Detection** (detector.py ligne 152-158)
   - [ ] Langue détectée: `es`
   - [ ] Confidence: _______ (attendu > 0.90)

2. **Translation** (detector.py ligne 384-457)
   - [ ] Traduction ES → FR: _______
   - [ ] Entités préservées ("Ross 308", "35"): OUI / NON
   - [ ] Translation confidence: _______

3. **Processing**
   - [ ] Intent extraction sur texte traduit
   - [ ] PostgreSQL query réussit: OUI / NON
   - [ ] Résultats trouvés: _______

4. **Response Translation**
   - [ ] Réponse générée en FR
   - [ ] Réponse traduite FR → ES: OUI / NON
   - [ ] Réponse finale en espagnol: OUI / NON
   - [ ] VERDICT: MULTILINGUAL SUCCESS / FAIL

---

#### Scénario 5: Calcul de Moulée (Plage d'âges)

```
Input: "Combien de moulée pour 20,000 poulets Ross 308 de 1 à 35 jours ?"
Language: FR
```

**Flow attendu:**

1. **Intent Extraction**
   - [ ] Breed: `ross 308` détecté
   - [ ] Start age: `1` détecté
   - [ ] Target age: `35` détecté
   - [ ] Bird count: `20000` détecté (ligne 133-159 rag_postgresql_retriever.py)
   - [ ] Metric: `feed_intake` détecté

2. **Calcul Detection** (rag_postgresql_retriever.py ligne 206-221)
   - [ ] `is_feed_calc` = True détecté
   - [ ] Méthode: `_calculate_feed_range()` appelée (ligne 359)

3. **PostgreSQL Feed Calculation** (ligne 359-575)
   - [ ] SQL: `SELECT feed_intake WHERE age_min BETWEEN 1 AND 35`
   - [ ] Résultats: _______ jours de données
   - [ ] Total feed per bird: _______ kg
   - [ ] Total for 20,000 birds: _______ tonnes

4. **Response**
   - [ ] Détail quotidien fourni: OUI / NON
   - [ ] Total en tonnes calculé: OUI / NON
   - [ ] Formule visible: OUI / NON
   - [ ] VERDICT: CALCULATION SUCCESS / FAIL

---

#### Scénario 6: Question avec Species Filter (Broiler vs Layer)

```
Input: "Comparaison Cobb 500 et ISA Brown à 42 jours"
Language: FR
```

**Flow attendu:**

1. **Intent Extraction**
   - [ ] Breeds: `["cobb 500", "isa brown"]` détectés
   - [ ] Species: Cobb 500 = broiler, ISA Brown = layer (intents.json ligne 11-55)

2. **Species Validation**
   - [ ] Comparaison cross-species détectée
   - [ ] Règle: `allow_cross_species: false` (intents.json ligne 99)
   - [ ] Action: REJET ou WARNING

3. **Response**
   - [ ] Message: "Impossible de comparer races de catégories différentes (broiler vs layer)"
   - [ ] Alternative proposée: OUI / NON
   - [ ] VERDICT: VALIDATION WORKS / FAILS

---

#### Scénario 7: Données Conflictuelles (PostgreSQL vs Weaviate)

```
Input: "Quel est le poids de Ross 308 à 21 jours ?"
Scenario: PostgreSQL dit "850g", Weaviate dit "870g"
```

**Flow attendu:**

1. **Double Search**
   - [ ] PostgreSQL retourne: 850g
   - [ ] Weaviate retourne: 870g

2. **Guardrails Consistency Check**
   - [ ] Inconsistency détectée: OUI / NON
   - [ ] Warning généré: OUI / NON

3. **Priority Rule**
   - [ ] Source prioritaire: PostgreSQL (données structurées)
   - [ ] Réponse finale: 850g
   - [ ] Mention source: "Selon les données officielles Ross 308..."
   - [ ] VERDICT: CONFLICT RESOLVED / AMBIGUOUS

---

#### Scénario 8: Question avec Sexe Explicite (Mode Strict)

```
Input: "Poids des FEMELLES Ross 308 à 35 jours UNIQUEMENT"
Language: FR
```

**Flow attendu:**

1. **Intent Extraction**
   - [ ] Sex: `female` détecté
   - [ ] `has_explicit_sex`: `true` détecté (emphase utilisateur)

2. **PostgreSQL Query** (rag_postgresql_retriever.py ligne 661-707)
   - [ ] Mode STRICT activé (ligne 676-682)
   - [ ] SQL: `WHERE LOWER(d.sex) = 'female'` (pas de fallback)
   - [ ] Résultats: UNIQUEMENT femelles

3. **Response**
   - [ ] Résultats incluent mixed/as_hatched: NON
   - [ ] VERDICT: STRICT MODE WORKS / FAILS

---

#### Scénario 9: Question Vétérinaire (Disclaimer requis)

```
Input: "Mon poulet est malade, que faire ?"
Language: FR
```

**Flow attendu:**

1. **OOD Detection**
   - [ ] Question avicole: OUI (acceptée)

2. **Veterinary Detection** (veterinary_handler.py ligne 120-175)
   - [ ] Keywords détectés: `["malade", "disease"]` (ligne 107, 132+ keywords)
   - [ ] `is_veterinary_query()` = True

3. **Response with Disclaimer**
   - [ ] Réponse générée normalement
   - [ ] Disclaimer ajouté (ligne 178-210)
   - [ ] Disclaimer en français: OUI / NON
   - [ ] Contient: "Consultez un vétérinaire qualifié" (ou équivalent)
   - [ ] VERDICT: DISCLAIMER ADDED / MISSING

---

#### Scénario 10: Cache Hit (Performance)

```
Input: "Poids Ross 308 mâles 35 jours" (DEUXIÈME FOIS)
Language: FR
```

**Flow attendu:**

1. **Cache Lookup** (cache_core.py ligne 308-348)
   - [ ] Cache key généré: _______
   - [ ] Cache hit: OUI / NON
   - [ ] Namespace: `responses`
   - [ ] TTL: 3600s (1 heure)

2. **Performance**
   - [ ] Temps avec cache: _______ ms (objectif: < 50ms)
   - [ ] Temps sans cache: _______ ms
   - [ ] Speedup: _______x
   - [ ] VERDICT: CACHE EFFECTIVE / INEFFECTIVE

---

## PARTIE 4: VALIDATION SÉCURITÉ

### 4.1 Test OOD (Out-of-Domain)

**Fichier analysé:** `C:\intelia_gpt\intelia-expert\llm\security\ood\detector.py`

#### Tests par stratégie:

☐ **Stratégie 1: Direct (FR/EN)** (ligne 300-382)

**Test avec 10 questions avicoles:**
1. "Poids Ross 308 35 jours" → Score: _______ (attendu > 0.50)
2. "Feed conversion broilers" → Score: _______ (attendu > 0.50)
3. "Mortalité poulets semaine 3" → Score: _______ (attendu > 0.50)
4. "Housing system layers" → Score: _______ (attendu > 0.40)
5. "Vaccination schedule chickens" → Score: _______ (attendu > 0.45)
6. "Température élevage 1ère semaine" → Score: _______ (attendu > 0.40)
7. "Densité poulets m²" → Score: _______ (attendu > 0.45)
8. "Lighting program broilers" → Score: _______ (attendu > 0.40)
9. "Consommation eau poulets" → Score: _______ (attendu > 0.45)
10. "Bec trimming layers" → Score: _______ (attendu > 0.35)

**Acceptance rate:** _______ / 10 (objectif: 10/10)

**Test avec 10 questions hors-domaine:**
1. "Météo demain Paris" → Score: _______ (attendu < 0.20)
2. "Recette tarte aux pommes" → Score: _______ (attendu < 0.10)
3. "Capital de la France" → Score: _______ (attendu < 0.10)
4. "Bitcoin price today" → Score: _______ (attendu < 0.10)
5. "Comment aller à Lyon" → Score: _______ (attendu < 0.10)
6. "Film à voir ce soir" → Score: _______ (attendu < 0.10)
7. "Meilleur restaurant Rome" → Score: _______ (attendu < 0.10)
8. "Apprendre Python" → Score: _______ (attendu < 0.15)
9. "Histoire Napoléon" → Score: _______ (attendu < 0.10)
10. "Voiture électrique pas chère" → Score: _______ (attendu < 0.10)

**Rejection rate:** _______ / 10 (objectif: 10/10)

**Métriques globales:**
- [ ] True Positives (avicole accepté): _______ / 10
- [ ] True Negatives (hors-domaine rejeté): _______ / 10
- [ ] False Positives (hors-domaine accepté): _______ / 10 (objectif: 0)
- [ ] False Negatives (avicole rejeté): _______ / 10 (objectif: 0)
- [ ] **Accuracy:** _______ % (objectif: > 95%)

---

☐ **Stratégie 2: Translation (ES/DE/IT)** (ligne 384-457)

**Tests traduction:**

| Langue | Question | Traduit FR | Score | Accepté | Status |
|--------|----------|------------|-------|---------|--------|
| ES | "Peso pollos 35 días" | _______ | _____ | ☐ OUI ☐ NON | ☐ |
| DE | "Gewicht Hühner 35 Tage" | _______ | _____ | ☐ OUI ☐ NON | ☐ |
| IT | "Peso polli 35 giorni" | _______ | _____ | ☐ OUI ☐ NON | ☐ |
| PT | "Peso frangos 35 dias" | _______ | _____ | ☐ OUI ☐ NON | ☐ |

**Critères:**
- [ ] Translation service available: OUI / NON
- [ ] Translation confidence > 0.80: OUI / NON
- [ ] Entités préservées: OUI / NON
- [ ] Faux négatifs (bonnes questions rejetées): _______ / 4 (objectif: 0)

---

☐ **Stratégie 3: Non-Latin (HI/ZH/TH)** (ligne 459-505)

**Tests patterns universels:**

| Langue | Question | Universal Score | Accepted | Status |
|--------|----------|-----------------|----------|--------|
| HI | "रॉस 308 वजन 35 दिन" | _______ | ☐ OUI ☐ NON | ☐ |
| ZH | "罗斯308体重35天" | _______ | ☐ OUI ☐ NON | ☐ |
| TH | "น้ำหนักไก่ 35 วัน" | _______ | ☐ OUI ☐ NON | ☐ |

**Critères:**
- [ ] Universal patterns détectés (Ross 308, chiffres): OUI / NON
- [ ] Seuils adaptés (0.25 vs 0.30 standard): OUI / NON
- [ ] Unicode handling correct: OUI / NON

---

☐ **Stratégie 4: Fallback** (ligne 507-575)

**Tests cas limites:**

1. **Service traduction DOWN** → Utilise fallback: OUI / NON
2. **Langue inconnue** (ex: AR arabe) → Fallback permissif: OUI / NON
3. **Question mixte** ("Peso Ross 308 35j") → Détection: _______

**Critères:**
- [ ] Fallback ne rejette pas trop (permissive): OUI / NON
- [ ] Fallback rejette spam évident: OUI / NON
- [ ] **Verdict:** BALANCED / TOO STRICT / TOO PERMISSIVE

---

### 4.2 Test Disclaimers Vétérinaires

**Fichier analysé:** `C:\intelia_gpt\intelia-expert\llm\generation\veterinary_handler.py`

☐ **Test 1: Détection des 132 keywords**

**Keywords configurés:** `veterinary_terms.json` (ligne 24-107 veterinary_handler.py)

**Tests:**
- [ ] "maladie" → Disclaimer: OUI / NON
- [ ] "traitement" → Disclaimer: OUI / NON
- [ ] "antibiotique" → Disclaimer: OUI / NON
- [ ] "vaccin" → Disclaimer: OUI / NON
- [ ] "symptôme" → Disclaimer: OUI / NON
- [ ] "infection" → Disclaimer: OUI / NON
- [ ] "mortalité élevée" → Disclaimer: OUI / NON
- [ ] "diagnostic" → Disclaimer: OUI / NON
- [ ] "poids normal" → Disclaimer: NON (pas vétérinaire)
- [ ] "feed intake" → Disclaimer: NON

**Total keywords testés:** _______ / 132
**Précision:** _______ % (objectif: > 95%)

---

☐ **Test 2: Faux Positifs**

**Questions ambiguës:**

1. "Taux de mortalité acceptable pour Ross 308" → Disclaimer: OUI / NON
   **Analyse:** Question technique, pas vraiment vétérinaire
   **Attendu:** PAS de disclaimer (ou disclaimer léger)

2. "Prévention coccidiose en élevage" → Disclaimer: OUI / NON
   **Analyse:** Prévention = mesures générales, pas traitement spécifique
   **Attendu:** Disclaimer (mentionner vétérinaire pour cas spécifiques)

3. "Signes de bonne santé poulets" → Disclaimer: OUI / NON
   **Analyse:** Information générale, pas diagnostic
   **Attendu:** Disclaimer léger ou pas de disclaimer

**Critères:**
- [ ] Faux positifs acceptables: < 10%
- [ ] VERDICT: PRECISE / TOO SENSITIVE

---

☐ **Test 3: Multilingue (12 langues)**

**Disclaimer dans chaque langue:**

| Langue | Keyword Test | Disclaimer Generated | Translation | Status |
|--------|--------------|----------------------|-------------|--------|
| FR | "maladie" | ☐ OUI ☐ NON | _______ | ☐ |
| EN | "disease" | ☐ OUI ☐ NON | _______ | ☐ |
| ES | "enfermedad" | ☐ OUI ☐ NON | _______ | ☐ |
| DE | "krankheit" | ☐ OUI ☐ NON | _______ | ☐ |
| IT | "malattia" | ☐ OUI ☐ NON | _______ | ☐ |
| PT | "doença" | ☐ OUI ☐ NON | _______ | ☐ |
| NL | "ziekte" | ☐ OUI ☐ NON | _______ | ☐ |
| PL | "choroba" | ☐ OUI ☐ NON | _______ | ☐ |
| HI | "बीमारी" | ☐ OUI ☐ NON | _______ | ☐ |
| ID | "penyakit" | ☐ OUI ☐ NON | _______ | ☐ |
| TH | "โรค" | ☐ OUI ☐ NON | _______ | ☐ |
| ZH | "疾病" | ☐ OUI ☐ NON | _______ | ☐ |

**Critères:**
- [ ] 12/12 langues supportées: OUI / NON
- [ ] Disclaimers traduits via `config/languages.json`: OUI / NON
- [ ] Qualité traduction acceptable: OUI / NON

---

## PARTIE 5: VALIDATION AVANT EXPANSION

### 5.1 Checklist de Préparation

☐ **Data Pipeline Robuste**

- [ ] **Ingestion automatisée (batch import)**
  - Script d'import batch pour Weaviate: EXISTE / À CRÉER
  - Script d'import batch pour PostgreSQL: EXISTE / À CRÉER
  - Validation format documents (PDF, Excel, JSON): IMPLÉMENTÉ / À FAIRE
  - Logs structurés pour imports: OUI / NON

- [ ] **Validation format documents**
  - Schema validation JSON: OUI / NON
  - Vérification metadata obligatoires (breed, age, sex, metric): OUI / NON
  - Détection duplicates automatique: OUI / NON
  - Rejet documents malformés: OUI / NON

- [ ] **Déduplication automatique**
  - Détection duplicates PostgreSQL (breed + age + sex + metric): OUI / NON
  - Détection duplicates Weaviate (embedding similarity > 0.95): OUI / NON
  - Stratégie merge conflicts: DÉFINIE / À DÉFINIR

- [ ] **Metadata extraction fiable**
  - Extraction automatique breed depuis filename/content: OUI / NON
  - Extraction age ranges: OUI / NON
  - Extraction sex: OUI / NON
  - Normalisation unités (g, kg, lb → g): OUI / NON

---

☐ **Monitoring en Place**

- [ ] **Logs structurés (JSON)**
  - Format JSON pour tous les logs: OUI / NON
  - Niveaux configurés (DEBUG, INFO, WARNING, ERROR): OUI / NON
  - Logs rotatifs (éviter remplissage disque): OUI / NON
  - Logs centralisés (ELK, Datadog, CloudWatch): OUI / NON / N/A

- [ ] **Métriques collectées**
  - Latence queries (P50, P95, P99): COLLECTÉ / NON
  - Taux erreurs par composant: COLLECTÉ / NON
  - Cache hit rate: COLLECTÉ / NON
  - OOD rejection rate: COLLECTÉ / NON
  - Guardrails rejection rate: COLLECTÉ / NON
  - Outil: Prometheus / Datadog / Custom / AUCUN

- [ ] **Alertes configurées**
  - Alerte si error rate > 5%: OUI / NON
  - Alerte si latency P95 > 3s: OUI / NON
  - Alerte si cache down: OUI / NON
  - Alerte si PostgreSQL down: OUI / NON
  - Alerte si Weaviate down: OUI / NON
  - Canal alertes (Email, Slack, PagerDuty): _______

- [ ] **Dashboard disponible**
  - Dashboard temps réel: OUI / NON
  - Graphiques latence: OUI / NON
  - Graphiques taux erreurs: OUI / NON
  - Graphiques utilisation cache: OUI / NON
  - Outil: Grafana / Datadog / Tableau / Custom / AUCUN

---

☐ **Tests Automatisés**

- [ ] **Suite de tests unitaires**
  - Coverage > 80%: OUI / NON
  - Coverage actuel: _______ %
  - Tests OOD detector: OUI / NON
  - Tests Guardrails: OUI / NON
  - Tests PostgreSQL retriever: OUI / NON
  - Tests Weaviate core: OUI / NON
  - Framework: pytest / unittest / autre: _______

- [ ] **Tests d'intégration bout-en-bout**
  - 10 scénarios E2E (voir Partie 3.1): IMPLÉMENTÉS / NON
  - Tests multilingues: OUI / NON
  - Tests calculs feed: OUI / NON
  - Exécution automatique: OUI / NON

- [ ] **Tests de régression**
  - Suite de golden queries (résultats attendus): OUI / NON
  - Nombre de golden queries: _______
  - Exécution avant chaque déploiement: OUI / NON

- [ ] **CI/CD pipeline**
  - Tests automatiques sur commit: OUI / NON
  - Tests automatiques sur PR: OUI / NON
  - Déploiement automatique si tests OK: OUI / NON
  - Outil: GitHub Actions / GitLab CI / Jenkins / autre: _______

---

☐ **Performance Validée**

- [ ] **Latence < 2s (P95)**
  - P95 latency actuelle: _______ ms
  - Objectif atteint: OUI / NON
  - Bottleneck identifié: _______

- [ ] **Throughput > 10 req/s**
  - Throughput actuel: _______ req/s
  - Load test effectué: OUI / NON
  - Objectif atteint: OUI / NON

- [ ] **Cache hit rate > 30%**
  - Cache hit rate actuel: _______ %
  - Namespaces avec meilleur hit rate: _______
  - Objectif atteint: OUI / NON

- [ ] **Coût par requête < $0.05**
  - Coût OpenAI par requête: $ _______
  - Coût infrastructure par requête: $ _______
  - Coût total: $ _______
  - Objectif atteint: OUI / NON
  - **Actions d'optimisation si dépassement:**
    - [ ] Augmenter cache TTL
    - [ ] Réduire tokens dans prompts
    - [ ] Utiliser modèle moins cher pour tâches simples

---

☐ **Qualité Mesurée**

- [ ] **RAGAS score > 0.8**
  - RAGAS implémenté: OUI / NON
  - Score actuel: _______
  - Métrique RAGAS utilisée: Context Precision / Faithfulness / Answer Relevancy / Toutes
  - Objectif atteint: OUI / NON

- [ ] **Hallucination rate < 5%**
  - Méthode mesure: Tests manuels / Guardrails stats / Autre
  - Hallucination rate actuel: _______ %
  - Objectif atteint: OUI / NON

- [ ] **Factual accuracy > 95%**
  - Méthode mesure: Vérification manuelle / Golden dataset / Autre
  - Accuracy actuelle: _______ %
  - Nombre tests effectués: _______
  - Objectif atteint: OUI / NON

- [ ] **User satisfaction > 4/5**
  - Feedback users collecté: OUI / NON
  - Satisfaction moyenne: _______ / 5
  - Nombre réponses: _______
  - Objectif atteint: OUI / NON

---

☐ **Scalabilité Confirmée**

- [ ] **Load test 100 concurrent users**
  - Test effectué: OUI / NON
  - Outil: Locust / k6 / JMeter / autre: _______
  - Résultat: PASS / FAIL
  - Latence P95 sous charge: _______ ms
  - Taux erreurs: _______ %

- [ ] **Weaviate peut gérer 100k docs**
  - Test avec 100k docs: EFFECTUÉ / SIMULATION / NON TESTÉ
  - Latence query avec 100k docs: _______ ms
  - Mémoire utilisée: _______ GB
  - VERDICT: READY / NEEDS SCALING

- [ ] **PostgreSQL indexé optimalement**
  - Index sur toutes colonnes critiques: OUI / NON
  - Index composites pour queries fréquentes: OUI / NON
  - Query plan analyzed: OUI / NON
  - **Actions si non optimal:**
    - [ ] Créer index manquants
    - [ ] Ajouter partitioning par age_min
    - [ ] Vacuum/Analyze régulier

- [ ] **Redis sizing adéquat**
  - Mémoire actuelle: _______ MB / 100 MB limit
  - Projection pour 10x volume: _______ MB
  - Sufficient: OUI / NON
  - **Action si insuffisant:** Augmenter limite à _______ MB

---

☐ **Sécurité Renforcée**

- [ ] **Rate limiting activé**
  - Rate limiting implémenté: OUI / NON
  - Limite actuelle: _______ req/min par user
  - Limite globale: _______ req/min
  - Protection DDoS: OUI / NON

- [ ] **OOD > 98% accuracy**
  - Accuracy actuelle: _______ % (voir Partie 4.1)
  - Objectif atteint: OUI / NON

- [ ] **Guardrails > 95% precision**
  - Precision actuelle: _______ % (voir Partie 2.2)
  - Objectif atteint: OUI / NON

- [ ] **Aucune fuite données sensibles**
  - Audit logs pour données sensibles: OUI / NON
  - Données utilisateurs anonymisées: OUI / NON / N/A
  - Secrets dans .env (pas hardcodés): OUI / NON
  - API keys sécurisées: OUI / NON

---

### 5.2 Tests de Charge

☐ **Test 1: Charge Normale**

**Configuration:**
- 10 users concurrents
- 1 requête / user / 30 secondes
- Durée: 1 heure
- Queries mixtes (50% simples, 30% calculs, 20% multilingues)

**Résultats:**
- [ ] Total queries: _______ (attendu: ~1200)
- [ ] Erreurs: _______ (objectif: 0)
- [ ] Latence P50: _______ ms
- [ ] Latence P95: _______ ms (objectif: < 2000ms)
- [ ] Latence P99: _______ ms (objectif: < 5000ms)
- [ ] Cache hit rate: _______ %
- [ ] VERDICT: PASS / FAIL

---

☐ **Test 2: Charge Pic**

**Configuration:**
- 50 users concurrents
- 1 requête / user / 10 secondes
- Durée: 15 minutes
- Queries mixtes

**Résultats:**
- [ ] Total queries: _______ (attendu: ~4500)
- [ ] Erreurs: _______ (objectif: 0)
- [ ] Latence P50: _______ ms
- [ ] Latence P95: _______ ms (objectif: < 5000ms)
- [ ] Latence P99: _______ ms
- [ ] Taux dégradation vs charge normale: _______ %
- [ ] VERDICT: PASS / FAIL

---

☐ **Test 3: Charge Extrême (Stress Test)**

**Configuration:**
- 100 users concurrents
- 1 requête / user / 5 secondes
- Durée: 5 minutes
- Objectif: Identifier breaking point

**Résultats:**
- [ ] Total queries: _______ (attendu: ~6000)
- [ ] Erreurs: _______ (acceptable: < 5%)
- [ ] Latence P95: _______ ms
- [ ] Breaking point identifié: _______ concurrent users
- [ ] Composant limitant: PostgreSQL / Weaviate / OpenAI / Redis / Autre
- [ ] VERDICT: BREAKING POINT IDENTIFIÉ

**Actions d'optimisation si breaking point < 100 users:**
- [ ] Augmenter pool PostgreSQL (actuellement 2-10, ligne 75-76 rag_postgresql_retriever.py)
- [ ] Augmenter cache Redis
- [ ] Implémenter queue pour OpenAI rate limiting
- [ ] Horizontally scale Weaviate

---

## PARTIE 6: CRITÈRES GO / NO-GO FINAUX

### Décision Expansion Massive de Données

#### CRITÈRES GO (Tous doivent être ✅):

☐ **Architecture Scalable**
- [ ] Weaviate peut gérer 100k docs avec latency < 2s
- [ ] PostgreSQL peut gérer 500k rows avec queries < 500ms
- [ ] Redis auto-purge fonctionne et limite respectée
- [ ] Tous les fallbacks (PostgreSQL → Weaviate → OpenAI) fonctionnent

☐ **Qualité > 95%**
- [ ] RAGAS score > 0.8 OU Factual accuracy > 95%
- [ ] Hallucination rate < 5%
- [ ] Guardrails precision > 95%
- [ ] Anti-hallucination fonctionne (races/ages hors scope)

☐ **Sécurité > 98%**
- [ ] OOD accuracy > 98% (questions hors-domaine rejetées)
- [ ] Disclaimers vétérinaires ajoutés à 100%
- [ ] Aucun leak de données sensibles
- [ ] Rate limiting actif

☐ **Performance < 2s P95**
- [ ] P95 latency < 2000ms (charge normale)
- [ ] P95 latency < 5000ms (charge pic)
- [ ] Cache hit rate > 30%
- [ ] Coût par requête < $0.05

☐ **Monitoring Complet**
- [ ] Dashboard temps réel disponible
- [ ] Alertes configurées (erreurs, latence, crashes)
- [ ] Logs structurés JSON
- [ ] Métriques collectées (latence, erreurs, cache)

☐ **Tests Automatisés**
- [ ] Suite E2E tests (10 scénarios) passe à 100%
- [ ] Tests unitaires > 80% coverage
- [ ] Tests de régression (golden queries) passent
- [ ] CI/CD pipeline actif

---

### VERDICT FINAL

**Date de validation:** _______

#### ✅ GO POUR EXPANSION SI:

- [ ] **TOUS** les critères GO ci-dessus sont cochés
- [ ] Aucun critère NO-GO détecté
- [ ] Score global: _______ / 100 points (détail ci-dessous)

**Calcul du score:**
- Architecture (25 points): _______ / 25
- Qualité (25 points): _______ / 25
- Sécurité (20 points): _______ / 20
- Performance (15 points): _______ / 15
- Monitoring (10 points): _______ / 10
- Tests (5 points): _______ / 5

**TOTAL:** _______ / 100

**Seuil GO:** ≥ 85/100

---

#### ❌ NO-GO SI:

- [ ] Hallucination rate > 10% (CRITIQUE)
- [ ] OOD accuracy < 90% (CRITIQUE)
- [ ] P95 latency > 5s même en charge normale (CRITIQUE)
- [ ] Échec tests de charge à 50 users (CRITIQUE)
- [ ] Aucun monitoring en place (BLOQUANT)
- [ ] Guardrails non fonctionnels (BLOQUANT)
- [ ] PostgreSQL/Weaviate crash sous charge normale (BLOQUANT)
- [ ] Score global < 70/100

**Raison NO-GO:** _______

**Actions correctives requises avant expansion:**
1. _______
2. _______
3. _______

**Estimation temps correction:** _______

**Re-validation prévue:** _______

---

## PARTIE 7: ACTIONS POST-VALIDATION

### Si GO: Plan d'Expansion

☐ **Phase 1: Import Graduel (Semaine 1)**
- [ ] Importer 10 races supplémentaires (total: 12 races)
- [ ] Valider queries sur nouvelles races
- [ ] Vérifier performance (latence stable)
- [ ] Vérifier qualité (aucune hallucination sur nouvelles races)

☐ **Phase 2: Scaling Modéré (Semaine 2-3)**
- [ ] Importer 25 races supplémentaires (total: 37 races)
- [ ] Ajouter 50 documents Weaviate
- [ ] Load test 50 users
- [ ] Ajuster cache si nécessaire

☐ **Phase 3: Expansion Complète (Semaine 4+)**
- [ ] Importer toutes les 51 races du registry
- [ ] Ajouter 100+ documents Weaviate
- [ ] Load test 100 users
- [ ] Monitoring continu 24/7

---

### Si NO-GO: Plan d'Amélioration

**Priorisation des actions:**

1. **CRITIQUE (bloquer expansion):**
   - _______
   - _______

2. **IMPORTANT (risque qualité):**
   - _______
   - _______

3. **SOUHAITABLE (optimisation):**
   - _______
   - _______

**Timeline amélioration:** _______

**Re-validation prévue:** _______

---

## ANNEXE: TABLEAU DE SYNTHÈSE

### Résumé Exécutif

| Catégorie | Score | Status | Actions |
|-----------|-------|--------|---------|
| Architecture & Scalabilité | __ / 25 | 🟢 🟡 🔴 | _______ |
| Qualité Réponses | __ / 25 | 🟢 🟡 🔴 | _______ |
| Sécurité & OOD | __ / 20 | 🟢 🟡 🔴 | _______ |
| Performance | __ / 15 | 🟢 🟡 🔴 | _______ |
| Monitoring & Ops | __ / 10 | 🟢 🟡 🔴 | _______ |
| Tests Automatisés | __ / 5 | 🟢 🟡 🔴 | _______ |
| **TOTAL** | **__ / 100** | 🟢 🟡 🔴 | _______ |

**Légende:**
- 🟢 READY (score ≥ 85%)
- 🟡 NEEDS IMPROVEMENT (score 70-84%)
- 🔴 NOT READY (score < 70%)

---

## NOTES & OBSERVATIONS

**Points forts identifiés:**
- _______
- _______
- _______

**Points faibles identifiés:**
- _______
- _______
- _______

**Risques pour expansion:**
- _______
- _______
- _______

**Recommandations:**
- _______
- _______
- _______

---

**Validé par:** _______
**Date:** _______
**Signature:** _______
