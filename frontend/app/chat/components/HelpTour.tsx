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
  const [isMobile, setIsMobile] = useState(false);
  const animationFrameRef = useRef<number>();

  // Détection mobile
  useEffect(() => {
    const detectMobile = () => {
      const userAgent = navigator.userAgent.toLowerCase();
      const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
      const isSmallScreen = window.innerWidth <= 768;
      const hasTouchScreen = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      const isIPadOS = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;

      return (isMobileUA || isIPadOS || (isSmallScreen && hasTouchScreen));
    };

    setIsMobile(detectMobile());

    const handleResize = () => {
      setIsMobile(detectMobile());
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const steps: HelpStep[] = [
    {
      target: "input[placeholder*='question'], input[aria-label*='question'], .chat-input-fixed input, input[type='text']",
      title: t("help.inputTitle"),
      description: t("help.inputDesc"),
      position: "top",
    },
    {
      target: "button[title*='send'], button[aria-label*='Envoyer'], button[title*='Envoyer'], button[title*='Sending']",
      title: t("help.sendTitle"),
      description: t("help.sendDesc"),
      position: "left",
    },
    {
      target: "button[title*='image'], button[aria-label*='image'], button[title*='Ajouter']",
      title: t("help.cameraTitle"),
      description: t("help.cameraDesc"),
      position: "top",
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

    // Calculer la position de la bulle - Adaptatif mobile/desktop
    const bubbleWidth = isMobile ? Math.min(300, window.innerWidth - 40) : 320;
    const bubbleHeight = isMobile ? 200 : 220;
    const padding = isMobile ? 12 : 20;

    let top = 0;
    let left = 0;

    if (isMobile) {
      // Sur mobile : positions simplifiées et optimisées
      switch (currentStep) {
        case 0: // Input - Au-dessus de l'input
          top = rect.top - bubbleHeight - 80;
          left = (window.innerWidth - bubbleWidth) / 2;
          break;
        case 1: // Send button - À gauche du bouton, plus bas
          top = rect.bottom - bubbleHeight + 40;
          left = Math.max(10, rect.left - bubbleWidth - padding);
          break;
        case 2: // Camera button - Au-dessus, bien espacé
          top = rect.top - bubbleHeight - 100;
          left = (window.innerWidth - bubbleWidth) / 2;
          break;
        case 3: // New conversation - En-dessous
          top = rect.bottom + padding + 10;
          left = Math.max(10, rect.left);
          break;
        case 4: // History - En-dessous
          top = rect.bottom + padding + 10;
          left = Math.max(10, rect.left);
          break;
        case 5: // User menu - En-dessous, aligné à droite
          top = rect.bottom + padding + 10;
          left = Math.min(window.innerWidth - bubbleWidth - 10, rect.right - bubbleWidth);
          break;
      }
    } else {
      // Desktop : logique originale
      const topPadding = currentStep === 2 ? 40 : padding;

      switch (step.position) {
        case "top":
          top = rect.top - bubbleHeight - topPadding;
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
    }

    // Ajuster si la bulle sort de l'écran
    const margin = isMobile ? 10 : 10;
    if (left < margin) left = margin;
    if (left + bubbleWidth > window.innerWidth - margin) {
      left = window.innerWidth - bubbleWidth - margin;
    }
    if (top < margin) top = margin;
    if (top + bubbleHeight > window.innerHeight - (isMobile ? 20 : 30)) {
      top = window.innerHeight - bubbleHeight - (isMobile ? 20 : 30);
    }

    setBubblePosition({ top, left });
  }, [currentStep, steps, isMobile]);

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
      setCurrentStep(0); // Reset to first step
      onClose();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSkip = () => {
    setCurrentStep(0); // Reset to first step
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
        className={`absolute bg-white rounded-2xl shadow-2xl transition-all duration-300 pointer-events-auto ${
          isMobile ? 'p-4' : 'p-6'
        }`}
        style={{
          top: bubblePosition.top,
          left: bubblePosition.left,
          width: isMobile ? `${Math.min(300, window.innerWidth - 40)}px` : "320px",
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
        <div className="flex items-center justify-center">
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
