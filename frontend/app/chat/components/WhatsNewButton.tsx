/**
 * WhatsNewButton
 * Version: 1.0.0
 * Last modified: 2025-10-29
 * Canny What's New integration
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
    // Load Canny SDK script
    if (typeof window !== 'undefined' && !(window as any).Canny) {
      const script = document.createElement('script');
      script.src = 'https://canny.io/sdk.js';
      script.async = true;
      document.body.appendChild(script);

      return () => {
        // Cleanup script on unmount
        if (script.parentNode) {
          script.parentNode.removeChild(script);
        }
      };
    }
  }, []);

  const handleClick = () => {
    // Call optional parent onClick
    if (onClick) {
      onClick();
    }

    // Open Canny changelog
    if (typeof window !== 'undefined' && (window as any).Canny) {
      const cannyConfig: any = {
        position: 'bottom',
        align: 'right',
      };

      // Use APP ID if available, otherwise use subdomain
      if (process.env.NEXT_PUBLIC_CANNY_APP_ID) {
        cannyConfig.appID = process.env.NEXT_PUBLIC_CANNY_APP_ID;
      } else {
        cannyConfig.subdomain = 'intelia';
      }

      (window as any).Canny('initChangelog', cannyConfig);
    } else {
      console.warn('[WhatsNew] Canny SDK not loaded yet');
    }
  };

  return (
    <button
      onClick={handleClick}
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
