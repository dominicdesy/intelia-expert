# Frontend UI Implementation - User Profiling Fields

## ✅ Already Completed:
- Backend SQL migration
- Backend API endpoints (auth.py + users.py)
- TypeScript interface updates (i18n.ts)
- Translations (fr, en, es, de)

## 📝 Remaining Work: Frontend UI Components

---

## 1. SIGNUP FORM - Ajouter les champs profiling

**Fichier**: `frontend/app/auth/signup/page.tsx` (ligne ~742)

**État actuel**: Formulaire signup avec email, password, nom, pays, etc.

**À ajouter**: Production type et category APRÈS les champs existants

### Code à ajouter au formulaire signup:

```tsx
{/* === NOUVEAU: Production Type & Category === */}
<div className="space-y-4 mt-6 pt-6 border-t border-gray-200">
  {/* Production Type */}
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-2">
      {t("profile.productionType.label")}
    </label>
    <p className="text-xs text-blue-600 mb-3 bg-blue-50 p-2 rounded">
      💡 {t("profile.productionType.why")}
    </p>
    <div className="space-y-2">
      <label className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
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
          className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <span className="text-sm text-gray-700">
          {t("profile.productionType.broiler")}
        </span>
      </label>
      <label className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
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
          className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <span className="text-sm text-gray-700">
          {t("profile.productionType.layer")}
        </span>
      </label>
    </div>
  </div>

  {/* Category */}
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-2">
      {t("profile.category.label")}
    </label>
    <p className="text-xs text-blue-600 mb-3 bg-blue-50 p-2 rounded">
      💡 {t("profile.category.why")}
    </p>
    <select
      value={category}
      onChange={(e) => setCategory(e.target.value)}
      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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

    {/* Conditional: Other Category Input */}
    {category === 'other' && (
      <input
        type="text"
        value={categoryOther}
        onChange={(e) => setCategoryOther(e.target.value)}
        placeholder={t("profile.category.otherPlaceholder")}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mt-2"
      />
    )}
  </div>
</div>
```

### État nécessaire (à ajouter en haut du composant):

```tsx
const [productionType, setProductionType] = useState<string[]>([]);
const [category, setCategory] = useState<string>('');
const [categoryOther, setCategoryOther] = useState<string>('');
```

### Payload signup (modifier la fonction handleSignup):

```tsx
// ANCIEN payload:
const signupPayload = {
  email,
  password,
  full_name: fullName,
  country: selectedCountry,
  preferred_language: currentLanguage,
};

// NOUVEAU payload (ajouter ces lignes):
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

---

## 2. PROFILE PAGE - Permettre modification

**Fichier**: `frontend/app/profile/page.tsx` (ligne ~410-488, onglet "profile")

**État actuel**: Formulaire profile avec fullName, email, userType

**À ajouter**: Production type et category APRÈS le champ userType

### Code à ajouter dans l'onglet "profile" form:

```tsx
{/* === NOUVEAU: Production Type === */}
<div>
  <label className="block text-sm font-medium text-gray-700 mb-2">
    {t("profile.productionType.label")}
  </label>
  <p className="text-xs text-gray-500 mb-3">
    {t("profile.productionType.why")}
  </p>
  <div className="space-y-2">
    <label className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
      <input
        type="checkbox"
        checked={formData.productionType.includes('broiler')}
        onChange={(e) => {
          const newProductionType = e.target.checked
            ? [...formData.productionType, 'broiler']
            : formData.productionType.filter(t => t !== 'broiler');
          setFormData(prev => ({ ...prev, productionType: newProductionType }));
        }}
        className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
      />
      <span className="text-sm text-gray-700">
        {t("profile.productionType.broiler")}
      </span>
    </label>
    <label className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
      <input
        type="checkbox"
        checked={formData.productionType.includes('layer')}
        onChange={(e) => {
          const newProductionType = e.target.checked
            ? [...formData.productionType, 'layer']
            : formData.productionType.filter(t => t !== 'layer');
          setFormData(prev => ({ ...prev, productionType: newProductionType }));
        }}
        className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
      />
      <span className="text-sm text-gray-700">
        {t("profile.productionType.layer")}
      </span>
    </label>
  </div>
</div>

{/* === NOUVEAU: Category === */}
<div>
  <label className="block text-sm font-medium text-gray-700 mb-2">
    {t("profile.category.label")}
  </label>
  <p className="text-xs text-gray-500 mb-3">
    {t("profile.category.why")}
  </p>
  <select
    value={formData.category}
    onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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

  {/* Conditional: Other Category Input */}
  {formData.category === 'other' && (
    <input
      type="text"
      value={formData.categoryOther}
      onChange={(e) => setFormData(prev => ({ ...prev, categoryOther: e.target.value }))}
      placeholder={t("profile.category.otherPlaceholder")}
      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mt-2"
    />
  )}
</div>
```

### État formData (modifier ligne ~129):

```tsx
// ANCIEN:
const [formData, setFormData] = useState({
  fullName: "",
  email: "",
  userType: "producer" as "producer" | "professional",
});

// NOUVEAU (ajouter ces champs):
const [formData, setFormData] = useState({
  fullName: "",
  email: "",
  userType: "producer" as "producer" | "professional",
  productionType: [] as string[],
  category: "",
  categoryOther: "",
});
```

### Initialisation depuis user (modifier useEffect ligne ~151):

```tsx
// ANCIEN:
setFormData({
  fullName: getSafeName(user),
  email: getSafeEmail(user),
  userType: getSafeUserType(user) as "producer" | "professional",
});

// NOUVEAU (ajouter ces lignes):
setFormData({
  fullName: getSafeName(user),
  email: getSafeEmail(user),
  userType: getSafeUserType(user) as "producer" | "professional",
  productionType: user.production_type || [],
  category: user.category || "",
  categoryOther: user.category_other || "",
});
```

### Payload update (modifier handleSubmit ligne ~238):

```tsx
// ANCIEN:
const dataToUpdate = {
  name: trimmedName,
  user_type: formData.userType,
};

// NOUVEAU (ajouter ces lignes):
const dataToUpdate = {
  name: trimmedName,
  user_type: formData.userType,
  production_type: formData.productionType.length > 0 ? formData.productionType : null,
  category: formData.category || null,
  category_other: formData.category === 'other' ? formData.categoryOther : null,
};
```

---

## 3. TYPES - Ajouter types TypeScript

**Fichier**: `frontend/types/index.ts` (ou là où User est défini)

### Ajouter au type User:

```typescript
export interface User {
  // ... champs existants ...
  production_type?: string[];
  category?: string;
  category_other?: string;
}
```

---

## 📋 Checklist Implementation:

### Signup Form:
- [ ] Ajouter state (productionType, category, categoryOther)
- [ ] Ajouter UI checkboxes + select dans le formulaire
- [ ] Modifier payload signup

### Profile Page:
- [ ] Ajouter champs à formData state
- [ ] Ajouter UI checkboxes + select dans l'onglet "profile"
- [ ] Initialiser depuis user data (useEffect)
- [ ] Modifier payload update (handleSubmit)

### Types:
- [ ] Ajouter production_type, category, category_other au type User

### Test:
- [ ] Test signup avec nouveaux champs
- [ ] Test profile update
- [ ] Vérifier données sauvegardées dans Supabase

---

## 🎯 Notes Importantes:

1. **Messages "Pourquoi"**: Déjà implémentés avec icône 💡 et fond bleu pour attirer l'attention

2. **Validation côté frontend**: Optionnelle (non requis pour signup), validation stricte côté backend déjà en place

3. **Traductions**: Déjà complétées pour fr/en/es/de

4. **UI/UX**:
   - Checkboxes avec bordure pour production_type (meilleure UX que dropdown)
   - Select dropdown pour category (8 options + other)
   - Input conditionnel si category="other"
   - Messages explicatifs en bleu (💡)

5. **Backend**: Déjà prêt à recevoir ces données

---

## Après l'implémentation UI:

Voir `IMPLEMENTATION_PLAN_USER_PROFILING.md` Phase 3 pour l'intégration LLM.
