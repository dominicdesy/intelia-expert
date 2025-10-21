# Décisions Techniques - Voice Realtime

Ce document répond aux questions **Q5, Q6, Q7** après exécution des POCs.

---

## Q5 : Stratégie d'Injection Contexte RAG

### Options Évaluées

#### Option A : Injection Après VAD (Simple)

**Flow** :
```
1. User parle
2. VAD détecte fin de parole (~200ms)
3. → Query Weaviate (~280ms P95)
4. → Injecter contexte dans OpenAI
5. → OpenAI génère réponse (~300ms)
Total estimé: ~780ms
```

**Avantages** :
- ✅ Simple à implémenter
- ✅ Contexte toujours pertinent (basé sur transcription complète)
- ✅ Logique linéaire facile à débugger

**Inconvénients** :
- ❌ Latence perceptible (~780ms)
- ❌ Dépasse objectif 500ms P95
- ❌ User doit attendre fin query Weaviate

**Code simplifié** :
```python
async def on_speech_end(transcript: str):
    # 1. Query Weaviate
    context = await query_weaviate(transcript)  # +280ms

    # 2. Injecter comme message système
    await openai_session.send({
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "system",
            "content": f"Contexte: {context}"
        }
    })

    # 3. Trigger réponse
    await openai_session.send({"type": "response.create"})
```

---

#### Option B : Pré-chargement Pendant Parole (Optimal)

**Flow** :
```
1. User commence à parler
2. → Streaming transcription partielle (OpenAI)
3. → Query Weaviate en parallèle avec transcription partielle
4. VAD détecte fin de parole (~200ms)
5. → Contexte DÉJÀ PRÊT
6. → OpenAI génère immédiatement (~300ms)
Total estimé: ~500ms
```

**Avantages** :
- ✅ Latence optimale (~500ms P95)
- ✅ Atteint objectif performance
- ✅ Meilleure UX (pas d'attente visible)

**Inconvénients** :
- ⚠️ Complexe à implémenter
- ⚠️ Risque query Weaviate avec transcription incomplète
- ⚠️ Gestion cache nécessaire (éviter queries inutiles)

**Code avancé** :
```python
class RealtimeRAGHandler:
    def __init__(self):
        self.partial_transcript = ""
        self.context_cache = None
        self.context_ready = False

    async def on_partial_transcript(self, partial: str):
        """Appelé dès qu'on a transcription partielle"""
        self.partial_transcript = partial

        # Si assez de mots, pré-charger contexte
        if len(partial.split()) >= 5:  # Au moins 5 mots
            if not self.context_ready:
                asyncio.create_task(self._preload_context(partial))

    async def _preload_context(self, query: str):
        """Query Weaviate en background"""
        self.context_cache = await query_weaviate(query)
        self.context_ready = True

    async def on_speech_end(self, final_transcript: str):
        """Fin de parole détectée"""
        # Attendre contexte si pas encore prêt
        if not self.context_ready:
            await asyncio.wait_for(
                self._wait_context_ready(),
                timeout=0.5  # Max 500ms
            )

        # Si contexte prêt, utiliser
        context = self.context_cache if self.context_ready else None

        # Générer réponse
        await self._generate_response(final_transcript, context)
```

---

#### Option C : Injection Post-Génération (Correction)

**Flow** :
```
1. User parle
2. OpenAI génère réponse immédiate (sans contexte)
3. → En parallèle, query Weaviate
4. → Si réponse incorrecte, corriger avec contexte
```

**Verdict** : ❌ **NON RECOMMANDÉ**
- Mauvaise UX (réponse puis correction visible)
- Complexe à gérer (comment détecter erreur ?)
- Gaspille tokens OpenAI

---

### 🎯 DÉCISION RECOMMANDÉE

**Option B (Pré-chargement)** avec fallback Option A.

**Stratégie hybride** :
```python
async def adaptive_rag_injection(partial_transcript, final_transcript):
    """Stratégie hybride intelligente"""

    # Tentative pré-chargement (Option B)
    if len(partial_transcript.split()) >= 5:
        context = await asyncio.wait_for(
            query_weaviate(partial_transcript),
            timeout=0.3  # Max 300ms
        )
        if context:
            return context

    # Fallback: Query après VAD (Option A)
    # Mais avec timeout strict
    try:
        context = await asyncio.wait_for(
            query_weaviate(final_transcript),
            timeout=0.2  # Max 200ms
        )
        return context
    except asyncio.TimeoutError:
        # Si trop lent, continuer sans contexte
        logger.warning("Weaviate timeout, using LLM general knowledge")
        return None
```

**Critères d'activation** :
- ✅ Option B si transcription partielle >5 mots
- ✅ Option A (timeout strict) si pas assez de mots
- ✅ Fallback sans contexte si Weaviate >200ms

---

## Q6 : Mécanisme d'Interruption Utilisateur

### Scénario Cible

```
1. LLM parle (génère réponse longue)
2. User commence à parler (interruption)
3. → Système doit arrêter immédiatement
4. → Écouter nouvelle question
5. → Conserver contexte conversationnel
```

### Détection de l'Interruption

**Méthode 1 : VAD Côté Client (Recommandée)**

```typescript
// Frontend: useVoiceRealtime.ts
const vadInstance = new VoiceActivityDetector({
  threshold: 0.3,
  minSpeechDuration: 300  // 300ms pour confirmer
});

vadInstance.on('speechStart', () => {
  if (isSpeaking) {  // LLM en train de parler
    handleInterruption();
  }
});

async function handleInterruption() {
  console.log('🛑 User interruption detected');

  // 1. Arrêter lecture audio locale
  audioQueue.clear();
  audioContext.suspend();

  // 2. Notifier backend
  websocket.send({
    type: 'user.interrupt',
    timestamp: Date.now()
  });

  // 3. Préparer écoute nouvelle question
  setIsListening(true);
  setIsSpeaking(false);
}
```

**Méthode 2 : VAD Côté Serveur (OpenAI)**

OpenAI Realtime API détecte automatiquement parole pendant génération.

```python
# Backend: voice_realtime.py
async def on_openai_event(event):
    if event['type'] == 'input_audio_buffer.speech_started':
        # OpenAI a détecté parole user
        if currently_speaking:
            await handle_interruption()

async def handle_interruption():
    # 1. Annuler génération en cours
    await openai_session.send({
        'type': 'response.cancel'
    })

    # 2. Notifier frontend
    await websocket.send_json({
        'type': 'llm.interrupted',
        'timestamp': datetime.now().isoformat()
    })
```

---

### Gestion du Contexte Conversationnel

**Question** : Conserver ou réinitialiser contexte ?

**Option A : Conserver Contexte (Recommandée)**
```python
# Historique conversation conservé
conversation_history = [
    {"role": "user", "content": "Quelle température..."},
    {"role": "assistant", "content": "La température d'incub—"},  # Interrompu
    {"role": "user", "content": "Non attends, plutôt l'humidité ?"}
]
```

**Option B : Réinitialiser**
```python
# Supprimer réponse incomplète
conversation_history = [
    {"role": "user", "content": "Quelle température..."},
    # Réponse interrompue supprimée
    {"role": "user", "content": "Plutôt l'humidité ?"}
]
```

**Décision** : **Option A (Conserver)**
- ✅ Permet au LLM de comprendre correction ("non attends...")
- ✅ Contexte conversationnel plus naturel
- ⚠️ Risque confusion si réponse partielle incorrecte

---

### Gestion de la Queue Audio Frontend

```typescript
class AudioQueue {
  private queue: AudioBuffer[] = [];
  private playing: boolean = false;

  clear() {
    this.queue = [];
    this.playing = false;

    // Arrêter lecture en cours
    if (this.currentSource) {
      this.currentSource.stop();
      this.currentSource = null;
    }
  }

  async playNext() {
    if (!this.playing || this.queue.length === 0) return;

    const buffer = this.queue.shift();
    this.currentSource = this.audioContext.createBufferSource();
    this.currentSource.buffer = buffer;
    this.currentSource.connect(this.audioContext.destination);

    this.currentSource.onended = () => {
      this.playNext();  // Chaînage
    };

    this.currentSource.start();
  }
}
```

---

### 🎯 DÉCISION RECOMMANDÉE

**Stratégie d'interruption complète** :

1. **Détection** : VAD client + VAD serveur (double sécurité)
2. **Action immédiate** :
   - Frontend : Clear audio queue + suspend playback
   - Backend : `response.cancel` à OpenAI
3. **Contexte** : Conserver historique avec réponse partielle
4. **Transition** : `isSpeaking → isListening` instantané

**Feedback UX** :
- Animation bouton : Bleu (speaking) → Vert (listening) immédiat
- Feedback haptique mobile (vibration courte)
- Optionnel : Message toast "Vous m'avez interrompu, je vous écoute"

---

## Q7 : Format Audio et Compatibilité Mobile

### Format Audio Sélectionné

**Après test Q4**, choisir entre :

#### Option 1 : PCM16 Raw + Base64 JSON (Simple)

```json
{
  "type": "audio.input",
  "audio": "AAABAAACAAA...",  // Base64
  "format": "pcm16",
  "sample_rate": 16000
}
```

**Avantages** :
- ✅ Compatible tous navigateurs
- ✅ Debugging facile (JSON lisible)
- ✅ Pas de codec complexe

**Inconvénients** :
- ❌ Overhead +33% bande passante
- ❌ Encoding/decoding CPU

**Verdict** : ✅ **RECOMMANDÉ pour MVP**

---

#### Option 2 : WebSocket Binaire + Opus (Optimisé)

```javascript
// Frontend
const opusEncoder = new OpusEncoder({
  sampleRate: 16000,
  channels: 1,
  bitrate: 16000
});

const compressed = opusEncoder.encode(pcmData);
websocket.send(compressed);  // Binaire direct
```

**Avantages** :
- ✅ Économie bande passante (compression ~10x)
- ✅ Latence réduite (moins de data)

**Inconvénients** :
- ❌ Complexité (encoder/decoder)
- ❌ Compatibilité variable (iOS Safari)

**Verdict** : ⚠️ **Phase 2 si problème bande passante**

---

### Sample Rate

**Options** :
- 16kHz (économie)
- 44.1kHz (qualité)
- 48kHz (standard pro)

**Décision** : **16kHz**
- ✅ Suffisant pour voix humaine
- ✅ Économie bande passante 2.75x vs 44.1kHz
- ✅ Supporté par OpenAI Realtime API

---

### Compatibilité Mobile

#### iOS Safari

**Problèmes connus** :
1. **Autoplay policy** : Audio ne démarre pas sans interaction user
2. **AudioContext** : Doit être créé après user gesture
3. **Microphone** : Permission requise

**Solutions** :
```typescript
// Créer AudioContext après click user
button.addEventListener('click', async () => {
  // 1. Créer context (obligatoire sur iOS)
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  await audioContext.resume();  // IMPORTANT pour iOS

  // 2. Demander micro
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

  // 3. Démarrer WebSocket
  connectWebSocket();
});
```

**Gestion Bluetooth** :
```typescript
// Détecter changement sortie audio
navigator.mediaDevices.addEventListener('devicechange', () => {
  console.log('Audio device changed (Bluetooth ?)');
  // Reconnecter si nécessaire
});
```

---

#### Android Chrome

**Moins de problèmes qu'iOS** :
- ✅ AudioContext plus permissif
- ✅ Autoplay policy moins stricte

**Optimisations** :
```typescript
// Wake lock pour éviter sleep pendant conversation
const wakeLock = await navigator.wakeLock.request('screen');
```

---

### Feedback Haptique

```typescript
// Vibration à l'interruption
if ('vibrate' in navigator) {
  navigator.vibrate(50);  // 50ms
}

// Pattern pour début/fin conversation
navigator.vibrate([100, 50, 100]);  // Bip-bip
```

---

### 🎯 DÉCISION RECOMMANDÉE

**Configuration audio finale** :

```typescript
const AUDIO_CONFIG = {
  // Format
  format: 'pcm16',
  encoding: 'base64',  // JSON pour MVP

  // Sample rate
  sampleRate: 16000,
  channels: 1,

  // Buffering
  chunkDuration: 100,  // 100ms chunks
  bufferSize: 4096,

  // Mobile
  iosAutoplayFix: true,
  androidWakeLock: true,
  hapticFeedback: true,

  // Fallback
  codecFallback: ['pcm16', 'opus', 'aac']
};
```

**Tests requis** :
- [ ] iPhone 12+ Safari (iOS 16+)
- [ ] Android Chrome (Android 11+)
- [ ] Test avec AirPods (Bluetooth)
- [ ] Test avec connexion 4G lente

---

## 📊 Tableau Récapitulatif des Décisions

| Question | Décision | Justification | Complexité |
|----------|----------|---------------|------------|
| **Q5: Injection RAG** | Option B (pré-chargement) + fallback | Latence optimale ~500ms | ⚠️ Moyenne |
| **Q6: Interruption** | VAD client + serveur, contexte conservé | UX naturelle | ✅ Simple |
| **Q7: Format audio** | PCM16 16kHz Base64 JSON | Compatibilité maximale | ✅ Simple |

---

## 🚀 Prochaines Étapes

Après validation de ces décisions :

1. ✅ **Phase 1** : Backend WebSocket (2-3 jours)
   - Implémenter Option B injection RAG
   - Gérer interruption avec `response.cancel`
   - Format audio PCM16 Base64

2. ✅ **Phase 2** : Frontend (2-3 jours)
   - Hook `useVoiceRealtime` avec VAD
   - AudioQueue avec gestion interruption
   - Fixes iOS Safari

3. ✅ **Phase 3** : Tests Mobile (1 jour)
   - iPhone 12+ Safari
   - Android Chrome
   - Bluetooth audio

4. ✅ **Phase 4** : Optimisations (1 jour)
   - Si bande passante problème → Opus codec
   - Cache Weaviate questions fréquentes
   - Monitoring latence production

---

## ✅ Validation Finale

**Date** : __________

**Décisions validées** :
- [ ] Q5 : Option B pré-chargement RAG
- [ ] Q6 : Interruption VAD double + contexte conservé
- [ ] Q7 : PCM16 16kHz Base64 JSON

**Signature tech lead** : __________

**GO pour Phase 1 développement** : ☐ OUI  ☐ NON
