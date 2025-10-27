/**
 * Adprovider
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import React from "react";
import { AdModal } from "./AdModal";
import { useAdSystem } from "@/lib/hooks/useAdSystem";

interface AdProviderProps {
  children: React.ReactNode;
  disabled?: boolean; // Ne pas montrer les pubs si true (modales ouvertes)
}

export const AdProvider: React.FC<AdProviderProps> = ({
  children,
  disabled = false,
}) => {
  const { showAd, currentAd, handleAdClose, handleAdClick } = useAdSystem();

  return (
    <>
      {children}
      {!disabled && showAd && currentAd && (
        <AdModal
          isOpen={showAd}
          onClose={handleAdClose}
          adData={currentAd}
          onAdClick={handleAdClick}
        />
      )}
    </>
  );
};
