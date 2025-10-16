"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "@/lib/languages/i18n";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  className?: string;
}

// Map interface languages to Web Speech API language codes
const LANGUAGE_MAP: Record<string, string> = {
  en: "en-US",
  fr: "fr-FR",
  es: "es-ES",
  de: "de-DE",
  it: "it-IT",
  pt: "pt-PT",
  nl: "nl-NL",
  pl: "pl-PL",
  ar: "ar-SA",
  zh: "zh-CN",
  ja: "ja-JP",
  hi: "hi-IN",
  id: "id-ID",
  th: "th-TH",
  tr: "tr-TR",
  vi: "vi-VN",
};

export const VoiceInput: React.FC<VoiceInputProps> = ({
  onTranscript,
  disabled = false,
  className = "",
}) => {
  const { t, currentLanguage } = useTranslation();
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const finalTranscriptRef = useRef("");

  // Check browser support on mount
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    // Initialize speech recognition
    const recognition = new SpeechRecognition();
    recognition.continuous = false; // Stop after user stops speaking
    recognition.interimResults = true; // Get interim results for better UX
    recognition.maxAlternatives = 1;

    // Set language based on interface language
    const speechLang = LANGUAGE_MAP[currentLanguage] || "en-US";
    recognition.lang = speechLang;

    recognitionRef.current = recognition;

    // Handle results
    recognition.onresult = (event: any) => {
      let interimTranscript = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      if (finalTranscript) {
        finalTranscriptRef.current = finalTranscript;
      }
    };

    // Handle end of speech
    recognition.onend = () => {
      setIsListening(false);
      if (finalTranscriptRef.current) {
        onTranscript(finalTranscriptRef.current);
        finalTranscriptRef.current = "";
      }
    };

    // Handle errors
    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      setIsListening(false);

      switch (event.error) {
        case "no-speech":
          setError(t("chat.voiceNoSpeech"));
          break;
        case "not-allowed":
        case "permission-denied":
          setError(t("chat.voicePermissionDenied"));
          break;
        case "network":
          setError(t("chat.voiceError"));
          break;
        default:
          setError(t("chat.voiceError"));
      }

      // Clear error after 3 seconds
      setTimeout(() => setError(null), 3000);
    };

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, [currentLanguage, onTranscript, t]);

  const toggleListening = useCallback(() => {
    if (!recognitionRef.current || disabled) return;

    if (isListening) {
      // Stop listening
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      // Start listening
      setError(null);
      finalTranscriptRef.current = "";
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.error("Error starting speech recognition:", err);
        setError(t("chat.voiceError"));
        setTimeout(() => setError(null), 3000);
      }
    }
  }, [isListening, disabled, t]);

  if (!isSupported) {
    return (
      <button
        disabled={true}
        className={`flex-shrink-0 h-12 w-12 flex items-center justify-center text-gray-300 cursor-not-allowed rounded-full ${className}`}
        title={t("chat.voiceNotSupported")}
        aria-label={t("chat.voiceNotSupported")}
        style={{
          minWidth: "48px",
          width: "48px",
          height: "48px",
        }}
      >
        <MicrophoneIcon className="opacity-50" />
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={toggleListening}
        disabled={disabled}
        className={`flex-shrink-0 h-12 w-12 flex items-center justify-center transition-colors rounded-full ${
          isListening
            ? "text-red-600 bg-red-50 hover:bg-red-100"
            : "text-blue-600 hover:text-blue-700 disabled:text-gray-300 hover:bg-blue-50"
        } ${className}`}
        title={
          isListening
            ? t("chat.voiceStop")
            : error
              ? error
              : t("chat.voiceStart")
        }
        aria-label={
          isListening
            ? t("chat.voiceStop")
            : error
              ? error
              : t("chat.voiceStart")
        }
        style={{
          minWidth: "48px",
          width: "48px",
          height: "48px",
        }}
      >
        <MicrophoneIcon className={isListening ? "animate-pulse" : ""} />
      </button>

      {/* Listening indicator */}
      {isListening && (
        <span className="absolute -top-1 -right-1 flex h-4 w-4">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-4 w-4 bg-red-500"></span>
        </span>
      )}

      {/* Error tooltip */}
      {error && !isListening && (
        <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-red-100 text-red-700 text-xs px-3 py-1 rounded-lg whitespace-nowrap shadow-lg">
          {error}
        </div>
      )}
    </div>
  );
};

// Microphone Icon Component
const MicrophoneIcon: React.FC<{ className?: string }> = ({
  className = "",
}) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    className={`w-5 h-5 ${className}`}
  >
    <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
    <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
  </svg>
);
