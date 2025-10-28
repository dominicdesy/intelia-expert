/**
 * PWAManager Component - Manages PWA Registration and Install Prompts
 * Version: 1.2.0
 * Last modified: 2025-10-28
 * Changes: Added showInstallPrompts prop to control visibility of install prompts
 */

"use client";

import { useEffect } from "react";
import InstallPrompt from "./InstallPrompt";
import IOSInstallBanner from "./IOSInstallBanner";

interface PWAManagerProps {
  showInstallPrompts?: boolean; // Control whether to show install prompts
}

export default function PWAManager({ showInstallPrompts = false }: PWAManagerProps) {
  useEffect(() => {
    // Register service worker (always registered, independent of prompts)
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js")
        .then((registration) => {
          console.log("Service Worker registered:", registration.scope);

          // Check for updates periodically
          setInterval(() => {
            registration.update();
          }, 60 * 60 * 1000); // Check every hour
        })
        .catch((error) => {
          console.error("Service Worker registration failed:", error);
        });
    }
  }, []);

  // Only show install prompts if explicitly enabled
  if (!showInstallPrompts) {
    return null;
  }

  return (
    <>
      {/* Android/Desktop install prompt */}
      <InstallPrompt />

      {/* iOS Safari install banner */}
      <IOSInstallBanner />
    </>
  );
}
