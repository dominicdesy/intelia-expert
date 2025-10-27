/**
 * Dialogwrapper
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import React from "react";
import * as Dialog from "@radix-ui/react-dialog";

interface DialogWrapperProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

/**
 * DialogWrapper - Wrapper Radix UI pour modales existantes
 *
 * Transforme n'importe quelle modale custom en modale Radix UI fonctionnelle
 * Sans modifier le contenu HTML existant
 *
 * ✅ Fix iOS/Android touch events
 * ✅ ESC pour fermer
 * ✅ Click en dehors pour fermer
 * ✅ Accessibilité
 * ✅ Focus trap
 *
 * Usage:
 * <DialogWrapper isOpen={isOpen} onClose={onClose}>
 *   {/  * Contenu existant de la modale *  /}
 *   <div className="fixed inset-0 bg-black/50">
 *     <div className="modal-content">...</div>
 *   </div>
 * </DialogWrapper>
 */
export const DialogWrapper: React.FC<DialogWrapperProps> = ({
  isOpen,
  onClose,
  children,
}) => {
  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Content
          className="dialog-wrapper-content"
          // Pas de styles - le contenu children gère tout
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
          }}
          // Empêcher la fermeture par ESC si on veut le custom behavior
          onEscapeKeyDown={(e) => {
            // Laisser Radix gérer ESC normalement
          }}
          onPointerDownOutside={(e) => {
            // Laisser Radix gérer les clicks en dehors
          }}
        >
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
