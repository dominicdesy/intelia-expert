"""
POC - Test OpenAI Realtime API
===============================

Tests à réaliser:
1. Connexion à l'API Realtime
2. Mesure de latence (streaming audio)
3. Test VAD (Voice Activity Detection) en français
4. Test interruption de génération

Requirements:
    pip install openai websockets asyncio
"""

import asyncio
import json
import time
import os
from datetime import datetime
import websockets
from dotenv import load_dotenv

# Charger .env depuis llm/
env_path = os.path.join(os.path.dirname(__file__), '..', 'llm', '.env')
load_dotenv(env_path)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable must be set")


class RealtimeAPITester:
    """Testeur pour OpenAI Realtime API"""

    def __init__(self):
        self.ws = None
        self.metrics = {
            "connection_time": 0,
            "first_audio_chunk_time": 0,
            "vad_detection_time": 0,
            "total_audio_chunks": 0,
            "errors": []
        }
        self.start_time = None
        self.first_chunk_received = False

    async def connect(self):
        """Établir connexion WebSocket avec OpenAI Realtime API"""
        print("🔌 Connexion à OpenAI Realtime API...")
        start = time.time()

        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

        try:
            # Créer une connexion WebSocket avec headers personnalisés
            self.ws = await websockets.connect(
                url,
                additional_headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "OpenAI-Beta": "realtime=v1"
                }
            )
            self.metrics["connection_time"] = (time.time() - start) * 1000
            print(f"✅ Connecté en {self.metrics['connection_time']:.2f}ms")
            return True
        except Exception as e:
            self.metrics["errors"].append(f"Connection failed: {str(e)}")
            print(f"❌ Erreur de connexion: {e}")
            return False

    async def configure_session(self):
        """Configurer session avec instructions en français"""
        print("\n⚙️ Configuration de la session...")

        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": (
                    "Tu es un expert en aviculture. "
                    "Réponds en français de manière concise et naturelle. "
                    "Si tu reçois du contexte supplémentaire, base ta réponse dessus."
                ),
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
            }
        }

        await self.ws.send(json.dumps(config))
        print("✅ Configuration envoyée")

    async def send_text_message(self, text: str):
        """Envoyer message texte (simule question vocale pour test simple)"""
        print(f"\n💬 Envoi question: '{text}'")
        self.start_time = time.time()
        self.first_chunk_received = False

        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        }

        await self.ws.send(json.dumps(message))

        # Trigger response
        response_trigger = {"type": "response.create"}
        await self.ws.send(json.dumps(response_trigger))
        print("✅ Requête envoyée, attente réponse...")

    async def listen_for_response(self, timeout: int = 10):
        """Écouter la réponse et mesurer métriques"""
        print("\n👂 Écoute des événements...")

        try:
            async with asyncio.timeout(timeout):
                async for message in self.ws:
                    data = json.loads(message)
                    event_type = data.get("type")

                    # Log tous les événements
                    if event_type:
                        print(f"  📡 Event: {event_type}")

                    # Mesure temps premier chunk audio
                    if event_type == "response.audio.delta" and not self.first_chunk_received:
                        self.metrics["first_audio_chunk_time"] = (time.time() - self.start_time) * 1000
                        self.first_chunk_received = True
                        print(f"  🎵 Premier chunk audio reçu en {self.metrics['first_audio_chunk_time']:.2f}ms")

                    # Compte chunks audio
                    if event_type == "response.audio.delta":
                        self.metrics["total_audio_chunks"] += 1

                    # Détection VAD
                    if event_type == "input_audio_buffer.speech_started":
                        print("  🎤 VAD: Début de parole détecté")

                    if event_type == "input_audio_buffer.speech_stopped":
                        vad_time = (time.time() - self.start_time) * 1000
                        self.metrics["vad_detection_time"] = vad_time
                        print(f"  🎤 VAD: Fin de parole détectée en {vad_time:.2f}ms")

                    # Fin de réponse
                    if event_type == "response.done":
                        print("  ✅ Réponse complète")
                        break

                    # Erreurs
                    if event_type == "error":
                        error_msg = data.get("error", {}).get("message", "Unknown error")
                        self.metrics["errors"].append(error_msg)
                        print(f"  ❌ Erreur: {error_msg}")

        except asyncio.TimeoutError:
            print(f"  ⏱️ Timeout après {timeout}s")
            self.metrics["errors"].append(f"Timeout after {timeout}s")

    async def test_interruption(self):
        """Tester capacité d'interruption"""
        print("\n🛑 Test interruption...")

        # Envoyer une longue question pour avoir temps d'interrompre
        await self.send_text_message(
            "Explique-moi en détail tout le processus d'incubation des œufs de poule "
            "depuis la collecte jusqu'à l'éclosion, avec tous les paramètres techniques."
        )

        # Attendre 2 secondes puis interrompre
        await asyncio.sleep(2)
        print("  ⏸️ Interruption de la génération...")

        cancel_msg = {
            "type": "response.cancel"
        }
        await self.ws.send(json.dumps(cancel_msg))
        print("  ✅ Commande d'interruption envoyée")

        # Attendre confirmation
        await asyncio.sleep(1)

    async def close(self):
        """Fermer connexion"""
        if self.ws:
            await self.ws.close()
            print("\n🔌 Connexion fermée")

    def print_metrics(self):
        """Afficher rapport de métriques"""
        print("\n" + "="*60)
        print("📊 RAPPORT DE TEST - OpenAI Realtime API")
        print("="*60)

        print(f"\n⏱️  LATENCE:")
        print(f"  - Connexion WebSocket: {self.metrics['connection_time']:.2f}ms")
        print(f"  - Premier chunk audio: {self.metrics['first_audio_chunk_time']:.2f}ms")
        if self.metrics['vad_detection_time']:
            print(f"  - Détection VAD: {self.metrics['vad_detection_time']:.2f}ms")

        print(f"\n📦 STREAMING:")
        print(f"  - Total chunks audio: {self.metrics['total_audio_chunks']}")

        if self.metrics['errors']:
            print(f"\n❌ ERREURS:")
            for error in self.metrics['errors']:
                print(f"  - {error}")
        else:
            print(f"\n✅ Aucune erreur")

        # Évaluation
        print(f"\n🎯 ÉVALUATION:")

        latency = self.metrics['first_audio_chunk_time']
        if latency > 0:
            if latency < 500:
                print(f"  ✅ Latence EXCELLENTE ({latency:.0f}ms < 500ms)")
            elif latency < 1000:
                print(f"  ⚠️  Latence ACCEPTABLE ({latency:.0f}ms < 1s)")
            else:
                print(f"  ❌ Latence TROP ÉLEVÉE ({latency:.0f}ms > 1s)")

        if self.metrics['total_audio_chunks'] > 0:
            print(f"  ✅ Streaming audio fonctionnel")

        print("\n" + "="*60)


async def main():
    """Exécution des tests"""
    tester = RealtimeAPITester()

    try:
        # Test 1: Connexion
        if not await tester.connect():
            return

        # Test 2: Configuration
        await tester.configure_session()
        await asyncio.sleep(1)  # Attendre confirmation config

        # Test 3: Question simple en français
        print("\n" + "="*60)
        print("TEST 1: Question simple en français")
        print("="*60)
        await tester.send_text_message("Quelle est la température d'incubation des œufs de poule ?")
        await tester.listen_for_response()

        # Test 4: Interruption
        print("\n" + "="*60)
        print("TEST 2: Capacité d'interruption")
        print("="*60)
        await tester.test_interruption()

    except Exception as e:
        print(f"\n💥 Erreur inattendue: {e}")
        tester.metrics["errors"].append(str(e))

    finally:
        await tester.close()
        tester.print_metrics()


if __name__ == "__main__":
    print(f"\n🚀 Démarrage POC OpenAI Realtime API")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    asyncio.run(main())
