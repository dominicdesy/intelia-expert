"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "@/lib/languages/i18n";

interface HelpStep {
  target: string; // Selector CSS
  title: string;
  description: string;
  position: "top" | "bottom" | "left" | "right";
}

interface HelpTourProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HelpTour({ isOpen, onClose }: HelpTourProps) {
  const { t } = useTranslation();
  const [currentStep, setCurrentStep] = useState(0);
  const [spotlightRect, setSpotlightRect] = useState<DOMRect | null>(null);
  const [bubblePosition, setBubblePosition] = useState({ top: 0, left: 0 });
  const animationFrameRef = useRef<number>();

  const steps: HelpStep[] = [
    {
      target: "input[placeholder*='question'], input[aria-label*='question'], .chat-input-fixed input, input[type='text']",
      title: t("help.inputTitle"),
      description: t("help.inputDesc"),
      position: "top",
    },
    {
      target: "button[title*='send'], button[aria-label*='Envoyer'], button[title*='Envoyer'], .chat-input-fixed button:last-child",
      title: t("help.sendTitle"),
      description: t("help.sendDesc"),
      position: "left",
    },
    {
      target: "button[title*='nouvelle conversation'], button[aria-label*='nouvelle conversation'], button[title*='Nouvelle conversation'], header button:first-child",
      title: t("help.newChatTitle"),
      description: t("help.newChatDesc"),
      position: "bottom",
    },
    {
      target: ".history-menu-container, header button:nth-child(2), button[aria-label*='historique']",
      title: t("help.historyTitle"),
      description: t("help.historyDesc"),
      position: "bottom",
    },
    {
      target: ".user-menu-container, header button:last-child, button[aria-label*='utilisateur']",
      title: t("help.profileTitle"),
      description: t("help.profileDesc"),
      position: "bottom",
    },
  ];

  const updateSpotlight = useCallback(() => {
    const step = steps[currentStep];

    // Essayer de trouver l'élément avec chaque sélecteur possible
    const selectors = step.target.split(',').map(s => s.trim());
    let element: Element | null = null;

    for (const selector of selectors) {
      element = document.querySelector(selector);
      if (element) {
        console.log(`[HelpTour] Element trouvé avec: ${selector}`);
        break;
      }
    }

    if (!element) {
      console.warn(`[HelpTour] Aucun élément trouvé pour l'étape ${currentStep + 1}. Sélecteurs essayés:`, selectors);
      // Mettre une position par défaut temporaire
      setBubblePosition({ top: 100, left: 100 });
      return;
    }

    const rect = element.getBoundingClientRect();
    console.log(`[HelpTour] Position de l'élément:`, rect);
    setSpotlightRect(rect);

    // Calculer la position de la bulle
    const bubbleWidth = 320;
    const bubbleHeight = 220; // Hauteur estimée pour le positionnement
    const padding = 20;

    let top = 0;
    let left = 0;

    switch (step.position) {
      case "top":
        top = rect.top - bubbleHeight - padding;
        left = rect.left + rect.width / 2 - bubbleWidth / 2;
        break;
      case "bottom":
        top = rect.bottom + padding;
        left = rect.left + rect.width / 2 - bubbleWidth / 2;
        break;
      case "left":
        top = rect.top + rect.height / 2 - bubbleHeight / 2;
        left = rect.left - bubbleWidth - padding;
        break;
      case "right":
        top = rect.top + rect.height / 2 - bubbleHeight / 2;
        left = rect.right + padding;
        break;
    }

    // Ajuster si la bulle sort de l'écran
    if (left < 10) left = 10;
    if (left + bubbleWidth > window.innerWidth - 10) {
      left = window.innerWidth - bubbleWidth - 10;
    }
    if (top < 10) top = 10;
    // Plus de marge en bas pour s'assurer que tout le contenu est visible
    if (top + bubbleHeight > window.innerHeight - 30) {
      top = window.innerHeight - bubbleHeight - 30;
    }

    setBubblePosition({ top, left });
  }, [currentStep, steps]);

  useEffect(() => {
    if (isOpen) {
      // Petit délai pour s'assurer que le DOM est prêt
      const initialTimeout = setTimeout(() => {
        updateSpotlight();
      }, 100);

      const handleResize = () => {
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
        }
        animationFrameRef.current = requestAnimationFrame(updateSpotlight);
      };

      window.addEventListener("resize", handleResize);
      window.addEventListener("scroll", handleResize, true);

      return () => {
        clearTimeout(initialTimeout);
        window.removeEventListener("resize", handleResize);
        window.removeEventListener("scroll", handleResize, true);
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
        }
      };
    }
  }, [isOpen, updateSpotlight]);

  // Mettre à jour le spotlight quand on change d'étape
  useEffect(() => {
    if (isOpen) {
      // Petit délai pour les animations
      const timeout = setTimeout(() => {
        updateSpotlight();
      }, 50);
      return () => clearTimeout(timeout);
    }
  }, [currentStep, isOpen, updateSpotlight]);

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onClose();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSkip = () => {
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999]">
      {/* Overlay avec spotlight */}
      <div className="absolute inset-0 pointer-events-none">
        <svg width="100%" height="100%" className="absolute inset-0">
          <defs>
            <mask id="spotlight-mask">
              <rect x="0" y="0" width="100%" height="100%" fill="white" />
              {spotlightRect && (
                <rect
                  x={spotlightRect.x - 8}
                  y={spotlightRect.y - 8}
                  width={spotlightRect.width + 16}
                  height={spotlightRect.height + 16}
                  rx="12"
                  fill="black"
                />
              )}
            </mask>
          </defs>
          <rect
            x="0"
            y="0"
            width="100%"
            height="100%"
            fill="rgba(0, 0, 0, 0.75)"
            mask="url(#spotlight-mask)"
          />
        </svg>

        {/* Contour du spotlight animé */}
        {spotlightRect && (
          <div
            className="absolute border-4 border-blue-500 rounded-xl transition-all duration-300 pointer-events-none"
            style={{
              top: spotlightRect.y - 8,
              left: spotlightRect.x - 8,
              width: spotlightRect.width + 16,
              height: spotlightRect.height + 16,
              boxShadow: "0 0 0 4px rgba(59, 130, 246, 0.3), 0 0 20px 8px rgba(59, 130, 246, 0.4)",
              animation: "pulse-border 2s ease-in-out infinite",
            }}
          />
        )}
      </div>

      {/* Bulle d'aide */}
      <div
        className="absolute bg-white rounded-2xl shadow-2xl p-6 transition-all duration-300 pointer-events-auto"
        style={{
          top: bubblePosition.top,
          left: bubblePosition.left,
          width: "320px",
          animation: "fadeInScale 0.3s ease-out",
        }}
      >
        {/* Header avec numéro d'étape */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
              {currentStep + 1}
            </div>
            <span className="text-xs text-gray-500 font-medium">
              {currentStep + 1} / {steps.length}
            </span>
          </div>
          <button
            onClick={handleSkip}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label={t("help.close")}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Contenu */}
        <div className="mb-4">
          <h3 className="text-lg font-bold text-gray-900 mb-2">
            {steps[currentStep].title}
          </h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            {steps[currentStep].description}
          </p>
        </div>

        {/* Boutons de navigation */}
        <div className="flex items-center justify-between">
          <button
            onClick={handlePrev}
            disabled={currentStep === 0}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span>{t("help.previous")}</span>
          </button>

          <div className="flex space-x-2">
            {Array.from({ length: steps.length }).map((_, index) => (
              <div
                key={index}
                className={`h-2 rounded-full transition-all duration-300 ${
                  index === currentStep
                    ? "w-6 bg-blue-600"
                    : "w-2 bg-gray-300"
                }`}
              />
            ))}
          </div>

          <button
            onClick={handleNext}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
          >
            <span>{currentStep === steps.length - 1 ? t("help.finish") : t("help.next")}</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeInScale {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        @keyframes pulse-border {
          0%, 100% {
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.3), 0 0 20px 8px rgba(59, 130, 246, 0.4);
          }
          50% {
            box-shadow: 0 0 0 8px rgba(59, 130, 246, 0.2), 0 0 30px 12px rgba(59, 130, 246, 0.3);
          }
        }
      `}</style>
    </div>
  );
}

// Bouton d'aide à intégrer dans le header
export function HelpButton({ onClick }: { onClick: () => void }) {
  const { t } = useTranslation();

  return (
    <button
      onClick={onClick}
      className="w-10 h-10 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors flex items-center justify-center border border-gray-200 hover:border-blue-300"
      title={t("help.buttonTitle")}
      aria-label={t("help.buttonTitle")}
    >
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    </button>
  );
}
