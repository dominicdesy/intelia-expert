"use client";
// app/auth/invitation/page.tsx - Page d'invitation utilisant le système i18n unifié

import React, { useEffect, useState, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslation } from "@/lib/languages/i18n";
import { secureLog } from "@/lib/utils/secureLogger";

// ==================== CONFIGURATION DES PAYS AVEC FALLBACK ====================
// Pays de fallback (les plus communs) en cas d'échec de l'API
const fallbackCountries = [
  { value: "CA", label: "Canada", phoneCode: "+1", flag: "🇨🇦" },
  { value: "US", label: "États-Unis", phoneCode: "+1", flag: "🇺🇸" },
  { value: "FR", label: "France", phoneCode: "+33", flag: "🇫🇷" },
  { value: "GB", label: "Royaume-Uni", phoneCode: "+44", flag: "🇬🇧" },
  { value: "DE", label: "Allemagne", phoneCode: "+49", flag: "🇩🇪" },
  { value: "IT", label: "Italie", phoneCode: "+39", flag: "🇮🇹" },
  { value: "ES", label: "Espagne", phoneCode: "+34", flag: "🇪🇸" },
  { value: "BE", label: "Belgique", phoneCode: "+32", flag: "🇧🇪" },
  { value: "CH", label: "Suisse", phoneCode: "+41", flag: "🇨🇭" },
  { value: "MX", label: "Mexique", phoneCode: "+52", flag: "🇲🇽" },
  { value: "BR", label: "Brésil", phoneCode: "+55", flag: "🇧🇷" },
  { value: "AU", label: "Australie", phoneCode: "+61", flag: "🇦🇺" },
  { value: "JP", label: "Japon", phoneCode: "+81", flag: "🇯🇵" },
  { value: "CN", label: "Chine", phoneCode: "+86", flag: "🇨🇳" },
  { value: "IN", label: "Inde", phoneCode: "+91", flag: "🇮🇳" },
  { value: "NL", label: "Pays-Bas", phoneCode: "+31", flag: "🇳🇱" },
  { value: "SE", label: "Suède", phoneCode: "+46", flag: "🇸🇪" },
  { value: "NO", label: "Norvège", phoneCode: "+47", flag: "🇳🇴" },
  { value: "DK", label: "Danemark", phoneCode: "+45", flag: "🇩🇰" },
  { value: "FI", label: "Finlande", phoneCode: "+358", flag: "🇫🇮" },
];

// Interface pour les pays
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

// Hook personnalisé pour charger les pays avec support multilingue
const useCountries = () => {
  const { currentLanguage } = useTranslation();
  const languageCode = getLanguageCode(currentLanguage);

  const [countries, setCountries] = useState<Country[]>(fallbackCountries);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    const fetchCountries = async () => {
      try {
        secureLog.log(
          `[Countries] Tentative de chargement via API REST Countries en ${currentLanguage} (${languageCode})...`,
        );

        const response = await fetch(
          "https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations",
          {
            headers: {
              Accept: "application/json",
            },
          },
        );

        if (!response.ok) {
          throw new Error(
            `API Error: ${response.status} ${response.statusText}`,
          );
        }

        const data = await response.json();
        secureLog.log(`[Countries] Données reçues: ${data.length} pays`);

        const formattedCountries = data
          .map((country: any) => {
            const phoneCode =
              country.idd?.root + (country.idd?.suffixes?.[0] || "");

            // MODIFICATION PRINCIPALE : Récupération du nom selon la langue
            let countryName = country.name?.common || country.cca2;

            // Essayer d'abord la traduction dans la langue demandée
            if (country.translations && country.translations[languageCode]) {
              countryName =
                country.translations[languageCode].common ||
                country.translations[languageCode].official;
            }
            // Si pas de traduction dans la langue demandée, essayer l'anglais
            else if (country.name?.common) {
              countryName = country.name.common;
            }

            return {
              value: country.cca2,
              label: countryName,
              phoneCode: phoneCode,
              flag: country.flag,
            };
          })
          .filter((country: Country) => {
            const hasValidCode =
              country.phoneCode &&
              country.phoneCode !== "undefined" &&
              country.phoneCode !== "null" &&
              country.phoneCode.length > 1 &&
              country.phoneCode.startsWith("+");
            return hasValidCode && country.value && country.label;
          })
          .sort((a: Country, b: Country) => {
            // Tri selon la langue actuelle
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

        if (formattedCountries.length >= 50) {
          setCountries(formattedCountries);
          setUsingFallback(false);
          secureLog.log(
            `[Countries] API REST Countries utilisée avec succès en ${currentLanguage}`,
          );
        } else {
          throw new Error("Données insuffisantes");
        }
      } catch (err) {
        secureLog.warn(
          "[Countries] API REST Countries bloquée, utilisation du fallback:",
          err,
        );
        setCountries(fallbackCountries);
        setUsingFallback(true);
      } finally {
        setLoading(false);
      }
    };

    const timer = setTimeout(fetchCountries, 100);
    return () => clearTimeout(timer);
  }, [currentLanguage, languageCode]); // MODIFICATION : Dépendance sur currentLanguage pour recharger quand la langue change

  return { countries, loading, usingFallback };
};

// ==================== VALIDATION ====================
const validatePassword = (
  password: string,
  t: (key: string) => string,
): string[] => {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push(t("validation.password.minLength"));
  }
  if (!/[A-Z]/.test(password)) {
    errors.push(t("validation.password.uppercase"));
  }
  if (!/[a-z]/.test(password)) {
    errors.push(t("validation.password.lowercase"));
  }
  if (!/\d/.test(password)) {
    errors.push(t("validation.password.number"));
  }
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push(t("validation.password.special"));
  }

  return errors;
};

const validatePhone = (
  countryCode: string,
  areaCode: string,
  phoneNumber: string,
  selectedCountry: string,
  countryCodeMap: Record<string, string>,
): boolean => {
  if (!countryCode.trim() && !areaCode.trim() && !phoneNumber.trim()) {
    return true;
  }

  const isAutoFilledCountryCodeOnly =
    countryCode.trim() &&
    !areaCode.trim() &&
    !phoneNumber.trim() &&
    selectedCountry &&
    countryCodeMap[selectedCountry] === countryCode.trim();

  if (isAutoFilledCountryCodeOnly) {
    return true;
  }

  const hasUserEnteredPhoneData = areaCode.trim() || phoneNumber.trim();

  if (hasUserEnteredPhoneData) {
    if (!countryCode.trim() || !areaCode.trim() || !phoneNumber.trim()) {
      return false;
    }

    if (!/^\+[1-9]\d{0,3}$/.test(countryCode.trim())) {
      return false;
    }

    if (!/^\d{3}$/.test(areaCode.trim())) {
      return false;
    }

    if (!/^\d{7}$/.test(phoneNumber.trim())) {
      return false;
    }
  }

  return true;
};

// ==================== COMPOSANTS ====================
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
  <img src="/images/favicon.png" alt="Intelia Logo" className={className} />
);

interface ProcessingResult {
  success: boolean;
  step: "validation" | "completion";
  message: string;
  details?: any;
}

const ProcessingStatus = ({ result }: { result: ProcessingResult }) => {
  const { t } = useTranslation();

  const getIcon = () => {
    if (result.success) {
      return (
        <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-6 h-6 text-green-600"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
      );
    } else {
      return (
        <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-6 h-6 text-red-600"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
            />
          </svg>
        </div>
      );
    }
  };

  const getStepText = () => {
    switch (result.step) {
      case "validation":
        return result.success
          ? t("invitation.status.tokenValidated")
          : t("invitation.status.tokenError");
      case "completion":
        return result.success
          ? t("invitation.status.accountCreated")
          : t("invitation.status.accountError");
      default:
        return t("invitation.status.processing");
    }
  };

  return (
    <div className="text-center">
      {getIcon()}
      <h2
        className={`text-lg font-semibold mb-4 ${result.success ? "text-green-900" : "text-red-900"}`}
      >
        {getStepText()}
      </h2>

      <div
        className={`text-sm mb-4 ${result.success ? "text-green-700" : "text-red-700"}`}
      >
        {result.message}
      </div>

      {result.success && result.step === "completion" && (
        <div className="text-sm text-gray-600">
          <p>{t("invitation.redirecting.dashboard")}</p>
          <div className="mt-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full animate-pulse"
                style={{ width: "100%" }}
              ></div>
            </div>
          </div>
        </div>
      )}

      {!result.success && (
        <div className="text-xs text-gray-600">
          {t("invitation.redirecting.login")}
        </div>
      )}
    </div>
  );
};

// ==================== COMPOSANT PRINCIPAL ====================
function InvitationAcceptPageContent() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<
    "loading" | "set-password" | "success" | "error"
  >("loading");
  const [message, setMessage] = useState("");
  const [userInfo, setUserInfo] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [hasProcessedToken, setHasProcessedToken] = useState(false);
  const [processingResult, setProcessingResult] =
    useState<ProcessingResult | null>(null);

  const {
    countries,
    loading: countriesLoading,
    usingFallback,
  } = useCountries();

  const countryCodeMap = useMemo(() => {
    return countries.reduce(
      (acc, country) => {
        acc[country.value] = country.phoneCode;
        return acc;
      },
      {} as Record<string, string>,
    );
  }, [countries]);

  const [formData, setFormData] = useState({
    password: "",
    confirmPassword: "",
    firstName: "",
    lastName: "",
    linkedinProfile: "",
    email: "",
    country: "",
    countryCode: "",
    areaCode: "",
    phoneNumber: "",
    companyName: "",
    companyWebsite: "",
    companyLinkedin: "",
    jobTitle: "",
  });

  const [errors, setErrors] = useState<string[]>([]);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        if (hasProcessedToken) {
          secureLog.log("[InvitationAccept] Token déjà traité, ignorer");
          return;
        }

        secureLog.log("[InvitationAccept] Début traitement invitation");

        const hash = window.location.hash;
        const token = searchParams.get("token");
        const type = searchParams.get("type");

        const hasInvitationInHash =
          hash &&
          (hash.includes("access_token") || hash.includes("type=invite"));
        const hasInvitationInQuery = token && type === "invite";

        if (hasInvitationInHash || hasInvitationInQuery) {
          secureLog.log("[InvitationAccept] Invitation détectée dans URL");
          setMessage(t("invitation.validating"));

          setHasProcessedToken(true);

          let accessToken = "";

          if (hasInvitationInHash) {
            const urlParams = new URLSearchParams(hash.substring(1));
            accessToken = urlParams.get("access_token") || "";
          } else if (hasInvitationInQuery) {
            accessToken = token || "";
          }

          if (!accessToken) {
            throw new Error(t("invitation.errors.missingToken"));
          }

          secureLog.log(
            "[InvitationAccept] Token extrait, validation via backend...",
          );

          const API_BASE_URL =
            process.env.NEXT_PUBLIC_API_URL ||
            process.env.NEXT_PUBLIC_API_BASE_URL;
          const validateResponse = await fetch(
            `${API_BASE_URL}/v1/auth/invitations/validate-token`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                access_token: accessToken,
              }),
            },
          );

          if (!validateResponse.ok) {
            const errorData = await validateResponse.json();
            setProcessingResult({
              success: false,
              step: "validation",
              message:
                errorData.detail || t("invitation.errors.tokenValidation"),
              details: errorData,
            });
            throw new Error(
              errorData.detail || t("invitation.errors.tokenValidation"),
            );
          }

          const validationResult = await validateResponse.json();
          secureLog.log(
            "[InvitationAccept] Token validé:",
            validationResult.user_email,
          );

          setProcessingResult({
            success: true,
            step: "validation",
            message: `${t("invitation.success.tokenValidated")}: ${validationResult.user_email}`,
            details: validationResult,
          });

          setUserInfo({
            email: validationResult.user_email,
            inviterName: validationResult.inviter_name,
            personalMessage: validationResult.invitation_data?.personal_message,
            language: validationResult.invitation_data?.language,
            invitationDate: validationResult.invitation_data?.invitation_date,
            accessToken: accessToken,
          });

          setFormData((prev) => ({
            ...prev,
            email: validationResult.user_email,
          }));

          secureLog.log("[InvitationAccept] Passage au mode set-password");
          setStatus("set-password");
          setMessage(t("invitation.completeProfile"));

          setTimeout(() => {
            window.history.replaceState(
              {},
              document.title,
              window.location.pathname,
            );
          }, 100);
        } else {
          if (!hasProcessedToken) {
            secureLog.log("[InvitationAccept] Pas d'invitation trouvée");
            setStatus("error");
            setMessage(t("invitation.errors.noInvitation"));
            setProcessingResult({
              success: false,
              step: "validation",
              message: t("invitation.errors.noInvitation"),
            });
            setTimeout(() => router.push("/auth/login"), 2000);
          }
        }
      } catch (error) {
        secureLog.error("[InvitationAccept] Erreur traitement:", error);
        setStatus("error");

        if (error instanceof Error) {
          setMessage(error.message);
        } else {
          setMessage(t("invitation.errors.processing"));
        }

        setTimeout(() => {
          router.push(
            "/auth/login?error=" +
              encodeURIComponent(
                error instanceof Error
                  ? error.message
                  : t("invitation.errors.generic"),
              ),
          );
        }, 4000);
      }
    };

    const timer = setTimeout(handleAuthCallback, 500);
    return () => clearTimeout(timer);
  }, [router, searchParams, hasProcessedToken, t]);

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => {
      const newData = { ...prev, [field]: value };

      if (field === "country" && value && countryCodeMap[value]) {
        newData.countryCode = countryCodeMap[value];
        newData.areaCode = "";
        newData.phoneNumber = "";
      }

      return newData;
    });

    if (errors.length > 0) {
      setErrors([]);
    }
  };

  const validateForm = (): string[] => {
    const validationErrors: string[] = [];

    if (!formData.password) {
      validationErrors.push(t("validation.required.password"));
    } else {
      const passwordErrors = validatePassword(formData.password, t);
      validationErrors.push(...passwordErrors);
    }

    if (!formData.confirmPassword) {
      validationErrors.push(t("validation.required.confirmPassword"));
    }

    if (formData.password !== formData.confirmPassword) {
      validationErrors.push(t("validation.password.mismatch"));
    }

    if (!formData.firstName.trim()) {
      validationErrors.push(t("validation.required.firstName"));
    }

    if (!formData.lastName.trim()) {
      validationErrors.push(t("validation.required.lastName"));
    }

    if (!formData.email.trim()) {
      validationErrors.push(t("validation.required.email"));
    }

    if (!formData.country) {
      validationErrors.push(t("validation.required.country"));
    }

    if (
      !validatePhone(
        formData.countryCode,
        formData.areaCode,
        formData.phoneNumber,
        formData.country,
        countryCodeMap,
      )
    ) {
      const hasUserEnteredPhoneData =
        formData.areaCode.trim() || formData.phoneNumber.trim();

      if (hasUserEnteredPhoneData) {
        const missingFields = [];
        if (!formData.countryCode.trim())
          missingFields.push(t("profile.countryCode"));
        if (!formData.areaCode.trim())
          missingFields.push(t("profile.areaCode"));
        if (!formData.phoneNumber.trim())
          missingFields.push(t("profile.phoneNumber"));

        if (missingFields.length > 0) {
          validationErrors.push(
            `${t("validation.phone.incomplete")}: ${missingFields.join(", ")}`,
          );
        } else {
          validationErrors.push(t("validation.phone.invalid"));
        }
      }
    }

    return validationErrors;
  };

  const handleFormSubmit = async () => {
    secureLog.log("[InvitationAccept] Début handleFormSubmit");

    const validationErrors = validateForm();

    if (validationErrors.length > 0) {
      secureLog.log(
        "[InvitationAccept] Erreurs de validation:",
        validationErrors,
      );
      setErrors(validationErrors);
      return;
    }

    secureLog.log("[InvitationAccept] Validation formulaire passée");
    setIsProcessing(true);
    setErrors([]);

    try {
      secureLog.log("[InvitationAccept] Finalisation du compte via backend...");

      if (!userInfo?.accessToken) {
        throw new Error(t("invitation.errors.missingAccessToken"));
      }

      const requestBody = {
        access_token: userInfo.accessToken,
        fullName: `${formData.firstName.trim()} ${formData.lastName.trim()}`,
        firstName: formData.firstName.trim(),
        lastName: formData.lastName.trim(),
        email: formData.email.trim(),
        linkedinProfile: formData.linkedinProfile.trim() || null,
        country: formData.country,
        phone:
          formData.countryCode && formData.areaCode && formData.phoneNumber
            ? `${formData.countryCode} ${formData.areaCode}-${formData.phoneNumber}`
            : null,
        company: formData.companyName.trim() || t("common.notSpecified"),
        companyName: formData.companyName.trim() || null,
        companyWebsite: formData.companyWebsite.trim() || null,
        companyLinkedin: formData.companyLinkedin.trim() || null,
        jobTitle: formData.jobTitle.trim() || t("common.notSpecified"),
        password: formData.password,
      };

      const clientValidationErrors = [];
      if (!requestBody.firstName)
        clientValidationErrors.push(t("validation.required.firstName"));
      if (!requestBody.lastName)
        clientValidationErrors.push(t("validation.required.lastName"));
      if (!requestBody.fullName)
        clientValidationErrors.push(t("validation.required.fullName"));
      if (!requestBody.email)
        clientValidationErrors.push(t("validation.required.email"));
      if (!requestBody.country)
        clientValidationErrors.push(t("validation.required.country"));
      if (!requestBody.password)
        clientValidationErrors.push(t("validation.required.password"));
      if (!requestBody.access_token)
        clientValidationErrors.push(t("validation.required.accessToken"));

      if (clientValidationErrors.length > 0) {
        secureLog.error(
          "[InvitationAccept] Erreurs validation client:",
          clientValidationErrors,
        );
        throw new Error(
          t("validation.invalidData") +
            ": " +
            clientValidationErrors.join(", "),
        );
      }

      const API_BASE_URL =
        process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
      const completeResponse = await fetch(
        `${API_BASE_URL}/v1/auth/invitations/complete-profile`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        },
      );

      if (!completeResponse.ok) {
        let errorData;
        const contentType = completeResponse.headers.get("content-type");

        try {
          if (contentType && contentType.includes("application/json")) {
            errorData = await completeResponse.json();
          } else {
            const textResponse = await completeResponse.text();
            errorData = { detail: textResponse, rawResponse: textResponse };
          }
        } catch (parseError) {
          secureLog.error(
            "[InvitationAccept] Erreur parsing réponse:",
            parseError,
          );
          errorData = {
            detail: `${t("error.generic")} ${completeResponse.status}: ${completeResponse.statusText}`,
          };
        }

        let errorMessage = t("invitation.errors.profileCompletion");

        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail
              .map((err: any) => {
                if (typeof err === "string") return err;
                if (err.msg)
                  return `${err.loc ? err.loc.join(".") + ": " : ""}${err.msg}`;
                if (err.message) return err.message;
                return JSON.stringify(err);
              })
              .join(", ");
          } else if (typeof errorData.detail === "string") {
            errorMessage = errorData.detail;
          } else if (typeof errorData.detail === "object") {
            errorMessage =
              errorData.detail.message || JSON.stringify(errorData.detail);
          }
        }

        setProcessingResult({
          success: false,
          step: "completion",
          message: errorMessage,
          details: errorData,
        });
        throw new Error(errorMessage);
      }

      const completionResult = await completeResponse.json();
      secureLog.log(
        "[InvitationAccept] Profil finalisé avec succès:",
        completionResult,
      );

      setStatus("success");
      setMessage(t("invitation.success.accountCreated"));
      setProcessingResult({
        success: true,
        step: "completion",
        message: `${t("invitation.success.welcome")}, ${formData.firstName}`,
      });

      setTimeout(() => {
        secureLog.log("[InvitationAccept] Redirection vers chat");
        router.push(completionResult.redirect_url || "/chat");
      }, 2000);
    } catch (error: any) {
      secureLog.error("[InvitationAccept] Erreur finalisation compte:", error);

      let errorMessage = t("invitation.errors.accountCompletion");

      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === "string") {
        errorMessage = error;
      } else if (error && typeof error === "object") {
        errorMessage = error.message || error.detail || JSON.stringify(error);
      }

      setErrors([errorMessage]);
    } finally {
      setIsProcessing(false);
    }
  };

  const isFormValid = () => {
    return (
      formData.password &&
      formData.confirmPassword &&
      formData.password === formData.confirmPassword &&
      validatePassword(formData.password, t).length === 0 &&
      formData.firstName.trim() &&
      formData.lastName.trim() &&
      formData.email.trim() &&
      formData.country &&
      validatePhone(
        formData.countryCode,
        formData.areaCode,
        formData.phoneNumber,
        formData.country,
        countryCodeMap,
      )
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center mb-8">
          <InteliaLogo className="w-16 h-16" />
        </div>

        <h1 className="text-center text-3xl font-bold text-gray-900 mb-2">
          {t("common.appName")}
        </h1>
        <p className="text-center text-sm text-gray-600 mb-8">
          {status === "set-password"
            ? t("invitation.completeProfile")
            : t("invitation.finalizingInvitation")}
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-2xl">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
          {/* Statut Loading */}
          {status === "loading" && (
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                {t("invitation.processing")}
              </h2>
              <p className="text-sm text-gray-600">
                {message || t("invitation.validating")}
              </p>

              <div className="mt-4 text-xs text-gray-400">
                <p>{t("invitation.backendValidation")}</p>
                <p>{t("invitation.waitMessage")}</p>
              </div>

              {processingResult && processingResult.step === "validation" && (
                <div className="mt-6">
                  <ProcessingStatus result={processingResult} />
                </div>
              )}
            </div>
          )}

          {/* Formulaire de création de profil complet */}
          {status === "set-password" && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4 text-center">
                {t("invitation.welcomeComplete")}
              </h2>

              {userInfo && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="font-medium text-blue-900 mb-2">
                    {t("invitation.validatedSuccess")}
                  </h3>
                  <div className="text-sm text-blue-800 space-y-1">
                    <p>
                      <strong>{t("profile.email")}:</strong> {userInfo.email}
                    </p>
                    {userInfo.inviterName && (
                      <p>
                        <strong>{t("invitation.invitedBy")}:</strong>{" "}
                        {userInfo.inviterName}
                      </p>
                    )}
                    {userInfo.personalMessage && (
                      <div className="mt-2 p-2 bg-white rounded border">
                        <p className="text-xs text-gray-600 mb-1">
                          {t("invitation.personalMessage")}:
                        </p>
                        <p className="text-sm italic">
                          "{userInfo.personalMessage}"
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {usingFallback && !countriesLoading && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
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
                      {t("countries.limitedList")}
                    </span>
                  </div>
                </div>
              )}

              {/* Messages d'erreur */}
              {errors.length > 0 && (
                <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-3">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg
                        className="h-5 w-5 text-red-400"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">
                        {t("validation.correctErrors")}
                      </h3>
                      <div className="mt-1 text-sm text-red-700">
                        {errors.map((error, index) => (
                          <div
                            key={index}
                            className="flex items-start space-x-2"
                          >
                            <span className="text-red-500 font-bold">•</span>
                            <span>{error}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-6">
                {/* Section Informations personnelles */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    {t("profile.personalInfo")}
                  </h3>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        {t("profile.firstName")}{" "}
                        <span className="text-red-500">
                          {t("form.required")}
                        </span>
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.firstName}
                        onChange={(e) =>
                          handleInputChange("firstName", e.target.value)
                        }
                        placeholder={t("placeholder.firstName")}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        {t("profile.lastName")}{" "}
                        <span className="text-red-500">
                          {t("form.required")}
                        </span>
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.lastName}
                        onChange={(e) =>
                          handleInputChange("lastName", e.target.value)
                        }
                        placeholder={t("placeholder.lastName")}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      />
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t("profile.linkedinProfile")} {t("common.optional")}
                    </label>
                    <input
                      type="url"
                      value={formData.linkedinProfile}
                      onChange={(e) =>
                        handleInputChange("linkedinProfile", e.target.value)
                      }
                      placeholder={t("placeholder.linkedinPersonal")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>
                </div>

                {/* Section Contact */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    {t("profile.contact")}
                  </h3>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t("profile.email")}{" "}
                      <span className="text-red-500">{t("form.required")}</span>
                    </label>
                    <input
                      type="email"
                      required
                      value={formData.email}
                      onChange={(e) =>
                        handleInputChange("email", e.target.value)
                      }
                      placeholder={t("placeholder.email")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm bg-gray-50"
                      disabled={true}
                      readOnly
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      {t("invitation.emailFromInvitation")}
                    </p>
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t("profile.country")}{" "}
                      <span className="text-red-500">{t("form.required")}</span>
                    </label>
                    {countriesLoading ? (
                      <div className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-gray-50">
                        <div className="flex items-center space-x-2">
                          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                          <span className="text-sm text-gray-600">
                            {t("countries.loading")}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <select
                        required
                        value={formData.country}
                        onChange={(e) =>
                          handleInputChange("country", e.target.value)
                        }
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      >
                        <option value="">
                          {t("placeholder.countrySelect")}
                        </option>
                        {countries.map((country) => (
                          <option key={country.value} value={country.value}>
                            {country.flag} {country.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t("profile.phone")} {t("common.optional")}
                    </label>
                    <p className="text-xs text-gray-500 mb-2">
                      {t("invitation.phoneAutoFill")}
                    </p>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          {t("profile.countryCode")}
                        </label>
                        <input
                          type="text"
                          placeholder="+1"
                          value={formData.countryCode}
                          onChange={(e) =>
                            handleInputChange("countryCode", e.target.value)
                          }
                          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm bg-gray-50"
                          disabled={isProcessing}
                          readOnly
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          {t("profile.areaCode")}
                        </label>
                        <input
                          type="text"
                          placeholder="514"
                          value={formData.areaCode}
                          onChange={(e) =>
                            handleInputChange("areaCode", e.target.value)
                          }
                          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          disabled={isProcessing}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          {t("profile.phoneNumber")}
                        </label>
                        <input
                          type="text"
                          placeholder="1234567"
                          value={formData.phoneNumber}
                          onChange={(e) =>
                            handleInputChange("phoneNumber", e.target.value)
                          }
                          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          disabled={isProcessing}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Section Entreprise */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    {t("profile.company")}
                  </h3>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t("profile.companyName")} {t("common.optional")}
                    </label>
                    <input
                      type="text"
                      value={formData.companyName}
                      onChange={(e) =>
                        handleInputChange("companyName", e.target.value)
                      }
                      placeholder={t("placeholder.companyName")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t("profile.companyWebsite")} {t("common.optional")}
                    </label>
                    <input
                      type="url"
                      value={formData.companyWebsite}
                      onChange={(e) =>
                        handleInputChange("companyWebsite", e.target.value)
                      }
                      placeholder={t("placeholder.companyWebsite")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t("profile.companyLinkedin")} {t("common.optional")}
                    </label>
                    <input
                      type="url"
                      value={formData.companyLinkedin}
                      onChange={(e) =>
                        handleInputChange("companyLinkedin", e.target.value)
                      }
                      placeholder={t("placeholder.linkedinCorporate")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t("profile.jobTitle")} {t("common.optional")}
                    </label>
                    <input
                      type="text"
                      value={formData.jobTitle}
                      onChange={(e) =>
                        handleInputChange("jobTitle", e.target.value)
                      }
                      placeholder={t("placeholder.jobTitle")}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>
                </div>

                {/* Section Mot de passe */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    {t("profile.security")}
                  </h3>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t("profile.password")}{" "}
                      <span className="text-red-500">{t("form.required")}</span>
                    </label>
                    <div className="mt-1 relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={formData.password}
                        onChange={(e) =>
                          handleInputChange("password", e.target.value)
                        }
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        onClick={() => setShowPassword(!showPassword)}
                        disabled={isProcessing}
                      >
                        {showPassword ? (
                          <svg
                            className="h-5 w-5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"
                            />
                          </svg>
                        ) : (
                          <svg
                            className="h-5 w-5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                            />
                          </svg>
                        )}
                      </button>
                    </div>

                    {formData.password && (
                      <div className="mt-3 bg-gray-50 rounded-lg p-3">
                        <h5 className="text-sm font-medium text-gray-900 mb-2">
                          {t("validation.password.requirements")}:
                        </h5>
                        <ul className="text-xs text-gray-600 space-y-1">
                          <li className="flex items-center space-x-2">
                            <span
                              className={
                                formData.password.length >= 8
                                  ? "text-green-600"
                                  : "text-gray-400"
                              }
                            >
                              {formData.password.length >= 8 ? "✓" : "○"}
                            </span>
                            <span>{t("validation.password.minLength")}</span>
                          </li>
                          <li className="flex items-center space-x-2">
                            <span
                              className={
                                /[A-Z]/.test(formData.password)
                                  ? "text-green-600"
                                  : "text-gray-400"
                              }
                            >
                              {/[A-Z]/.test(formData.password) ? "✓" : "○"}
                            </span>
                            <span>{t("validation.password.uppercase")}</span>
                          </li>
                          <li className="flex items-center space-x-2">
                            <span
                              className={
                                /[a-z]/.test(formData.password)
                                  ? "text-green-600"
                                  : "text-gray-400"
                              }
                            >
                              {/[a-z]/.test(formData.password) ? "✓" : "○"}
                            </span>
                            <span>{t("validation.password.lowercase")}</span>
                          </li>
                          <li className="flex items-center space-x-2">
                            <span
                              className={
                                /\d/.test(formData.password)
                                  ? "text-green-600"
                                  : "text-gray-400"
                              }
                            >
                              {/\d/.test(formData.password) ? "✓" : "○"}
                            </span>
                            <span>{t("validation.password.number")}</span>
                          </li>
                          <li className="flex items-center space-x-2">
                            <span
                              className={
                                /[!@#$%^&*(),.?":{}|<>]/.test(formData.password)
                                  ? "text-green-600"
                                  : "text-gray-400"
                              }
                            >
                              {/[!@#$%^&*(),.?":{}|<>]/.test(formData.password)
                                ? "✓"
                                : "○"}
                            </span>
                            <span>{t("validation.password.special")}</span>
                          </li>
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t("profile.confirmPassword")}{" "}
                      <span className="text-red-500">{t("form.required")}</span>
                    </label>
                    <div className="mt-1 relative">
                      <input
                        type={showConfirmPassword ? "text" : "password"}
                        required
                        value={formData.confirmPassword}
                        onChange={(e) =>
                          handleInputChange("confirmPassword", e.target.value)
                        }
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        onClick={() =>
                          setShowConfirmPassword(!showConfirmPassword)
                        }
                        disabled={isProcessing}
                      >
                        {showConfirmPassword ? (
                          <svg
                            className="h-5 w-5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"
                            />
                          </svg>
                        ) : (
                          <svg
                            className="h-5 w-5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                            />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {formData.password && formData.confirmPassword && (
                    <div className="mt-2 text-xs">
                      {formData.confirmPassword === formData.password ? (
                        <span className="text-green-600 flex items-center">
                          <svg
                            className="w-3 h-3 mr-1"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                          {t("validation.password.match")}
                        </span>
                      ) : (
                        <span className="text-red-600 flex items-center">
                          <svg
                            className="w-3 h-3 mr-1"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                          {t("validation.password.mismatch")}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleFormSubmit}
                  disabled={isProcessing || !isFormValid()}
                  className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isProcessing ? (
                    <div className="flex items-center justify-center space-x-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>{t("invitation.creatingAccount")}</span>
                    </div>
                  ) : (
                    t("invitation.createAccount")
                  )}
                </button>
              </div>
            </div>
          )}

          {(status === "success" || status === "error") && processingResult && (
            <ProcessingStatus result={processingResult} />
          )}

          <div className="mt-8 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center">
              {t("invitation.needHelp")} {t("contact.supportEmail")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function InvitationAcceptPage() {
  const { t } = useTranslation();

  return (
    <React.Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
          <div className="text-center">
            <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">{t("invitation.loadingInvitation")}</p>
          </div>
        </div>
      }
    >
      <InvitationAcceptPageContent />
    </React.Suspense>
  );
}
