/**
 * WhatsNewButton
 * Version: 2.0.0
 * Last modified: 2025-10-30
 * Headway What's New integration
 */
"use client";

import React, { useEffect } from "react";
import { useTranslation } from "@/lib/languages/i18n";

interface WhatsNewButtonProps {
  onClick?: () => void;
}

export function WhatsNewButton({ onClick }: WhatsNewButtonProps) {
  const { t } = useTranslation();

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const config = {
      selector: "#headway-widget-trigger",
      account: "JVoZPy",
      callbacks: {
        onWidgetReady: (widget: any) => {
          console.log('[Headway] Widget ready', widget);
        },
        onShowWidget: () => {
          console.log('[Headway] Widget shown');
          if (onClick) {
            onClick();
          }
        }
      }
    };

    // Check if Headway is already loaded
    if ((window as any).Headway) {
      // Headway is already loaded, just reinitialize
      console.log('[Headway] Reinitializing widget');
      (window as any).Headway.init(config);
    } else {
      // Load Headway SDK for the first time
      (window as any).HW_config = config;

      const script = document.createElement('script');
      script.src = 'https://cdn.headwayapp.co/widget.js';
      script.async = true;
      script.onload = () => {
        console.log('[Headway] Script loaded');
        // For SPAs, explicitly call init after script loads
        if ((window as any).Headway) {
          (window as any).Headway.init(config);
        }
      };
      document.body.appendChild(script);
    }

    // Cleanup: destroy widget instance on unmount
    return () => {
      if ((window as any).Headway) {
        console.log('[Headway] Cleaning up widget');
      }
    };
  }, [onClick]);

  return (
    <button
      id="headway-widget-trigger"
      type="button"
      className="w-10 h-10 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors flex items-center justify-center border border-gray-200 hover:border-blue-300"
      title={t("whatsNew.buttonTitle")}
      aria-label={t("whatsNew.buttonTitle")}
    >
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"
        />
      </svg>
    </button>
  );
}
