"use client";

import React, { useState, useEffect } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { apiClient } from "@/lib/api/client";
import toast from "react-hot-toast";

interface CurrencyInfo {
  billing_currency: string | null;
  is_set: boolean;
  suggested_currency: string;
  detected_country: string;
  available_currencies: string[];
  currency_names: Record<string, string>;
}

interface CurrencySelectorProps {
  user: any;
}

export const CurrencySelector: React.FC<CurrencySelectorProps> = ({ user }) => {
  const { t } = useTranslation();
  const [currencyInfo, setCurrencyInfo] = useState<CurrencyInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isChanging, setIsChanging] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    fetchCurrencyPreference();
  }, []);

  const fetchCurrencyPreference = async () => {
    try {
      console.log("[CurrencySelector] Fetching currency preference...");

      const response = await apiClient.getSecure<CurrencyInfo>("billing/currency-preference");

      console.log("[CurrencySelector] API response:", response);

      if (response.success && response.data) {
        console.log("[CurrencySelector] Currency data received:", response.data);
        setCurrencyInfo(response.data);
      } else {
        console.error("[CurrencySelector] API error:", response.error);
        toast.error(response.error?.message || "Erreur de chargement des devises");
      }
    } catch (error) {
      console.error("[CurrencySelector] Error fetching currency:", error);
      toast.error("Erreur de chargement des devises");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCurrencyChange = async (currency: string) => {
    setIsChanging(true);
    try {
      console.log("[CurrencySelector] Updating currency to:", currency);

      // FastAPI expects currency as query parameter, not JSON body
      const response = await apiClient.postSecure(`billing/set-currency?currency=${currency}`);

      console.log("[CurrencySelector] Update response:", response);

      if (response.success) {
        toast.success(t("billing.currencyUpdated"));
        await fetchCurrencyPreference();
        setIsDropdownOpen(false);
      } else {
        console.error("[CurrencySelector] Update error:", response.error);
        const errorMsg = typeof response.error?.message === 'string'
          ? response.error.message
          : t("billing.currencyUpdateFailed");
        toast.error(errorMsg);
      }
    } catch (error) {
      console.error("[CurrencySelector] Error updating currency:", error);
      toast.error(t("billing.currencyUpdateFailed"));
    } finally {
      setIsChanging(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex items-center">
          <svg
            className="animate-spin h-5 w-5 text-gray-400 mr-3"
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
          <span className="text-sm text-gray-600">
            {t("billing.loadingCurrency")}
          </span>
        </div>
      </div>
    );
  }

  if (!currencyInfo) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div className="flex items-center">
          <svg
            className="w-5 h-5 text-red-600 mr-3"
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
          <div>
            <p className="text-sm font-medium text-red-900">
              Erreur de chargement des devises
            </p>
            <p className="text-xs text-red-700 mt-1">
              Vérifiez la console (F12) pour plus de détails
            </p>
          </div>
        </div>
      </div>
    );
  }

  const currentCurrency = currencyInfo.billing_currency || currencyInfo.suggested_currency;
  const currentCurrencyName = currencyInfo.currency_names[currentCurrency];

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center mb-2">
            <svg
              className="w-5 h-5 text-blue-600 mr-2"
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
            <h3 className="text-sm font-semibold text-blue-900">
              {t("billing.billingCurrency")}
            </h3>
          </div>

          <p className="text-sm text-blue-800 mb-1">
            {currencyInfo.is_set ? (
              <span>
                <span className="font-medium">{t("billing.current")}:</span>{" "}
                {currentCurrencyName}
              </span>
            ) : (
              <span>
                <span className="font-medium">{t("billing.suggested")}:</span>{" "}
                {currentCurrencyName}
                <span className="text-blue-600 text-xs ml-2">
                  ({t("billing.notSetYet")})
                </span>
              </span>
            )}
          </p>

          {!currencyInfo.is_set && (
            <p className="text-xs text-blue-700 mt-1">
              {t("billing.currencyRequiredForUpgrade")}
            </p>
          )}
        </div>

        <div className="relative ml-4">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            disabled={isChanging}
            className="px-3 py-2 bg-white border border-blue-300 rounded-lg text-sm font-medium text-blue-700 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {isChanging ? (
              <>
                <svg
                  className="animate-spin h-4 w-4 mr-2"
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
                {t("common.loading")}
              </>
            ) : (
              <>
                {t("billing.changeCurrency")}
                <svg
                  className={`w-4 h-4 ml-2 transition-transform ${
                    isDropdownOpen ? "rotate-180" : ""
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </>
            )}
          </button>

          {isDropdownOpen && (
            <>
              {/* Backdrop pour fermer le dropdown */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setIsDropdownOpen(false)}
              />

              {/* Dropdown Menu */}
              <div className="absolute right-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-20 max-h-96 overflow-y-auto">
                <div className="p-2">
                  <div className="text-xs text-gray-500 px-3 py-2 font-medium">
                    {t("billing.selectCurrency")}
                  </div>

                  {currencyInfo.available_currencies.map((currency) => {
                    const isSelected = currency === currentCurrency;
                    const isSuggested = currency === currencyInfo.suggested_currency;

                    return (
                      <button
                        key={currency}
                        onClick={() => handleCurrencyChange(currency)}
                        className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                          isSelected
                            ? "bg-blue-100 text-blue-900 font-medium"
                            : "text-gray-700 hover:bg-gray-100"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span>{currencyInfo.currency_names[currency]}</span>
                          <div className="flex items-center">
                            {isSuggested && !isSelected && (
                              <span className="text-xs text-blue-600 mr-2">
                                {t("billing.suggested")}
                              </span>
                            )}
                            {isSelected && (
                              <svg
                                className="w-4 h-4 text-blue-600"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
