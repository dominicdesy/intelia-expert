# Guide d'intégration - User Profiling pour LLM

Ce guide explique comment intégrer la personnalisation du profil utilisateur dans le système de génération LLM.

## Fichiers créés

- `llm/core/user_profiling.py` - Fonctions de récupération et personnalisation du profil

## Fonctions disponibles

### 1. `get_user_profile(user_id: str) -> Dict`

Récupère le profil depuis PostgreSQL.

**Retourne:**
```python
{
    'production_type': ['broiler', 'layer'],  # ou []
    'category': 'health_veterinary',  # ou None
    'category_other': 'texte libre',  # ou None
    'country': 'US'  # Code pays ISO 2 lettres
}
```

### 2. `build_personalized_system_prompt(base_prompt: str, user_profile: Dict) -> str`

Enrichit le system prompt avec le contexte utilisateur.

**Personnalisations appliquées:**

1. **Système de mesure** (selon pays):
   - USA (US) → Système impérial (lb, °F, gal)
   - Autres pays → Système métrique (kg, °C, L)

2. **Type de production** (broiler/layer):
   - Oriente les réponses vers le type de production spécifique
   - Priorise les métriques pertinentes (FCR pour broiler, HD pour layer)
   - Adapte les exemples de maladies

3. **Catégorie/expertise**:
   - `health_veterinary` → Langage technique, diagnostics différentiels
   - `farm_operations` → Solutions pratiques, langage clair
   - `feed_nutrition` → Formulation détaillée, standards NRC
   - `management_oversight` → KPIs, ROI, benchmarks
   - `breeding_hatchery` → Breeders, incubation, éclosabilité
   - `processing` → Qualité carcasse, HACCP, sécurité alimentaire
   - `equipment_technology` → Specs techniques, automatisation, ROI équipements
   - Autre/vide → Approche générale équilibrée

### 3. `build_weaviate_filter(user_profile: Dict) -> Optional[Dict]`

Construit un filtre Weaviate pour ne retourner que les documents pertinents.

**Logique:**
- Si `production_type` vide → Pas de filtre (tous les documents)
- Si `broiler` seulement → Retourne documents "broiler" + "general"
- Si `layer` seulement → Retourne documents "layer" + "general"
- Si `broiler` ET `layer` → Retourne documents "broiler" + "layer" + "both" + "general"

## Intégration dans generators.py

### Option 1: Modification minimale (recommandée)

**Dans `llm/generation/generators.py`, méthode `_build_enhanced_prompt`:**

```python
def _build_enhanced_prompt(
    self,
    query: str,
    context_docs: List[Union[Document, dict]],
    enrichment: ContextEnrichment,
    conversation_context: str,
    language: str,
    poultry_type: str,
    user_id: Optional[str] = None,  # NOUVEAU paramètre
) -> Tuple[str, str]:
    """Build enhanced prompt with context"""

    # ... code existant pour construire system_prompt_parts ...

    # Construction du system_prompt de base
    system_prompt = "\n\n".join(system_prompt_parts)

    # 🆕 PERSONNALISATION PROFIL UTILISATEUR
    if user_id:
        try:
            from llm.core.user_profiling import get_user_profile, build_personalized_system_prompt

            user_profile = get_user_profile(user_id)
            if user_profile:
                system_prompt = build_personalized_system_prompt(system_prompt, user_profile)
                logger.info(f"✅ System prompt personalized for user {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to personalize prompt: {e}")
            # Continue with base prompt if personalization fails

    # ... suite du code ...

    return system_prompt, user_prompt
```

**Ensuite, dans `generate_response` et `generate_response_with_cot`:**

```python
async def generate_response(
    self,
    query: str,
    context_docs: List[Union[Document, dict]],
    conversation_context: str = "",
    language: Optional[str] = None,
    intent_result=None,
    detected_domain: str = None,
    user_id: Optional[str] = None,  # NOUVEAU paramètre
) -> str:
    """Generate response with optional user profiling"""

    # ... code existant ...

    # Appel à _build_enhanced_prompt avec user_id
    system_prompt, user_prompt = self._build_enhanced_prompt(
        query,
        context_docs,
        enrichment,
        conversation_context,
        lang,
        poultry_type,
        user_id=user_id,  # NOUVEAU: passer user_id
    )

    # ... suite du code ...
```

### Option 2: Intégration dans les endpoints API

**Dans les endpoints qui appellent `generate_response` (ex: SSE streaming):**

```python
from llm.core.user_profiling import get_user_profile, build_weaviate_filter

@router.post("/api/v1/query")
async def query_endpoint(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get('id')

    # 🆕 Récupérer le profil utilisateur
    user_profile = get_user_profile(user_id) if user_id else {}

    # 🆕 Construire le filtre Weaviate
    weaviate_filter = build_weaviate_filter(user_profile) if user_profile else None

    # Récupérer les documents avec filtre
    context_docs = await retriever.retrieve(
        query=request.query,
        where_filter=weaviate_filter,  # NOUVEAU: filtre par production_type
        limit=10
    )

    # Générer la réponse avec user_id
    response = await generator.generate_response(
        query=request.query,
        context_docs=context_docs,
        user_id=user_id,  # NOUVEAU: passer user_id
        language=request.language
    )

    return {"response": response}
```

## Test de l'intégration

```python
# Test simple
from llm.core.user_profiling import get_user_profile, build_personalized_system_prompt

# 1. Récupérer un profil
user_id = "123e4567-e89b-12d3-a456-426614174000"
profile = get_user_profile(user_id)
print(profile)
# {'production_type': ['broiler'], 'category': 'farm_operations', 'country': 'CA'}

# 2. Personnaliser un prompt
base_prompt = "You are an expert poultry consultant."
personalized_prompt = build_personalized_system_prompt(base_prompt, profile)
print(personalized_prompt)
# Ajoute les sections pour système métrique, broiler focus, farm operator style

# 3. Filtrer Weaviate
from llm.core.user_profiling import build_weaviate_filter
weaviate_filter = build_weaviate_filter(profile)
print(weaviate_filter)
# {'operator': 'Or', 'operands': [{'path': ['production_type'], ...}]}
```

## Checklist d'intégration

- [ ] Ajouter paramètre `user_id` à `generate_response()` dans generators.py
- [ ] Ajouter paramètre `user_id` à `_build_enhanced_prompt()` dans generators.py
- [ ] Appeler `get_user_profile()` et `build_personalized_system_prompt()` dans `_build_enhanced_prompt()`
- [ ] Passer `user_id` depuis les endpoints API (SSE, REST)
- [ ] Utiliser `build_weaviate_filter()` lors de la récupération Weaviate
- [ ] Tester avec différents profils (broiler seul, layer seul, les deux, pas de profil)
- [ ] Tester avec USA (système impérial) vs autres pays (métrique)
- [ ] Tester avec différentes catégories (vétérinaire, fermier, nutritionniste, etc.)

## Impact attendu

**Sans profil:**
```
Q: "What's the ideal body weight at 35 days?"
A: "The ideal body weight at 35 days is 2.1 kg (4.6 lb)..."
```

**Avec profil (USA, broiler, farm_operations):**
```
Q: "What's the ideal body weight at 35 days?"
A: "For broilers at 35 days, you're looking for around 4.6 lb.
Check your birds daily - they should feel solid and meaty in the breast...
If you're seeing birds below 4 lb at this age, check feed intake..."
```

**Avec profil (Canada, broiler, health_veterinary):**
```
Q: "What's the ideal body weight at 35 days?"
A: "The target body weight for broilers at 35 days is 2.1 kg, with acceptable range 1.9-2.3 kg depending on genetic line.
Deviations may indicate:
- Growth rate issues (check FCR, review nutrition)
- Subclinical disease (coccidiosis, enteritis)
- Environmental stress (temperature, ventilation)
Differential diagnosis should include..."
```

## Notes importantes

- La personnalisation est **optionnelle** - si pas de user_id, le système fonctionne normalement
- Si erreur lors de la récupération du profil, le système continue avec le prompt de base
- Les filtres Weaviate sont aussi optionnels - si pas de production_type, tous les documents sont retournés
- Le pays détermine le système de mesure (US = impérial, autres = métrique)
