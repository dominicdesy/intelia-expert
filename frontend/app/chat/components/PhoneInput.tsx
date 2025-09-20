import React, { useMemo } from "react";
import { useTranslation } from "@/lib/languages/i18n";

interface PhoneInputProps {
  countryCode: string;
  areaCode: string;
  phoneNumber: string;
  onChange: (data: {
    country_code: string;
    area_code: string;
    phone_number: string;
  }) => void;
  // Nouvelles props pour recevoir les données des pays depuis UserInfoModal
  countries?: Array<{
    value: string;
    label: string;
    phoneCode: string;
    flag?: string;
  }>;
  countriesLoading?: boolean;
  usingFallback?: boolean;
}

interface PhoneCode {
  code: string;
  country: string;
  flag?: string;
  priority?: number;
}

// Codes de secours avec priorité (inchangé)
const fallbackPhoneCodes: PhoneCode[] = [
  { code: "+1", country: "Canada/États-Unis", flag: "🇨🇦🇺🇸", priority: 1 },
  { code: "+33", country: "France", flag: "🇫🇷", priority: 2 },
  { code: "+32", country: "Belgique", flag: "🇧🇪", priority: 3 },
  { code: "+41", country: "Suisse", flag: "🇨🇭", priority: 4 },
  { code: "+49", country: "Allemagne", flag: "🇩🇪", priority: 5 },
  { code: "+44", country: "Royaume-Uni", flag: "🇬🇧", priority: 6 },
  { code: "+39", country: "Italie", flag: "🇮🇹", priority: 7 },
  { code: "+34", country: "Espagne", flag: "🇪🇸", priority: 8 },
  { code: "+31", country: "Pays-Bas", flag: "🇳🇱", priority: 9 },
  { code: "+46", country: "Suède", flag: "🇸🇪", priority: 10 },
  { code: "+47", country: "Norvège", flag: "🇳🇴", priority: 11 },
  { code: "+45", country: "Danemark", flag: "🇩🇰", priority: 12 },
  { code: "+358", country: "Finlande", flag: "🇫🇮", priority: 13 },
  { code: "+52", country: "Mexique", flag: "🇲🇽", priority: 14 },
  { code: "+55", country: "Brésil", flag: "🇧🇷", priority: 15 },
  { code: "+61", country: "Australie", flag: "🇦🇺", priority: 16 },
  { code: "+81", country: "Japon", flag: "🇯🇵", priority: 17 },
  { code: "+86", country: "Chine", flag: "🇨🇳", priority: 18 },
  { code: "+91", country: "Inde", flag: "🇮🇳", priority: 19 },
  { code: "+7", country: "Russie", flag: "🇷🇺", priority: 20 },
];

export const PhoneInput: React.FC<PhoneInputProps> = ({
  countryCode,
  areaCode,
  phoneNumber,
  onChange,
  countries = [],
  countriesLoading = false,
  usingFallback = true,
}) => {
  const { t } = useTranslation();

  // Convertir les données countries en phoneCodes
  const phoneCodes = useMemo(() => {
    if (countries.length === 0 || usingFallback) {
      return fallbackPhoneCodes;
    }

    // Transformer les données countries en phoneCodes
    const transformed = countries
      .filter((country) => country.phoneCode && country.phoneCode !== "+")
      .reduce((acc: PhoneCode[], current) => {
        const existing = acc.find((item) => item.code === current.phoneCode);
        if (existing) {
          // Si plusieurs pays ont le même code, les combiner
          if (!existing.country.includes(current.label)) {
            existing.country += `, ${current.label}`;
          }
        } else {
          acc.push({
            code: current.phoneCode,
            country: current.label,
            flag: current.flag,
          });
        }
        return acc;
      }, [])
      .sort((a: PhoneCode, b: PhoneCode) => {
        // Priorité aux codes les plus courants
        const priorityA =
          fallbackPhoneCodes.find((f) => f.code === a.code)?.priority || 999;
        const priorityB =
          fallbackPhoneCodes.find((f) => f.code === b.code)?.priority || 999;

        if (priorityA !== priorityB) {
          return priorityA - priorityB;
        }

        // Puis tri alphabétique par pays
        return a.country.localeCompare(b.country);
      });

    return transformed.length > 50 ? transformed : fallbackPhoneCodes;
  }, [countries, usingFallback]);

  const handleChange = (
    field: "country" | "area" | "number",
    value: string,
  ) => {
    onChange({
      country_code: field === "country" ? value : countryCode,
      area_code: field === "area" ? value : areaCode,
      phone_number: field === "number" ? value : phoneNumber,
    });
  };

  // IDs uniques pour les labels - FIX MICROSOFT EDGE
  const componentId = useMemo(
    () => `phone-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    [],
  );
  const countryId = `${componentId}-country`;
  const areaId = `${componentId}-area`;
  const numberId = `${componentId}-number`;

  return (
    <div>
      {/* Avertissement si utilisation de la liste de secours */}
      {usingFallback && !countriesLoading && (
        <div className="mb-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
          <div className="flex items-center space-x-1">
            <svg
              className="w-3 h-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
            <span>{t("phone.limitedList")}</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-12 gap-3 items-end">
        {/* Code pays */}
        <div className="col-span-4">
          <label
            htmlFor={countryId}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {t("phone.countryCode")}
          </label>
          <select
            id={countryId}
            name="countryCode"
            value={countryCode}
            onChange={(e) => handleChange("country", e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm bg-white h-10"
            aria-describedby={`${countryId}-help`}
            disabled={countriesLoading}
          >
            <option value="">
              {countriesLoading ? t("phone.loading") : t("phone.select")}
            </option>
            {phoneCodes.map(({ code, country, flag }) => (
              <option key={code} value={code}>
                {flag ? `${flag} ` : ""}
                {code} {country}
              </option>
            ))}
          </select>
          <div id={`${countryId}-help`} className="sr-only">
            {t("phone.countryCodeHelp")}
          </div>
          {countriesLoading && (
            <div className="mt-1 text-xs text-gray-500">
              {t("phone.loadingCodes")}
            </div>
          )}
        </div>

        {/* Code régional */}
        <div className="col-span-3">
          <label
            htmlFor={areaId}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {t("phone.areaCode")}
          </label>
          <input
            type="text"
            id={areaId}
            name="areaCode"
            value={areaCode}
            onChange={(e) =>
              handleChange("area", e.target.value.replace(/\D/g, ""))
            }
            placeholder={t("phone.areaCodePlaceholder")}
            disabled={!countryCode}
            maxLength={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:text-gray-500 h-10"
            aria-describedby={`${areaId}-help`}
          />
          <div id={`${areaId}-help`} className="sr-only">
            {t("phone.areaCodeHelp")}
          </div>
        </div>

        {/* Numéro principal */}
        <div className="col-span-5">
          <label
            htmlFor={numberId}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {t("phone.phoneNumber")}
          </label>
          <input
            type="tel"
            id={numberId}
            name="phoneNumber"
            value={phoneNumber}
            onChange={(e) =>
              handleChange("number", e.target.value.replace(/\D/g, ""))
            }
            placeholder={t("phone.phoneNumberPlaceholder")}
            disabled={!countryCode}
            maxLength={10}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:text-gray-500 h-10"
            aria-describedby={`${numberId}-help`}
          />
          <div id={`${numberId}-help`} className="sr-only">
            {t("phone.phoneNumberHelp")}
          </div>
        </div>
      </div>
    </div>
  );
};

// Hook de validation avec i18n
export const usePhoneValidation = () => {
  const { t } = useTranslation();

  const validatePhoneFields = (
    countryCode: string,
    areaCode: string,
    phoneNumber: string,
  ) => {
    const hasAnyField = countryCode || areaCode || phoneNumber;
    if (!hasAnyField) return { isValid: true, errors: [] };

    const errors: string[] = [];
    if (hasAnyField && !countryCode)
      errors.push(t("phone.validation.countryRequired"));
    if (hasAnyField && !phoneNumber)
      errors.push(t("phone.validation.numberRequired"));

    return { isValid: errors.length === 0, errors };
  };

  return { validatePhoneFields };
};
