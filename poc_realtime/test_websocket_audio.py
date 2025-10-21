"""
POC - Test Architecture WebSocket Bidirectionnel pour Audio
=============================================================

Tests à réaliser:
1. WebSocket FastAPI backend
2. WebSocket client (simuler frontend)
3. Routing audio bidirectionnel
4. Format audio (Base64 vs Binary)
5. Gestion buffering et latence réseau

Stack:
    Backend: FastAPI WebSocket
    Client: websockets library (simule browser)
    Audio: PCM16 raw audio data
"""

import asyncio
import json
import time
import base64
from datetime import datetime
from typing import Optional
import websockets

# Simuler audio data (PCM16)
def generate_fake_audio_chunk(duration_ms: int = 100) -> bytes:
    """Génère fake audio PCM16 pour test"""
    # PCM16 = 2 bytes par sample, 16kHz sample rate
    num_samples = int(16000 * duration_ms / 1000)  # 16kHz
    # Simuler silence (zeros)
    return bytes([0] * num_samples * 2)


class WebSocketAudioTester:
    """Testeur WebSocket pour streaming audio bidirectionnel"""

    def __init__(self, backend_url: str = "ws://localhost:8000/ws/voice"):
        self.backend_url = backend_url
        self.ws = None
        self.metrics = {
            "connection_time": 0,
            "chunks_sent": 0,
            "chunks_received": 0,
            "total_latency": [],
            "errors": []
        }
        self.audio_queue = []
        self.running = False

    async def connect(self) -> bool:
        """Connexion au backend WebSocket"""
        print(f"🔌 Connexion à {self.backend_url}...")
        start = time.time()

        try:
            # Note: En production, ajouter JWT token dans headers
            self.ws = await websockets.connect(self.backend_url)
            self.metrics["connection_time"] = (time.time() - start) * 1000
            print(f"✅ Connecté en {self.metrics['connection_time']:.2f}ms")
            self.running = True
            return True
        except ConnectionRefusedError:
            print(f"❌ Backend non disponible sur {self.backend_url}")
            print(f"💡 Démarrer backend: uvicorn backend.app.main:app --reload")
            self.metrics["errors"].append("Backend not running")
            return False
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            self.metrics["errors"].append(f"Connection: {str(e)}")
            return False

    async def send_audio_chunk(self, audio_data: bytes, format: str = "base64"):
        """Envoyer chunk audio au backend"""
        if format == "base64":
            # Format JSON avec base64
            payload = {
                "type": "audio.input",
                "audio": base64.b64encode(audio_data).decode('utf-8'),
                "format": "pcm16",
                "sample_rate": 16000
            }
            await self.ws.send(json.dumps(payload))
        else:
            # Format binaire pur (plus efficace)
            await self.ws.send(audio_data)

        self.metrics["chunks_sent"] += 1

    async def receive_audio_chunks(self):
        """Recevoir chunks audio du backend (streaming réponse)"""
        try:
            async for message in self.ws:
                # Mesurer latency
                receive_time = time.time()

                if isinstance(message, str):
                    # Message JSON
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "audio.output":
                        # Chunk audio reçu
                        audio_b64 = data.get("audio")
                        audio_data = base64.b64decode(audio_b64)
                        self.audio_queue.append(audio_data)
                        self.metrics["chunks_received"] += 1

                        print(f"  🎵 Chunk audio reçu: {len(audio_data)} bytes")

                    elif msg_type == "error":
                        error_msg = data.get("message", "Unknown")
                        print(f"  ❌ Erreur backend: {error_msg}")
                        self.metrics["errors"].append(error_msg)

                    elif msg_type == "connection.ready":
                        print(f"  ✅ Backend prêt")

                else:
                    # Message binaire
                    self.audio_queue.append(message)
                    self.metrics["chunks_received"] += 1

                if not self.running:
                    break

        except websockets.exceptions.ConnectionClosed:
            print("  🔌 Connexion fermée par backend")

    async def test_bidirectional_streaming(self, duration_seconds: int = 5):
        """Test streaming bidirectionnel"""
        print(f"\n🔄 Test streaming bidirectionnel ({duration_seconds}s)...\n")

        # Task pour recevoir audio
        receive_task = asyncio.create_task(self.receive_audio_chunks())

        # Simuler envoi audio chunks (100ms chunks)
        num_chunks = int(duration_seconds * 10)  # 10 chunks/sec

        for i in range(num_chunks):
            audio_chunk = generate_fake_audio_chunk(100)  # 100ms
            await self.send_audio_chunk(audio_chunk)

            print(f"  📤 Envoyé chunk {i+1}/{num_chunks} ({len(audio_chunk)} bytes)")

            # Attendre 100ms (simule temps réel)
            await asyncio.sleep(0.1)

        # Attendre derniers chunks
        print("\n  ⏳ Attente derniers chunks audio...")
        await asyncio.sleep(2)

        # Arrêter réception
        self.running = False
        receive_task.cancel()

        try:
            await receive_task
        except asyncio.CancelledError:
            pass

    async def test_network_latency(self):
        """Test latence réseau (RTT)"""
        print(f"\n📡 Test latence réseau (ping-pong)...\n")

        latencies = []
        for i in range(10):
            start = time.time()

            # Envoyer ping
            ping = {"type": "ping", "timestamp": start}
            await self.ws.send(json.dumps(ping))

            # Attendre pong
            response = await self.ws.recv()
            rtt = (time.time() - start) * 1000

            latencies.append(rtt)
            print(f"  Ping {i+1}/10: {rtt:.2f}ms")

        avg_latency = sum(latencies) / len(latencies)
        self.metrics["network_rtt"] = avg_latency
        print(f"\n  📊 RTT moyen: {avg_latency:.2f}ms")

    async def test_format_comparison(self):
        """Comparer format Base64 vs Binaire"""
        print(f"\n⚖️  Comparaison formats audio...\n")

        audio_chunk = generate_fake_audio_chunk(100)

        # Test Base64
        start = time.time()
        b64_data = base64.b64encode(audio_chunk).decode('utf-8')
        payload_json = json.dumps({"type": "audio", "data": b64_data})
        base64_time = (time.time() - start) * 1000
        base64_size = len(payload_json.encode('utf-8'))

        # Test Binaire
        start = time.time()
        binary_data = audio_chunk
        binary_time = (time.time() - start) * 1000
        binary_size = len(binary_data)

        print(f"  Base64 JSON:")
        print(f"    - Taille: {base64_size} bytes")
        print(f"    - Temps encode: {base64_time:.4f}ms")
        print(f"    - Overhead: {(base64_size / binary_size - 1) * 100:.1f}%")

        print(f"\n  Binaire:")
        print(f"    - Taille: {binary_size} bytes")
        print(f"    - Temps: {binary_time:.4f}ms")

        print(f"\n  💡 Recommandation:")
        if base64_size < binary_size * 1.5:
            print(f"    ✅ Base64 acceptable (overhead <50%)")
        else:
            print(f"    ⚠️  Binaire recommandé (économie bande passante)")

    async def close(self):
        """Fermer connexion"""
        self.running = False
        if self.ws:
            await self.ws.close()
            print("\n🔌 Connexion fermée")

    def print_report(self):
        """Rapport final"""
        print("\n" + "="*60)
        print("📊 RAPPORT DE TEST - WebSocket Audio Streaming")
        print("="*60)

        print(f"\n📡 CONNEXION:")
        print(f"  - Temps connexion: {self.metrics['connection_time']:.2f}ms")
        if "network_rtt" in self.metrics:
            print(f"  - RTT moyen: {self.metrics['network_rtt']:.2f}ms")

        print(f"\n📦 STREAMING:")
        print(f"  - Chunks envoyés: {self.metrics['chunks_sent']}")
        print(f"  - Chunks reçus: {self.metrics['chunks_received']}")

        if self.audio_queue:
            total_audio = sum(len(chunk) for chunk in self.audio_queue)
            print(f"  - Total audio reçu: {total_audio / 1024:.2f} KB")

        print(f"\n🎯 ÉVALUATION:")
        if self.metrics["chunks_sent"] > 0:
            if self.metrics["chunks_received"] > 0:
                print(f"  ✅ Streaming bidirectionnel fonctionnel")
            else:
                print(f"  ❌ Aucun audio reçu (problème backend)")
        else:
            print(f"  ⚠️  Aucun chunk envoyé")

        if self.metrics["errors"]:
            print(f"\n❌ ERREURS:")
            for error in self.metrics["errors"]:
                print(f"  - {error}")

        print("\n" + "="*60)


async def test_without_backend():
    """Tests sans backend (format, encoding, etc.)"""
    print("\n" + "="*60)
    print("TEST STANDALONE: Format Audio")
    print("="*60)

    tester = WebSocketAudioTester()
    await tester.test_format_comparison()


async def test_with_backend():
    """Tests avec backend running"""
    print("\n" + "="*60)
    print("TEST AVEC BACKEND")
    print("="*60)

    tester = WebSocketAudioTester()

    try:
        if not await tester.connect():
            return

        # Test ping-pong
        await tester.test_network_latency()

        # Test streaming
        await tester.test_bidirectional_streaming(duration_seconds=3)

        tester.print_report()

    except Exception as e:
        print(f"💥 Erreur: {e}")
        tester.metrics["errors"].append(str(e))

    finally:
        await tester.close()


async def main():
    """Exécution des tests"""

    # Tests standalone (sans backend)
    await test_without_backend()

    # Tests avec backend
    print("\n" + "="*60)
    print("Tentative connexion backend...")
    print("="*60)
    await test_with_backend()


if __name__ == "__main__":
    print(f"\n🚀 Démarrage POC WebSocket Audio Streaming")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    asyncio.run(main())
