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
  const playbackAudioContextRef = useRef<AudioContext | null>(null); // For playing OpenAI audio
  const micAudioContextRef = useRef<AudioContext | null>(null); // For capturing microphone
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false); // Prevent overlapping audio playback
  const isBufferingRef = useRef(true); // Pre-buffer chunks before playing
  const reconnectAttemptsRef = useRef(0);

  // ============================================================
  // VÉRIFICATION ACCÈS
  // ============================================================

  const isSuperAdmin = user?.is_admin === true;
  const hasInteliaPlan = user?.plan === "intelia";
  const canUseVoiceRealtime = isSuperAdmin || hasInteliaPlan;

  // ============================================================
  // WEBSOCKET
  // ============================================================

  const connectWebSocket = useCallback(async () => {
    if (!isAuthenticated || !canUseVoiceRealtime) {
      setError({
        type: "auth",
        message: "Voice Realtime access requires Intelia plan or admin privileges",
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
        // Chunk audio reçu du backend (legacy)
        handleAudioOutput(data.audio);
        if (state !== "speaking") {
          setState("speaking");
        }
        break;

      case "response.audio.delta":
        // OpenAI audio response chunk
        if (data.delta) {
          handleAudioOutput(data.delta);
          if (state !== "speaking") {
            setState("speaking");
          }
        }
        break;

      case "response.audio.done":
        console.log("✅ OpenAI finished speaking");
        setState("listening");
        break;

      case "input_audio_buffer.speech_started":
        console.log("🎤 Speech detected");
        break;

      case "input_audio_buffer.speech_stopped":
        console.log("🎤 Speech stopped");
        break;

      case "conversation.item.input_audio_transcription.completed":
        console.log("📝 Transcription:", data.transcript);
        break;

      case "response.audio_transcript.delta":
        // Optionally log what AI is saying
        // console.log("🗣️", data.delta);
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
        const errorMessage = data.error?.message || data.message || "Server error";
        setError({
          type: "unknown",
          message: errorMessage,
        });
        break;

      case "connection.ready":
        console.log("✅ Backend ready");
        break;

      // Ignore other OpenAI protocol messages
      case "input_audio_buffer.committed":
      case "conversation.item.created":
      case "response.created":
      case "response.output_item.added":
      case "response.content_part.added":
      case "conversation.item.input_audio_transcription.delta":
        // Silently ignore these informational messages
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
      console.log("🔊 Received audio chunk, length:", base64Audio.length);

      // Décoder Base64
      const audioData = atob(base64Audio);
      const arrayBuffer = new Uint8Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        arrayBuffer[i] = audioData.charCodeAt(i);
      }

      console.log("🔊 Decoded audio buffer:", arrayBuffer.length, "bytes");

      // Ajouter à queue
      audioQueueRef.current.push(arrayBuffer.buffer);
      console.log("🔊 Audio queue length:", audioQueueRef.current.length);

      // Jouer si pas déjà en cours
      if (!playbackAudioContextRef.current) {
        console.log("🔊 Initializing playback AudioContext...");
        await initPlaybackAudioContext();
      }

      playAudioQueue();
    } catch (err) {
      console.error("❌ Audio output error:", err);
    }
  }, []);

  const initPlaybackAudioContext = async () => {
    if (playbackAudioContextRef.current) {
      // Always try to resume if suspended (autoplay policy)
      if (playbackAudioContextRef.current.state === "suspended") {
        console.log("🔊 Playback AudioContext suspended, resuming...");
        await playbackAudioContextRef.current.resume();
        console.log("🔊 Playback AudioContext state:", playbackAudioContextRef.current.state);
      }
      return;
    }

    console.log("🔊 Creating new playback AudioContext (using system sample rate)");
    playbackAudioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    // Don't force 24kHz - let it use system default (usually 48kHz)
    // We'll create the AudioBuffer at 24kHz which will be resampled automatically

    console.log("🔊 Playback AudioContext created, state:", playbackAudioContextRef.current.state);

    // iOS Safari fix: resume context immediately
    if (playbackAudioContextRef.current.state === "suspended") {
      console.log("🔊 Playback AudioContext suspended on creation, resuming...");
      await playbackAudioContextRef.current.resume();
      console.log("🔊 Playback AudioContext resumed, state:", playbackAudioContextRef.current.state);
    }
  };

  const playAudioQueue = async () => {
    // Prevent overlapping playback
    if (isPlayingRef.current) {
      console.log("🔊 Already playing, skipping...");
      return;
    }

    if (!playbackAudioContextRef.current || audioQueueRef.current.length === 0) {
      console.log("🔊 playAudioQueue: Playback AudioContext or queue empty");
      return;
    }

    // Pre-buffer: wait for at least 2 chunks before starting (reduces gaps)
    if (isBufferingRef.current && audioQueueRef.current.length < 2) {
      console.log("🔊 Buffering... waiting for more chunks");
      return;
    }
    isBufferingRef.current = false;

    isPlayingRef.current = true;
    const pcm16Buffer = audioQueueRef.current.shift()!;
    console.log("🔊 Playing audio chunk, buffer size:", pcm16Buffer.byteLength);

    try {
      // Convert PCM16 (Int16) → Float32 for Web Audio API
      const pcm16 = new Int16Array(pcm16Buffer);
      const float32 = new Float32Array(pcm16.length);

      for (let i = 0; i < pcm16.length; i++) {
        // Convert Int16 to Float32 (-1.0 to 1.0)
        float32[i] = pcm16[i] / (pcm16[i] < 0 ? 0x8000 : 0x7FFF);
      }

      console.log("🔊 Converted to Float32, samples:", float32.length);

      // Create AudioBuffer manually (OpenAI sends PCM16 at 24kHz mono)
      const audioBuffer = playbackAudioContextRef.current.createBuffer(
        1, // mono
        float32.length,
        24000 // OpenAI sample rate
      );

      audioBuffer.getChannelData(0).set(float32);
      console.log("🔊 AudioBuffer created, duration:", audioBuffer.duration, "seconds");

      // Create gain node for fade in/out (prevents clicks)
      const gainNode = playbackAudioContextRef.current.createGain();
      const currentTime = playbackAudioContextRef.current.currentTime;
      const duration = audioBuffer.duration;

      // Fade in (first 10ms)
      gainNode.gain.setValueAtTime(0, currentTime);
      gainNode.gain.linearRampToValueAtTime(1, currentTime + 0.01);

      // Fade out (last 10ms)
      gainNode.gain.setValueAtTime(1, currentTime + duration - 0.01);
      gainNode.gain.linearRampToValueAtTime(0, currentTime + duration);

      // Create source and connect through gain node
      const source = playbackAudioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(gainNode);
      gainNode.connect(playbackAudioContextRef.current.destination);

      source.onended = () => {
        console.log("🔊 Audio chunk finished playing");
        isPlayingRef.current = false;

        // Play next chunk
        if (audioQueueRef.current.length > 0) {
          playAudioQueue();
        } else {
          setState("listening");
          isBufferingRef.current = true; // Reset buffering for next response
        }
      };

      console.log("🔊 Starting audio playback...");
      source.start();
    } catch (err) {
      console.error("❌ Audio playback error:", err);
      isPlayingRef.current = false; // Reset on error
      isBufferingRef.current = true; // Reset buffering
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

      // AudioContext pour capturer en PCM16 (format OpenAI)
      const micAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 24000, // OpenAI requires 24kHz
      });
      micAudioContextRef.current = micAudioContext;

      const microphone = micAudioContext.createMediaStreamSource(stream);
      const processor = micAudioContext.createScriptProcessor(4096, 1, 1);
      audioProcessorRef.current = processor;

      processor.onaudioprocess = (event) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        const inputData = event.inputBuffer.getChannelData(0);

        // Convert Float32 → PCM16
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        // Convert to base64
        const bytes = new Uint8Array(pcm16.buffer);
        const base64 = btoa(String.fromCharCode.apply(null, Array.from(bytes)));

        // Send to backend
        wsRef.current.send(
          JSON.stringify({
            type: "audio.input",
            audio: base64,
          })
        );
      };

      microphone.connect(processor);
      processor.connect(micAudioContext.destination);

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
    if (audioProcessorRef.current) {
      audioProcessorRef.current.disconnect();
      audioProcessorRef.current = null;
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
      if (playbackAudioContextRef.current) {
        playbackAudioContextRef.current.close();
      }
      if (micAudioContextRef.current) {
        micAudioContextRef.current.close();
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
    hasInteliaPlan,
    canUseVoiceRealtime: canUseVoiceRealtime && isAuthenticated,

    // Actions
    startConversation,
    stopConversation,
    interrupt,
  };
}
