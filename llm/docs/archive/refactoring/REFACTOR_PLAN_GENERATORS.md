# Plan de Refactoring: generators.py

**Fichier:** `generation/generators.py` (1,204 lignes)
**Date:** 2025-10-05

## Analyse Actuelle

### Structure
- 1 Dataclass: `ContextEnrichment`
- 2 Classes: `EntityDescriptionsManager`, `EnhancedResponseGenerator`
- `EnhancedResponseGenerator`: ~1,000 lignes avec 20+ méthodes

### Responsabilités Mélangées

**EnhancedResponseGenerator fait TOUT:**
1. ✅ Language management (noms langues, exemples, instructions)
2. ✅ Entity enrichment (contexts, descriptions, metrics)
3. ✅ Prompt building (system prompts, specialized prompts)
4. ✅ Response generation (LLM calls, caching)
5. ✅ Post-processing (cleanup, validation)
6. ✅ Veterinary disclaimers
7. ✅ Document handling (conversion, metadata)

**Problème:** Une classe ne devrait pas avoir 7 responsabilités!

## Groupes Fonctionnels

### 1. Language Management (5 méthodes)
- `_load_language_names()`
- `_generate_fallback_language_names()`
- `_get_critical_language_instructions()`
- `_generate_language_examples()`
- Support multilingue

### 2. Entity & Context Enrichment (2 méthodes + 1 classe)
- `EntityDescriptionsManager` class (déjà séparée ✓)
- `_build_entity_enrichment()`
- `ContextEnrichment` dataclass

### 3. Prompt Building (4 méthodes)
- `_build_enhanced_prompt()`
- `_get_fallback_system_prompt()`
- `build_specialized_prompt()`
- Construction prompts avec enrichissement

### 4. Response Generation (1 méthode principale)
- `generate_response()` - Point d'entrée async
- Orchestration LLM calls + cache

### 5. Post-Processing (1 méthode)
- `_post_process_response()`
- Cleanup et validation

### 6. Veterinary Logic (2 méthodes)
- `_is_veterinary_query()`
- `_get_veterinary_disclaimer()`

### 7. Document Utilities (3 méthodes)
- `_doc_to_dict()`
- `_get_doc_content()`
- `_get_doc_metadata()`

## Solution Proposée

### Architecture Modulaire

```
generation/
├── __init__.py
├── models.py                      # ContextEnrichment dataclass
├── entity_manager.py              # EntityDescriptionsManager (déjà bien)
├── language_handler.py            # Language management
├── prompt_builder.py              # Prompt construction
├── response_generator.py          # Main generator (simple orchestrator)
├── post_processor.py              # Response post-processing
├── veterinary_handler.py          # Veterinary disclaimers
└── document_utils.py              # Document conversion utilities
```

### Bénéfices

1. **Separation of Concerns:**
   - Chaque module = 1 responsabilité
   - Fichiers < 200 lignes chacun

2. **Testabilité:**
   - Modules testables indépendamment
   - Mocking simplifié

3. **Réutilisabilité:**
   - LanguageHandler réutilisable ailleurs
   - DocumentUtils génériques

4. **Maintenabilité:**
   - Modifications localisées
   - Code navigable

## Plan d'Implémentation

### Phase 1: Extraction des Modèles
1. ✅ Créer `generation/models.py`
   - `ContextEnrichment` dataclass

### Phase 2: Extraction des Utilitaires
2. ✅ Créer `generation/document_utils.py`
   - `_doc_to_dict()`, `_get_doc_content()`, `_get_doc_metadata()`

3. ✅ Créer `generation/language_handler.py`
   - `LanguageHandler` class avec toutes les méthodes de langue

### Phase 3: Extraction de la Logique Métier
4. ✅ Créer `generation/entity_manager.py`
   - Déplacer `EntityDescriptionsManager` (déjà bien structuré)
   - Ajouter `_build_entity_enrichment()`

5. ✅ Créer `generation/prompt_builder.py`
   - `PromptBuilder` class avec construction prompts

6. ✅ Créer `generation/veterinary_handler.py`
   - `VeterinaryHandler` class

7. ✅ Créer `generation/post_processor.py`
   - `ResponsePostProcessor` class

### Phase 4: Orchestration
8. ✅ Créer `generation/response_generator.py`
   - `ResponseGenerator` class (orchestrator simple)
   - Délègue aux modules spécialisés

### Phase 5: Backward Compatibility
9. ✅ Wrapper dans `generators.py`
   - `EnhancedResponseGenerator` délègue à `ResponseGenerator`

## Estimation

- **Effort:** 3-4 heures
- **Réduction complexité:** 80%
- **Lignes par fichier:** 100-250 (vs 1,204)
- **Backward Compatible:** Oui

## Décision

✅ Procéder avec refactoring modulaire
