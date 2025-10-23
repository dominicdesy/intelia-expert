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
 * - Position fixe en bas à droite
 * - Accès: Super admins + utilisateurs avec plan Intelia
 *
 * Usage:
 * <VoiceRealtimeButton />
 */

"use client";

import React, { useEffect } from "react";
import { useVoiceRealtime } from "@/lib/hooks/useVoiceRealtime";
import { useTranslation } from "@/lib/languages/i18n";
import { Mic, MicOff, Volume2, AlertCircle, Loader2 } from "lucide-react";

// ============================================================
// COMPONENT
// ============================================================

export function VoiceRealtimeButton() {
  const { t } = useTranslation();
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

  // Afficher uniquement si l'utilisateur a accès (admin ou plan Intelia)
  if (!canUseVoiceRealtime) {
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

  // Détection mobile pour position adaptative
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

  return (
    <div
      className="flex flex-col items-end gap-2"
      style={{
        position: 'fixed',
        bottom: isMobile ? 'max(8rem, calc(env(safe-area-inset-bottom, 0px) + 8rem))' : 'max(1.5rem, env(safe-area-inset-bottom, 1.5rem))',
        right: isMobile ? 'max(2rem, env(safe-area-inset-right, 2rem))' : 'max(1.5rem, env(safe-area-inset-right, 1.5rem))',
        zIndex: 9999,
        pointerEvents: 'auto',
        // Empêcher le bouton de disparaître lors du zoom
        transform: 'translate3d(0, 0, 0)',
        willChange: 'transform',
      }}
    >
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
        {state === "idle" && t("chat.voiceRealtimeIdle")}
        {state === "connecting" && t("chat.voiceRealtimeConnecting")}
        {state === "listening" && `🎤 ${t("chat.voiceRealtimeListening")}`}
        {state === "speaking" && `🔊 ${t("chat.voiceRealtimeSpeaking")}`}
        {state === "error" && `⚠️ ${t("chat.voiceRealtimeError")}`}
      </div>

      {/* Instructions (première utilisation) */}
      {state === "idle" && (
        <div className="absolute bottom-full right-0 mb-3 bg-gray-800 text-gray-200 rounded-lg p-3 shadow-xl text-xs max-w-xs hidden group-hover:block">
          <div className="font-semibold mb-1">{t("chat.voiceRealtimeBetaTitle")}</div>
          <ul className="space-y-1 text-gray-400">
            <li>• {t("chat.voiceRealtimeClickStart")}</li>
            <li>• {t("chat.voiceRealtimeDoubleClick")}</li>
            <li>• {t("chat.voiceRealtimeAdminOnly")}</li>
          </ul>
        </div>
      )}
    </div>
  );
}
