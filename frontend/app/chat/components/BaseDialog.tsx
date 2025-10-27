/**
 * Basedialog
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import React from "react";
import * as Dialog from "@radix-ui/react-dialog";

interface BaseDialogProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  maxWidth?: string;
  showCloseButton?: boolean;
}

/**
 * BaseDialog - Composant de dialogue réutilisable basé sur Radix UI
 *
 * Avantages vs custom overlay:
 * - ✅ Gestion automatique des événements tactiles iOS/Android
 * - ✅ Fermeture avec ESC
 * - ✅ Fermeture en cliquant en dehors (overlay)
 * - ✅ Accessibilité WAI-ARIA
 * - ✅ Focus trap automatique
 * - ✅ Portal rendering (évite z-index issues)
 * - ✅ Animation CSS smooth
 *
 * Usage:
 * <BaseDialog isOpen={isOpen} onClose={onClose} title="Mon Titre">
 *   <div>Contenu de la modale</div>
 * </BaseDialog>
 */
export const BaseDialog: React.FC<BaseDialogProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = "700px",
  showCloseButton = true,
}) => {
  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        {/* Overlay - fond semi-transparent avec blur */}
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 animate-in fade-in-0" />

        {/* Content - modale centrée */}
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-xl border border-gray-200 z-50 w-[95vw] max-h-[90vh] overflow-y-auto animate-in fade-in-0 zoom-in-95"
          style={{ maxWidth, minWidth: "320px" }}
        >
          {/* Header (si title fourni) */}
          {(title || showCloseButton) && (
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              {title && (
                <Dialog.Title className="text-xl font-semibold text-gray-900">
                  {title}
                </Dialog.Title>
              )}
              {showCloseButton && (
                <Dialog.Close asChild>
                  <button
                    className="text-gray-400 hover:text-gray-600 text-2xl transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center ml-auto"
                    aria-label="Fermer"
                  >
                    ×
                  </button>
                </Dialog.Close>
              )}
            </div>
          )}

          {/* Description (hidden but accessible for screen readers) */}
          <Dialog.Description className="sr-only">
            {description || title || "Dialog content"}
          </Dialog.Description>

          {/* Content */}
          <div className="p-6">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
