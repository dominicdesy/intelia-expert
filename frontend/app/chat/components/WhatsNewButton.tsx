/**
 * WhatsNewButton
 * Version: 3.0.0
 * Last modified: 2025-10-30
 * Headway What's New integration - Simplified approach based on working examples
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

    // Skip if already initialized
    if ((window as any).headwayInitialized) {
      console.log('[Headway] Already initialized');
      return;
    }

    console.log('[Headway] Loading script...');

    const script = document.createElement('script');
    script.src = 'https://cdn.headwayapp.co/widget.js';
    script.async = true;

    script.onload = () => {
      console.log('[Headway] Script loaded, calling init...');

      // Wait a bit for Headway to be available
      setTimeout(() => {
        if ((window as any).Headway) {
          console.log('[Headway] Headway object found, initializing...');

          try {
            const result = (window as any).Headway.init({
              selector: '#headway-badge',
              trigger: '#headway-trigger-button',
              account: 'JVoZPy',
              callbacks: {
                onWidgetReady: (widget: any) => {
                  console.log('[Headway] Widget ready!', widget);
                  console.log('[Headway] Unseen count:', widget?.getUnseenCount?.());
                },
                onShowWidget: () => {
                  console.log('[Headway] Widget shown!');
                  if (onClick) onClick();
                },
                onReadMore: () => {
                  console.log('[Headway] Read more clicked');
                },
                onHideWidget: () => {
                  console.log('[Headway] Widget hidden');
                }
              }
            });
            console.log('[Headway] Init result:', result);
            (window as any).headwayInitialized = true;
          } catch (error) {
            console.error('[Headway] Init error:', error);
          }
        } else {
          console.error('[Headway] Headway object not found after script load');
        }
      }, 100);
    };

    script.onerror = () => {
      console.error('[Headway] Failed to load script');
    };

    document.head.appendChild(script);

    return () => {
      // Cleanup on unmount
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };
  }, [onClick]);

  return (
    <div className="relative">
      {/* Hidden badge container for Headway */}
      <div id="headway-badge" className="hidden" />

      {/* Custom trigger button */}
      <button
        id="headway-trigger-button"
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
    </div>
  );
}
