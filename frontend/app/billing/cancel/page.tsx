"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "@/lib/languages/i18n";

export default function BillingCancelPage() {
  const { t } = useTranslation();
  const router = useRouter();

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
          {t("stripe.cancel.title")}
        </h1>

        {/* Message */}
        <p className="text-gray-600 mb-6">
          {t("stripe.cancel.message")}
        </p>

        {/* Informations */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <span className="text-blue-600 text-xl mr-3">ℹ️</span>
            <div className="text-sm text-left text-blue-900">
              <p className="font-medium mb-1">{t("stripe.cancel.youCanStill")}</p>
              <ul className="list-disc list-inside space-y-1 text-blue-800">
                <li>{t("stripe.cancel.continueEssential")}</li>
                <li>{t("stripe.cancel.retryLater")}</li>
                <li>{t("stripe.cancel.contactUs")}</li>
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
            {t("stripe.cancel.backToHome")}
          </button>
          <button
            onClick={() => router.back()}
            className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
          >
            {t("stripe.cancel.retry")}
          </button>
        </div>

        {/* Aide */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-500">
            {t("stripe.cancel.needHelp")}{" "}
            <a
              href="mailto:support@intelia.com"
              className="text-blue-600 hover:text-blue-700 underline"
            >
              {t("stripe.cancel.contactSupport")}
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
