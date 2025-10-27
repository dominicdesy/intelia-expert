/**
 * IOSInstallBanner Component - iOS Safari Installation Instructions
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */

"use client";

import { useState, useEffect } from "react";
import { X, Share, Plus, Square } from "lucide-react";

export default function IOSInstallBanner() {
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    // Check if already dismissed
    const dismissed = localStorage.getItem("ios-install-dismissed");
    if (dismissed) {
      const dismissedTime = parseInt(dismissed);
      const daysSinceDismissed =
        (Date.now() - dismissedTime) / (1000 * 60 * 60 * 24);

      // Show again after 7 days
      if (daysSinceDismissed < 7) {
        return;
      }
    }

    // Check if already installed
    if ((window.navigator as any).standalone === true) {
      return;
    }

    // Detect iOS Safari
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isSafari = /Safari/.test(navigator.userAgent) && !/CriOS|FxiOS|OPiOS|mercury/.test(navigator.userAgent);

    if (isIOS && isSafari) {
      // Wait a bit before showing to avoid overwhelming on first visit
      const timer = setTimeout(() => {
        setShowBanner(true);
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, []);

  const handleDismiss = () => {
    localStorage.setItem("ios-install-dismissed", Date.now().toString());
    setShowBanner(false);
  };

  if (!showBanner) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t-2 border-blue-500 shadow-2xl animate-slide-up">
      <div className="max-w-2xl mx-auto p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-100 rounded-xl p-2">
              <img
                src="/images/logo.png"
                alt="Intelia Expert"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <h3 className="font-bold text-gray-900">
                Installer Intelia Expert
              </h3>
              <p className="text-sm text-gray-600">
                Ajoutez l'app à votre écran d'accueil
              </p>
            </div>
          </div>
          <button
            onClick={handleDismiss}
            className="p-1 hover:bg-gray-100 rounded-full transition-colors"
            aria-label="Fermer"
          >
            <X size={24} className="text-gray-500" />
          </button>
        </div>

        {/* Visual Instructions */}
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <p className="text-sm font-medium text-gray-700">
            Pour installer cette app :
          </p>

          {/* Step 1 */}
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
              1
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-800">
                Appuyez sur le bouton <strong>Partager</strong>
              </p>
              <div className="mt-1 flex items-center gap-2 text-blue-600">
                <Share size={20} />
                <span className="text-xs">(en bas de Safari)</span>
              </div>
            </div>
          </div>

          {/* Step 2 */}
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
              2
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-800">
                Sélectionnez <strong>"Sur l'écran d'accueil"</strong>
              </p>
              <div className="mt-1 flex items-center gap-2 text-blue-600">
                <Plus size={20} />
                <Square size={16} />
                <span className="text-xs">(faites défiler vers le bas)</span>
              </div>
            </div>
          </div>

          {/* Step 3 */}
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
              3
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-800">
                Appuyez sur <strong>"Ajouter"</strong> en haut à droite
              </p>
            </div>
          </div>
        </div>

        {/* Footer Note */}
        <p className="mt-3 text-xs text-gray-500 text-center">
          L'icône apparaîtra sur votre écran d'accueil
        </p>
      </div>
    </div>
  );
}
