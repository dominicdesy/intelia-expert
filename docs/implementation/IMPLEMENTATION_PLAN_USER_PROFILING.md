# Plan d'implémentation: User Profiling (production_type + category)

## ✅ PHASE 1: BACKEND - TERMINÉ

### SQL Migration (Supabase)
- ✅ `add_user_profile_fields.sql` créé et exécuté
- ✅ Colonnes ajoutées: `production_type TEXT[]`, `category TEXT`, `category_other TEXT`
- ✅ Index créés pour performance

### API Endpoints
- ✅ `backend/app/api/v1/auth.py` - UserRegister model mis à jour
- ✅ `backend/app/api/v1/users.py` - UserProfileUpdate model mis à jour
- ✅ Validators ajoutés pour valider production_type (broiler/layer) et category (8 catégories)

### Commit & Push
- ✅ Commit: `6e7ada88` - "feat: Add production_type and category fields to user profile (backend)"
- ✅ Pushed to main

---

## 🔄 PHASE 2: FRONTEND - EN COURS

### A. Traductions i18n (`frontend/lib/languages/i18n.ts`)

**Ajouter à l'interface TranslationKeys:**
```typescript
// User Profiling
"profile.productionType.label": string;
"profile.productionType.description": string;
"profile.productionType.broiler": string;
"profile.productionType.layer": string;
"profile.productionType.both": string;
"profile.productionType.why": string;

"profile.category.label": string;
"profile.category.description": string;
"profile.category.why": string;
"profile.category.breedingHatchery": string;
"profile.category.feedNutrition": string;
"profile.category.farmOperations": string;
"profile.category.healthVeterinary": string;
"profile.category.processing": string;
"profile.category.managementOversight": string;
"profile.category.equipmentTechnology": string;
"profile.category.other": string;
"profile.category.otherPlaceholder": string;
```

**Ajouter les traductions (fr/en/es/de):**
```typescript
fr: {
  "profile.productionType.label": "Type de production",
  "profile.productionType.description": "Sélectionnez votre type de production avicole",
  "profile.productionType.broiler": "Poulet de chair (Broiler)",
  "profile.productionType.layer": "Poule pondeuse (Layer)",
  "profile.productionType.both": "Les deux",
  "profile.productionType.why": "Cette information nous permet de personnaliser les réponses selon votre type de production et de filtrer les documents pertinents.",

  "profile.category.label": "Votre activité",
  "profile.category.description": "Sélectionnez votre domaine d'activité dans la chaîne de valeur",
  "profile.category.why": "Cela nous aide à adapter le niveau de détail et le type de réponses (pratiques, techniques, stratégiques).",
  "profile.category.breedingHatchery": "Reproduction & Couvoir",
  "profile.category.feedNutrition": "Nutrition & Alimentation",
  "profile.category.farmOperations": "Élevage",
  "profile.category.healthVeterinary": "Santé & Vétérinaire",
  "profile.category.processing": "Transformation & Abattage",
  "profile.category.managementOversight": "Gestion & Supervision",
  "profile.category.equipmentTechnology": "Équipements & Technologie",
  "profile.category.other": "Autre",
  "profile.category.otherPlaceholder": "Précisez votre activité...",
},

en: {
  "profile.productionType.label": "Production Type",
  "profile.productionType.description": "Select your poultry production type",
  "profile.productionType.broiler": "Broiler",
  "profile.productionType.layer": "Layer",
  "profile.productionType.both": "Both",
  "profile.productionType.why": "This helps us personalize responses based on your production type and filter relevant documents.",

  "profile.category.label": "Your Activity",
  "profile.category.description": "Select your area of activity in the value chain",
  "profile.category.why": "This helps us adapt the level of detail and type of responses (practical, technical, strategic).",
  "profile.category.breedingHatchery": "Breeding & Hatchery",
  "profile.category.feedNutrition": "Feed & Nutrition",
  "profile.category.farmOperations": "Farm Operations",
  "profile.category.healthVeterinary": "Health & Veterinary",
  "profile.category.processing": "Processing & Slaughter",
  "profile.category.managementOversight": "Management & Oversight",
  "profile.category.equipmentTechnology": "Equipment & Technology",
  "profile.category.other": "Other",
  "profile.category.otherPlaceholder": "Please specify your activity...",
}
```

### B. Signup Form (`frontend/app/auth/signup/page.tsx`)

**Localisation:**
Fichier: ~961 lignes, chercher la section du formulaire d'inscription (~ligne 742)

**Modifications:**
1. Ajouter state pour production_type et category:
```typescript
const [productionType, setProductionType] = useState<string[]>([]);
const [category, setCategory] = useState<string>('');
const [categoryOther, setCategoryOther] = useState<string>('');
```

2. Ajouter les champs après les champs existants (email, password, nom, etc.):
```typescript
{/* Production Type */}
<div className="mb-4">
  <label className="block text-sm font-medium text-gray-700 mb-2">
    {t("profile.productionType.label")}
  </label>
  <p className="text-xs text-gray-500 mb-3">
    {t("profile.productionType.why")}
  </p>
  <div className="space-y-2">
    <label className="flex items-center">
      <input
        type="checkbox"
        checked={productionType.includes('broiler')}
        onChange={(e) => {
          if (e.target.checked) {
            setProductionType([...productionType, 'broiler']);
          } else {
            setProductionType(productionType.filter(t => t !== 'broiler'));
          }
        }}
        className="mr-2"
      />
      {t("profile.productionType.broiler")}
    </label>
    <label className="flex items-center">
      <input
        type="checkbox"
        checked={productionType.includes('layer')}
        onChange={(e) => {
          if (e.target.checked) {
            setProductionType([...productionType, 'layer']);
          } else {
            setProductionType(productionType.filter(t => t !== 'layer'));
          }
        }}
        className="mr-2"
      />
      {t("profile.productionType.layer")}
    </label>
  </div>
</div>

{/* Category */}
<div className="mb-4">
  <label className="block text-sm font-medium text-gray-700 mb-2">
    {t("profile.category.label")}
  </label>
  <p className="text-xs text-gray-500 mb-3">
    {t("profile.category.why")}
  </p>
  <select
    value={category}
    onChange={(e) => setCategory(e.target.value)}
    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
  >
    <option value="">-- {t("profile.category.description")} --</option>
    <option value="breeding_hatchery">{t("profile.category.breedingHatchery")}</option>
    <option value="feed_nutrition">{t("profile.category.feedNutrition")}</option>
    <option value="farm_operations">{t("profile.category.farmOperations")}</option>
    <option value="health_veterinary">{t("profile.category.healthVeterinary")}</option>
    <option value="processing">{t("profile.category.processing")}</option>
    <option value="management_oversight">{t("profile.category.managementOversight")}</option>
    <option value="equipment_technology">{t("profile.category.equipmentTechnology")}</option>
    <option value="other">{t("profile.category.other")}</option>
  </select>

  {category === 'other' && (
    <input
      type="text"
      value={categoryOther}
      onChange={(e) => setCategoryOther(e.target.value)}
      placeholder={t("profile.category.otherPlaceholder")}
      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 mt-2"
    />
  )}
</div>
```

3. Ajouter au payload de signup (handleSignup function):
```typescript
const signupPayload = {
  email,
  password,
  full_name: fullName,
  country: selectedCountry,
  preferred_language: currentLanguage,
  production_type: productionType.length > 0 ? productionType : null,
  category: category || null,
  category_other: category === 'other' ? categoryOther : null,
};
```

### C. Profile Page (`frontend/app/profile/page.tsx`)

**Localisation:**
Fichier: 754 lignes, section "profile" tab (ligne ~410-488)

**Modifications:**
1. Ajouter state dans formData:
```typescript
const [formData, setFormData] = useState({
  fullName: "",
  email: "",
  userType: "producer" as "producer" | "professional",
  productionType: [] as string[],
  category: "",
  categoryOther: "",
});
```

2. Initialiser depuis user data (useEffect):
```typescript
setFormData({
  fullName: getSafeName(user),
  email: getSafeEmail(user),
  userType: getSafeUserType(user) as "producer" | "professional",
  productionType: user.production_type || [],
  category: user.category || "",
  categoryOther: user.category_other || "",
});
```

3. Ajouter les champs dans le formulaire (après userType):
```typescript
{/* Production Type */}
<div>
  <label className="block text-sm font-medium text-gray-700 mb-2">
    {t("profile.productionType.label")}
  </label>
  <div className="space-y-2">
    <label className="flex items-center">
      <input
        type="checkbox"
        checked={formData.productionType.includes('broiler')}
        onChange={(e) => {
          const newProductionType = e.target.checked
            ? [...formData.productionType, 'broiler']
            : formData.productionType.filter(t => t !== 'broiler');
          setFormData(prev => ({ ...prev, productionType: newProductionType }));
        }}
        className="mr-2"
      />
      {t("profile.productionType.broiler")}
    </label>
    <label className="flex items-center">
      <input
        type="checkbox"
        checked={formData.productionType.includes('layer')}
        onChange={(e) => {
          const newProductionType = e.target.checked
            ? [...formData.productionType, 'layer']
            : formData.productionType.filter(t => t !== 'layer');
          setFormData(prev => ({ ...prev, productionType: newProductionType }));
        }}
        className="mr-2"
      />
      {t("profile.productionType.layer")}
    </label>
  </div>
</div>

{/* Category */}
<div>
  <label className="block text-sm font-medium text-gray-700 mb-2">
    {t("profile.category.label")}
  </label>
  <select
    value={formData.category}
    onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
  >
    <option value="">-- {t("common.optional")} --</option>
    <option value="breeding_hatchery">{t("profile.category.breedingHatchery")}</option>
    <option value="feed_nutrition">{t("profile.category.feedNutrition")}</option>
    <option value="farm_operations">{t("profile.category.farmOperations")}</option>
    <option value="health_veterinary">{t("profile.category.healthVeterinary")}</option>
    <option value="processing">{t("profile.category.processing")}</option>
    <option value="management_oversight">{t("profile.category.managementOversight")}</option>
    <option value="equipment_technology">{t("profile.category.equipmentTechnology")}</option>
    <option value="other">{t("profile.category.other")}</option>
  </select>

  {formData.category === 'other' && (
    <input
      type="text"
      value={formData.categoryOther}
      onChange={(e) => setFormData(prev => ({ ...prev, categoryOther: e.target.value }))}
      placeholder={t("profile.category.otherPlaceholder")}
      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 mt-2"
    />
  )}
</div>
```

4. Mettre à jour handleSubmit:
```typescript
const dataToUpdate = {
  name: trimmedName,
  user_type: formData.userType,
  production_type: formData.productionType.length > 0 ? formData.productionType : null,
  category: formData.category || null,
  category_other: formData.category === 'other' ? formData.categoryOther : null,
};
```

---

## 🤖 PHASE 3: LLM INTEGRATION

### A. Récupérer le profil utilisateur

**Fichier: `llm/generation/generators.py` ou `llm/routing/llm_router.py`**

Ajouter une fonction pour récupérer le profil:
```python
def get_user_profile(user_id: str) -> dict:
    """Récupère le profil utilisateur depuis Supabase"""
    try:
        from app.database.connection import get_pg_connection

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT production_type, category, category_other
                    FROM users
                    WHERE auth_user_id = %s
                """, (user_id,))
                result = cur.fetchone()

                if result:
                    return {
                        'production_type': result[0] or [],
                        'category': result[1],
                        'category_other': result[2]
                    }
        return {}
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        return {}
```

### B. Adapter le system prompt

**Fichier: `llm/core/prompts.py` ou directement dans `generators.py`**

```python
def build_personalized_system_prompt(base_prompt: str, user_profile: dict) -> str:
    """
    Adapte le system prompt selon le profil utilisateur

    Args:
        base_prompt: Prompt système de base
        user_profile: {production_type: [...], category: str, category_other: str}

    Returns:
        System prompt personnalisé
    """
    personalization = ""

    # 1. Production Type Adaptations
    production_types = user_profile.get('production_type', [])

    if 'broiler' in production_types and 'layer' not in production_types:
        personalization += "\n\nUser Context: This user works ONLY with broilers (meat chickens).\n"
        personalization += "- Focus on broiler-specific metrics: FCR (Feed Conversion Ratio), ADG (Average Daily Gain), slaughter weight, meat yield\n"
        personalization += "- Emphasize growth performance, feed efficiency, and processing quality\n"
        personalization += "- When discussing diseases, prioritize conditions affecting broilers (ascites, sudden death syndrome, leg problems)\n"

    elif 'layer' in production_types and 'broiler' not in production_types:
        personalization += "\n\nUser Context: This user works ONLY with layers (egg-laying hens).\n"
        personalization += "- Focus on layer-specific metrics: HD (Hen-Day production), egg mass, feed per dozen eggs, egg quality\n"
        personalization += "- Emphasize egg production performance, shell quality, and laying persistency\n"
        personalization += "- When discussing diseases, prioritize conditions affecting layers (cage layer fatigue, egg peritonitis)\n"

    elif 'broiler' in production_types and 'layer' in production_types:
        personalization += "\n\nUser Context: This user works with BOTH broilers and layers.\n"
        personalization += "- Provide balanced information for both production types\n"
        personalization += "- When answering, specify which production type the information applies to\n"

    # 2. Category Adaptations (expertise level and response style)
    category = user_profile.get('category')

    if category == 'health_veterinary':
        personalization += "\n\nExpertise Level: VETERINARY/HEALTH PROFESSIONAL\n"
        personalization += "- Provide detailed technical explanations with scientific terminology\n"
        personalization += "- Include differential diagnoses and clinical reasoning\n"
        personalization += "- Reference relevant studies or veterinary protocols when applicable\n"
        personalization += "- Discuss pathophysiology, treatment protocols, and dosage calculations\n"

    elif category == 'farm_operations':
        personalization += "\n\nExpertise Level: FARM OPERATOR/PRODUCER\n"
        personalization += "- Provide PRACTICAL, actionable solutions\n"
        personalization += "- Focus on day-to-day farm management and problem-solving\n"
        personalization += "- Use clear language without excessive jargon\n"
        personalization += "- Include specific steps and 'what to look for' indicators\n"
        personalization += "- When discussing health issues, explain when to call a veterinarian\n"

    elif category == 'feed_nutrition':
        personalization += "\n\nExpertise Level: NUTRITION SPECIALIST\n"
        personalization += "- Provide detailed nutritional analysis and formulation guidance\n"
        personalization += "- Include specific nutrient requirements and formulation strategies\n"
        personalization += "- Discuss feed ingredients, amino acid profiles, energy systems (ME, AME)\n"
        personalization += "- Reference nutritional standards (NRC, breeder company guides)\n"

    elif category == 'management_oversight':
        personalization += "\n\nExpertise Level: MANAGEMENT/STRATEGIC\n"
        personalization += "- Provide strategic insights with performance data and KPIs\n"
        personalization += "- Include cost-benefit analysis and ROI considerations\n"
        personalization += "- Focus on decision-making support and performance optimization\n"
        personalization += "- Reference industry benchmarks and comparative data\n"

    elif category == 'breeding_hatchery':
        personalization += "\n\nExpertise Level: BREEDING/HATCHERY SPECIALIST\n"
        personalization += "- Focus on breeder management, egg quality, and hatchability\n"
        personalization += "- Include incubation parameters and embryo development\n"
        personalization += "- Discuss genetic selection and flock management\n"

    elif category == 'processing':
        personalization += "\n\nExpertise Level: PROCESSING SPECIALIST\n"
        personalization += "- Focus on slaughter operations, meat quality, and food safety\n"
        personalization += "- Include processing yields, carcass quality, and shelf life\n"
        personalization += "- Discuss regulatory compliance and HACCP protocols\n"

    elif category == 'equipment_technology':
        personalization += "\n\nExpertise Level: EQUIPMENT/TECHNOLOGY PROVIDER\n"
        personalization += "- Focus on technical specifications and equipment performance\n"
        personalization += "- Include automation, sensors, and data management systems\n"
        personalization += "- Discuss ROI and equipment selection criteria\n"

    else:
        # Generic fallback (no category or category='other')
        personalization += "\n\nExpertise Level: GENERAL\n"
        personalization += "- Provide balanced, accessible information\n"
        personalization += "- Explain technical concepts clearly\n"
        personalization += "- Offer both practical and theoretical insights\n"

    # Combine base prompt with personalization
    return base_prompt + personalization
```

### C. Filtrage Weaviate

**Fichier: `llm/retrieval/weaviate_client.py` ou dans le router LLM**

```python
def build_weaviate_filter(user_profile: dict) -> dict:
    """
    Construit un filtre Weaviate basé sur le profil utilisateur

    Returns:
        Filtre Weaviate compatible avec where clause
    """
    production_types = user_profile.get('production_type', [])

    if not production_types:
        # Pas de filtre si production_type non défini
        return {}

    # Filtre pour récupérer documents:
    # - production_type = user's type OU
    # - production_type = "universal" (applicable aux deux)
    filter_operands = []

    for prod_type in production_types:
        filter_operands.append({
            "path": ["production_type"],
            "operator": "Equal",
            "valueString": prod_type
        })

    # Ajouter documents universels
    filter_operands.append({
        "path": ["production_type"],
        "operator": "Equal",
        "valueString": "universal"
    })

    return {
        "where": {
            "operator": "Or",
            "operands": filter_operands
        }
    }
```

### D. Intégration dans le flux LLM

**Fichier: `llm/routing/llm_router.py` - Fonction principale**

```python
async def route_question(
    query: str,
    user_id: str,  # Ajouter user_id comme paramètre
    language: str = "fr",
    conversation_history: list = None
):
    """Route la question avec personnalisation basée sur le profil"""

    # 1. Récupérer le profil utilisateur
    user_profile = get_user_profile(user_id)

    # 2. Construire le system prompt personnalisé
    base_prompt = get_base_system_prompt(language)
    system_prompt = build_personalized_system_prompt(base_prompt, user_profile)

    # 3. Construire le filtre Weaviate
    weaviate_filter = build_weaviate_filter(user_profile)

    # 4. Récupérer documents avec filtre
    documents = await retrieve_documents(
        query=query,
        filter=weaviate_filter,
        limit=10
    )

    # 5. Générer réponse avec prompt personnalisé
    response = await generate_response(
        query=query,
        documents=documents,
        system_prompt=system_prompt,
        conversation_history=conversation_history
    )

    return response
```

---

## 📋 CHECKLIST FINALE

### Backend
- [x] SQL migration exécutée
- [x] Auth endpoint mis à jour
- [x] Users endpoint mis à jour
- [x] Validators ajoutés
- [x] Commit + Push

### Frontend
- [ ] Traductions i18n ajoutées (fr, en, es, de)
- [ ] Signup form modifié
- [ ] Profile page modifiée
- [ ] Messages "Pourquoi" ajoutés
- [ ] Commit + Push frontend

### LLM
- [ ] Fonction get_user_profile() créée
- [ ] Fonction build_personalized_system_prompt() créée
- [ ] Fonction build_weaviate_filter() créée
- [ ] Intégration dans llm_router.py
- [ ] Tests avec différents profils
- [ ] Commit + Push LLM

### Testing
- [ ] Test signup avec production_type + category
- [ ] Test profile update
- [ ] Test LLM avec profil broiler/farm_operations
- [ ] Test LLM avec profil layer/health_veterinary
- [ ] Test LLM sans profil (fallback générique)
- [ ] Test filtrage Weaviate

---

## 🎯 PROCHAINES ÉTAPES IMMÉDIATES

1. **Ajouter traductions i18n** (frontend/lib/languages/i18n.ts)
2. **Modifier signup form** (frontend/app/auth/signup/page.tsx)
3. **Modifier profile page** (frontend/app/profile/page.tsx)
4. **Commit + Push frontend**
5. **Implémenter personnalisation LLM**
6. **Tests complets**

---

## 📝 NOTES IMPORTANTES

- **Production Types**: broiler, layer (peuvent coexister)
- **Categories**: 8 catégories + "other" avec champ texte libre
- **Fallback**: Si user_profile vide → prompt générique
- **Weaviate**: Documents doivent avoir metadata "production_type" pour filtrage
- **Privacy**: Ces données ne sont PAS affichées publiquement, uniquement pour personnalisation
