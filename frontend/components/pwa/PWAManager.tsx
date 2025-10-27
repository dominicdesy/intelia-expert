/**
 * PWAManager Component - Manages PWA Registration and Install Prompts
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */

"use client";

import { useEffect } from "react";
import InstallPrompt from "./InstallPrompt";
import IOSInstallBanner from "./IOSInstallBanner";

export default function PWAManager() {
  useEffect(() => {
    // Register service worker
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

  return (
    <>
      {/* Android/Desktop install prompt */}
      <InstallPrompt />

      {/* iOS Safari install banner */}
      <IOSInstallBanner />
    </>
  );
}
