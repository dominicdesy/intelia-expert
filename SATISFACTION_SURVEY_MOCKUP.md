# 📊 Sondage de Satisfaction - Placement dans l'Interface

## 🎯 Où apparaîtra le sondage ?

Le sondage apparaîtra **dans le flux de conversation**, comme un message système distinct.

---

## 📱 Mockup Visuel

```
┌─────────────────────────────────────────────────────┐
│  [+]  [History]                      [?]  [Profile] │  ← Header
├─────────────────────────────────────────────────────┤
│                                                     │
│  👤 User:                                          │
│  ┌───────────────────────────────────────────┐    │
│  │ Comment prévenir la coccidiose ?          │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│                                          🤖 AI:    │
│  ┌───────────────────────────────────────────┐    │
│  │ La coccidiose est une maladie...         │    │
│  │ (longue réponse détaillée)               │    │
│  │ 👍 👎                                     │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  👤 User:                                          │
│  ┌───────────────────────────────────────────┐    │
│  │ Et pour les pondeuses ?                   │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│                                          🤖 AI:    │
│  ┌───────────────────────────────────────────┐    │
│  │ Pour les pondeuses, c'est différent...   │    │
│  │ 👍 👎                                     │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  ... (23 autres échanges) ...                     │
│                                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │ 🌟 Before you go — could you rate your     │ │  ← SONDAGE
│  │    experience today?                        │ │
│  │                                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │    😊     │  │    😐     │  │    🙁     │ │ │
│  │  │ Satisfied │  │  Neutral  │  │Unsatisfied│ │ │
│  │  └──────────┘  └──────────┘  └──────────┘ │ │
│  │                                              │ │
│  │  [Skip this survey]                         │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│  👤 User:  (peut continuer la conversation)       │
│  ┌───────────────────────────────────────────┐    │
│  │ Merci, une autre question...              │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
├─────────────────────────────────────────────────────┤
│  📷🎤 | [Type your message...]           | ➤       │  ← Footer
└─────────────────────────────────────────────────────┘
```

---

## 🔍 Détails d'Implémentation

### 1️⃣ Position dans le DOM

**Emplacement exact :**
```tsx
// Dans ChatInterface component (page.tsx)

<MessageList
  processedMessages={processedMessages}  // Messages normaux
  // ... autres props
/>

{/* NOUVEAU: Sondage de satisfaction */}
{shouldShowSurvey && !surveyCompleted && (
  <SatisfactionSurvey
    conversationId={currentConversation.id}
    onComplete={handleSurveyComplete}
    onSkip={handleSurveySkip}
  />
)}

{isLoadingChat && <LoadingDots />}

<div ref={messagesEndRef} />  {/* Scroll anchor */}
```

**Rendu :** Le sondage apparaît **APRÈS** tous les messages, **AVANT** l'indicateur de chargement.

---

### 2️⃣ Logique d'Affichage

```typescript
// Quand afficher le sondage ?

const shouldShowSurvey = useMemo(() => {
  if (!currentConversation) return false;

  const messageCount = currentConversation.message_count || 0;
  const lastSurveyAt = localStorage.getItem(`survey_${currentConversation.id}`);

  // Première fois : ~25 messages (±5 pour variation)
  if (!lastSurveyAt && messageCount >= 20 && messageCount <= 30) {
    return Math.random() < 0.3; // 30% de chance à chaque render
  }

  // Suivantes : tous les ~40 messages
  if (lastSurveyAt) {
    const lastCount = parseInt(lastSurveyAt);
    const delta = messageCount - lastCount;

    if (delta >= 35 && delta <= 45) {
      return Math.random() < 0.3;
    }
  }

  return false;
}, [currentConversation?.message_count]);
```

---

### 3️⃣ Design du Composant SatisfactionSurvey

```tsx
┌────────────────────────────────────────────────────┐
│  🌟 Before you go — could you rate your           │
│     experience today?                              │
│                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐│
│  │      😊       │  │      😐       │  │    🙁     ││
│  │   Satisfied   │  │    Neutral    │  │Unsatisfied││
│  │               │  │               │  │          ││
│  │  ✓ Helpful    │  │  ⚖️ Okay      │  │ ❌ Poor   ││
│  └──────────────┘  └──────────────┘  └──────────┘│
│                                                    │
│  [💬 Add a comment (optional)]                    │  ← Si cliqué
│  ┌──────────────────────────────────────────────┐ │
│  │ Tell us more... (optional)                   │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  [Skip this survey]                               │
└────────────────────────────────────────────────────┘

État après clic sur un bouton:
┌────────────────────────────────────────────────────┐
│  ✅ Thank you for your feedback!                  │
│                                                    │
│  Your rating helps us improve Intelia Expert.     │
└────────────────────────────────────────────────────┘
  ↓ (disparaît après 3 secondes)
```

---

## 🎨 Variantes de Styles

### Style 1: **Cards distinctes** (Recommandé)
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│     😊      │  │     😐      │  │     🙁      │
│  Satisfied  │  │   Neutral   │  │ Unsatisfied │
│             │  │             │  │             │
│ [    ✓    ] │  │ [    ⚖️    ] │  │ [    ❌    ] │
└─────────────┘  └─────────────┘  └─────────────┘
  hover: scale(1.05), shadow-lg
  active: scale(0.95)
```

### Style 2: **Boutons horizontaux simples**
```
[😊 Satisfied]  [😐 Neutral]  [🙁 Unsatisfied]
```

### Style 3: **Emoji grande taille clickable**
```
      😊              😐              🙁
   Satisfied       Neutral      Unsatisfied

   (emoji size: 48px, clickable avec hover effect)
```

---

## 📊 Données Enregistrées

### Table: `conversation_satisfaction_surveys`

```sql
CREATE TABLE conversation_satisfaction_surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    user_id TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('satisfied', 'neutral', 'unsatisfied')),
    comment TEXT,
    message_count_at_survey INTEGER,  -- Nombre de messages au moment du sondage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Exemple de données:**
```
id: uuid
conversation_id: a1b2c3d4...
user_id: user_123
rating: "satisfied"
comment: "Super rapide et précis !"
message_count_at_survey: 27
created_at: 2025-10-23 10:30:00
```

---

## 🔄 Flow Utilisateur

```
User pose 25+ questions
         ↓
Sondage apparaît dans le chat
         ↓
    ┌────┴────┐
    ↓         ↓
  Clique   Skip
    ↓         ↓
  Rate    Continue
    ↓
Commentaire (optionnel)
    ↓
Enregistré en DB
    ↓
Message "Merci !" (3s)
    ↓
Continue conversation
```

---

## 📱 Responsive Mobile

### Desktop (>768px)
```
┌──────────────────────────────────────────────┐
│  🌟 Before you go — could you rate your     │
│     experience today?                        │
│                                              │
│  [😊 Satisfied]  [😐 Neutral]  [🙁 Unsatisfied] │
│                                              │
│  [Skip]                                      │
└──────────────────────────────────────────────┘
```

### Mobile (<768px)
```
┌─────────────────────────┐
│ 🌟 Rate your experience│
│                         │
│    ┌─────────────┐     │
│    │     😊      │     │
│    │  Satisfied  │     │
│    └─────────────┘     │
│                         │
│    ┌─────────────┐     │
│    │     😐      │     │
│    │   Neutral   │     │
│    └─────────────┘     │
│                         │
│    ┌─────────────┐     │
│    │     🙁      │     │
│    │ Unsatisfied │     │
│    └─────────────┘     │
│                         │
│    [Skip]               │
└─────────────────────────┘
```

---

## 🎯 Quelle option préférez-vous ?

**Option A: Card dans le flux de messages** (Recommandée)
- ✅ Naturel, suit le flow
- ✅ Pas intrusif
- ✅ Facile à skip

**Option B: Modal popup**
- ⚠️ Plus intrusif
- ⚠️ Bloque la conversation
- ❌ Moins naturel

**Option C: Bannière sticky en haut**
- ⚠️ Prend de l'espace
- ⚠️ Cache le header
- ❌ Mobile problématique

---

## ⏰ Timing Recommandé

```javascript
// Première apparition
messageCount >= 23 && messageCount <= 27  // ~25 (±2)
  → 30% de chance à chaque nouveau message

// Apparitions suivantes
lastSurvey + 38 <= messageCount <= lastSurvey + 42  // ~40 (±2)
  → 30% de chance
```

**Pourquoi 30% de chance ?**
- Évite d'apparaître systématiquement au même moment
- Rend l'expérience plus naturelle
- Réduit la fatigue de sondage

---

## 🚀 Résumé Visuel Final

```
Chat normal:
[Message 1] [Message 2] ... [Message 24]

Déclenchement:
[Message 25] ← Trigger zone (23-27)
     ↓
[SONDAGE APPARAÎT ICI] 🌟
     ↓
User peut:
  - Répondre au sondage
  - Skip
  - Continuer à poser des questions

Le sondage reste visible jusqu'à:
  - User clique (rate ou skip)
  - User pose une nouvelle question (auto-skip)
```

---

**Question finale:** Préférez-vous le **Style 1 (Cards)**, **Style 2 (Boutons)**, ou **Style 3 (Emojis grands)** ?
