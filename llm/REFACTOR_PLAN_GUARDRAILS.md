# Plan de Refactoring: advanced_guardrails.py

## Analyse Actuelle

**Fichier:** `security/advanced_guardrails.py` (1,521 lignes)

### Structure
- 1 Enum: `VerificationLevel`
- 1 Dataclass: `GuardrailResult`
- 1 Grosse Classe: `AdvancedResponseGuardrails` (~1,450 lignes)

### Méthodes de AdvancedResponseGuardrails (30+ méthodes)

**Groupes Fonctionnels:**

1. **Configuration & Initialization (5 méthodes)**
   - `__init__` (310 lignes!) - TROP LONG
   - `get_guardrails_config`
   - `clear_cache`
   - `get_cache_stats`
   - `_generate_cache_key`, `_get_from_cache`, `_store_in_cache`

2. **Verification Core (3 méthodes)**
   - `verify_response` (async) - Point d'entrée principal
   - `quick_verify` (async) - Vérification rapide
   - `_make_adaptive_validation_decision`

3. **Evidence & Support (3 méthodes)**
   - `_check_evidence_support` (async)
   - `_find_enhanced_claim_support` (async)
   - `_quick_document_overlap` (async)

4. **Hallucination Detection (2 méthodes)**
   - `_detect_hallucination_risk` (async)
   - `_detect_internal_contradictions`

5. **Domain & Entity Validation (2 méthodes)**
   - `_check_domain_consistency` (async)
   - `_check_entity_consistency` (async)

6. **Claims Extraction (8 méthodes)**
   - `_extract_enhanced_factual_claims`
   - `_extract_numeric_claims`
   - `_extract_qualitative_claims`
   - `_extract_comparative_claims`
   - `_extract_key_elements`
   - `_extract_claim_context`
   - `_extract_comparison_elements`
   - `_verify_factual_claims` (async)

7. **Claims Verification (5 méthodes)**
   - `_verify_enhanced_numeric_claim` (async)
   - `_verify_specific_numeric_claim` (async)
   - `_verify_enhanced_qualitative_claim` (async)
   - `_verify_comparative_claim` (async)
   - `_find_unsupported_statements_parallel` (async)

8. **Text Analysis Utilities (7 méthodes)**
   - `_fuzzy_match`
   - `_normalize_text`
   - `_find_entity_variants`
   - `_check_numeric_coherence`
   - `_analyze_violations`
   - `_calculate_enhanced_confidence`
   - `_safe_extract_result`

## Problèmes Identifiés

1. **God Class Anti-Pattern**
   - Une classe fait tout (1,450 lignes)
   - Responsabilités multiples mélangées
   - Difficile à tester et maintenir

2. **Méthode __init__ Géante**
   - 310 lignes de patterns hardcodés
   - Devrait être dans des fichiers config JSON
   - Mélange configuration et données

3. **Manque de Séparation des Responsabilités**
   - Cache management mélangé avec verification
   - Text analysis mélangé avec domain logic
   - Claims extraction/verification dans même classe

## Solution Proposée

### Architecture Modulaire

```
security/guardrails/
├── __init__.py
├── core.py                  # Main orchestrator (simple)
├── config.py                # Configuration & patterns
├── models.py                # GuardrailResult, VerificationLevel
├── cache.py                 # Cache management
├── evidence_checker.py      # Evidence & support verification
├── hallucination_detector.py # Hallucination detection
├── claims_extractor.py      # Claims extraction
├── claims_verifier.py       # Claims verification
├── text_analyzer.py         # Text utilities (fuzzy match, normalize)
└── domain_validator.py      # Domain & entity consistency
```

### Bénéfices

1. **Maintenabilité**
   - Fichiers < 300 lignes chacun
   - Responsabilité unique par module
   - Facile à comprendre et modifier

2. **Testabilité**
   - Chaque module testable indépendamment
   - Mocking plus simple
   - Tests unitaires ciblés

3. **Réutilisabilité**
   - Modules utilisables séparément
   - text_analyzer réutilisable ailleurs
   - cache module générique

4. **Configuration Externalisée**
   - Patterns dans JSON/YAML
   - Pas de hardcoding dans __init__
   - Facile à ajuster sans code change

## Plan d'Implémentation

### Phase 1: Extraction des Modèles et Config
1. Créer `security/guardrails/models.py`
2. Créer `security/guardrails/config.py` avec patterns
3. Externaliser patterns vers JSON si possible

### Phase 2: Extraction des Utilitaires
4. Créer `security/guardrails/text_analyzer.py`
5. Créer `security/guardrails/cache.py`

### Phase 3: Extraction de la Logique Métier
6. Créer `security/guardrails/claims_extractor.py`
7. Créer `security/guardrails/claims_verifier.py`
8. Créer `security/guardrails/evidence_checker.py`
9. Créer `security/guardrails/hallucination_detector.py`
10. Créer `security/guardrails/domain_validator.py`

### Phase 4: Orchestration
11. Créer `security/guardrails/core.py` (simple orchestrator)
12. Maintenir backward compatibility via `advanced_guardrails.py`

### Phase 5: Cleanup
13. Remplacer `advanced_guardrails.py` par thin wrapper
14. Tests de non-régression
15. Documentation

## Estimation

- **Effort:** 4-6 heures
- **Réduction de complexité:** 80%
- **Lignes par fichier:** 150-300 (vs 1,521)
- **Backward Compatible:** Oui (wrapper)

## Décision

Procéder avec le refactoring modulaire?
- ✅ Oui - Architecture propre et maintenable
- ❌ Non - Garder monolithe (technique debt)
