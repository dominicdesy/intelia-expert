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

  const [dots, setDots] = useState("");

  // Animation des points
  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => {
        if (prev === "...") return "";
        return prev + ".";
      });
    }, 500);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {/* Icône animée */}
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
      </div>

      {/* Texte avec animation de fondu */}
      <span className="text-sm text-gray-600 animate-pulse font-medium">
        {loadingText}
        <span className="inline-block w-6 text-left">{dots}</span>
      </span>

      {/* Style CSS pour l'animation personnalisée */}
      <style jsx>{`
        @keyframes fadeInOut {
          0%,
          100% {
            opacity: 0.4;
          }
          50% {
            opacity: 1;
          }
        }

        .animate-pulse {
          animation: fadeInOut 2s ease-in-out infinite;
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
