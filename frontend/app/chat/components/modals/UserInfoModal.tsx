import React, {
  useState,
  useEffect,
  useMemo,
  useCallback,
  useRef,
  startTransition,
} from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { useAuthStore } from "@/lib/stores/auth";
import { usePasskey } from "@/lib/hooks/usePasskey";
import { UserInfoModalProps } from "@/types";
import { CountrySelect } from "../CountrySelect";
import { apiClient } from "@/lib/api/client";
import { secureLog } from "@/lib/utils/secureLogger";
import { BaseDialog } from "../BaseDialog";

// Debug utility - TEMPORAIREMENT DÉSACTIVÉ
const debugLog = (category: string, message: string, data?: any) => {
  // Désactivé pour réduire le bruit console
  return;
};

interface Country {
  value: string;
  label: string;
  phoneCode: string;
  flag?: string;
}

// Mapping des codes de langue vers les codes utilisés par REST Countries
const getLanguageCode = (currentLanguage: string): string => {
  const mapping: Record<string, string> = {
    fr: "fra", // Français
    es: "spa", // Espagnol
    de: "deu", // Allemand
    pt: "por", // Portugais
    nl: "nld", // Néerlandais
    pl: "pol", // Polonais
    zh: "zho", // Chinois
    hi: "hin", // Hindi
    th: "tha", // Thaï
    en: "eng", // Anglais (fallback)
  };
  return mapping[currentLanguage] || "eng";
};

// Fallback countries avec traductions multilingues (conservé)
const getFallbackCountries = (currentLanguage: string): Country[] => {
  const translations: Record<string, Record<string, string>> = {
    en: {
      CA: "Canada",
      US: "United States",
      FR: "France",
      GB: "United Kingdom",
      DE: "Germany",
      IT: "Italy",
      ES: "Spain",
      BE: "Belgium",
      CH: "Switzerland",
      MX: "Mexico",
      BR: "Brazil",
      AU: "Australia",
      JP: "Japan",
      CN: "China",
      IN: "India",
      NL: "Netherlands",
      SE: "Sweden",
      NO: "Norway",
      DK: "Denmark",
      FI: "Finland",
    },
    fr: {
      CA: "Canada",
      US: "États-Unis",
      FR: "France",
      GB: "Royaume-Uni",
      DE: "Allemagne",
      IT: "Italie",
      ES: "Espagne",
      BE: "Belgique",
      CH: "Suisse",
      MX: "Mexique",
      BR: "Brésil",
      AU: "Australie",
      JP: "Japon",
      CN: "Chine",
      IN: "Inde",
      NL: "Pays-Bas",
      SE: "Suède",
      NO: "Norvège",
      DK: "Danemark",
      FI: "Finlande",
    },
  };

  const phoneCodesMap: Record<string, string> = {
    CA: "+1",
    US: "+1",
    FR: "+33",
    GB: "+44",
    DE: "+49",
    IT: "+39",
    ES: "+34",
    BE: "+32",
    CH: "+41",
    MX: "+52",
    BR: "+55",
    AU: "+61",
    JP: "+81",
    CN: "+86",
    IN: "+91",
    NL: "+31",
    SE: "+46",
    NO: "+47",
    DK: "+45",
    FI: "+358",
  };

  const flagsMap: Record<string, string> = {
    CA: "🇨🇦",
    US: "🇺🇸",
    FR: "🇫🇷",
    GB: "🇬🇧",
    DE: "🇩🇪",
    IT: "🇮🇹",
    ES: "🇪🇸",
    BE: "🇧🇪",
    CH: "🇨🇭",
    MX: "🇲🇽",
    BR: "🇧🇷",
    AU: "🇦🇺",
    JP: "🇯🇵",
    CN: "🇨🇳",
    IN: "🇮🇳",
    NL: "🇳🇱",
    SE: "🇸🇪",
    NO: "🇳🇴",
    DK: "🇩🇰",
    FI: "🇫🇮",
  };

  const langTranslations = translations[currentLanguage] || translations.en;

  return Object.keys(langTranslations)
    .map((code) => ({
      value: code,
      label: langTranslations[code],
      phoneCode: phoneCodesMap[code],
      flag: flagsMap[code],
    }))
    .sort((a, b) => {
      const locale = currentLanguage === "fr" ? "fr" : "en";
      return a.label.localeCompare(b.label, locale, { numeric: true });
    });
};

// Interface TypeScript pour les données utilisateur API (conservée)
interface UserProfileUpdate {
  first_name?: string;
  last_name?: string;
  full_name?: string;
  country?: string;
  company_name?: string;
  company_website?: string;
  user_type?: string;
  language?: string;
  whatsapp_number?: string;
}

const useCountries = () => {
  const { currentLanguage } = useTranslation();
  const languageCode = getLanguageCode(currentLanguage);

  const [countries, setCountries] = useState<Country[]>(() =>
    getFallbackCountries(currentLanguage),
  );
  const [loading, setLoading] = useState(false);
  const [usingFallback, setUsingFallback] = useState(true);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    debugLog("COUNTRIES", "Hook initialized with language", currentLanguage);

    const fetchCountries = async () => {
      if (abortControllerRef.current) {
        debugLog("COUNTRIES", "Aborting previous request");
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();
      const signal = abortControllerRef.current.signal;

      try {
        debugLog(
          "COUNTRIES",
          `Starting fetch for language: ${currentLanguage} (${languageCode})`,
        );
        setLoading(true);

        const response = await fetch(
          "https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations",
          {
            signal,
            headers: {
              Accept: "application/json",
              "User-Agent": "Mozilla/5.0 (compatible; Intelia/1.0)",
              "Cache-Control": "no-cache",
            },
          },
        );

        debugLog("COUNTRIES", "Fetch response", {
          ok: response.ok,
          status: response.status,
        });

        if (!response.ok || signal.aborted) return;

        const data = await response.json();
        debugLog("COUNTRIES", "Data received", { count: data?.length });

        if (signal.aborted) return;

        const formattedCountries = data
          .map((country: any) => {
            let phoneCode = "";
            if (country.idd?.root) {
              phoneCode = country.idd.root;
              if (country.idd.suffixes && country.idd.suffixes[0]) {
                phoneCode += country.idd.suffixes[0];
              }
            }

            let countryName = country.name?.common || country.cca2;

            if (country.translations && country.translations[languageCode]) {
              countryName =
                country.translations[languageCode].common ||
                country.translations[languageCode].official;
            } else if (country.name?.common) {
              countryName = country.name.common;
            }

            return {
              value: country.cca2,
              label: countryName,
              phoneCode: phoneCode,
              flag: country.flag || "",
            };
          })
          .filter((country: Country) => {
            const hasValidCode =
              country.phoneCode &&
              country.phoneCode !== "undefined" &&
              country.phoneCode !== "null" &&
              country.phoneCode.length > 1 &&
              country.phoneCode.startsWith("+") &&
              /^\+\d+$/.test(country.phoneCode);

            const hasValidInfo =
              country.value &&
              country.value.length === 2 &&
              country.label &&
              country.label.length > 1;

            return hasValidCode && hasValidInfo;
          })
          .sort((a: Country, b: Country) => {
            const locale =
              languageCode === "fra"
                ? "fr"
                : languageCode === "spa"
                  ? "es"
                  : languageCode === "deu"
                    ? "de"
                    : languageCode === "por"
                      ? "pt"
                      : languageCode === "nld"
                        ? "nl"
                        : languageCode === "pol"
                          ? "pl"
                          : languageCode === "zho"
                            ? "zh"
                            : "en";

            return a.label.localeCompare(b.label, locale, { numeric: true });
          });

        debugLog("COUNTRIES", "Countries processed", {
          count: formattedCountries.length,
        });

        if (formattedCountries.length >= 50 && !signal.aborted) {
          setCountries(formattedCountries);
          setUsingFallback(false);
          debugLog("COUNTRIES", `Using API countries in ${currentLanguage}`);

          const france = formattedCountries.find((c) => c.value === "FR");
          const usa = formattedCountries.find((c) => c.value === "US");
          const germany = formattedCountries.find((c) => c.value === "DE");

          secureLog.log(
            `[UserInfoModal-Countries] Exemples en ${currentLanguage}:`,
          );
          secureLog.log("  France:", france?.label);
          secureLog.log("  USA:", usa?.label);
          secureLog.log("  Germany:", germany?.label);
        }
      } catch (error) {
        if (
          error instanceof Error &&
          error.name !== "AbortError" &&
          !signal.aborted
        ) {
          debugLog("COUNTRIES", "Fetch error, using fallback", error.message);
          setCountries(getFallbackCountries(currentLanguage));
          setUsingFallback(true);
        }
      } finally {
        if (!signal.aborted) {
          setLoading(false);
          debugLog("COUNTRIES", "Loading finished");
        }
      }
    };

    setCountries(getFallbackCountries(currentLanguage));

    fetchCountries();

    return () => {
      debugLog("COUNTRIES", "Cleanup");
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [currentLanguage, languageCode]);

  return { countries, loading, usingFallback };
};

// Validation de mot de passe synchronisée avec page.tsx
const validatePassword = (password: string): string[] => {
  const errors: string[] = [];

  if (!password || password.trim().length === 0) {
    errors.push("Le mot de passe est requis");
    return errors;
  }

  if (password.length < 8) {
    errors.push("Au moins 8 caractères requis");
  }

  if (!/[A-Z]/.test(password)) {
    errors.push("Au moins une majuscule requise");
  }

  if (!/[a-z]/.test(password)) {
    errors.push("Au moins une minuscule requise");
  }

  if (!/\d/.test(password)) {
    errors.push("Au moins un chiffre requis");
  }

  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push("Au moins un caractère spécial requis (!@#$%^&*(),.?\":{}|<>)");
  }

  return errors;
};

// Composant d'indicateur de force du mot de passe moderne (conservé)
const PasswordStrengthIndicator: React.FC<{ password: string }> = ({
  password,
}) => {
  const validation = { errors: validatePassword(password) };

  const requirements = [
    { test: password.length >= 8, label: "Au moins 8 caractères" },
    { test: /[A-Z]/.test(password), label: "Au moins une majuscule" },
    { test: /[a-z]/.test(password), label: "Au moins une minuscule" },
    { test: /\d/.test(password), label: "Au moins un chiffre" },
    {
      test: /[!@#$%^&*(),.?":{}|<>]/.test(password),
      label: "Au moins un caractère spécial (!@#$%...)",
    },
  ];

  const passedRequirements = requirements.filter((req) => req.test).length;
  const strength = passedRequirements / requirements.length;

  const getStrengthColor = () => {
    if (strength < 0.4) return "bg-red-500";
    if (strength < 0.7) return "bg-yellow-500";
    if (strength < 0.9) return "bg-blue-500";
    return "bg-green-500";
  };

  const getStrengthLabel = () => {
    if (strength < 0.4) return "Faible";
    if (strength < 0.7) return "Moyen";
    if (strength < 0.9) return "Bon";
    return "Excellent";
  };

  return (
    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-gray-700">
          Force du mot de passe
        </p>
        <span
          className={`text-xs font-medium ${
            strength < 0.4
              ? "text-red-600"
              : strength < 0.7
                ? "text-yellow-600"
                : strength < 0.9
                  ? "text-blue-600"
                  : "text-green-600"
          }`}
        >
          {getStrengthLabel()}
        </span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${getStrengthColor()}`}
          style={{ width: `${strength * 100}%` }}
        ></div>
      </div>

      <div className="grid grid-cols-1 gap-1 text-xs">
        {requirements.map((req, index) => (
          <div
            key={index}
            className={`flex items-center ${req.test ? "text-green-600" : "text-gray-400"}`}
          >
            <span className="mr-2 text-sm">{req.test ? "✅" : "⭕"}</span>
            <span>{req.label}</span>
          </div>
        ))}
      </div>

      {strength < 1 && (
        <div className="mt-3 pt-2 border-t border-gray-200">
          <p className="text-xs text-gray-600 font-medium mb-1">Conseils :</p>
          <ul className="text-xs text-gray-600 space-y-1">
            {password.length < 12 && (
              <li>• Utilisez 12+ caractères pour plus de sécurité</li>
            )}
            {!/[A-Z]/.test(password) && !/[a-z]/.test(password) && (
              <li>• Mélangez majuscules et minuscules</li>
            )}
            {!/[!@#$%^&*()_+=\[\]{};':"|,.<>?-]/.test(password) && (
              <li>
                • Les caractères spéciaux renforcent la sécurité (optionnel)
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};

// Password input component (conservé)
const PasswordInput: React.FC<{
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  autoComplete: string;
  required?: boolean;
  showStrength?: boolean;
  showPassword: boolean;
  onToggleShow: () => void;
}> = ({
  id,
  label,
  value,
  onChange,
  placeholder,
  autoComplete,
  required,
  showStrength,
  showPassword,
  onToggleShow,
}) => {
  debugLog("COMPONENT", `PasswordInput rendered for ${id}`);

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <div className="relative">
        <input
          id={id}
          type={showPassword ? "text" : "password"}
          name={id}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => {
            debugLog("INPUT", `Password ${id} changed`, {
              length: e.target.value.length,
            });
            onChange(e.target.value);
          }}
          className="input-primary pr-10"
          placeholder={placeholder}
          required={required}
        />
        <button
          type="button"
          onClick={() => {
            debugLog("INTERACTION", `Toggle password visibility for ${id}`);
            onToggleShow();
          }}
          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
        >
          {showPassword ? (
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 11-4.243-4.243m4.242 4.242L9.88 9.88"
              />
            </svg>
          ) : (
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          )}
        </button>
      </div>
      {showStrength && <PasswordStrengthIndicator password={value} />}
    </div>
  );
};

// Error display component (conservé)
const ErrorDisplay: React.FC<{ errors: string[]; title: string }> = ({
  errors,
  title,
}) => {
  if (errors.length === 0) return null;

  debugLog("ERROR", `Displaying ${errors.length} errors`, errors);

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <div className="text-sm text-red-800">
        <p className="font-medium mb-2">{title} :</p>
        <ul className="list-disc list-inside space-y-1">
          {errors.map((error, index) => (
            <li key={index}>{error}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

// Main component
export const UserInfoModal: React.FC<UserInfoModalProps> = ({
  isOpen,
  user,
  onClose,
}) => {
  debugLog("LIFECYCLE", "Component mounting", {
    hasUser: !!user,
    userEmail: user?.email,
    timestamp: Date.now(),
  });

  // ✅ TOUS LES HOOKS SONT MAINTENANT AU DÉBUT DU COMPOSANT
  const { updateProfile } = useAuthStore();
  const isMountedRef = useRef(true);
  const { t, changeLanguage, getCurrentLanguage } = useTranslation();
  const {
    countries,
    loading: countriesLoading,
    usingFallback,
  } = useCountries();
  const {
    isSupported: isPasskeySupported,
    isLoading: isPasskeyLoading,
    registerPasskey,
    getPasskeys,
    deletePasskey: removePasskey,
  } = usePasskey();

  // userDataMemo avec dépendance stable
  const userDataMemo = useMemo(() => {
    if (!user?.id) {
      return {
        firstName: "",
        lastName: "",
        email: "",
        country: "",
        companyName: "",
        companyWebsite: "",
        productionType: [] as string[],
        category: "",
        categoryOther: "",
        whatsappNumber: "",
      };
    }

    const memo = {
      firstName: user.firstName || "",
      lastName: user.lastName || "",
      email: user.email || "",
      country: user.country || "",
      companyName: user.companyName || "",
      companyWebsite: user.companyWebsite || "",
      productionType: user.production_type || [],
      category: user.category || "",
      categoryOther: user.category_other || "",
      whatsappNumber: (user as any).whatsapp_number || "",
    };

    debugLog("DATA", "User data memo updated", memo);
    return memo;
  }, [
    user?.id,
    user?.firstName,
    user?.lastName,
    user?.email,
    user?.country,
    user?.companyName,
    user?.companyWebsite,
    user?.production_type,
    user?.category,
    user?.category_other,
    user?.whatsapp_number,
  ]);

  // States - Initialize with stable data
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("profile");
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);

  // Initialize formData
  const [formData, setFormData] = useState(() => {
    if (!user?.id) {
      return {
        firstName: "",
        lastName: "",
        email: "",
        country: "",
        companyName: "",
        companyWebsite: "",
        productionType: [] as string[],
        category: "",
        categoryOther: "",
        whatsappNumber: "",
      };
    }

    debugLog("STATE", "Initializing formData with user data");
    return {
      firstName: user.firstName || "",
      lastName: user.lastName || "",
      email: user.email || "",
      country: user.country || "",
      companyName: user.companyName || "",
      companyWebsite: user.companyWebsite || "",
      productionType: user.production_type || [],
      category: user.category || "",
      categoryOther: user.category_other || "",
      whatsappNumber: (user as any).whatsapp_number || "",
    };
  });

  const [passwordData, setPasswordData] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [showPasswords, setShowPasswords] = useState({
    currentPassword: false,
    newPassword: false,
    confirmPassword: false,
  });
  const [passkeys, setPasskeys] = useState<any[]>([]);
  const [isLoadingPasskeys, setIsLoadingPasskeys] = useState(false);
  const [passkeySuccess, setPasskeySuccess] = useState("");

  const tabs = useMemo(
    () => [
      { id: "profile", label: t("nav.profile"), icon: "👤" },
      { id: "password", label: t("profile.password"), icon: "🔒" },
      { id: "passkey", label: t("passkey.title"), icon: "🔐" },
    ],
    [t],
  );

  // Protection unmount-safe
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);


  // Validation functions
  const validatePasswordField = useCallback((password: string): string[] => {
    return validatePassword(password);
  }, []);

  const validateEmail = useCallback(
    (email: string): string[] => {
      const errors: string[] = [];
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      if (!email.trim()) {
        errors.push(t("error.emailRequired"));
      } else if (!emailRegex.test(email)) {
        errors.push(t("error.emailInvalid"));
      } else if (email.length > 254) {
        errors.push(t("error.emailTooLong"));
      }

      debugLog("VALIDATION", "Email validation", { email, errors });
      return errors;
    },
    [t],
  );

  const validateUrl = useCallback(
    (url: string, fieldName: string): string[] => {
      const errors: string[] = [];

      if (url.trim()) {
        try {
          new URL(url);
          if (!url.startsWith("http://") && !url.startsWith("https://")) {
            errors.push(`${fieldName} ${t("error.urlProtocol")}`);
          }
        } catch {
          errors.push(`${fieldName} ${t("error.urlInvalid")}`);
        }
      }

      debugLog("VALIDATION", "URL validation", { url, fieldName, errors });
      return errors;
    },
    [t],
  );

  const validateWhatsAppNumber = useCallback(
    (phoneNumber: string): string[] => {
      const errors: string[] = [];

      if (!phoneNumber.trim()) {
        return errors; // Optional field
      }

      // Remove all non-digit characters except +
      const cleaned = phoneNumber.replace(/[^\d+]/g, '');

      // Must start with +
      if (!cleaned.startsWith('+')) {
        errors.push("Le numéro WhatsApp doit commencer par + (ex: +1 234 567 8900)");
        return errors;
      }

      // Must have at least 8 digits (+ country code)
      const digitsOnly = cleaned.replace(/\+/g, '');
      if (digitsOnly.length < 8) {
        errors.push("Le numéro WhatsApp est trop court (minimum 8 chiffres)");
      }

      if (digitsOnly.length > 15) {
        errors.push("Le numéro WhatsApp est trop long (maximum 15 chiffres)");
      }

      debugLog("VALIDATION", "WhatsApp number validation", { phoneNumber, cleaned, errors });
      return errors;
    },
    [],
  );

  // Event handlers
  const handleClose = useCallback(() => {
    debugLog("INTERACTION", "Close button clicked", { isLoading });
    if (!isLoading) {
      onClose();
    }
  }, [isLoading, onClose]);

  const handleFormDataChange = useCallback((field: string, value: string | string[]) => {
    debugLog("INTERACTION", "Form data changed", {
      field,
      value: typeof value === 'string' ? value.substring(0, 20) + "..." : value,
    });
    setFormData((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handlePasswordDataChange = useCallback(
    (field: string, value: string) => {
      debugLog("INTERACTION", "Password data changed", {
        field,
        valueLength: value.length,
      });
      setPasswordData((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const handleShowPasswordToggle = useCallback(
    (field: keyof typeof showPasswords) => {
      debugLog("INTERACTION", "Password visibility toggled", { field });
      setShowPasswords((prev) => ({ ...prev, [field]: !prev[field] }));
    },
    [],
  );

  // Fonction handleProfileSave
  const handleProfileSave = useCallback(async () => {
    if (!isMountedRef.current || isLoading) return;
    setIsLoading(true);
    setFormErrors([]);

    try {
      const errors: string[] = [];

      // Validation complète avec traductions
      if (!formData.firstName.trim()) {
        errors.push(t("error.firstNameRequired"));
      } else if (formData.firstName.length > 50) {
        errors.push(t("error.firstNameTooLong"));
      }

      if (!formData.lastName.trim()) {
        errors.push(t("error.lastNameRequired"));
      } else if (formData.lastName.length > 50) {
        errors.push(t("error.lastNameTooLong"));
      }

      const emailErrors = validateEmail(formData.email);
      errors.push(...emailErrors);

      if (formData.companyWebsite) {
        const websiteErrors = validateUrl(
          formData.companyWebsite,
          t("profile.companyWebsite"),
        );
        errors.push(...websiteErrors);
      }

      if (formData.companyName && formData.companyName.length > 100) {
        errors.push(t("error.companyNameTooLong"));
      }

      if (formData.whatsappNumber) {
        const whatsappErrors = validateWhatsAppNumber(formData.whatsappNumber);
        errors.push(...whatsappErrors);
      }

      if (errors.length > 0) {
        if (isMountedRef.current) setFormErrors(errors);
        return;
      }

      secureLog.log("[UserInfoModal] Mise à jour via store unifié");

      const updateData = {
        firstName: formData.firstName?.trim(),
        lastName: formData.lastName?.trim(),
        name: `${formData.firstName?.trim()} ${formData.lastName?.trim()}`.trim(),
        email: formData.email?.trim(),
        country: formData.country,
        companyName: formData.companyName,
        companyWebsite: formData.companyWebsite,
        production_type: formData.productionType.length > 0 ? formData.productionType : null,
        category: formData.category || null,
        category_other: formData.category === 'other' ? formData.categoryOther : null,
        whatsapp_number: formData.whatsappNumber?.trim() || null,
      };

      await updateProfile(updateData);

      secureLog.log(
        "[UserInfoModal] Profil mis à jour avec succès via store unifié",
      );

      if (!isMountedRef.current) return;

      startTransition(() => {
        if (isMountedRef.current) {
          handleClose();
        }
      });
    } catch (error: any) {
      if (isMountedRef.current) {
        secureLog.error("Erreur mise à jour profil:", error);
        let errorMessage = t("common.unexpectedError");

        if (error.message) {
          if (error.message.includes("Failed to fetch")) {
            errorMessage =
              "Problème de connexion réseau. Vérifiez votre connexion internet.";
          } else if (
            error.message.includes("401") ||
            error.message.includes("unauthorized")
          ) {
            errorMessage = t("error.userNotConnected");
          } else {
            errorMessage = error.message;
          }
        }

        setFormErrors([errorMessage]);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [
    isLoading,
    formData,
    validateEmail,
    validateUrl,
    validateWhatsAppNumber,
    updateProfile,
    handleClose,
    t,
  ]);

  // Fonction handlePasswordChange
  const handlePasswordChange = useCallback(async () => {
    debugLog("API", "Password change started");

    if (isLoading) return;

    const errors: string[] = [];

    if (!passwordData.currentPassword) {
      errors.push(t("error.currentPasswordRequired"));
    }
    if (!passwordData.newPassword) {
      errors.push(t("error.newPasswordRequired"));
    }
    if (!passwordData.confirmPassword) {
      errors.push(t("error.confirmPasswordRequired"));
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      errors.push(t("form.passwordMismatch"));
    }

    const passwordValidationErrors = validatePasswordField(
      passwordData.newPassword,
    );
    errors.push(...passwordValidationErrors);

    setPasswordErrors(errors);

    if (errors.length > 0) {
      debugLog("API", "Password change validation failed", { errors });
      return;
    }

    setIsLoading(true);

    try {
      debugLog("API", "Changing password via apiClient");

      const response = await apiClient.postSecure("/auth/change-password", {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword,
      });

      if (!response.success) {
        throw new Error(response.error?.message || t("error.changePassword"));
      }

      debugLog("API", "Password changed successfully");

      setPasswordData({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
      setPasswordErrors([]);
      secureLog.log(t("success.passwordChanged"));

      startTransition(() => {
        if (isMountedRef.current) {
          handleClose();
        }
      });
    } catch (error: any) {
      debugLog("API", "Password change error", { error: error?.message });
      secureLog.error("Erreur technique:", error);

      let errorMessage = t("error.passwordServerError");
      if (error.message?.includes("Incorrect current password")) {
        errorMessage = t("error.currentPasswordIncorrect");
      }

      setPasswordErrors([errorMessage]);
    } finally {
      debugLog("API", "Password change finished");
      setIsLoading(false);
    }
  }, [passwordData, validatePasswordField, handleClose, isLoading, t]);

  // Passkey handlers
  const loadPasskeys = useCallback(async () => {
    setIsLoadingPasskeys(true);
    try {
      const credentials = await getPasskeys();
      setPasskeys(credentials);
    } catch (err: any) {
      debugLog("PASSKEY", "Failed to load passkeys", err);
    } finally {
      setIsLoadingPasskeys(false);
    }
  }, [getPasskeys]);

  const handleSetupPasskey = useCallback(async () => {
    setFormErrors([]);
    setPasskeySuccess("");

    if (!isPasskeySupported()) {
      setFormErrors([t("passkey.setup.notSupported") || "WebAuthn not supported"]);
      return;
    }

    try {
      const deviceName =
        window.navigator.userAgent.includes("iPhone")
          ? "iPhone"
          : window.navigator.userAgent.includes("iPad")
            ? "iPad"
            : window.navigator.userAgent.includes("Android")
              ? "Android"
              : "Browser";

      await registerPasskey(deviceName);
      setPasskeySuccess(t("passkey.setup.success") || "Passkey configured successfully!");
      await loadPasskeys();
    } catch (err: any) {
      setFormErrors([err.message || t("passkey.setup.error") || "Failed to setup passkey"]);
    }
  }, [isPasskeySupported, registerPasskey, loadPasskeys, t]);

  const handleDeletePasskey = useCallback(async (credentialId: string) => {
    try {
      await removePasskey(credentialId);
      setPasskeySuccess(t("passkey.manage.deleteSuccess") || "Passkey deleted successfully!");
      await loadPasskeys();
    } catch (err: any) {
      setFormErrors([err.message || t("passkey.manage.deleteError") || "Failed to delete passkey"]);
    }
  }, [removePasskey, loadPasskeys, t]);

  // Load passkeys when passkey tab is active
  useEffect(() => {
    if (activeTab === "passkey" && user) {
      loadPasskeys();
    }
  }, [activeTab, user, loadPasskeys]);

  debugLog("STATE", "Component states initialized", {
    isLoading,
    activeTab,
    formErrorsCount: formErrors.length,
    passwordErrorsCount: passwordErrors.length,
  });

  debugLog("RENDER", "Component rendering", {
    activeTab,
    hasCountries: countries.length,
    usingFallback,
    countriesLoading,
  });

  // ✅ VÉRIFICATION USER EN FIN DE FONCTION
  if (!user) {
    debugLog("LIFECYCLE", "No user provided - returning null");
    return null;
  }

  return (
    <BaseDialog
      isOpen={isOpen}
      onClose={onClose}
      title={t("profile.title")}
      description={t("profile.description")}
    >
      {/* Tabs */}
      <div className="border-b border-gray-200 -mx-6 -mt-6 mb-6">
        <nav className="flex px-6" data-debug="tabs-nav">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  debugLog("INTERACTION", `Tab clicked: ${tab.id}`);
                  setActiveTab(tab.id);
                }}
                className={`py-3 px-4 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
                data-debug={`tab-${tab.id}`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

      {/* Content */}
      <div className="space-y-6">
            {/* Errors */}
            <ErrorDisplay
              errors={formErrors}
              title={t("error.validationErrors")}
            />

            {/* Fallback Warning */}
            {usingFallback && !countriesLoading && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                <div className="flex items-center space-x-2">
                  <svg
                    className="w-4 h-4 text-yellow-600"
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
                  <span className="text-sm text-yellow-800">
                    {t("countries.fallbackWarning")}
                  </span>
                </div>
              </div>
            )}

            {/* Profile Tab */}
            {activeTab === "profile" && (
              <div className="space-y-6" data-debug="profile-tab">
                {/* Personal Info */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                    {t("profile.personalInfo")}
                    <span className="text-red-500 ml-1">*</span>
                  </h3>

                  <div className="grid grid-cols-1 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t("profile.firstName")}
                      </label>
                      <input
                        type="text"
                        value={formData.firstName}
                        onChange={(e) =>
                          handleFormDataChange("firstName", e.target.value)
                        }
                        className="input-primary"
                        required
                        data-debug="firstName-input"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t("profile.lastName")}
                      </label>
                      <input
                        type="text"
                        value={formData.lastName}
                        onChange={(e) =>
                          handleFormDataChange("lastName", e.target.value)
                        }
                        className="input-primary"
                        required
                        data-debug="lastName-input"
                      />
                    </div>
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t("profile.email")}
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) =>
                        handleFormDataChange("email", e.target.value)
                      }
                      className="input-primary"
                      required
                      data-debug="email-input"
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t("profile.whatsappNumber")}
                      <span className="text-gray-500 text-sm ml-1">
                        ({t("common.optional")})
                      </span>
                    </label>
                    <input
                      type="tel"
                      value={formData.whatsappNumber || ""}
                      onChange={(e) =>
                        handleFormDataChange("whatsappNumber", e.target.value)
                      }
                      placeholder="+1 234 567 8900"
                      className="input-primary"
                      data-debug="whatsapp-input"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      📱 {t("profile.whatsappDescription")}
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t("profile.country")}{" "}
                      <span className="text-gray-500 text-sm">
                        ({t("common.optional")})
                      </span>
                    </label>
                    <div data-debug="country-select">
                      <CountrySelect
                        countries={countries}
                        value={formData.country}
                        onChange={(countryValue: string) =>
                          handleFormDataChange("country", countryValue)
                        }
                        placeholder={t("placeholder.countrySelect")}
                      />
                    </div>
                  </div>
                </div>

                {/* Professional Info */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                    {t("profile.professionalInfo")}
                    <span className="text-gray-500 text-sm ml-2">
                      ({t("common.optional")})
                    </span>
                  </h3>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t("profile.companyName")}
                      </label>
                      <input
                        type="text"
                        value={formData.companyName}
                        onChange={(e) =>
                          handleFormDataChange("companyName", e.target.value)
                        }
                        placeholder={t("placeholder.companyName")}
                        className="input-primary"
                        data-debug="company-name-input"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t("profile.companyWebsite")}
                      </label>
                      <input
                        type="url"
                        value={formData.companyWebsite}
                        onChange={(e) =>
                          handleFormDataChange("companyWebsite", e.target.value)
                        }
                        placeholder={t("placeholder.companyWebsite")}
                        className="input-primary"
                        data-debug="company-website-input"
                      />
                    </div>

                    {/* Production Type */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t("profile.productionType.label")}
                      </label>
                      <div className="space-y-2">
                        <label className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formData.productionType.includes('broiler')}
                            onChange={(e) => {
                              const newProductionType = e.target.checked
                                ? [...formData.productionType, 'broiler']
                                : formData.productionType.filter(t => t !== 'broiler');
                              handleFormDataChange('productionType', newProductionType);
                            }}
                            className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <span className="text-sm text-gray-700">
                            {t("profile.productionType.broiler")}
                          </span>
                        </label>
                        <label className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formData.productionType.includes('layer')}
                            onChange={(e) => {
                              const newProductionType = e.target.checked
                                ? [...formData.productionType, 'layer']
                                : formData.productionType.filter(t => t !== 'layer');
                              handleFormDataChange('productionType', newProductionType);
                            }}
                            className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <span className="text-sm text-gray-700">
                            {t("profile.productionType.layer")}
                          </span>
                        </label>
                      </div>
                    </div>

                    {/* Category */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t("profile.category.label")}
                      </label>
                      <select
                        value={formData.category}
                        onChange={(e) => handleFormDataChange('category', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="">-- {t("common.optional")} --</option>
                        <option value="breeding_hatchery">{t("profile.category.breedingHatchery")}</option>
                        <option value="feed_nutrition">{t("profile.category.feedNutrition")}</option>
                        <option value="farm_operations">{t("profile.category.farmOperations")}</option>
                        <option value="health_veterinary">{t("profile.category.healthVeterinary")}</option>
                        <option value="processing">{t("profile.category.processing")}</option>
                        <option value="management_oversight">{t("profile.category.managementOversight")}</option>
                        <option value="equipment_technology">{t("profile.category.equipmentTechnology")}</option>
                        <option value="other">{t("profile.category.other")}</option>
                      </select>

                      {/* Conditional: Other Category Input */}
                      {formData.category === 'other' && (
                        <input
                          type="text"
                          value={formData.categoryOther}
                          onChange={(e) => handleFormDataChange('categoryOther', e.target.value)}
                          placeholder={t("profile.category.otherPlaceholder")}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mt-2"
                        />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Password Tab */}
            {activeTab === "password" && (
              <div className="space-y-6" data-debug="password-tab">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                    {t("profile.password")}
                  </h3>

                  <div className="space-y-4">
                    <PasswordInput
                      id="currentPassword"
                      label={t("profile.currentPassword")}
                      value={passwordData.currentPassword}
                      onChange={(value) =>
                        handlePasswordDataChange("currentPassword", value)
                      }
                      placeholder={t("placeholder.currentPassword")}
                      autoComplete="current-password"
                      required
                      showPassword={showPasswords.currentPassword}
                      onToggleShow={() =>
                        handleShowPasswordToggle("currentPassword")
                      }
                    />

                    <PasswordInput
                      id="newPassword"
                      label={t("profile.newPassword")}
                      value={passwordData.newPassword}
                      onChange={(value) =>
                        handlePasswordDataChange("newPassword", value)
                      }
                      placeholder={t("placeholder.newPassword")}
                      autoComplete="new-password"
                      required
                      showStrength
                      showPassword={showPasswords.newPassword}
                      onToggleShow={() =>
                        handleShowPasswordToggle("newPassword")
                      }
                    />

                    <PasswordInput
                      id="confirmPassword"
                      label={t("profile.confirmPassword")}
                      value={passwordData.confirmPassword}
                      onChange={(value) =>
                        handlePasswordDataChange("confirmPassword", value)
                      }
                      placeholder={t("placeholder.confirmPassword")}
                      autoComplete="new-password"
                      required
                      showPassword={showPasswords.confirmPassword}
                      onToggleShow={() =>
                        handleShowPasswordToggle("confirmPassword")
                      }
                    />
                  </div>
                </div>

                <ErrorDisplay
                  errors={passwordErrors}
                  title={t("profile.passwordErrors")}
                />
              </div>
            )}

            {/* Passkey Tab */}
            {activeTab === "passkey" && (
              <div className="space-y-6" data-debug="passkey-tab">
                {passkeySuccess && (
                  <div className="p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
                    {passkeySuccess}
                  </div>
                )}

                <div className="p-4 border border-blue-200 rounded-lg bg-blue-50">
                  <h3 className="text-lg font-medium text-gray-900 mb-2 flex items-center">
                    <span className="mr-2">🔐</span>
                    {t("passkey.setupTitle") || "Configure votre Passkey"}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    {t("passkey.description") || "Utilisez Face ID, Touch ID ou votre empreinte digitale pour vous connecter rapidement."}
                  </p>

                  <div className="bg-white bg-opacity-70 rounded p-3 mb-4 space-y-2 text-sm">
                    <div className="flex items-start">
                      <span className="mr-2">✓</span>
                      <span>{t("passkey.benefits.faster") || "Connexion rapide avec biométrie"}</span>
                    </div>
                    <div className="flex items-start">
                      <span className="mr-2">✓</span>
                      <span>{t("passkey.benefits.secure") || "Plus sécurisé que les mots de passe"}</span>
                    </div>
                    <div className="flex items-start">
                      <span className="mr-2">✓</span>
                      <span>{t("passkey.benefits.noPassword") || "Aucun mot de passe à retenir"}</span>
                    </div>
                  </div>

                  <button
                    onClick={handleSetupPasskey}
                    disabled={isPasskeyLoading || !isPasskeySupported()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isPasskeyLoading
                      ? t("passkey.setup.inProgress") || "Configuration..."
                      : t("passkey.setupButton") || "Configurer un Passkey"}
                  </button>
                </div>

                <div className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3">
                    {t("passkey.registered") || "Passkeys enregistrés"}
                  </h4>

                  {isLoadingPasskeys ? (
                    <div className="flex justify-center py-4">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                    </div>
                  ) : passkeys.length === 0 ? (
                    <p className="text-sm text-gray-500">
                      {t("passkey.noPasskeys") || "Aucun passkey enregistré"}
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {passkeys.map((passkey) => (
                        <div
                          key={passkey.id}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded"
                        >
                          <div className="flex items-center space-x-2">
                            <span>🔐</span>
                            <div>
                              <p className="font-medium text-sm text-gray-900">
                                {passkey.device_name || "Appareil"}
                              </p>
                              <p className="text-xs text-gray-500">
                                Ajouté le {new Date(passkey.created_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => handleDeletePasskey(passkey.credential_id)}
                            className="text-red-600 hover:text-red-700 text-sm font-medium"
                          >
                            {t("passkey.manage.delete") || "Supprimer"}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Footer Buttons */}
            {activeTab !== "passkey" && (
              <div
                className="flex justify-end space-x-3 pt-4 pb-8"
                data-debug="footer"
              >
                <button
                  onClick={handleClose}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium transition-colors"
                  disabled={isLoading}
                  data-debug="cancel-button"
                >
                  {t("modal.cancel")}
                </button>
                <button
                  onClick={
                    activeTab === "profile"
                      ? handleProfileSave
                      : handlePasswordChange
                  }
                  disabled={isLoading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  data-debug="save-button"
                >
                  {isLoading && (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  )}
                  {isLoading ? t("modal.loading") : t("modal.save")}
                </button>
              </div>
            )}
      </div>
    </BaseDialog>
  );
};
