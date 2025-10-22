/**
 * useVoiceRealtime Hook
 * =====================
 *
 * Hook React pour conversation vocale en temps réel avec WebSocket
 *
 * Features:
 * - Connexion WebSocket au backend
 * - Capture audio microphone
 * - Streaming bidirectionnel
 * - Gestion états (idle/listening/speaking)
 * - Auto-reconnexion
 * - Gestion erreurs
 *
 * Sécurité:
 * - Requiert authentification JWT
 * - Réservé super admin (is_admin = true)
 */

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useAuthStore } from "./useAuthStore";

// ============================================================
// TYPES
// ============================================================

export type VoiceRealtimeState = "idle" | "connecting" | "listening" | "speaking" | "error";

export interface VoiceRealtimeConfig {
  backendUrl?: string;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  audioFormat?: "pcm16";
  sampleRate?: number;
}

export interface VoiceRealtimeError {
  type: "microphone" | "websocket" | "auth" | "network" | "unknown";
  message: string;
  code?: string;
}

// ============================================================
// CONSTANTES
// ============================================================

const DEFAULT_CONFIG: VoiceRealtimeConfig = {
  backendUrl: process.env.NEXT_PUBLIC_API_URL || "https://expert.intelia.com",
  autoReconnect: true,
  maxReconnectAttempts: 3,
  audioFormat: "pcm16",
  sampleRate: 16000,
};

// ============================================================
// HOOK
// ============================================================

export function useVoiceRealtime(config: VoiceRealtimeConfig = {}) {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };

  // Auth
  const { user, isAuthenticated, getAuthToken } = useAuthStore();

  // États
  const [state, setState] = useState<VoiceRealtimeState>("idle");
  const [error, setError] = useState<VoiceRealtimeError | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0); // Volume microphone 0-100

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const reconnectAttemptsRef = useRef(0);

  // ============================================================
  // VÉRIFICATION ADMIN
  // ============================================================

  const isSuperAdmin = user?.is_admin === true;

  // ============================================================
  // WEBSOCKET
  // ============================================================

  const connectWebSocket = useCallback(async () => {
    if (!isAuthenticated || !isSuperAdmin) {
      setError({
        type: "auth",
        message: "Super admin access required",
      });
      return false;
    }

    setState("connecting");
    setError(null);

    try {
      // Obtenir JWT token
      const token = await getAuthToken();
      if (!token) {
        throw new Error("No auth token available");
      }

      // WebSocket URL
      const wsUrl = `${finalConfig.backendUrl?.replace("https://", "wss://").replace("http://", "ws://")}/api/v1/ws/voice`;

      console.log("🔌 [Voice Realtime] Connecting to WebSocket:", wsUrl);

      // Connexion WebSocket
      const ws = new WebSocket(wsUrl);

      // Event: Open
      ws.onopen = () => {
        console.log("✅ WebSocket connected");
        setIsConnected(true);
        setState("idle");
        reconnectAttemptsRef.current = 0;

        // Envoyer token d'authentification
        ws.send(
          JSON.stringify({
            type: "auth",
            token: token,
          })
        );
      };

      // Event: Message
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (err) {
          console.error("❌ Invalid WebSocket message:", err);
        }
      };

      // Event: Error
      ws.onerror = (err) => {
        console.error("❌ WebSocket error:", err);
        setError({
          type: "websocket",
          message: "WebSocket connection error",
        });
      };

      // Event: Close
      ws.onclose = () => {
        console.log("🔌 WebSocket closed");
        setIsConnected(false);
        setState("idle");

        // Auto-reconnect
        if (
          finalConfig.autoReconnect &&
          reconnectAttemptsRef.current < finalConfig.maxReconnectAttempts!
        ) {
          reconnectAttemptsRef.current++;
          console.log(`🔄 Reconnecting... (${reconnectAttemptsRef.current}/${finalConfig.maxReconnectAttempts})`);
          setTimeout(() => connectWebSocket(), 2000);
        }
      };

      wsRef.current = ws;
      return true;
    } catch (err: any) {
      console.error("❌ WebSocket connection failed:", err);
      setError({
        type: "websocket",
        message: err.message || "Failed to connect",
      });
      setState("error");
      return false;
    }
  }, [isAuthenticated, isSuperAdmin, getAuthToken, finalConfig]);

  // ============================================================
  // WEBSOCKET MESSAGE HANDLER
  // ============================================================

  const handleWebSocketMessage = useCallback((data: any) => {
    const { type } = data;

    switch (type) {
      case "audio.output":
        // Chunk audio reçu du backend
        handleAudioOutput(data.audio);
        if (state !== "speaking") {
          setState("speaking");
        }
        break;

      case "session.created":
        console.log("✅ OpenAI session created:", data.session?.id);
        break;

      case "session.updated":
        console.log("✅ OpenAI session updated");
        break;

      case "session.timeout":
        setError({
          type: "network",
          message: data.message || "Session timeout",
        });
        disconnect();
        break;

      case "error":
        console.error("❌ Server error received:", data);
        setError({
          type: "unknown",
          message: data.message || data.error || "Server error",
        });
        break;

      case "connection.ready":
        console.log("✅ Backend ready");
        break;

      default:
        console.log("📨 Unknown message type:", type);
    }
  }, [state]);

  // ============================================================
  // AUDIO OUTPUT (Backend → Speakers)
  // ============================================================

  const handleAudioOutput = useCallback(async (base64Audio: string) => {
    try {
      // Décoder Base64
      const audioData = atob(base64Audio);
      const arrayBuffer = new Uint8Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        arrayBuffer[i] = audioData.charCodeAt(i);
      }

      // Ajouter à queue
      audioQueueRef.current.push(arrayBuffer.buffer);

      // Jouer si pas déjà en cours
      if (!audioContextRef.current) {
        await initAudioContext();
      }

      playAudioQueue();
    } catch (err) {
      console.error("❌ Audio output error:", err);
    }
  }, []);

  const initAudioContext = async () => {
    if (audioContextRef.current) return;

    audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
      sampleRate: finalConfig.sampleRate,
    });

    // iOS Safari fix: resume context
    if (audioContextRef.current.state === "suspended") {
      await audioContextRef.current.resume();
    }
  };

  const playAudioQueue = async () => {
    if (!audioContextRef.current || audioQueueRef.current.length === 0) return;

    const audioBuffer = audioQueueRef.current.shift()!;

    try {
      // Convertir en AudioBuffer
      const decodedBuffer = await audioContextRef.current.decodeAudioData(audioBuffer);

      // Créer source et jouer
      const source = audioContextRef.current.createBufferSource();
      source.buffer = decodedBuffer;
      source.connect(audioContextRef.current.destination);

      source.onended = () => {
        // Jouer prochain chunk
        if (audioQueueRef.current.length > 0) {
          playAudioQueue();
        } else {
          setState("listening");
        }
      };

      source.start();
    } catch (err) {
      console.error("❌ Audio playback error:", err);
    }
  };

  // ============================================================
  // MICROPHONE
  // ============================================================

  const startMicrophone = useCallback(async () => {
    try {
      console.log("🎤 Requesting microphone access...");

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: finalConfig.sampleRate,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      mediaStreamRef.current = stream;

      // MediaRecorder pour capturer audio
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm",
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          // Convertir Blob → Base64
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = (reader.result as string).split(",")[1];

            // Envoyer au backend
            wsRef.current!.send(
              JSON.stringify({
                type: "audio.input",
                audio: base64,
                format: finalConfig.audioFormat,
                sample_rate: finalConfig.sampleRate,
              })
            );
          };
          reader.readAsDataURL(event.data);
        }
      };

      // Démarrer capture (chunks de 100ms)
      mediaRecorder.start(100);
      mediaRecorderRef.current = mediaRecorder;

      // Audio level (pour UI feedback)
      startAudioLevelMonitoring(stream);

      console.log("✅ Microphone started");
      setState("listening");

      return true;
    } catch (err: any) {
      console.error("❌ Microphone access denied:", err);
      setError({
        type: "microphone",
        message: "Microphone access denied. Please enable in settings.",
      });
      setState("error");
      return false;
    }
  }, [finalConfig]);

  const stopMicrophone = useCallback(() => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    console.log("🛑 Microphone stopped");
  }, []);

  // ============================================================
  // AUDIO LEVEL MONITORING (Visual feedback)
  // ============================================================

  const startAudioLevelMonitoring = (stream: MediaStream) => {
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const microphone = audioContext.createMediaStreamSource(stream);
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    microphone.connect(analyser);
    analyser.fftSize = 256;

    const updateLevel = () => {
      analyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setAudioLevel(Math.min(100, Math.round((average / 255) * 100)));

      if (mediaStreamRef.current) {
        requestAnimationFrame(updateLevel);
      }
    };

    updateLevel();
  };

  // ============================================================
  // PUBLIC API
  // ============================================================

  const startConversation = useCallback(async () => {
    // 1. Connecter WebSocket
    const connected = await connectWebSocket();
    if (!connected) return false;

    // 2. Attendre connexion
    await new Promise((resolve) => setTimeout(resolve, 500));

    // 3. Démarrer microphone
    const started = await startMicrophone();
    return started;
  }, [connectWebSocket, startMicrophone]);

  const stopConversation = useCallback(() => {
    stopMicrophone();
    disconnect();
  }, [stopMicrophone]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    stopMicrophone();
    setIsConnected(false);
    setState("idle");
    audioQueueRef.current = [];
  }, [stopMicrophone]);

  const interrupt = useCallback(() => {
    // Interrompre génération en cours
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "interrupt",
        })
      );
    }

    // Clear audio queue
    audioQueueRef.current = [];

    setState("listening");
  }, []);

  // ============================================================
  // CLEANUP
  // ============================================================

  useEffect(() => {
    return () => {
      disconnect();
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [disconnect]);

  // ============================================================
  // RETURN
  // ============================================================

  return {
    // États
    state,
    isConnected,
    isListening: state === "listening",
    isSpeaking: state === "speaking",
    error,
    audioLevel,

    // Permissions
    isSuperAdmin,
    canUseVoiceRealtime: isSuperAdmin && isAuthenticated,

    // Actions
    startConversation,
    stopConversation,
    interrupt,
  };
}
