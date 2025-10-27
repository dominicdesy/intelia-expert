/**
 * Countrypricingmanager
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { buildApiUrl } from "@/lib/api/config";
import { useTranslation } from "@/lib/languages/i18n";

interface CountryPricing {
  country_code: string;
  country_name: string;
  plan_name: string;
  display_price: number;
  display_currency: string;
  display_currency_symbol: string;
  tier_level: number;
  stripe_price_id: string;
  price_type: string; // 'auto_marketing' or 'custom'
}

interface CountryPricingManagerProps {
  accessToken: string;
}

export default function CountryPricingManager({
  accessToken,
}: CountryPricingManagerProps) {
  const { t } = useTranslation();
  const [countries, setCountries] = useState<CountryPricing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCountry, setSelectedCountry] = useState<string>("");
  const [selectedPlan, setSelectedPlan] = useState<string>("essential");
  const [editingPrice, setEditingPrice] = useState<string | null>(null);
  const [priceValue, setPriceValue] = useState<number>(0);
  const [currencyValue, setCurrencyValue] = useState<string>("USD");
  const [editingTier, setEditingTier] = useState<string | null>(null);
  const [tierValue, setTierValue] = useState<number>(1);
  const [showPlanMenu, setShowPlanMenu] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"name" | "tier">("name");

  const availableCurrencies = ["CAD", "USD", "EUR"];
  const availablePlans = ["essential", "pro", "elite"];

  useEffect(() => {
    fetchCountries();
  }, []);

  // Close plan menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      if (showPlanMenu) {
        setShowPlanMenu(null);
      }
    };

    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [showPlanMenu]);

  const fetchCountries = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(buildApiUrl("/billing/admin/countries"), {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error(t("admin.pricing.loadError"));
      }

      const data = await response.json();
      setCountries(data.countries || []);
    } catch (error) {
      console.error("[CountryPricingManager] Erreur fetch countries:", error);
      toast.error(t("admin.pricing.loadError"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdatePrice = async (countryCode: string, planName: string) => {
    try {
      const response = await fetch(
        buildApiUrl(`/billing/admin/countries/${countryCode}/pricing`),
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            plan_name: planName,
            price: priceValue,
            currency: currencyValue,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t("admin.pricing.updateError"));
      }

      const data = await response.json();
      toast.success(
        `Prix modifié pour ${countryCode}-${planName}: ${data.new_price} ${data.currency}`
      );

      setEditingPrice(null);
      await fetchCountries();
    } catch (error: any) {
      console.error("[CountryPricingManager] Erreur update price:", error);
      toast.error(error.message || t("admin.pricing.updateError"));
    }
  };

  const handleDeleteCountry = async (countryCode: string, countryName: string) => {
    if (!confirm(t("admin.pricing.deleteConfirm").replace("{country}", countryName).replace("{code}", countryCode))) {
      return;
    }

    try {
      const response = await fetch(
        buildApiUrl(`/billing/admin/countries/${countryCode}`),
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t("admin.pricing.deleteError"));
      }

      toast.success(t("admin.pricing.deleteSuccess").replace("{country}", countryName));
      await fetchCountries();
    } catch (error: any) {
      console.error("[CountryPricingManager] Erreur delete country:", error);
      toast.error(error.message || t("admin.pricing.deleteError"));
    }
  };

  const handleUpdateTier = async (countryCode: string) => {
    try {
      const response = await fetch(
        buildApiUrl(`/billing/admin/countries/${countryCode}/tier`),
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            tier_level: tierValue,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t("admin.pricing.updateError"));
      }

      const data = await response.json();
      toast.success(
        t("admin.pricing.tierUpdated").replace("{code}", countryCode).replace("{oldTier}", String(data.old_tier)).replace("{newTier}", String(data.new_tier))
      );

      setEditingTier(null);
      await fetchCountries();
    } catch (error: any) {
      console.error("[CountryPricingManager] Erreur update tier:", error);
      toast.error(error.message || t("admin.pricing.tierUpdateError"));
    }
  };

  // Filter countries by search term
  const filteredCountries = countries.filter(
    (c) =>
      c.country_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.country_code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Group by country for easier display
  const groupedByCountry = filteredCountries.reduce((acc, pricing) => {
    if (!acc[pricing.country_code]) {
      acc[pricing.country_code] = {
        country_code: pricing.country_code,
        country_name: pricing.country_name,
        tier_level: pricing.tier_level,
        plans: {},
      };
    }
    acc[pricing.country_code].plans[pricing.plan_name] = pricing;
    return acc;
  }, {} as Record<string, any>);

  const countryEntries = Object.values(groupedByCountry).sort((a: any, b: any) => {
    if (sortBy === "tier") {
      // Sort by tier first, then by name
      if (a.tier_level !== b.tier_level) {
        return a.tier_level - b.tier_level;
      }
      return a.country_name.localeCompare(b.country_name);
    }
    // Default: sort alphabetically by name
    return a.country_name.localeCompare(b.country_name);
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {t("admin.pricing.title")}
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              {t("admin.pricing.countriesConfigured").replace("{count}", String(countryEntries.length))}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center bg-white border border-gray-300 rounded-md overflow-hidden">
              <button
                onClick={() => setSortBy("name")}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  sortBy === "name"
                    ? "bg-blue-600 text-white"
                    : "bg-white text-gray-700 hover:bg-gray-100"
                }`}
              >
                A-Z
              </button>
              <button
                onClick={() => setSortBy("tier")}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  sortBy === "tier"
                    ? "bg-blue-600 text-white"
                    : "bg-white text-gray-700 hover:bg-gray-100"
                }`}
              >
                Tier
              </button>
            </div>
            <button
              onClick={fetchCountries}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              {t("admin.pricing.refresh")}
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder={t("admin.pricing.searchPlaceholder")}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <svg
            className="absolute left-3 top-2.5 h-5 w-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t("admin.pricing.country")}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t("admin.pricing.tier")}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Essential
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Pro
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Elite
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t("admin.plans.actions")}
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {countryEntries.map((country: any) => (
              <tr key={country.country_code} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <span className="text-2xl mr-2">
                      {String.fromCodePoint(
                        ...[...country.country_code.toUpperCase()].map(
                          (c) => 127397 + c.charCodeAt(0)
                        )
                      )}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {country.country_name}
                      </div>
                      <div className="text-xs text-gray-500">
                        {country.country_code}
                      </div>
                    </div>
                  </div>
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  {editingTier === country.country_code ? (
                    <div className="flex items-center gap-1">
                      <select
                        value={tierValue}
                        onChange={(e) => setTierValue(parseInt(e.target.value))}
                        className="px-2 py-1 border border-gray-300 rounded text-sm"
                        autoFocus
                      >
                        <option value={1}>{t("admin.pricing.tierLevel").replace("{level}", "1")}</option>
                        <option value={2}>{t("admin.pricing.tierLevel").replace("{level}", "2")}</option>
                        <option value={3}>{t("admin.pricing.tierLevel").replace("{level}", "3")}</option>
                        <option value={4}>{t("admin.pricing.tierLevel").replace("{level}", "4")}</option>
                      </select>
                      <button
                        onClick={() => handleUpdateTier(country.country_code)}
                        className="px-1.5 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => setEditingTier(null)}
                        className="px-1.5 py-1 bg-gray-400 text-white text-xs rounded hover:bg-gray-500"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <span
                      onClick={() => {
                        setEditingTier(country.country_code);
                        setTierValue(country.tier_level);
                      }}
                      className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full cursor-pointer hover:opacity-75 transition-opacity ${
                        country.tier_level === 1
                          ? "bg-green-100 text-green-800"
                          : country.tier_level === 2
                          ? "bg-blue-100 text-blue-800"
                          : country.tier_level === 3
                          ? "bg-purple-100 text-purple-800"
                          : "bg-orange-100 text-orange-800"
                      }`}
                    >
                      {t("admin.pricing.tierLevel").replace("{level}", String(country.tier_level))}
                    </span>
                  )}
                </td>

                {availablePlans.map((planName) => {
                  const pricing = country.plans[planName];
                  const editKey = `${country.country_code}-${planName}`;

                  return (
                    <td key={planName} className="px-6 py-4 whitespace-nowrap">
                      {editingPrice === editKey ? (
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            value={priceValue}
                            onChange={(e) =>
                              setPriceValue(parseFloat(e.target.value) || 0)
                            }
                            className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                            step="0.01"
                            min="0"
                            autoFocus
                          />
                          <select
                            value={currencyValue}
                            onChange={(e) => setCurrencyValue(e.target.value)}
                            className="px-2 py-1 border border-gray-300 rounded text-sm"
                          >
                            {availableCurrencies.map((curr) => (
                              <option key={curr} value={curr}>
                                {curr}
                              </option>
                            ))}
                          </select>
                          <button
                            onClick={() =>
                              handleUpdatePrice(country.country_code, planName)
                            }
                            className="px-1.5 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                          >
                            ✓
                          </button>
                          <button
                            onClick={() => setEditingPrice(null)}
                            className="px-1.5 py-1 bg-gray-400 text-white text-xs rounded hover:bg-gray-500"
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <span className="text-sm text-gray-900">
                            {pricing
                              ? `${pricing.display_currency_symbol}${pricing.display_price.toFixed(
                                  2
                                )} ${pricing.display_currency}`
                              : "Non configuré"}
                          </span>
                          {pricing && pricing.price_type === "auto_marketing" && (
                            <span
                              className="text-xs px-1 py-0.5 bg-blue-100 text-blue-700 rounded"
                              title={t("admin.pricing.marketingPriceTooltip")}
                            >
                              Auto
                            </span>
                          )}
                          {pricing && pricing.price_type === "custom" && (
                            <span
                              className="text-xs px-1 py-0.5 bg-purple-100 text-purple-700 rounded"
                              title={t("admin.pricing.customPriceTooltip")}
                            >
                              Custom
                            </span>
                          )}
                        </div>
                      )}
                    </td>
                  );
                })}

                <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                  {editingPrice?.startsWith(country.country_code) ||
                  editingTier === country.country_code ? null : (
                    <div className="flex items-center justify-end gap-2">
                      <div className="relative">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShowPlanMenu(
                              showPlanMenu === country.country_code
                                ? null
                                : country.country_code
                            );
                          }}
                          className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:border-blue-500 focus:ring-2 focus:ring-blue-500 cursor-pointer bg-white"
                        >
                          {t("admin.pricing.editButton")}
                        </button>
                        {showPlanMenu === country.country_code && (
                          <div className="absolute right-0 mt-1 w-32 bg-white border border-gray-300 rounded-md shadow-lg z-10">
                            {availablePlans.map((plan) => (
                              <button
                                key={plan}
                                onClick={() => {
                                  const pricing = country.plans[plan];
                                  const editKey = `${country.country_code}-${plan}`;
                                  setEditingPrice(editKey);
                                  setPriceValue(pricing?.display_price || 0);
                                  setCurrencyValue(pricing?.display_currency || "USD");
                                  setShowPlanMenu(null);
                                }}
                                className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 transition-colors"
                              >
                                {plan.charAt(0).toUpperCase() + plan.slice(1)}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() =>
                          handleDeleteCountry(
                            country.country_code,
                            country.country_name
                          )
                        }
                        className="px-2 py-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
                        title={t("admin.pricing.deleteButton")}
                      >
                        🗑️
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {countryEntries.length === 0 && (
        <div className="px-6 py-12 text-center text-gray-500">
          {searchTerm
            ? t("admin.pricing.noCountriesFound").replace("{search}", searchTerm)
            : t("admin.pricing.noCountries")}
        </div>
      )}

      {/* Legend */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-4 text-xs text-gray-600">
            <div className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-full bg-green-100 border border-green-300"></span>
              {t("admin.pricing.tier1")}
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-full bg-blue-100 border border-blue-300"></span>
              {t("admin.pricing.tier2")}
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-full bg-purple-100 border border-purple-300"></span>
              {t("admin.pricing.tier3")}
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-full bg-orange-100 border border-orange-300"></span>
              {t("admin.pricing.tier4")}
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-600">
            <div className="flex items-center gap-1">
              <span className="px-1 py-0.5 bg-blue-100 text-blue-700 rounded">Auto</span>
              <span>{t("admin.pricing.marketingPrice")}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="px-1 py-0.5 bg-purple-100 text-purple-700 rounded">Custom</span>
              <span>{t("admin.pricing.customPrice")}</span>
            </div>
          </div>
        </div>
        <div className="text-xs text-gray-600 bg-blue-50 border border-blue-200 rounded p-2">
          <strong>Calcul automatique:</strong> Les prix "Auto" sont calculés depuis les prix tier (Gestion des plans)
          + conversion devise + ajustement marketing (ex: 20.34 → 19.99).
          {t("admin.pricing.customizeNote")}
        </div>
      </div>
    </div>
  );
}
