# Voice Realtime - Documentation Complète

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Fonctionnalités](#fonctionnalités)
4. [Contrôle d'accès](#contrôle-daccès)
5. [Détection de langue et vitesse](#détection-de-langue-et-vitesse)
6. [Composants](#composants)
7. [Configuration](#configuration)
8. [Utilisation](#utilisation)
9. [Dépannage](#dépannage)
10. [Historique des corrections](#historique-des-corrections)

---

## Vue d'ensemble

**Voice Realtime** est une fonctionnalité de conversation vocale en temps réel utilisant l'API OpenAI Realtime. Elle permet aux utilisateurs de parler directement avec l'assistant IA et de recevoir des réponses audio en temps réel.

### Caractéristiques principales

- 🎤 **Conversation vocale bidirectionnelle** en temps réel
- 🌍 **Support multilingue** (10 langues avec TTS)
- ⚡ **Accélération automatique** pour le chinois (15% plus rapide)
- 🔊 **Audio optimisé** sans clics ni coupures
- 🎯 **Accès contrôlé** (Super admins + plan Intelia)
- 📱 **Compatible mobile** avec bouton flottant

---

## Architecture

### Stack technique

```
User (Browser)
    ↓ WebSocket
Frontend (React + Next.js)
    ↓ WebSocket (/api/v1/ws/voice)
Backend (FastAPI)
    ↓ WebSocket
OpenAI Realtime API
```

### Flux de données

1. **Audio Input**: Microphone → PCM16 (24kHz) → Base64 → WebSocket → Backend → OpenAI
2. **Audio Output**: OpenAI → Base64 → WebSocket → Backend → Frontend → Web Audio API
3. **Transcription**: OpenAI transcrit automatiquement (Whisper)
4. **Langue**: Frontend détecte langue → Backend ajuste vitesse OpenAI

---

## Fonctionnalités

### 1. Conversation vocale

- **Capture audio**: AudioContext + ScriptProcessorNode
- **Format**: PCM16 mono 24kHz (format natif OpenAI)
- **Streaming**: Audio envoyé en temps réel (pas d'attente)
- **VAD (Voice Activity Detection)**: Détection automatique de la parole

### 2. Optimisations audio

#### Prévention des clics audio
- **Gain node avec fade in/out** (3ms)
- **Pre-buffering** (2 chunks avant de jouer)
- **Seamless scheduling** avec `nextPlayTimeRef`

```typescript
// Fade in (3ms)
gainNode.gain.setValueAtTime(0, startTime);
gainNode.gain.linearRampToValueAtTime(1, startTime + 0.003);

// Fade out (3ms)
gainNode.gain.setValueAtTime(1, endTime - 0.003);
gainNode.gain.linearRampToValueAtTime(0, endTime);
```

#### Prévention des overlaps
- **Flag isPlayingRef**: Empêche lecture simultanée
- **Queue système**: `audioQueueRef` pour gérer les chunks

### 3. Support multilingue

#### Langues supportées (avec TTS)
- 🇫🇷 Français
- 🇬🇧 Anglais
- 🇪🇸 Espagnol
- 🇵🇹 Portugais
- 🇩🇪 Allemand
- 🇮🇹 Italien
- 🇳🇱 Néerlandais
- 🇯🇵 Japonais
- 🇨🇳 Chinois
- 🇰🇷 Coréen

#### Langues supportées (sans TTS)
- 🇹🇭 Thaï (transcription uniquement)
- 🇮🇳 Hindi (transcription uniquement)

---

## Contrôle d'accès

### Qui peut accéder?

Voice Realtime est accessible à:
1. **Super admins** (`is_admin = true`)
2. **Utilisateurs avec plan Intelia** (`plan_name = 'intelia'`)

### Plan Intelia

Le plan Intelia est un plan spécial pour les employés:
- ✅ Gratuit
- ✅ Quota illimité (999,999 questions)
- ✅ Accès Voice Realtime
- ✅ Support prioritaire
- ❌ Non visible publiquement
- ❌ Non auto-assignable

### Attribution du plan Intelia

#### Via SQL (recommandé)

```sql
-- Pour un nouvel utilisateur
INSERT INTO user_billing_info (user_email, plan_name)
VALUES ('email@example.com', 'intelia');

-- Pour un utilisateur existant
UPDATE user_billing_info
SET plan_name = 'intelia'
WHERE user_email = 'email@example.com';
```

#### Vérifier l'accès

```sql
-- Voir tous les utilisateurs avec plan Intelia
SELECT u.email, u.full_name, ubi.plan_name, u.is_admin
FROM users u
LEFT JOIN user_billing_info ubi ON u.email = ubi.user_email
WHERE ubi.plan_name = 'intelia' OR u.is_admin = true;
```

### Implémentation du contrôle d'accès

#### Frontend (`useVoiceRealtime.ts`)

```typescript
const isSuperAdmin = user?.is_admin === true;
const hasInteliaPlan = user?.plan === "intelia";
const canUseVoiceRealtime = isSuperAdmin || hasInteliaPlan;

// Le bouton n'est affiché que si canUseVoiceRealtime = true
if (!canUseVoiceRealtime) {
  return null; // Pas de bouton
}
```

#### Backend (`/auth/me`)

Le plan est chargé depuis `user_billing_info` dans **tous les chemins de code**:
1. Chemin principal (Supabase profile)
2. Fallback (JWT uniquement)
3. Exception fallback

```python
# Récupération du plan dans tous les cas
user_plan = "essential"  # Default
try:
    with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT plan_name
                FROM user_billing_info
                WHERE user_email = %s
            """, (current_user.get("email"),))

            billing_row = cur.fetchone()
            if billing_row:
                user_plan = billing_row["plan_name"]
except Exception as e:
    logger.warning(f"Erreur récupération plan: {e}")

return {
    # ...
    "plan": user_plan,
    # ...
}
```

---

## Détection de langue et vitesse

### Problème initial

Le chinois parlé est souvent perçu comme "trop lent" par les locuteurs natifs. Solution: accélérer de 15%.

### Approche côté client (❌ ÉCHEC)

**Ce qui a été essayé:**
```typescript
// ❌ NE FONCTIONNE PAS
source.playbackRate.value = 1.15;
source.start(scheduledTime); // Le onended ne se déclenche jamais!
```

**Problème:**
- Combinaison de `playbackRate` + `start(scheduledTime)` casse le callback `onended`
- Les chunks audio ne s'enchaînent plus
- Silence complet après le premier chunk

### Solution côté serveur (✅ FONCTIONNE)

**Implémentation:**

1. **Frontend détecte la langue** (Unicode regex)
```typescript
function detectLanguage(text: string): string {
  if (/[\u4e00-\u9fff]/.test(text)) return "zh"; // Chinois
  if (/[\u3040-\u309f\u30a0-\u30ff]/.test(text)) return "ja"; // Japonais
  if (/[\uac00-\ud7af]/.test(text)) return "ko"; // Coréen
  return "en";
}
```

2. **Frontend envoie au backend**
```typescript
ws.send(JSON.stringify({
  type: "language.detected",
  language: "zh"
}));
```

3. **Backend reconfigure OpenAI**
```python
async def configure_openai_session(self, language: Optional[str] = None):
    speed = 1.15 if language == "zh" else 1.0

    config = {
        "type": "session.update",
        "session": {
            # ... autres configs ...
            "temperature": 0.8,
            "max_response_output_tokens": 4096
        }
    }

    # Ajouter speed seulement si différent de 1.0
    if speed != 1.0:
        config["session"]["speed"] = speed
        logger.info(f"⚡ Adjusting playback speed to {speed}x for language: {language}")

    await self.openai_ws.send(json.dumps(config))
```

**Avantages:**
- ✅ Le paramètre `speed` est natif dans l'API OpenAI
- ✅ Aucun problème avec `onended`
- ✅ Audio s'enchaîne parfaitement
- ✅ Configuration dynamique (change en temps réel)

### Flux complet

```
1. User parle en chinois
2. OpenAI transcrit → "你好"
3. Frontend détecte "zh"
4. Frontend envoie {"type": "language.detected", "language": "zh"}
5. Backend reçoit message
6. Backend appelle configure_openai_session(language="zh")
7. OpenAI configure session avec speed=1.15
8. Toutes les réponses suivantes sont 15% plus rapides
```

---

## Composants

### Frontend

#### 1. `useVoiceRealtime.ts` (Hook principal)

**Responsabilités:**
- Gestion WebSocket client ↔ backend
- Capture microphone (PCM16 24kHz)
- Playback audio avec Web Audio API
- Détection de langue
- Gestion états (idle/connecting/listening/speaking/error)

**États:**
```typescript
type VoiceRealtimeState = "idle" | "connecting" | "listening" | "speaking" | "error";
```

**API publique:**
```typescript
const {
  state,              // État actuel
  isConnected,        // WebSocket connecté?
  isListening,        // En écoute?
  isSpeaking,         // En train de parler?
  error,              // Erreur actuelle
  audioLevel,         // Niveau microphone (0-100)
  canUseVoiceRealtime, // Accès autorisé?
  startConversation,  // Démarrer
  stopConversation,   // Arrêter
  interrupt,          // Interrompre réponse
} = useVoiceRealtime();
```

#### 2. `VoiceRealtimeButton.tsx` (UI)

**Caractéristiques:**
- Bouton flottant en bas à droite
- Position fixe avec `z-index: 9999`
- Compatible notch iOS (`env(safe-area-inset-*)`)
- Résistant au zoom (`transform: translate3d(0,0,0)`)
- Animations (pulse pour listening, ping pour speaking)
- Indicateur volume audio
- Messages d'erreur contextuels

**États visuels:**
- **Idle**: Gris, icône MicOff
- **Connecting**: Jaune, spinner
- **Listening**: Vert avec pulse, icône Mic
- **Speaking**: Bleu avec animation, icône Volume2
- **Error**: Rouge, icône AlertCircle

### Backend

#### 1. `voice_realtime.py` (WebSocket endpoint)

**Endpoint:** `/api/v1/ws/voice`

**Classes principales:**
- `RateLimiter`: Limite 5 sessions/heure/user
- `WeaviateRAGService`: Pré-chargement contexte RAG
- `VoiceRealtimeSession`: Gestion session utilisateur

**Flux:**
```python
async def run(self):
    """Session lifecycle"""
    1. connect_openai()              # Connexion OpenAI
    2. configure_openai_session()    # Config initiale
    3. asyncio.gather(
         forward_client_to_openai(),  # Client → OpenAI
         forward_openai_to_client(),  # OpenAI → Client
         monitor_session_timeout()    # Timeout 10 min
       )
    4. cleanup()                     # Fermeture propre
```

**Messages WebSocket:**

| Type | Direction | Description |
|------|-----------|-------------|
| `auth` | Client → Backend | Authentification JWT |
| `audio.input` | Client → Backend | Chunk audio microphone |
| `language.detected` | Client → Backend | Langue détectée |
| `interrupt` | Client → Backend | Annuler réponse en cours |
| `response.audio.delta` | Backend → Client | Chunk audio réponse |
| `session.timeout` | Backend → Client | Session expirée |

#### 2. Configuration OpenAI

```python
config = {
    "type": "session.update",
    "session": {
        "modalities": ["text", "audio"],
        "instructions": "You are a poultry farming expert...",
        "voice": "alloy",
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_transcription": {
            "model": "whisper-1"
        },
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500
        },
        "temperature": 0.8,
        "max_response_output_tokens": 4096,
        "speed": 1.15  # Optionnel, pour chinois
    }
}
```

---

## Configuration

### Variables d'environnement

#### Backend (`.env`)

```bash
# Feature flag
ENABLE_VOICE_REALTIME=true

# OpenAI
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=postgresql://...

# Optional: Weaviate RAG
WEAVIATE_URL=https://...
WEAVIATE_API_KEY=...
```

#### Frontend (`.env.local`)

```bash
NEXT_PUBLIC_API_URL=https://expert.intelia.com
```

### Limites de sécurité

```python
# backend/app/api/v1/voice_realtime.py
MAX_SESSION_DURATION = 600  # 10 minutes max
MAX_SESSIONS_PER_USER_PER_HOUR = 5
RATE_LIMIT_WINDOW = 3600  # 1 heure
```

---

## Utilisation

### Pour les développeurs

#### Tester localement

1. **Backend:**
```bash
cd backend
export ENABLE_VOICE_REALTIME=true
export OPENAI_API_KEY=sk-...
uvicorn app.main:app --reload
```

2. **Frontend:**
```bash
cd frontend
npm run dev
```

3. **Donner accès Intelia à votre compte test:**
```sql
UPDATE user_billing_info
SET plan_name = 'intelia'
WHERE user_email = 'votre.email@test.com';
```

4. **Ouvrir:** http://localhost:3000/chat
5. **Cliquer** sur le bouton microphone en bas à droite

#### Debug

**Frontend (console navigateur):**
```
🔌 [Voice Realtime] Connecting to WebSocket
✅ WebSocket connected
🎤 Microphone started
📝 Transcription: "Bonjour"
🌍 Detected language: fr
🔊 Received audio chunk
```

**Backend (logs):**
```
🔌 Connecting to OpenAI Realtime API
✅ OpenAI connected in 234.56ms
⚙️ OpenAI session configured
🌍 Language detected: zh
⚡ Adjusting playback speed to 1.15x for language: zh
```

### Pour les utilisateurs finaux

1. **Se connecter** avec compte ayant plan Intelia ou admin
2. **Autoriser microphone** (popup navigateur)
3. **Cliquer** sur bouton flottant en bas à droite
4. **Parler** naturellement dans votre langue
5. **Écouter** la réponse audio
6. **Double-cliquer** pour interrompre si nécessaire

---

## Dépannage

### Problème: Bouton Voice Realtime invisible

**Symptôme:** Utilisateur avec plan Intelia ne voit pas le bouton

**Causes possibles:**

1. **Plan non chargé correctement**
   - Vérifier `/auth/me` retourne `"plan": "intelia"`
   - Logs backend: `[/auth/me] ✅ Main path - Returning for ... with plan=intelia`

2. **Cache navigateur**
   - Déconnexion/reconnexion
   - Vider cache (Ctrl+Shift+Del)
   - Mode incognito pour tester

3. **Backend non redémarré**
   - Après modification de `auth.py`, redémarrer backend

**Solution:**
```sql
-- Vérifier le plan dans la DB
SELECT u.email, u.full_name, ubi.plan_name, u.is_admin
FROM users u
LEFT JOIN user_billing_info ubi ON u.email = ubi.user_email
WHERE u.email = 'utilisateur@email.com';

-- Si plan incorrect, corriger:
UPDATE user_billing_info
SET plan_name = 'intelia'
WHERE user_email = 'utilisateur@email.com';
```

### Problème: Audio avec clics

**Symptôme:** Sons de "clic" entre les chunks audio

**Solution:** Déjà implémentée (gain node avec fades)

**Si le problème persiste:**
- Vérifier que `isBufferingRef` fonctionne (pre-buffer 2 chunks)
- Vérifier logs: `🔊 Buffering... waiting for more chunks`

### Problème: Audio ne s'enchaîne pas

**Symptôme:** Silence après le premier chunk

**Causes:**
1. `onended` ne se déclenche pas
2. `isPlayingRef` bloqué à `true`

**Debug:**
```typescript
source.onended = () => {
  console.log("🔊 Audio chunk finished playing"); // Ce log apparaît?
  isPlayingRef.current = false;
  // ...
};
```

### Problème: Accélération chinoise ne fonctionne pas

**Symptôme:** Audio chinois à vitesse normale

**Debug:**

1. **Vérifier détection langue (frontend):**
```
Console: 🌍 Detected language: zh
```

2. **Vérifier envoi au backend:**
```
Console: Sent language.detected message
```

3. **Vérifier backend logs:**
```
Backend: 🌍 Language detected: zh
Backend: ⚡ Adjusting playback speed to 1.15x for language: zh
```

4. **Tester avec texte chinois simple:**
   - Parler: "你好" (nǐ hǎo)
   - Vérifier que regex détecte bien: `/[\u4e00-\u9fff]/.test("你好")` = true

### Problème: Microphone non accessible

**Symptôme:** Erreur "Microphone access denied"

**Solutions:**
1. **Vérifier permissions navigateur** (icône cadenas dans URL)
2. **HTTPS requis** (localhost OK en développement)
3. **Navigateur compatible** (Chrome, Firefox, Safari modernes)

---

## Historique des corrections

### 1. Overlapping audio (Voices multiples)

**Date:** Session 1
**Problème:** Plusieurs voix parlaient simultanément
**Cause:** `playAudioQueue()` appelé en parallèle
**Solution:** Flag `isPlayingRef` pour empêcher appels concurrents

```typescript
const isPlayingRef = useRef(false);

const playAudioQueue = async () => {
  if (isPlayingRef.current) return;
  isPlayingRef.current = true;
  // ... play audio ...
  source.onended = () => {
    isPlayingRef.current = false;
    playAudioQueue(); // Next chunk
  };
};
```

### 2. Clics audio ("griche")

**Date:** Session 1
**Problème:** Sons de clic entre chunks audio
**Cause:** Transitions abruptes entre chunks
**Solution:** Gain node avec fade in/out + pre-buffering

```typescript
// Fade in/out (3ms)
gainNode.gain.setValueAtTime(0, startTime);
gainNode.gain.linearRampToValueAtTime(1, startTime + 0.003);
gainNode.gain.setValueAtTime(1, endTime - 0.003);
gainNode.gain.linearRampToValueAtTime(0, endTime);

// Pre-buffering
if (isBufferingRef.current && audioQueueRef.current.length < 2) {
  return; // Attendre plus de chunks
}
```

### 3. Plan Intelia non accessible

**Date:** Session 1
**Problème:** Utilisateurs avec plan "intelia" ne voyaient pas le bouton
**Cause:** `/auth/me` ne chargeait le plan que dans le chemin principal (pas les fallbacks)
**Solution:** Ajouter récupération du plan dans tous les chemins

```python
# Ajouté dans fallback ET exception handler
user_plan = "essential"
try:
    with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT plan_name FROM user_billing_info
                WHERE user_email = %s
            """, (current_user.get("email"),))
            billing_row = cur.fetchone()
            if billing_row:
                user_plan = billing_row["plan_name"]
except Exception as e:
    logger.warning(f"Erreur récupération plan: {e}")
```

### 4. Accélération chinoise cassait l'audio

**Date:** Session 2
**Problème:** Après implémentation `playbackRate=1.15`, silence total
**Cause:** `source.start(scheduledTime)` + `playbackRate` casse `onended`
**Solution:** Déplacer l'accélération côté serveur (paramètre `speed` OpenAI)

```python
# Backend - server-side speed adjustment
speed = 1.15 if language == "zh" else 1.0
config["session"]["speed"] = speed
```

### 5. Bouton disparaît lors du zoom

**Date:** Session 2
**Problème:** Bouton Voice Realtime disparaît quand user zoom
**Cause:** Position `fixed` sans optimisation pour zoom
**Solution:** Styles inline avec `transform: translate3d`

```typescript
style={{
  position: 'fixed',
  bottom: 'max(1.5rem, env(safe-area-inset-bottom, 1.5rem))',
  right: 'max(1.5rem, env(safe-area-inset-right, 1.5rem))',
  zIndex: 9999,
  transform: 'translate3d(0, 0, 0)',
  willChange: 'transform',
}}
```

---

## Améliorations futures

### Court terme
- [ ] Ajouter indicateur de connexion réseau
- [ ] Timeout configurable par plan
- [ ] Statistiques d'utilisation par utilisateur
- [ ] Support d'autres voix OpenAI (alloy, echo, fable, onyx, nova, shimmer)

### Moyen terme
- [ ] Mode "push-to-talk" en option
- [ ] Historique des conversations vocales
- [ ] Export audio des conversations
- [ ] Support TTS pour Thai et Hindi (quand disponible chez OpenAI)

### Long terme
- [ ] Mode hors ligne (avec models locaux)
- [ ] Personnalisation de la voix
- [ ] Support vidéo en temps réel
- [ ] Traduction simultanée

---

## Ressources

### Documentation officielle
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

### Code source
- Frontend: `frontend/lib/hooks/useVoiceRealtime.ts`
- Frontend UI: `frontend/components/VoiceRealtimeButton.tsx`
- Backend: `backend/app/api/v1/voice_realtime.py`
- Auth: `backend/app/api/v1/auth.py` (endpoint `/auth/me`)

### Tests
- Plan Intelia: `backend/sql/stripe/29_add_intelia_plan.sql`
- Billing: `backend/app/api/v1/billing.py`

---

**Dernière mise à jour:** 2025-10-22
**Version:** 1.0
**Statut:** ✅ Production
