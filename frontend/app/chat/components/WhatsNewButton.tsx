/**
 * WhatsNewButton
 * Version: 4.0.0
 * Last modified: 2025-10-30
 * Headway What's New integration - With notification badge and custom positioning
 */
"use client";

import React, { useEffect, useState } from "react";
import { useTranslation } from "@/lib/languages/i18n";

interface WhatsNewButtonProps {
  onClick?: () => void;
}

export function WhatsNewButton({ onClick }: WhatsNewButtonProps) {
  const { t } = useTranslation();
  const [unseenCount, setUnseenCount] = useState<number>(0);

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
                  const count = widget?.getUnseenCount?.() || 0;
                  console.log('[Headway] Unseen count:', count);
                  setUnseenCount(count);
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
                  // Refresh unseen count after widget is closed
                  if ((window as any).Headway) {
                    const count = (window as any).Headway.getUnseenCount?.() || 0;
                    setUnseenCount(count);
                  }
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
      {/*
        Badge container for Headway - positioned absolutely to overlay the button
        The widget popover anchors to this badge, not the trigger button
      */}
      <div
        id="headway-badge"
        className="absolute top-0 left-0 w-full h-full pointer-events-none z-10"
        style={{ opacity: 0 }}
      />

      {/* Custom trigger button */}
      <button
        id="headway-trigger-button"
        type="button"
        className="w-10 h-10 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors flex items-center justify-center border border-gray-200 hover:border-blue-300 relative"
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

        {/* Notification badge */}
        {unseenCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex items-center justify-center rounded-full h-5 w-5 bg-red-500 text-white text-xs font-bold">
              {unseenCount > 9 ? '9+' : unseenCount}
            </span>
          </span>
        )}
      </button>
    </div>
  );
}
