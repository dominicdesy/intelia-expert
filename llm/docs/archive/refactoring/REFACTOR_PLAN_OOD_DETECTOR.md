# Plan de Refactoring: security/ood_detector.py

**Date:** 2025-10-05
**Objectif:** Refactoriser `security/ood_detector.py` (1,135 lignes) en architecture modulaire

---

## 📊 Analyse du Fichier Actuel

### Structure Actuelle
```
security/ood_detector.py (1,135 lignes)
├── DomainRelevance (Enum - 5 valeurs)
├── DomainScore (Dataclass - 9 fields)
└── MultilingualOODDetector (God Class - 24 méthodes, ~1,000 lignes)
    ├── __init__
    ├── _init_translation_service_safe
    ├── _load_blocked_terms
    ├── _build_domain_vocabulary_from_service
    ├── calculate_ood_score_multilingual (PUBLIC)
    ├── calculate_ood_score (PUBLIC, legacy)
    ├── _calculate_ood_score_for_language
    ├── _calculate_ood_direct
    ├── _calculate_ood_with_translation
    ├── _calculate_ood_non_latin
    ├── _calculate_ood_fallback
    ├── _normalize_query
    ├── _analyze_query_context
    ├── _calculate_domain_relevance
    ├── _detect_blocked_terms
    ├── _detect_universal_patterns
    ├── _apply_context_boosters
    ├── _select_adaptive_threshold
    ├── _log_ood_decision
    ├── _update_ood_metrics
    ├── get_detector_stats (PUBLIC)
    └── test_query_analysis (PUBLIC)
```

**Classes de Compatibilité:**
- `EnhancedOODDetector` (wrapper legacy, 14 lignes)

**Fonctions Factory:**
- `create_ood_detector()`
- `create_multilingual_ood_detector()`

### Problèmes Identifiés

1. **God Class Anti-Pattern:**
   - `MultilingualOODDetector`: 24 méthodes, ~1,000 lignes
   - 7+ responsabilités mélangées dans une classe

2. **Responsabilités Mélangées:**
   - ✗ Loading configuration (blocked terms, vocabulary)
   - ✗ Translation service management
   - ✗ Query normalization
   - ✗ Context analysis
   - ✗ Domain relevance calculation
   - ✗ Multiple OOD strategies (direct, translation, non-latin, fallback)
   - ✗ Logging and metrics
   - ✗ Statistics and testing

3. **Configuration Hardcodée:**
   - 80+ lignes de configuration dans `__init__` et méthodes
   - Language adjustments hardcodés
   - Adaptive thresholds hardcodés
   - Fallback terms hardcodés

4. **Complexité Élevée:**
   - Méthodes de 100+ lignes (_calculate_ood_with_translation, _build_domain_vocabulary_from_service)
   - Logique conditionnelle imbriquée
   - Stratégies multiples difficiles à tester indépendamment

---

## 🎯 Architecture Cible

### Package Structure
```
security/ood/
├── __init__.py                          # Package entry with exports
├── models.py                            # Data models (~40 lignes)
│   ├── DomainRelevance (Enum)
│   └── DomainScore (Dataclass)
├── config.py                            # Configuration constants (~150 lignes)
│   ├── ADAPTIVE_THRESHOLDS
│   ├── LANGUAGE_ADJUSTMENTS
│   ├── FALLBACK_BLOCKED_TERMS
│   ├── FALLBACK_UNIVERSAL_TERMS
│   └── TECHNICAL_PATTERNS
├── vocabulary_builder.py                # Domain vocabulary (~200 lignes)
│   └── VocabularyBuilder
│       ├── build_from_service()
│       └── build_fallback()
├── query_normalizer.py                  # Query normalization (~150 lignes)
│   └── QueryNormalizer (static)
│       ├── normalize_query()
│       └── normalize_non_latin()
├── context_analyzer.py                  # Context analysis (~200 lignes)
│   └── ContextAnalyzer (static)
│       ├── analyze_query_context()
│       ├── detect_technical_indicators()
│       └── classify_query_type()
├── domain_calculator.py                 # Domain relevance (~200 lignes)
│   └── DomainCalculator
│       ├── calculate_domain_relevance()
│       ├── detect_blocked_terms()
│       ├── detect_universal_patterns()
│       ├── apply_context_boosters()
│       └── select_adaptive_threshold()
├── translation_handler.py               # Translation management (~150 lignes)
│   └── TranslationHandler
│       ├── __init__() - safe initialization
│       ├── translate_query()
│       └── is_available()
├── ood_strategies.py                    # OOD calculation strategies (~300 lignes)
│   └── OODStrategy
│       ├── calculate_direct()
│       ├── calculate_with_translation()
│       ├── calculate_non_latin()
│       └── calculate_fallback()
├── detector.py                          # Main orchestrator (~250 lignes)
│   └── OODDetector
│       ├── __init__()
│       ├── calculate_ood_score_multilingual() (PUBLIC)
│       ├── calculate_ood_score() (PUBLIC, legacy)
│       ├── get_detector_stats() (PUBLIC)
│       └── test_query_analysis() (PUBLIC)
└── legacy_wrapper.py                    # Backward compatibility (~50 lignes)
    ├── MultilingualOODDetector (wrapper)
    ├── EnhancedOODDetector (wrapper)
    ├── create_ood_detector()
    └── create_multilingual_ood_detector()
```

### Responsabilités par Module

#### 1. **models.py** (Data Models)
- `DomainRelevance` enum
- `DomainScore` dataclass (utilise `SerializableMixin`)
- Types purs, pas de logique

#### 2. **config.py** (Configuration)
- Externaliser toutes les configurations hardcodées
- Constants pour thresholds, adjustments, patterns
- Vocabulaire de fallback

#### 3. **vocabulary_builder.py** (Vocabulary Construction)
**Responsabilité:** Construire vocabulaire du domaine
```python
class VocabularyBuilder:
    @staticmethod
    def build_from_service(translation_service, supported_languages) -> Dict[DomainRelevance, Set[str]]:
        """Build vocabulary from translation service"""

    @staticmethod
    def build_fallback(domain_keywords) -> Dict[DomainRelevance, Set[str]]:
        """Build fallback vocabulary"""
```

#### 4. **query_normalizer.py** (Query Normalization)
**Responsabilité:** Normaliser queries selon la langue
```python
class QueryNormalizer:
    @staticmethod
    def normalize_query(query: str, language: str) -> str:
        """Normalize query for Latin scripts"""

    @staticmethod
    def normalize_non_latin(query: str, language: str) -> str:
        """Normalize query for non-Latin scripts"""
```

#### 5. **context_analyzer.py** (Context Analysis)
**Responsabilité:** Analyser contexte des queries
```python
class ContextAnalyzer:
    @staticmethod
    def analyze_query_context(query: str, words: List[str], intent_result) -> Dict:
        """Analyze query context"""

    @staticmethod
    def detect_technical_indicators(query: str) -> List[Dict]:
        """Detect technical indicators"""
```

#### 6. **domain_calculator.py** (Domain Relevance)
**Responsabilité:** Calculer pertinence domaine
```python
class DomainCalculator:
    def __init__(self, domain_vocabulary, blocked_terms):
        ...

    def calculate_domain_relevance(self, words, context, language) -> DomainScore:
        """Calculate domain relevance"""

    def detect_blocked_terms(self, query, words) -> Dict:
        """Detect blocked terms"""

    def detect_universal_patterns(self, query, language) -> float:
        """Detect universal patterns"""

    def apply_context_boosters(self, base_score, context, intent) -> float:
        """Apply context boosters"""

    def select_adaptive_threshold(self, context, domain_analysis) -> float:
        """Select adaptive threshold"""
```

#### 7. **translation_handler.py** (Translation Management)
**Responsabilité:** Gérer service de traduction
```python
class TranslationHandler:
    def __init__(self):
        self.service = self._init_safe()
        self.cache = {}

    def _init_safe(self):
        """Safe initialization with fallback"""

    def translate_query(self, query, target_lang, source_lang) -> TranslationResult:
        """Translate query with caching"""

    def is_available(self) -> bool:
        """Check if translation service is available"""
```

#### 8. **ood_strategies.py** (OOD Calculation Strategies)
**Responsabilité:** Stratégies de calcul OOD
```python
class OODStrategy:
    def __init__(self, domain_calculator, translation_handler, normalizer, context_analyzer):
        ...

    def calculate_direct(self, query, intent, language) -> Tuple[bool, float, Dict]:
        """Direct OOD for fr/en"""

    def calculate_with_translation(self, query, intent, language) -> Tuple[bool, float, Dict]:
        """OOD with translation for Latin languages"""

    def calculate_non_latin(self, query, intent, language) -> Tuple[bool, float, Dict]:
        """OOD for non-Latin scripts"""

    def calculate_fallback(self, query, intent, language) -> Tuple[bool, float, Dict]:
        """Fallback OOD calculation"""
```

#### 9. **detector.py** (Main Orchestrator)
**Responsabilité:** Orchestrer détection OOD
```python
class OODDetector:
    def __init__(self, blocked_terms_path=None):
        # Initialize all components
        self.vocabulary_builder = VocabularyBuilder()
        self.translation_handler = TranslationHandler()
        self.domain_calculator = DomainCalculator(...)
        self.strategy = OODStrategy(...)

    def calculate_ood_score_multilingual(self, query, intent, language) -> Tuple:
        """Main entry point - multilingual"""

    def calculate_ood_score(self, query, intent) -> Tuple:
        """Legacy entry point"""

    def get_detector_stats(self) -> Dict:
        """Get detector statistics"""

    def test_query_analysis(self, query, language) -> Dict:
        """Test and diagnose query"""
```

#### 10. **legacy_wrapper.py** (Backward Compatibility)
**Responsabilité:** Wrapper pour API existante
```python
class MultilingualOODDetector:
    """Wrapper for backward compatibility"""
    def __init__(self, blocked_terms_path=None):
        self._detector = OODDetector(blocked_terms_path)

    # Delegate all methods to _detector

class EnhancedOODDetector(MultilingualOODDetector):
    """Legacy alias"""
```

---

## 📋 Plan d'Exécution

### Phase 1: Création des Modèles et Configuration
1. ✅ Créer `security/ood/models.py`
   - Déplacer `DomainRelevance`, `DomainScore`
   - Appliquer `SerializableMixin` à `DomainScore`

2. ✅ Créer `security/ood/config.py`
   - Externaliser `ADAPTIVE_THRESHOLDS`
   - Externaliser `LANGUAGE_ADJUSTMENTS`
   - Externaliser `FALLBACK_BLOCKED_TERMS`
   - Externaliser `FALLBACK_UNIVERSAL_TERMS`
   - Externaliser `TECHNICAL_PATTERNS`

### Phase 2: Extraction des Utilitaires
3. ✅ Créer `security/ood/vocabulary_builder.py`
   - Extraire `_build_domain_vocabulary_from_service()`
   - Créer méthode `build_fallback()`

4. ✅ Créer `security/ood/query_normalizer.py`
   - Extraire `_normalize_query()`
   - Logique spécialisée pour scripts non-latins

5. ✅ Créer `security/ood/context_analyzer.py`
   - Extraire `_analyze_query_context()`
   - Logique de détection d'indicateurs techniques

### Phase 3: Extraction de la Logique Métier
6. ✅ Créer `security/ood/domain_calculator.py`
   - Extraire `_calculate_domain_relevance()`
   - Extraire `_detect_blocked_terms()`
   - Extraire `_detect_universal_patterns()`
   - Extraire `_apply_context_boosters()`
   - Extraire `_select_adaptive_threshold()`

7. ✅ Créer `security/ood/translation_handler.py`
   - Extraire `_init_translation_service_safe()`
   - Gérer cache de traduction

8. ✅ Créer `security/ood/ood_strategies.py`
   - Extraire `_calculate_ood_direct()`
   - Extraire `_calculate_ood_with_translation()`
   - Extraire `_calculate_ood_non_latin()`
   - Extraire `_calculate_ood_fallback()`

### Phase 4: Création de l'Orchestrateur
9. ✅ Créer `security/ood/detector.py`
   - Classe `OODDetector` comme orchestrateur simple
   - Coordonner tous les modules
   - API publique: `calculate_ood_score_multilingual()`, `calculate_ood_score()`
   - Utilitaires: `get_detector_stats()`, `test_query_analysis()`

### Phase 5: Backward Compatibility
10. ✅ Créer `security/ood/legacy_wrapper.py`
    - Wrapper `MultilingualOODDetector` → `OODDetector`
    - Wrapper `EnhancedOODDetector` → `OODDetector`
    - Factory functions

11. ✅ Créer `security/ood/__init__.py`
    - Exporter nouvelle API
    - Exporter legacy API
    - Documentation

12. ✅ Créer `security/ood_detector_refactored.py`
    - Wrapper de compatibilité ultime
    - Import depuis `security.ood`

### Phase 6: Tests et Validation
13. ✅ Tester imports
14. ✅ Tester API nouvelle
15. ✅ Tester API legacy
16. ✅ Documentation finale

---

## 🎯 Objectifs de Qualité

### Métriques Cibles
- **Lignes par fichier:** < 350 lignes
- **Responsabilités par classe:** 1 unique
- **Complexité cyclomatique:** Réduite de ~85%
- **Backward compatibility:** 100%
- **Testabilité:** Chaque module testable indépendamment

### Patterns Appliqués
1. **Separation of Concerns:** Chaque module = 1 responsabilité
2. **Strategy Pattern:** Stratégies OOD interchangeables
3. **Static Utility Classes:** Normalizer, ContextAnalyzer
4. **Dependency Injection:** Composants injectés dans orchestrateur
5. **Safe Initialization:** Fallback robustes partout
6. **Backward Compatibility:** Wrappers transparents

---

## ✅ Bénéfices Attendus

### Maintenabilité
- ✅ Fichiers gérables (<350 lignes)
- ✅ Responsabilités claires
- ✅ Code navigable facilement

### Testabilité
- ✅ Modules isolés testables
- ✅ Mocking simple
- ✅ Coverage facile

### Réutilisabilité
- ✅ `VocabularyBuilder` réutilisable
- ✅ `QueryNormalizer` réutilisable
- ✅ `TranslationHandler` réutilisable

### Évolutivité
- ✅ Nouvelles stratégies OOD faciles à ajouter
- ✅ Nouvelle langue = config simple
- ✅ Nouveaux patterns = config.py

---

## 🔄 Comparaison avec Refactorings Précédents

| Aspect | Guardrails | Generators | OOD Detector |
|--------|-----------|-----------|--------------|
| **Taille avant** | 1,521 lignes | 1,204 lignes | 1,135 lignes |
| **Fichiers après** | 10 modules | 9 modules | **10 modules** |
| **Pattern principal** | Orchestrator | Orchestrator | **Strategy + Orchestrator** |
| **Réduction complexité** | ~85% | ~80% | **~85% (estimé)** |
| **Backward compat** | 100% ✓ | 100% ✓ | **100% ✓** |

**Similarités:**
- Même approche modulaire
- Separation of Concerns
- Configuration externalisée
- Backward compatibility wrappers

**Spécificités OOD:**
- **Strategy Pattern** pour 4 stratégies de calcul
- **Translation service** avec fallback robuste
- **Multilingual support** natif
- **Safe initialization** critique

---

## 📊 Estimation

**Temps estimé:** 2-3 heures
**Complexité:** Moyenne-Élevée (multilingual + translation service)
**Risque:** Faible (pattern éprouvé × 2)

**Fichiers à créer:** 10
**Fichiers à modifier:** 1 (pour imports dans agents)
**Tests requis:** Imports + API fonctionnelle

---

**Architecte:** Claude Code
**Date:** 2025-10-05
**Status:** ✅ PLAN PRÊT
