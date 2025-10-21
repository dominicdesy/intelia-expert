/**
 * VoiceRealtimeButton Component
 * ==============================
 *
 * Bouton icône pour conversation vocale en temps réel
 *
 * Features:
 * - Icône microphone animée
 * - États visuels (idle/listening/speaking)
 * - Indicateur volume microphone
 * - Gestion erreurs
 * - Feedback haptique mobile
 * - Position fixe en bas à droite (pour super admin seulement)
 *
 * Usage:
 * <VoiceRealtimeButton />
 */

"use client";

import React, { useEffect } from "react";
import { useVoiceRealtime } from "@/lib/hooks/useVoiceRealtime";
import { Mic, MicOff, Volume2, AlertCircle, Loader2 } from "lucide-react";

// ============================================================
// COMPONENT
// ============================================================

export function VoiceRealtimeButton() {
  const {
    state,
    isConnected,
    isListening,
    isSpeaking,
    error,
    audioLevel,
    isSuperAdmin,
    canUseVoiceRealtime,
    startConversation,
    stopConversation,
    interrupt,
  } = useVoiceRealtime();

  // ============================================================
  // PERMISSIONS
  // ============================================================

  // Si pas super admin, ne rien afficher
  if (!isSuperAdmin || !canUseVoiceRealtime) {
    return null;
  }

  // ============================================================
  // HANDLERS
  // ============================================================

  const handleClick = async () => {
    // Feedback haptique mobile
    if (navigator.vibrate) {
      navigator.vibrate(50);
    }

    if (state === "idle") {
      // Démarrer conversation
      const started = await startConversation();
      if (!started) {
        console.error("Failed to start conversation");
      }
    } else if (state === "listening" || state === "speaking") {
      // Arrêter conversation
      stopConversation();
    } else if (state === "connecting") {
      // Attendre...
    }
  };

  const handleInterrupt = () => {
    if (isSpeaking) {
      interrupt();
      if (navigator.vibrate) {
        navigator.vibrate([50, 50, 50]); // Triple vibration
      }
    }
  };

  // ============================================================
  // VISUAL STATES
  // ============================================================

  const getButtonColor = () => {
    switch (state) {
      case "listening":
        return "bg-green-500 hover:bg-green-600 shadow-green-500/50";
      case "speaking":
        return "bg-blue-500 hover:bg-blue-600 shadow-blue-500/50";
      case "connecting":
        return "bg-yellow-500 hover:bg-yellow-600 shadow-yellow-500/50";
      case "error":
        return "bg-red-500 hover:bg-red-600 shadow-red-500/50";
      default:
        return "bg-gray-700 hover:bg-gray-600 shadow-gray-700/50";
    }
  };

  const getIcon = () => {
    switch (state) {
      case "listening":
        return <Mic className="h-6 w-6" />;
      case "speaking":
        return <Volume2 className="h-6 w-6" />;
      case "connecting":
        return <Loader2 className="h-6 w-6 animate-spin" />;
      case "error":
        return <AlertCircle className="h-6 w-6" />;
      default:
        return <MicOff className="h-6 w-6" />;
    }
  };

  const getTooltip = () => {
    switch (state) {
      case "listening":
        return "Listening... Click to stop";
      case "speaking":
        return "Speaking... Click to interrupt";
      case "connecting":
        return "Connecting...";
      case "error":
        return error?.message || "Error";
      default:
        return "Start voice conversation (Super Admin)";
    }
  };

  // ============================================================
  // AUTO-SCROLL LORS DU SPEAKING
  // ============================================================

  useEffect(() => {
    if (isSpeaking) {
      // Optionnel: scroll auto vers le bas si réponse visible
      // window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    }
  }, [isSpeaking]);

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {/* Indicateur audio level (pendant listening) */}
      {isListening && audioLevel > 0 && (
        <div className="bg-gray-800 rounded-lg px-3 py-2 shadow-lg">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Volume</span>
            <div className="w-20 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 transition-all duration-100"
                style={{ width: `${audioLevel}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Message erreur */}
      {error && (
        <div className="bg-red-900/90 text-red-100 rounded-lg px-4 py-2 shadow-lg max-w-xs text-sm">
          <div className="font-semibold mb-1">{error.type.toUpperCase()}</div>
          <div>{error.message}</div>
        </div>
      )}

      {/* Bouton principal */}
      <button
        onClick={handleClick}
        onDoubleClick={handleInterrupt}
        title={getTooltip()}
        disabled={state === "connecting"}
        className={`
          ${getButtonColor()}
          text-white
          rounded-full
          p-4
          shadow-2xl
          transition-all
          duration-300
          transform
          hover:scale-110
          active:scale-95
          disabled:opacity-50
          disabled:cursor-not-allowed
          ${isListening ? "animate-pulse" : ""}
          ${isSpeaking ? "shadow-2xl" : ""}
        `}
      >
        {getIcon()}

        {/* Badge admin */}
        {state === "idle" && (
          <div className="absolute -top-1 -right-1 bg-orange-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
            A
          </div>
        )}

        {/* Animation pulse listening */}
        {isListening && (
          <>
            <span className="absolute inset-0 rounded-full bg-green-500 animate-ping opacity-75" />
            <span className="absolute inset-0 rounded-full bg-green-500 animate-pulse opacity-50" />
          </>
        )}

        {/* Animation wave speaking */}
        {isSpeaking && (
          <>
            <span className="absolute inset-0 rounded-full bg-blue-500 animate-ping opacity-75" />
            <span className="absolute inset-0 rounded-full bg-blue-500 animate-pulse opacity-50" />
          </>
        )}
      </button>

      {/* Indicateur état (texte) */}
      <div className="bg-gray-800/90 text-gray-300 rounded-full px-3 py-1 text-xs shadow-lg">
        {state === "idle" && "Voice AI (Admin)"}
        {state === "connecting" && "Connecting..."}
        {state === "listening" && "🎤 Listening"}
        {state === "speaking" && "🔊 Speaking"}
        {state === "error" && "⚠️ Error"}
      </div>

      {/* Instructions (première utilisation) */}
      {state === "idle" && (
        <div className="absolute bottom-full right-0 mb-3 bg-gray-800 text-gray-200 rounded-lg p-3 shadow-xl text-xs max-w-xs hidden group-hover:block">
          <div className="font-semibold mb-1">Voice Realtime (BETA)</div>
          <ul className="space-y-1 text-gray-400">
            <li>• Click to start conversation</li>
            <li>• Double-click to interrupt</li>
            <li>• Super admin only</li>
          </ul>
        </div>
      )}
    </div>
  );
}
