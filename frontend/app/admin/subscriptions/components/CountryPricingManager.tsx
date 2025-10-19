"use client";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { buildApiUrl } from "@/lib/api/config";

interface CountryPricing {
  country_code: string;
  country_name: string;
  plan_name: string;
  display_price: number;
  display_currency: string;
  display_currency_symbol: string;
  tier_level: number;
  stripe_price_id: string;
}

interface CountryPricingManagerProps {
  accessToken: string;
}

export default function CountryPricingManager({
  accessToken,
}: CountryPricingManagerProps) {
  const [countries, setCountries] = useState<CountryPricing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCountry, setSelectedCountry] = useState<string>("");
  const [selectedPlan, setSelectedPlan] = useState<string>("essential");
  const [editingPrice, setEditingPrice] = useState<string | null>(null);
  const [priceValue, setPriceValue] = useState<number>(0);
  const [currencyValue, setCurrencyValue] = useState<string>("USD");

  const availableCurrencies = ["CAD", "USD", "EUR"];
  const availablePlans = ["essential", "pro", "elite"];

  useEffect(() => {
    fetchCountries();
  }, []);

  const fetchCountries = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(buildApiUrl("/billing/admin/countries"), {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Erreur lors du chargement des pays");
      }

      const data = await response.json();
      setCountries(data.countries || []);
    } catch (error) {
      console.error("[CountryPricingManager] Erreur fetch countries:", error);
      toast.error("Erreur lors du chargement des pays");
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
        throw new Error(errorData.detail || "Erreur lors de la mise à jour");
      }

      const data = await response.json();
      toast.success(
        `Prix modifié pour ${countryCode}-${planName}: ${data.new_price} ${data.currency}`
      );

      setEditingPrice(null);
      await fetchCountries();
    } catch (error: any) {
      console.error("[CountryPricingManager] Erreur update price:", error);
      toast.error(error.message || "Erreur lors de la mise à jour du prix");
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

  const countryEntries = Object.values(groupedByCountry).sort((a: any, b: any) =>
    a.country_name.localeCompare(b.country_name)
  );

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
              Gestion des Prix par Pays
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              {countryEntries.length} pays configurés • Devises: CAD, USD, EUR
            </p>
          </div>
          <button
            onClick={fetchCountries}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            🔄 Actualiser
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Rechercher un pays (ex: Canada, FR)..."
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
                Pays
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tier
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
                Actions
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
                  <span
                    className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      country.tier_level === 1
                        ? "bg-green-100 text-green-800"
                        : country.tier_level === 2
                        ? "bg-blue-100 text-blue-800"
                        : country.tier_level === 3
                        ? "bg-purple-100 text-purple-800"
                        : "bg-orange-100 text-orange-800"
                    }`}
                  >
                    Tier {country.tier_level}
                  </span>
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
                        <span className="text-sm text-gray-900">
                          {pricing
                            ? `${pricing.display_currency_symbol}${pricing.display_price.toFixed(
                                2
                              )} ${pricing.display_currency}`
                            : "Non configuré"}
                        </span>
                      )}
                    </td>
                  );
                })}

                <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                  {editingPrice?.startsWith(country.country_code) ? null : (
                    <select
                      onChange={(e) => {
                        const planName = e.target.value;
                        if (planName) {
                          const pricing = country.plans[planName];
                          const editKey = `${country.country_code}-${planName}`;
                          setEditingPrice(editKey);
                          setPriceValue(
                            pricing?.display_price || 0
                          );
                          setCurrencyValue(
                            pricing?.display_currency || "USD"
                          );
                        }
                      }}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:border-blue-500 focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer"
                      defaultValue=""
                    >
                      <option value="">✏️  Modifier...</option>
                      {availablePlans.map((plan) => (
                        <option key={plan} value={plan}>
                          {plan.charAt(0).toUpperCase() + plan.slice(1)}
                        </option>
                      ))}
                    </select>
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
            ? `Aucun pays trouvé pour "${searchTerm}"`
            : "Aucun pays configuré"}
        </div>
      )}

      {/* Legend */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center gap-4 text-xs text-gray-600">
          <div className="flex items-center gap-2">
            <span className="inline-block w-3 h-3 rounded-full bg-green-100 border border-green-300"></span>
            Tier 1 (Marchés émergents)
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-3 h-3 rounded-full bg-blue-100 border border-blue-300"></span>
            Tier 2 (Intermédiaire)
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-3 h-3 rounded-full bg-purple-100 border border-purple-300"></span>
            Tier 3 (Développés)
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-3 h-3 rounded-full bg-orange-100 border border-orange-300"></span>
            Tier 4 (Premium)
          </div>
        </div>
      </div>
    </div>
  );
}
