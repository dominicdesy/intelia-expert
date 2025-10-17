# Plan d'Implémentation: Conversation Vocale en Temps Réel

## 📋 Vue d'Ensemble

Transformer l'expérience actuelle (question → attendre la réponse complète → écouter) en une conversation naturelle et fluide avec réponses en streaming audio.

---

## 🎯 Objectifs

1. **Streaming Audio Immédiat**: L'utilisateur entend la réponse dès les premiers mots générés
2. **Latence Réduite**: ~500ms entre question vocale et début de la réponse audio
3. **Conversation Naturelle**: Possibilité d'interrompre et de reprendre comme une vraie conversation
4. **Expérience Mobile Optimale**: Fluidité parfaite sur iPhone/Android

---

## 🏗️ Architecture Proposée

```
┌─────────────────┐
│   Frontend      │
│   (Next.js)     │
│                 │
│  • Microphone   │
│  • Web Audio    │
│  • Audio Queue  │
└────────┬────────┘
         │ WebSocket
         ↓
┌─────────────────┐
│    Backend      │
│   (FastAPI)     │
│                 │
│  • WebSocket    │
│  • OpenAI RT    │
│  • Weaviate     │
└─────────────────┘
```

---

## 🔧 Technologies Requises

### Backend
- **OpenAI Realtime API**: Streaming audio bidirectionnel
- **WebSocket (FastAPI)**: Communication temps réel avec frontend
- **Weaviate**: RAG pour contexte métier (déjà en place)

### Frontend
- **WebSocket API**: Communication bidirectionnelle
- **Web Audio API**: Lecture audio fluide avec queue
- **MediaRecorder**: Capture audio microphone (déjà en place)

---

## 📦 Composants à Développer

### 1. Backend - Endpoint WebSocket (`/ws/voice`)

**Fichier**: `backend/app/api/v1/voice_realtime.py`

**Responsabilités**:
- Accepter connexions WebSocket des clients
- Gérer session OpenAI Realtime API
- Router les messages audio bidirectionnels
- Injecter contexte RAG au bon moment
- Gérer erreurs et reconnexions

**Flow**:
```
1. Client se connecte → Créer session OpenAI RT
2. Client envoie audio → Transférer à OpenAI
3. OpenAI génère réponse → Injecter contexte Weaviate si nécessaire
4. OpenAI stream audio → Transférer au client
5. Client déconnecte → Nettoyer session
```

**Pseudo-code clé**:
```python
@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()

    # Créer session OpenAI Realtime
    openai_session = await create_openai_realtime_session()

    # Router messages bidirectionnels
    async with asyncio.TaskGroup() as tg:
        tg.create_task(forward_client_to_openai(websocket, openai_session))
        tg.create_task(forward_openai_to_client(openai_session, websocket))
```

---

### 2. Frontend - Hook React (`useVoiceRealtime`)

**Fichier**: `frontend/lib/hooks/useVoiceRealtime.ts`

**Responsabilités**:
- Gérer connexion WebSocket
- Capturer audio microphone en continu
- Envoyer chunks audio au backend
- Recevoir chunks audio de réponse
- Jouer audio avec queue pour éviter coupures
- Gérer états (listening, speaking, idle)

**API du Hook**:
```typescript
const {
  isConnected,           // WebSocket connecté
  isListening,           // Microphone actif
  isSpeaking,            // LLM parle
  startConversation,     // Démarrer session
  stopConversation,      // Arrêter session
  interrupt,             // Interrompre LLM
  audioLevel             // Volume micro (UI feedback)
} = useVoiceRealtime();
```

**Flow Audio**:
```
Microphone → MediaRecorder → chunks 100ms → WebSocket → Backend
Backend → WebSocket → Audio Queue → Web Audio API → Speakers
```

---

### 3. Frontend - Composant UI (`VoiceRealtimeButton`)

**Fichier**: `frontend/components/VoiceRealtimeButton.tsx`

**Responsabilités**:
- Bouton visuel pour démarrer/arrêter conversation
- Animation visuelle pendant écoute/parole
- Indicateur de volume microphone (waveform)
- Gestion états d'erreur
- Feedback haptique sur mobile

**États visuels**:
- 🎤 **Idle**: Bouton microphone gris
- 🟢 **Listening**: Animation verte pulsante
- 🔵 **Speaking**: Animation bleue (LLM parle)
- ⏸️ **Interrupted**: Bouton pause
- ❌ **Error**: Indicateur rouge

---

## 🔄 Flow Complet d'une Conversation

### Cas d'Usage: "Quelle est la température d'incubation des œufs?"

```
1. [USER] Appuie sur bouton vocal
   ↓
2. [FRONTEND] Démarre WebSocket + Microphone
   ↓
3. [BACKEND] Crée session OpenAI Realtime
   ↓
4. [USER] Parle: "Quelle est la température..."
   ↓
5. [FRONTEND] Envoie audio chunks (100ms) via WebSocket
   ↓
6. [BACKEND] Transfère à OpenAI Realtime API
   ↓
7. [OPENAI] Détecte fin de phrase (VAD)
   ↓
8. [BACKEND] Intercepte question → Query Weaviate
   ↓
9. [BACKEND] Injecte contexte: "Voici infos pertinentes: ..."
   ↓
10. [OPENAI] Génère réponse avec contexte
    ↓
11. [OPENAI] Stream audio chunks
    ↓
12. [BACKEND] Transfère chunks au client
    ↓
13. [FRONTEND] Queue audio + lecture immédiate
    ↓
14. [USER] Entend réponse ~500ms après fin de question
    ↓
15. [USER] Peut interrompre ou poser nouvelle question
```

---

## 🎨 Intégration RAG (Weaviate)

### Stratégie d'Injection de Contexte

**Option A: Injection Transparente** (Recommandée)
```python
# Dès que OpenAI détecte fin de question
async def on_speech_end(transcript: str):
    # Query Weaviate
    context = await query_weaviate(transcript)

    # Injecter comme message système
    await openai_session.send({
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "system",
            "content": f"Context from database: {context}"
        }
    })

    # OpenAI génère réponse avec contexte
```

**Option B: Instructions Système Pré-configurées**
```python
# Au début de session
system_instructions = """
Tu es un expert avicole. Utilise le contexte fourni.
Si contexte disponible, base ta réponse dessus.
Si pas de contexte, utilise tes connaissances générales.
"""
```

---

## 📱 Optimisations Mobile

### 1. Gestion Batterie
- Utiliser WebRTC VAD (Voice Activity Detection) pour économiser bande passante
- Arrêter microphone quand LLM parle
- Déconnecter WebSocket après 30s inactivité

### 2. Gestion Réseau
- Reconnexion automatique si perte connexion
- Buffer audio local en cas de latence réseau
- Dégrader qualité audio si connexion lente (44kHz → 16kHz)

### 3. Audio Mobile
- Utiliser AudioContext avec autoplay policy
- Gérer changements audio route (Bluetooth, écouteurs)
- Feedback haptique via Vibration API

---

## 🐛 Gestion d'Erreurs

### Erreurs Critiques
1. **Microphone refusé**: Fallback vers input texte
2. **WebSocket fermé**: Tentative reconnexion (3x)
3. **OpenAI API timeout**: Message d'erreur + retry
4. **Weaviate indisponible**: Continuer sans contexte

### UX Errors
```typescript
// Afficher message contextuel
setError({
  type: 'microphone_denied',
  message: t('voice.error.microphone'),
  action: 'settings' // Lien vers paramètres device
})
```

---

## 📊 Métriques de Succès

### KPIs à Tracker
1. **Latence P95**: < 500ms (question → début réponse)
2. **Taux d'interruption**: % conversations interrompues par user
3. **Durée moyenne conversation**: Objectif 2-3 tours
4. **Taux d'erreur**: < 1% des sessions
5. **Adoption**: % utilisateurs utilisant mode vocal

---

## 🚀 Plan de Développement (Estimé)

### Phase 1: Backend Foundation (2-3 jours)
- [ ] Endpoint WebSocket `/ws/voice`
- [ ] Intégration OpenAI Realtime API
- [ ] Tests basiques audio bidirectionnel

### Phase 2: Frontend Basic (2-3 jours)
- [ ] Hook `useVoiceRealtime`
- [ ] Composant `VoiceRealtimeButton`
- [ ] WebSocket client + audio queue

### Phase 3: RAG Integration (1-2 jours)
- [ ] Injection contexte Weaviate
- [ ] Tests avec vraies questions métier
- [ ] Tuning prompts système

### Phase 4: Mobile Polish (1-2 jours)
- [ ] Optimisations batterie
- [ ] Gestion erreurs réseau
- [ ] Tests iPhone/Android

### Phase 5: Production (1 jour)
- [ ] Monitoring/logs
- [ ] Rate limiting
- [ ] Documentation API

**Total estimé**: 7-10 jours de développement

---

## 🔐 Sécurité & Coûts

### Sécurité
- Authentifier WebSocket avec JWT token
- Limiter durée session (10 min max)
- Rate limiting par utilisateur (5 sessions/heure)

### Coûts OpenAI Realtime API
- **Input audio**: $0.06 / minute
- **Output audio**: $0.24 / minute
- **Estimation**: 1000 conversations/mois de 2 min = ~$600/mois

**Optimisation coûts**:
- Arrêter microphone quand LLM parle (-50% input)
- VAD pour ne transmettre que quand user parle
- Timeout après inactivité

---

## 📚 Ressources Techniques

### Documentation OpenAI
- [Realtime API Guide](https://platform.openai.com/docs/guides/realtime)
- [WebRTC Integration](https://platform.openai.com/docs/guides/realtime-webrtc)

### Exemples de Référence
```bash
# Repo OpenAI officiel
git clone https://github.com/openai/openai-realtime-api-beta

# Exemple Next.js
cd examples/next-js-voice-assistant
```

### Web APIs Utilisées
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [MediaRecorder API](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder)

---

## 🎯 Alternative: Implémentation Hybride

Si budget/temps limité, considérer approche hybride:

### Option Simple (déjà fait)
- STT (Speech-to-Text) → LLM → TTS (Text-to-Speech)
- Latence: ~2-3 secondes
- Coût: ~$200/mois pour 1000 conversations

### Option Temps Réel (ce document)
- Streaming audio bidirectionnel
- Latence: ~500ms
- Coût: ~$600/mois pour 1000 conversations

**Recommandation**: Commencer hybride, migrer vers temps réel si adoption forte.

---

## 📞 Support & Questions

Ce plan sera la base de notre implémentation la semaine prochaine. Pour toute clarification:
- Relire ce document
- Consulter exemples OpenAI
- Tester démo OpenAI Realtime Console

**Status**: ✅ Document de référence prêt pour développement
