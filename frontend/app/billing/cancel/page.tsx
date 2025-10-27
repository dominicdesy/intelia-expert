/**
 * Page
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "@/lib/languages/i18n";

export default function BillingCancelPage() {
  const { t, currentLanguage } = useTranslation();
  const router = useRouter();

  // Helper pour accéder aux traductions non-typées
  const tUnsafe = (key: string): string => {
    try {
      return (t as any)(key) || key;
    } catch {
      return key;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-xl p-8 text-center">
        {/* Icône */}
        <div className="mb-6">
          <div className="mx-auto w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center">
            <svg
              className="w-12 h-12 text-yellow-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
        </div>

        {/* Titre */}
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          {tUnsafe("stripe.billing.cancel.title")}
        </h1>

        {/* Message */}
        <p className="text-gray-600 mb-6">
          {tUnsafe("stripe.billing.cancel.message")}
        </p>

        {/* Informations */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <span className="text-blue-600 text-xl mr-3">ℹ️</span>
            <div className="text-sm text-left text-blue-900">
              <p className="font-medium mb-1">{tUnsafe("stripe.billing.cancel.canStill")}</p>
              <ul className="list-disc list-inside space-y-1 text-blue-800">
                <li>{tUnsafe("stripe.billing.cancel.continueEssential")}</li>
                <li>{tUnsafe("stripe.billing.cancel.retryLater")}</li>
                <li>{tUnsafe("stripe.billing.cancel.contactUs")}</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Boutons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => router.push("/chat")}
            className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
          >
            {tUnsafe("stripe.billing.cancel.backToHome")}
          </button>
          <button
            onClick={() => router.back()}
            className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
          >
            {tUnsafe("stripe.billing.cancel.retry")}
          </button>
        </div>

        {/* Aide */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-500">
            {tUnsafe("stripe.billing.cancel.needHelp")}{" "}
            <a
              href="mailto:cognito@intelia.com"
              className="text-blue-600 hover:text-blue-700 underline"
            >
              {tUnsafe("stripe.billing.cancel.contactSupport")}
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
