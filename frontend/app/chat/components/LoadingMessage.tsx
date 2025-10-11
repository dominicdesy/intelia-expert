/**
 * Composant LoadingMessage
 * Affiche un message animé pendant le chargement de la réponse de l'IA
 */

"use client";

import React, { useEffect, useState, useMemo } from "react";
import { getRandomLoadingMessage } from "../utils/loadingMessages";

interface LoadingMessageProps {
  language?: string;
  className?: string;
}

export const LoadingMessage: React.FC<LoadingMessageProps> = ({
  language = "en",
  className = "",
}) => {
  // Générer un message aléatoire au montage du composant
  const loadingText = useMemo(
    () => getRandomLoadingMessage(language),
    [language]
  );

  // Diviser le texte en caractères pour l'animation wave
  const characters = useMemo(() => loadingText.split(""), [loadingText]);

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {/* Icône animée */}
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
      </div>

      {/* Texte avec animation wave */}
      <span className="text-sm font-medium flex">
        {characters.map((char, index) => (
          <span
            key={index}
            className="animate-wave inline-block"
            style={{
              animationDelay: `${index * 0.1}s`,
              color: char === " " ? "transparent" : undefined,
            }}
          >
            {char === " " ? "\u00A0" : char}
          </span>
        ))}
      </span>

      {/* Style CSS pour l'animation personnalisée */}
      <style jsx>{`
        @keyframes wave {
          0%,
          100% {
            transform: translateY(0) scale(1);
            color: #4b5563;
          }
          25% {
            transform: translateY(-4px) scale(1.1);
            color: #3b82f6;
          }
          50% {
            transform: translateY(-6px) scale(1.15);
            color: #2563eb;
          }
          75% {
            transform: translateY(-4px) scale(1.1);
            color: #3b82f6;
          }
        }

        .animate-wave {
          animation: wave 2s ease-in-out infinite;
          display: inline-block;
        }

        @keyframes bounce {
          0%,
          100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-8px);
          }
        }

        .animate-bounce {
          animation: bounce 1s ease-in-out infinite;
        }

        [animation-delay\\:"-0\\.3s"] {
          animation-delay: -0.3s;
        }

        [animation-delay\\:"-0\\.15s"] {
          animation-delay: -0.15s;
        }
      `}</style>
    </div>
  );
};

export default LoadingMessage;
