# 📱 Projet: Redesign Complet Interface Mobile iPhone

## 📊 Vue d'ensemble

**Objectif**: Refonte complète de l'interface mobile pour une expérience utilisateur optimale sur iPhone, avec un design moderne, épuré et professionnel.

**Scope**: Interface mobile uniquement (iPhone prioritaire)

**Durée estimée**: 2-3 heures de développement

**Status**: 📝 Planifié - Non démarré

---

## 🎨 Spécifications de Design

### 🧭 En-tête (Header)

**Dimensions & Style:**
- Hauteur: `52px`
- Position: `sticky top-0`
- Fond: `#FFFFFF` (clair) / `#0F172A` (sombre)
- Bordure inférieure: `1px solid #E5E7EB` (clair) / `#334155` (sombre)
- Effet: `backdrop-blur`, `shadow-sm`

**Contenu (gauche → droite):**
1. **Logo Intelia** (gauche)
   - Icône arrondie: `24×24px`
   - Bordure radius: `rounded-full`

2. **Titre** (centre-gauche)
   - Texte: "Intelia Expert"
   - Police: `Inter, 15px, font-medium`
   - Couleur: `#0F172A` (clair) / `#E2E8F0` (sombre)

3. **Avatar utilisateur** (droite)
   - Cercle bleu Intelia: `#005EB8`
   - Initiale blanche: `#FFFFFF`
   - Taille: `32×32px`

**Comportement:**
- Reste visible au scroll (sticky)
- Ombre subtile au scroll
- Support `env(safe-area-inset-top)` pour le notch

---

### 💬 Corps Principal (Zone de Conversation)

**Container:**
- Fond global: `#F7F9FC` (clair) / `#0F172A` (sombre)
- Padding: `12px horizontal, 8-10px vertical`
- Hauteur: `calc(100dvh - header - footer)`
- Overflow: `overflow-y: auto`
- Scroll behavior: `smooth`

#### ✅ Bulles Intelia (Messages du bot)

**Style:**
- Fond: `#FFFFFF` (clair) / `#1E293B` (sombre)
- Bordure: `1px solid #E5E7EB` (clair) / `#334155` (sombre)
- Texte: `#0F172A` (clair) / `#E2E8F0` (sombre)
- Border radius: `16px`
- Padding: `8px 12px`
- Largeur max: `85%`
- Alignement: `justify-start`

**Avatar:**
- Logo Intelia: `20×20px`
- Position: à gauche de la bulle
- Margin right: `8px`

**Espacement:**
- Entre messages du même auteur: `6px`
- Entre messages d'auteurs différents: `10px`

#### 👤 Bulles Utilisateur

**Style:**
- Fond: `#005EB8` (bleu Intelia)
- Texte: `#FFFFFF`
- Border radius: `16px`
- Padding: `8px 12px`
- Largeur max: `85%`
- Alignement: `justify-end`

**Espacement:**
- Vertical entre messages: `8px`

#### 💡 Messages Contextuels (Quick Replies)

**Bulles principales:**
- Même style que bulles Intelia

**Chips de réponses rapides:**
- Border radius: `12px`
- Bordure: `1px solid #D1D5DB`
- Fond: `#FFFFFF`
- Texte: `#374151, 14px`
- Padding: `6px 12px`
- Hover/Active: `bg-gray-50 #F3F4F6`

**Exemples de chips:**
- "Comparer aux femelles"
- "Voir courbe 0–42 jours"
- "Afficher sources"
- "Plus de détails"

**Disposition:**
- Flex wrap horizontal
- Gap: `8px`
- Margin top: `8px`

---

### 🎤📷 Zone d'Entrée (Footer)

**Container:**
- Fond: `#FFFFFF` (clair) / `#1E1F22` (sombre)
- Bordure supérieure: `1px solid #E5E7EB` / `#2C2C2C`
- Padding vertical: `8px`
- Padding bottom: `calc(8px + env(safe-area-inset-bottom))`
- Position: `fixed bottom-0`

**Disposition (gauche → droite):**

| Élément | Position | Taille | Fonction |
|---------|----------|--------|----------|
| 📷 Caméra | Extrême gauche | `36×36px` | Capture image (caméra/galerie) |
| ✏️ Champ texte | Centre (flex-1) | Min `44px`, Max `132px` | Saisie multiligne auto-expand |
| 🎤 Micro | Droite du champ | `36×36px` | Dictée vocale |
| ➤ Envoyer | Extrême droite | `44px` hauteur | Envoi message |

#### Styles des Éléments

**📷 Bouton Caméra:**
```css
width: 36px
height: 36px
background: transparent
color: #6B7280 (clair) / #CBD5E1 (sombre)
border-radius: 50%
active:bg-gray-100 / active:bg-gray-700
```

**✏️ Champ Texte:**
```css
background: #F9FAFB (clair) / #2C2C2C (sombre)
color: #0F172A / #E5E7EB
placeholder: #9CA3AF
border: 1px solid #D1D5DB / #334155
border-radius: 12px
padding: 10px 12px
font-size: 15px
min-height: 44px
max-height: 132px (≈3 lignes)
resize: none
overflow-y: auto

focus:ring-2
focus:ring-[#005EB8]/40
focus:border-[#005EB8]
```

**🎤 Bouton Micro:**
```css
width: 36px
height: 36px
background: transparent
color: #6B7280 (clair) / #CBD5E1 (sombre)
border-radius: 50%
active:bg-gray-100 / active:bg-gray-700

/* État actif (enregistrement) */
active:bg-blue-50
active:color-blue-600
animation: pulse 1.5s infinite
```

**➤ Bouton Envoyer:**
```css
background: #005EB8
color: #FFFFFF
font-weight: 500
font-size: 15px
padding: 12px 16px
border-radius: 12px
min-height: 44px
min-width: 44px

hover:bg-#004A90
active:scale-95

/* État désactivé (texte vide) */
disabled:opacity-50
disabled:cursor-not-allowed
```

---

## 🧠 Comportements Intelligents (UX Dynamique)

### Animations

1. **Apparition des bulles:**
   - Fade in: `80ms ease-in-out`
   - Légère translation: `translateY(8px) → translateY(0)`

2. **Envoi de message:**
   - Bulle utilisateur: fade in + slide from right
   - Auto-scroll vers le bas: `smooth behavior`
   - Clear input field immédiatement

3. **Quick replies:**
   - Apparition après la bulle Intelia: `delay 200ms`
   - Fade in staggered: chaque chip +50ms

4. **Micro actif:**
   - Pulse animation bleu: `1.5s infinite`
   - Indicateur visuel d'enregistrement

### Interactions

1. **Textarea auto-expand:**
   - Démarre à 1 ligne (`44px`)
   - S'étend automatiquement jusqu'à 3 lignes max (`132px`)
   - Au-delà: scroll interne

2. **Bouton Envoyer intelligent:**
   - Désactivé (grisé) si texte vide ET aucune image
   - Activé dès qu'il y a du contenu
   - Icône change: avion grisé → avion bleu

3. **Caméra:**
   - Ouvre `<input type="file" accept="image/*" capture="environment" />`
   - Support multi-images
   - Preview thumbnails au-dessus du champ texte

4. **Scroll automatique:**
   - Nouveau message → scroll to bottom
   - Sauf si l'utilisateur a scroll up manuellement
   - Bouton "Scroll to bottom" apparaît si >200px du bas

---

## ⚙️ Accessibilité & Performance

### Accessibilité (WCAG 2.1 AA)

- ✅ Police minimum: `15px`
- ✅ Contraste texte: `> 4.5:1`
- ✅ Cibles tactiles: minimum `44×44px`
- ✅ `aria-live="polite"` sur messages entrants
- ✅ `aria-label` sur tous les boutons
- ✅ Focus visible: `ring-2` bleu Intelia
- ✅ Support clavier (Enter pour envoyer)

### Performance

- ✅ Lazy rendering si > 100 messages
- ✅ Virtual scrolling pour grandes conversations
- ✅ Debounce sur textarea auto-resize (100ms)
- ✅ Optimisation images: lazy load, compression
- ✅ CSS containment sur les bulles
- ✅ RequestAnimationFrame pour animations
- ✅ Target: 60 FPS constant

### Support iPhone

- ✅ Optimisé iPhone 13, 14, 15 (390px width)
- ✅ Support notch: `viewport-fit=cover`
- ✅ Safe areas: `env(safe-area-inset-*)`
- ✅ iOS Safari-specific fixes:
  - `-webkit-appearance: none`
  - `touch-action: manipulation`
  - Prevent zoom: `font-size: 16px` minimum

---

## 🌓 Dark Mode

### Activation
```css
@media (prefers-color-scheme: dark) {
  /* Styles sombre */
}
```

### Palette de couleurs

| Élément | Light Mode | Dark Mode |
|---------|------------|-----------|
| Background | `#F7F9FC` | `#0F172A` |
| Header/Footer | `#FFFFFF` | `#1E1F22` |
| Bulle Intelia | `#FFFFFF` | `#1E293B` |
| Bulle User | `#005EB8` | `#005EB8` |
| Texte primaire | `#0F172A` | `#E2E8F0` |
| Texte secondaire | `#6B7280` | `#94A3B8` |
| Bordures | `#E5E7EB` | `#334155` |
| Input background | `#F9FAFB` | `#2C2C2C` |
| Icônes | `#6B7280` | `#CBD5E1` |

---

## 📋 Plan d'Implémentation (Phases)

### Phase 1: Structure & Layout (30-45 min)
**Fichiers à modifier:**
- `frontend/app/chat/page.tsx`
- Potentiellement créer: `frontend/app/chat/components/MobileChat.tsx`

**Tâches:**
1. Créer nouveau header compact (52px)
   - Logo 24×24 + Titre + Avatar
   - Sticky positioning
   - Safe area inset top
2. Refonte footer (zone d'entrée)
   - Disposition: Caméra | Textarea | Micro | Send
   - Safe area inset bottom
3. Ajuster hauteur corps principal
   - `calc(100dvh - 52px header - Xpx footer)`
4. Conditional rendering: `{isMobileDevice ? <MobileChat /> : <DesktopChat />}`

**Tests:**
- Header reste visible au scroll
- Footer reste fixé en bas
- Notch iPhone géré correctement
- Pas de zone morte tactile

---

### Phase 2: Messages & Bulles (30-45 min)
**Fichiers:**
- `frontend/app/chat/page.tsx` (MessageList component)
- Styles Tailwind inline ou nouveau CSS module

**Tâches:**
1. Refonte bulles Intelia:
   - Fond blanc/sombre + bordure
   - Border radius 16px
   - Padding 8×12
   - Max width 85%
   - Logo 20×20 à gauche
2. Refonte bulles utilisateur:
   - Fond bleu #005EB8
   - Texte blanc
   - Alignement droite
3. Espacement messages:
   - 6px intra-auteur
   - 10px inter-auteurs
4. Markdown rendering propre dans les bulles

**Tests:**
- Bulles s'affichent correctement
- Alignement gauche/droite
- Logo visible sur bulles Intelia
- Largeur max respectée

---

### Phase 3: Zone d'Entrée Interactive (30-45 min)
**Fichiers:**
- `frontend/app/chat/page.tsx` (ChatInput component)
- Possiblement nouveau: `frontend/app/chat/components/MobileInput.tsx`

**Tâches:**
1. Textarea auto-expand:
   - Min height 44px (1 ligne)
   - Max height 132px (3 lignes)
   - Auto-resize on input
   - Scroll interne au-delà
2. Bouton Send intelligent:
   - Désactivé si vide
   - `disabled:opacity-50`
   - Visual feedback on press
3. Bouton caméra (36×36):
   - Trigger file input
   - Support multi-images
4. Bouton micro (36×36):
   - Integration avec VoiceInput existant
   - Animation pulse quand actif

**Tests:**
- Textarea grandit/rétrécie correctement
- Bouton send s'active/désactive
- Caméra ouvre sélecteur
- Micro fonctionne
- Layout ne casse pas avec 3 lignes

---

### Phase 4: Quick Replies / Chips (20-30 min)
**Fichiers:**
- Nouveau: `frontend/app/chat/components/QuickReplyChips.tsx`
- `frontend/app/chat/page.tsx` (integration)

**Tâches:**
1. Composant QuickReplyChips:
   ```tsx
   <QuickReplyChips
     suggestions={["Comparer aux femelles", "Voir courbe 0–42 jours"]}
     onSelect={(text) => handleQuickReply(text)}
   />
   ```
2. Styles chips:
   - Border radius 12px
   - Border 1px gray
   - Padding 6×12
   - Hover effect
3. Logic pour générer suggestions:
   - Option A: Hardcodé selon contexte
   - Option B: LLM génère suggestions
   - Option C: Mix des deux
4. Affichage conditionnel:
   - Seulement sur messages Intelia
   - Fade in avec delay

**Tests:**
- Chips s'affichent sous les bulles Intelia
- Clic sur chip remplit le textarea
- Wrap correctement sur plusieurs lignes
- Animations smooth

---

### Phase 5: Animations & Polish (20-30 min)
**Fichiers:**
- `frontend/styles/globals.css` (animations CSS)
- `frontend/app/chat/page.tsx` (scroll behavior)

**Tâches:**
1. Animations bulles:
   ```css
   @keyframes fadeSlideIn {
     from { opacity: 0; transform: translateY(8px); }
     to { opacity: 1; transform: translateY(0); }
   }
   ```
2. Scroll automatique:
   - Nouveau message → scroll to bottom
   - Détection user scroll up
   - Bouton "Scroll to bottom" si nécessaire
3. Micro pulse animation:
   ```css
   @keyframes pulse {
     0%, 100% { opacity: 1; transform: scale(1); }
     50% { opacity: 0.7; transform: scale(1.05); }
   }
   ```
4. Send button press effect:
   - `active:scale-95`
   - Haptic feedback (si possible)

**Tests:**
- Animations fluides (60 fps)
- Pas de jank au scroll
- Auto-scroll fonctionne
- Pulse visible sur micro

---

### Phase 6: Dark Mode (30 min)
**Fichiers:**
- `frontend/app/chat/page.tsx`
- `frontend/styles/globals.css`

**Tâches:**
1. Détection mode:
   ```tsx
   const isDark = useMediaQuery('(prefers-color-scheme: dark)')
   ```
2. Appliquer palette sombre:
   - Background: #0F172A
   - Bulles: #1E293B
   - Texte: #E2E8F0
   - Etc.
3. Conditional classes:
   ```tsx
   className={isDark ? 'bg-slate-900' : 'bg-gray-50'}
   ```
4. Transitions smooth entre modes

**Tests:**
- Dark mode s'active automatiquement
- Tous les éléments ont couleurs sombre
- Contraste suffisant (4.5:1)
- Pas de flash au switch

---

### Phase 7: Tests & Optimisation (30 min)
**Tests complets:**

1. **Fonctionnels:**
   - [ ] Envoyer message texte
   - [ ] Envoyer image
   - [ ] Voice input
   - [ ] Quick replies
   - [ ] Scroll conversations longues
   - [ ] Dark mode toggle

2. **Visuels:**
   - [ ] Bulles alignées correctement
   - [ ] Espacements respectés
   - [ ] Couleurs conformes spec
   - [ ] Animations smooth

3. **Performance:**
   - [ ] 60 FPS au scroll
   - [ ] Pas de lag au typing
   - [ ] Images loadent vite
   - [ ] Build size raisonnable

4. **Accessibilité:**
   - [ ] Contraste > 4.5:1
   - [ ] Touch targets > 44px
   - [ ] ARIA labels présents
   - [ ] Keyboard navigation

5. **iPhone-specific:**
   - [ ] Notch géré (safe areas)
   - [ ] Pas de zoom involontaire
   - [ ] Keyboard push content up
   - [ ] Safari iOS quirks gérés

**Optimisations:**
- Lazy load messages (>100)
- Debounce textarea resize
- Memoize components
- CSS containment
- Image compression

---

## 🚀 Stratégie de Déploiement

### Option A: Branche de développement (RECOMMANDÉ)

```bash
# 1. Créer branche
git checkout -b feature/mobile-redesign

# 2. Développer par phases
git commit -m "Phase 1: Structure & Layout"
git commit -m "Phase 2: Messages & Bulles"
# ... etc

# 3. Tester complètement
npm run build
# Tests manuels sur iPhone

# 4. Merge quand prêt
git checkout main
git merge feature/mobile-redesign
git push
```

**Avantages:**
- ✅ Prod reste stable pendant développement
- ✅ Possibilité de rollback facile
- ✅ Review de code possible
- ✅ Tests sans pression

### Option B: Feature Flag

```tsx
// frontend/config/features.ts
export const MOBILE_REDESIGN_ENABLED =
  process.env.NEXT_PUBLIC_MOBILE_REDESIGN === 'true'

// Dans le code
{MOBILE_REDESIGN_ENABLED ? <NewMobileUI /> : <CurrentMobileUI />}
```

**Avantages:**
- ✅ Deploy progressif
- ✅ A/B testing possible
- ✅ Rollback instantané (toggle env var)

### Option C: Direct sur main (RISQUÉ)

Commits successifs sur main avec tests entre chaque phase.

**Inconvénients:**
- ❌ Risque de casser la prod
- ❌ Pression pour finir vite
- ❌ Difficile de rollback partiellement

---

## 📝 Checklist Pré-démarrage

Avant de commencer le développement, confirmer:

- [ ] **Desktop**: Interface actuelle reste inchangée?
- [ ] **Dark Mode**: Implémenter dès phase 1 ou plus tard?
- [ ] **Quick Replies**: Logic de génération définie?
- [ ] **Branche**: Créer `feature/mobile-redesign` ou direct main?
- [ ] **Fonctionnalités**: Liste confirmée de ce qu'on garde/supprime
- [ ] **Timeline**: Disponibilité pour 2-3h de dev continu?
- [ ] **Tests**: Accès à iPhone réel pour tester?

---

## 🎯 Résultat Attendu

### Avant (Interface actuelle mobile)
```
┌─────────────────────────────────────┐
│ ☰  🏢 Intelia          📋  ❓  👤  │ Header
├─────────────────────────────────────┤
│                                     │
│  🤖 Bonjour, comment puis-je...    │
│                                     │
│            Quelle est la cause 👤  │
│                                     │
│  🤖 La cause principale est...     │
│                                     │
├─────────────────────────────────────┤
│ [=========== Input ===========]    │
│                          [Send] [📷]│ Footer
└─────────────────────────────────────┘
```

### Après (Nouveau design)
```
┌─────────────────────────────────────┐
│ 🔵 Intelia Expert              👤  │ 52px sticky
├─────────────────────────────────────┤
│                                     │
│ 🤖 Bonjour, comment puis-je vous   │ Bulle blanche
│    aider aujourd'hui?               │ bordure grise
│                                     │
│    [Comparer mâles]  [Sources]     │ Quick chips
│                                     │
│             Quelle est la cause 👤 │ Bulle bleue
│             exacte?                 │ #005EB8
│                                     │
│ 🤖 La cause principale est la      │
│    variation de température...     │
│                                     │
├─────────────────────────────────────┤
│ 📷 [──── Input auto-expand ────]   │
│                            🎤  ➤   │ Footer fixe
└─────────────────────────────────────┘
```

**Améliorations visuelles:**
- ✅ Header épuré: logo + titre + avatar (gain de place)
- ✅ Bulles modernes avec bordures subtiles
- ✅ Quick replies pour interaction rapide
- ✅ Input expansible (1-3 lignes)
- ✅ Espacement optimisé (plus aéré)
- ✅ Couleurs cohérentes (bleu Intelia #005EB8)
- ✅ Dark mode natif

---

## 📚 Ressources & Références

### Design System
- **Couleur principale**: #005EB8 (Bleu Intelia)
- **Police**: Inter (Google Fonts)
- **Icons**: Heroicons ou Lucide React
- **Tailwind Config**: Étendre avec couleurs custom

### Inspirations
- iMessage (iOS)
- WhatsApp Web
- ChatGPT mobile
- Claude.ai mobile

### Documentation
- [iOS Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/ios)
- [Safe Area Insets](https://webkit.org/blog/7929/designing-websites-for-iphone-x/)
- [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/quickref/)

---

## 🐛 Problèmes Potentiels & Solutions

### 1. Keyboard push sur iOS
**Problème**: Clavier iOS pousse le contenu au lieu de overlay
**Solution**:
```tsx
useEffect(() => {
  const handleResize = () => {
    // Ajuster height en fonction du viewport
    document.documentElement.style.setProperty(
      '--app-height',
      `${window.innerHeight}px`
    )
  }
  window.addEventListener('resize', handleResize)
  handleResize()
}, [])
```

### 2. Zoom involontaire sur input focus (iOS)
**Problème**: iOS zoom si font-size < 16px
**Solution**:
```css
input, textarea {
  font-size: 16px !important; /* Minimum pour éviter zoom */
}
```

### 3. Scroll bounce effect (iOS)
**Problème**: Overscroll montre le fond
**Solution**:
```css
body {
  overscroll-behavior: none;
}
```

### 4. Textarea ne s'auto-resize pas
**Problème**: Hauteur fixe
**Solution**:
```tsx
const autoResize = (e) => {
  e.target.style.height = 'auto'
  e.target.style.height = Math.min(e.target.scrollHeight, 132) + 'px'
}
```

### 5. Safe area inset non supporté
**Problème**: Vieux navigateurs
**Solution**:
```css
padding-bottom: 8px; /* Fallback */
padding-bottom: calc(8px + env(safe-area-inset-bottom)); /* Modern */
```

---

## ✅ Critères de Succès

Le projet sera considéré réussi quand:

1. **Visuel**: Interface conforme aux specs (95%+)
2. **Fonctionnel**: Toutes les fonctionnalités marchent
3. **Performance**: 60 FPS sur iPhone 13+
4. **Accessibilité**: WCAG 2.1 AA respecté
5. **Tests**: Pas de régression sur desktop
6. **Build**: Compile sans erreurs ni warnings
7. **User Testing**: Feedback utilisateur positif

---

## 📞 Contact & Questions

Pour toute question pendant l'implémentation:
- Vérifier ce document d'abord
- Tester sur iPhone réel si possible
- Prendre des screenshots pour comparaison
- Commit fréquemment pour rollback facile

**Date de création**: 2025-10-18
**Dernière mise à jour**: 2025-10-18
**Status**: 📝 Planifié

---

## 🎬 Prêt à Démarrer?

Quand tu veux commencer:

1. **Lire ce document complètement** ✅
2. **Confirmer les choix** (branche, dark mode, etc.)
3. **Créer la branche**: `git checkout -b feature/mobile-redesign`
4. **Suivre les phases** une par une
5. **Tester après chaque phase**
6. **Demander de l'aide** si bloqué

Bon courage! 🚀
