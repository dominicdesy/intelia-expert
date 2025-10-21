"""
POC - Backend WebSocket Minimal pour Test Audio
================================================

Backend FastAPI minimal pour tester architecture WebSocket.
IMPORTANT: Ce n'est PAS le backend final, juste un POC pour Q4.

Usage:
    uvicorn backend_websocket_minimal:app --reload --port 8000
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import base64
from datetime import datetime
from typing import Dict, List

app = FastAPI(title="POC WebSocket Audio")

# CORS pour dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gérer connexions actives
active_connections: List[WebSocket] = []


class AudioStreamManager:
    """Gestionnaire de streaming audio (POC simplifié)"""

    def __init__(self):
        self.audio_buffer = []
        self.processing = False

    async def process_audio_chunk(self, audio_data: bytes) -> bytes:
        """
        Simule traitement audio:
        1. Dans vrai système: Forward à OpenAI Realtime
        2. OpenAI retourne audio chunks
        3. On retourne au client

        Pour POC: on retourne l'audio tel quel (echo)
        """
        # Simuler latence processing (OpenAI)
        await asyncio.sleep(0.1)

        # Dans vrai système: audio_response = await openai_realtime_session.get_response()
        # Pour POC: echo
        return audio_data


stream_manager = AudioStreamManager()


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "POC WebSocket Audio",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket pour streaming audio bidirectionnel

    Messages attendus du client:
    - {"type": "audio.input", "audio": "base64...", "format": "pcm16"}
    - {"type": "ping", "timestamp": 123456}

    Messages envoyés au client:
    - {"type": "audio.output", "audio": "base64..."}
    - {"type": "connection.ready"}
    - {"type": "error", "message": "..."}
    """
    await websocket.accept()
    active_connections.append(websocket)

    print(f"✅ Client connecté: {websocket.client}")

    # Confirmer connexion
    await websocket.send_json({
        "type": "connection.ready",
        "timestamp": datetime.now().isoformat()
    })

    try:
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
                msg_type = data.get("type")

                # Ping-pong (test latence)
                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat(),
                        "client_timestamp": data.get("timestamp")
                    })
                    continue

                # Audio input
                if msg_type == "audio.input":
                    audio_b64 = data.get("audio")
                    if not audio_b64:
                        continue

                    # Décoder audio
                    audio_bytes = base64.b64decode(audio_b64)

                    print(f"  📥 Reçu audio: {len(audio_bytes)} bytes")

                    # Traiter (dans vrai système: forward à OpenAI)
                    processed_audio = await stream_manager.process_audio_chunk(audio_bytes)

                    # Retourner audio (simuler réponse OpenAI)
                    response_b64 = base64.b64encode(processed_audio).decode('utf-8')

                    await websocket.send_json({
                        "type": "audio.output",
                        "audio": response_b64,
                        "format": "pcm16",
                        "sample_rate": 16000
                    })

                    print(f"  📤 Envoyé audio: {len(processed_audio)} bytes")

                # Autre type de message
                else:
                    print(f"  ⚠️  Type message inconnu: {msg_type}")

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
            except Exception as e:
                print(f"  ❌ Erreur traitement: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        print(f"🔌 Client déconnecté: {websocket.client}")
    except Exception as e:
        print(f"💥 Erreur WebSocket: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.get("/stats")
async def get_stats():
    """Stats connexions actives"""
    return {
        "active_connections": len(active_connections),
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Démarrage backend WebSocket POC")
    print("📡 Endpoint: ws://localhost:8000/ws/voice\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
