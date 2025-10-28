/**
 * Billing Currency Selection Page
 * Version: 1.0.0
 * Last modified: 2025-10-28
 *
 * Dedicated page for selecting billing currency before subscription upgrade
 */
"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslation } from "@/lib/languages/i18n";
import { apiClient } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import toast from "react-hot-toast";

interface CurrencyInfo {
  billing_currency: string | null;
  is_set: boolean;
  suggested_currency: string;
  detected_country: string;
  available_currencies: string[];
  currency_names: Record<string, string>;
}

export default function BillingCurrencyPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isAuthenticated } = useAuthStore();

  const [currencyInfo, setCurrencyInfo] = useState<CurrencyInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectedCurrency, setSelectedCurrency] = useState<string | null>(null);

  // Redirect destination after currency selection
  const redirectTo = searchParams?.get("redirect") || "/chat";
  const planToUpgrade = searchParams?.get("plan");

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/");
      return;
    }

    fetchCurrencyPreference();
  }, [isAuthenticated]);

  const fetchCurrencyPreference = async () => {
    try {
      const response = await apiClient.getSecure<CurrencyInfo>("billing/currency-preference");

      if (response.success && response.data) {
        setCurrencyInfo(response.data);

        // If currency is already set, redirect
        if (response.data.is_set && !planToUpgrade) {
          toast.success(t("billing.currencyAlreadySet"));
          setTimeout(() => router.push(redirectTo), 1500);
        }
      } else {
        toast.error(response.error?.message || t("billing.errorLoadingCurrency"));
      }
    } catch (error) {
      console.error("[BillingCurrency] Error fetching currency:", error);
      toast.error(t("billing.errorLoadingCurrency"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleCurrencySelect = async (currency: string) => {
    setIsSelecting(true);
    setSelectedCurrency(currency);

    try {
      const response = await apiClient.postSecure(`billing/set-currency?currency=${currency}`);

      if (response.success) {
        toast.success(t("billing.currencyUpdated"));

        // Redirect after successful selection
        setTimeout(() => {
          if (planToUpgrade) {
            // If coming from upgrade flow, return to chat with plan parameter
            router.push(`${redirectTo}?upgrade=${planToUpgrade}`);
          } else {
            router.push(redirectTo);
          }
        }, 1500);
      } else {
        const errorMsg = typeof response.error?.message === 'string'
          ? response.error.message
          : t("billing.currencyUpdateFailed");
        toast.error(errorMsg);
        setIsSelecting(false);
        setSelectedCurrency(null);
      }
    } catch (error) {
      console.error("[BillingCurrency] Error updating currency:", error);
      toast.error(t("billing.currencyUpdateFailed"));
      setIsSelecting(false);
      setSelectedCurrency(null);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full mx-4">
          <div className="flex flex-col items-center">
            <svg
              className="animate-spin h-12 w-12 text-blue-600 mb-4"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <p className="text-gray-600 text-lg">{t("billing.loadingCurrency")}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!currencyInfo) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="bg-red-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-red-600"
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
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {t("billing.errorTitle")}
            </h2>
            <p className="text-gray-600 mb-6">
              {t("billing.errorLoadingCurrency")}
            </p>
            <button
              onClick={() => router.push(redirectTo)}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t("common.goBack")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const suggestedCurrency = currencyInfo.suggested_currency;
  const currentCurrency = currencyInfo.billing_currency;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          <div className="text-center mb-6">
            <div className="bg-blue-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {t("billing.selectYourCurrency")}
            </h1>
            <p className="text-gray-600">
              {planToUpgrade
                ? t("billing.currencyRequiredForUpgrade")
                : t("billing.currencyDescription")}
            </p>
          </div>

          {/* Current/Suggested Currency Info */}
          {(currentCurrency || suggestedCurrency) && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <div className="flex items-start">
                <svg
                  className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
                <div>
                  <p className="text-sm font-medium text-blue-900">
                    {currencyInfo.is_set ? (
                      <>
                        {t("billing.currentCurrency")}: <span className="font-bold">{currencyInfo.currency_names[currentCurrency!]}</span>
                      </>
                    ) : (
                      <>
                        {t("billing.suggestedBasedOnLocation")}: <span className="font-bold">{currencyInfo.currency_names[suggestedCurrency]}</span>
                        <span className="text-xs ml-2">({currencyInfo.detected_country})</span>
                      </>
                    )}
                  </p>
                  {!currencyInfo.is_set && (
                    <p className="text-xs text-blue-700 mt-1">
                      {t("billing.canSelectDifferent")}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Currency Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {currencyInfo.available_currencies.map((currency) => {
            const isSuggested = currency === suggestedCurrency;
            const isCurrent = currency === currentCurrency;
            const isSelected = selectedCurrency === currency;
            const isDisabled = isSelecting && !isSelected;

            return (
              <button
                key={currency}
                onClick={() => handleCurrencySelect(currency)}
                disabled={isSelecting}
                className={`
                  relative bg-white rounded-xl p-6 text-left transition-all
                  ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-1 hover:shadow-lg cursor-pointer'}
                  ${isCurrent ? 'ring-2 ring-green-500 shadow-lg' : 'shadow-md'}
                  ${isSuggested && !isCurrent ? 'ring-2 ring-blue-400' : ''}
                  ${isSelected ? 'ring-2 ring-blue-600 shadow-xl' : ''}
                `}
              >
                {/* Badge */}
                {(isSuggested || isCurrent) && (
                  <div className="absolute -top-2 -right-2">
                    <span
                      className={`
                        inline-block px-2 py-1 rounded-full text-xs font-semibold text-white shadow
                        ${isCurrent ? 'bg-green-500' : 'bg-blue-500'}
                      `}
                    >
                      {isCurrent ? t("billing.current") : t("billing.suggested")}
                    </span>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="text-2xl font-bold text-gray-900 mb-1">
                      {currency}
                    </div>
                    <div className="text-sm text-gray-600">
                      {currencyInfo.currency_names[currency]}
                    </div>
                  </div>

                  {isSelected && isSelecting && (
                    <svg
                      className="animate-spin h-6 w-6 text-blue-600"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                  )}

                  {isCurrent && !isSelecting && (
                    <svg
                      className="w-6 h-6 text-green-600"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <button
            onClick={() => router.push(redirectTo)}
            className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium"
          >
            ← {t("common.goBack")}
          </button>
        </div>
      </div>
    </div>
  );
}
