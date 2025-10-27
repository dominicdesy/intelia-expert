/**
 * Page
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { useTranslation, availableLanguages } from "@/lib/languages/i18n";
import { secureLog } from "@/lib/utils/secureLogger";

// ==================== VALIDATION MOT DE PASSE SYNCHRONISÉE AVEC PAGE.TSX ====================
const validatePassword = (
  password: string,
  t: (key: string) => string,
): string[] => {
  const errors: string[] = [];

  if (!password || password.trim().length === 0) {
    errors.push(t("validation.required.password"));
    return errors;
  }

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

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
  <img src="/images/favicon.png" alt="Intelia Logo" className={className} />
);

// ==================== ICONES ====================
const EyeIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
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
);

const EyeSlashIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.34 6.34m6.822 10.565l-3.536-3.536"
    />
  </svg>
);

// ==================== INDICATEUR DE FORCE INTERNATIONALISÉ ====================
const PasswordStrengthIndicator: React.FC<{
  password: string;
  t: (key: string) => string;
}> = ({ password, t }) => {
  const validation = { errors: validatePassword(password, t) };

  const requirements = [
    { test: password.length >= 8, label: t("validation.password.minLength") },
    {
      test: /[A-Z]/.test(password),
      label: t("validation.password.uppercase"),
    },
    {
      test: /[a-z]/.test(password),
      label: t("validation.password.lowercase"),
    },
    { test: /\d/.test(password), label: t("validation.password.number") },
    {
      test: /[!@#$%^&*(),.?":{}|<>]/.test(password),
      label: t("validation.password.special"),
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
    if (strength < 0.4) return t("resetPassword.strength.weak");
    if (strength < 0.7) return t("resetPassword.strength.medium");
    if (strength < 0.9) return t("resetPassword.strength.good");
    return t("resetPassword.strength.excellent");
  };

  return (
    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-gray-700">
          {t("resetPassword.passwordStrength")}
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
          <p className="text-xs text-gray-600 font-medium mb-1">
            {t("resetPassword.tips")}:
          </p>
          <ul className="text-xs text-gray-600 space-y-1">
            {password.length < 12 && (
              <li>• {t("resetPassword.tip.longerPassword")}</li>
            )}
            {!/[A-Z]/.test(password) && !/[a-z]/.test(password) && (
              <li>• {t("resetPassword.tip.mixCase")}</li>
            )}
            {!/[!@#$%^&*()_+=\[\]{};':"|,.<>?-]/.test(password) && (
              <li>• {t("resetPassword.tip.specialChars")}</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};

// ==================== COMPOSANT CHAMP MOT DE PASSE ====================
interface PasswordFieldProps {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  label: string;
  disabled?: boolean;
  showStrength?: boolean;
  confirmValue?: string;
  isConfirmField?: boolean;
  t: (key: string) => string;
}

const PasswordField: React.FC<PasswordFieldProps> = ({
  value,
  onChange,
  placeholder,
  label,
  disabled = false,
  showStrength = false,
  confirmValue,
  isConfirmField = false,
  t,
}) => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>
      <div className="relative">
        <input
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 pr-10 transition-colors"
          placeholder={placeholder}
          disabled={disabled}
          autoComplete={isConfirmField ? "new-password" : "new-password"}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-600 transition-colors"
          disabled={disabled}
        >
          {showPassword ? (
            <EyeSlashIcon className="h-5 w-5 text-gray-400" />
          ) : (
            <EyeIcon className="h-5 w-5 text-gray-400" />
          )}
        </button>
      </div>

      {showStrength && value && (
        <PasswordStrengthIndicator password={value} t={t} />
      )}

      {isConfirmField && value && confirmValue && (
        <div className="mt-1 text-xs">
          {confirmValue === value ? (
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
  );
};

// ==================== PAGE SUCCES ====================
const SuccessPage = ({ t }: { t: (key: string) => string }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      window.location.href = "https://expert.intelia.com/";
    }, 3000);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <div className="bg-white p-8 rounded-lg shadow-lg border border-gray-200">
          <div className="text-6xl mb-4">✅</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            {t("success.passwordChanged")}
          </h1>
          <p className="text-gray-600 mb-6 leading-relaxed">
            {t("resetPassword.success.description")}
          </p>
          <div className="flex justify-center mb-4">
            <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full"></div>
          </div>
          <a
            href="https://expert.intelia.com/"
            className="inline-block text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            {t("resetPassword.success.goToSite")}
          </a>
        </div>
      </div>
    </div>
  );
};

// ==================== PAGE ERREUR TOKEN ====================
const InvalidTokenPage = ({ t }: { t: (key: string) => string }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <div className="bg-white p-8 rounded-lg shadow-lg border border-gray-200">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            {t("resetPassword.invalidToken.title")}
          </h1>
          <p className="text-gray-600 mb-6 leading-relaxed">
            {t("resetPassword.invalidToken.description")}
          </p>
          <div className="space-y-3">
            <a
              href="https://expert.intelia.com/forgot-password"
              className="block w-full py-2 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t("resetPassword.invalidToken.requestNew")}
            </a>
            <a
              href="https://expert.intelia.com/"
              className="block text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
            >
              {t("resetPassword.invalidToken.backToSite")}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

// ==================== PAGE CONTENU PRINCIPAL ====================
function ResetPasswordPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, user } = useAuthStore();
  const { t, changeLanguage } = useTranslation();

  const [formData, setFormData] = useState({
    newPassword: "",
    confirmPassword: "",
    email: "",  // NOUVEAU: pour les codes OTP
  });
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [success, setSuccess] = useState(false);
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isOtpToken, setIsOtpToken] = useState(false);  // NOUVEAU: détecter si c'est un OTP

  // 🌍 DÉTECTION DE LANGUE DEPUIS L'URL
  useEffect(() => {
    const langParam = searchParams.get("lang");
    if (langParam && availableLanguages.some((l) => l.code === langParam)) {
      secureLog.log("[ResetPassword] Changement de langue détecté:", langParam);
      changeLanguage(langParam);
    }
  }, [searchParams, changeLanguage]);

  // Extraction du token (conservé identique)
  useEffect(() => {
    const extractTokenFromUrl = () => {
      const resetToken = searchParams.get("token");
      const accessTokenQuery = searchParams.get("access_token");

      let accessTokenHash = null;
      if (typeof window !== "undefined") {
        const hash = window.location.hash.substring(1);
        const hashParams = new URLSearchParams(hash);
        accessTokenHash = hashParams.get("access_token");
      }

      return resetToken || accessTokenQuery || accessTokenHash;
    };

    const finalToken = extractTokenFromUrl();
    secureLog.log(`[ResetPassword] Token détecté: ${finalToken ? "Présent" : "Absent"} `);

    if (!finalToken) {
      setTokenValid(false);
      return;
    }

    // NOUVEAU: Détecter si c'est un code OTP (court, 6-8 chiffres)
    const isShortOtp = finalToken.length <= 10 && /^\d+$/.test(finalToken);
    if (isShortOtp) {
      secureLog.log(`[ResetPassword] Code OTP détecté (${finalToken.length} chiffres)`);
      setIsOtpToken(true);
    } else {
      secureLog.log(`[ResetPassword] Token JWT détecté (${finalToken.length} chars)`);
      setIsOtpToken(false);
    }

    setToken(finalToken);
    setTokenValid(true);
  }, [searchParams]);

  // Redirection si déjà connecté
  useEffect(() => {
    if (isAuthenticated && user) {
      router.push("/chat");
    }
  }, [isAuthenticated, user, router]);

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors.length > 0) {
      setErrors([]);
    }
  };

  const handleSubmit = async () => {
    const validationErrors: string[] = [];

    // NOUVEAU: Valider l'email pour les codes OTP
    if (isOtpToken && !formData.email.trim()) {
      validationErrors.push(t("validation.required.email"));
    }
    if (isOtpToken && formData.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
      validationErrors.push("Invalid email format");
    }

    if (!formData.newPassword) {
      validationErrors.push(t("validation.required.password"));
    }
    if (!formData.confirmPassword) {
      validationErrors.push(t("validation.required.confirmPassword"));
    }
    if (formData.newPassword !== formData.confirmPassword) {
      validationErrors.push(t("validation.password.mismatch"));
    }

    const passwordValidationErrors = validatePassword(formData.newPassword, t);
    validationErrors.push(...passwordValidationErrors);

    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsLoading(true);
    setErrors([]);

    try {
      // NOUVEAU: Inclure l'email pour les codes OTP
      const requestBody: any = {
        token: token,
        new_password: formData.newPassword,
      };

      if (isOtpToken && formData.email.trim()) {
        requestBody.email = formData.email.trim();
        secureLog.log(`[ResetPassword] Envoi OTP avec email: ${formData.email.trim()}`);
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/auth/confirm-reset-password`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        },
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Erreur ${response.status}`);
      }

      setSuccess(true);
    } catch (error: any) {
      secureLog.error("[ResetPassword] Erreur:", error);

      if (error.message.includes("400")) {
        setErrors([t("resetPassword.errors.tokenExpired")]);
      } else if (error.message.includes("429")) {
        setErrors([t("resetPassword.errors.tooManyAttempts")]);
      } else if (error.message.includes("Failed to fetch")) {
        setErrors([t("resetPassword.errors.connectionProblem")]);
      } else {
        setErrors([error.message || t("resetPassword.errors.generic")]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const isFormValid = () => {
    // NOUVEAU: Valider aussi l'email pour les codes OTP
    const emailValid = !isOtpToken || (formData.email.trim() && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim()));

    return (
      emailValid &&
      formData.newPassword &&
      formData.confirmPassword &&
      formData.newPassword === formData.confirmPassword &&
      validatePassword(formData.newPassword, t).length === 0
    );
  };

  // États de chargement
  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{t("common.loading")}</p>
        </div>
      </div>
    );
  }

  if (success) {
    return <SuccessPage t={t} />;
  }

  if (tokenValid === false) {
    return <InvalidTokenPage t={t} />;
  }

  if (tokenValid === null) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{t("resetPassword.validatingLink")}</p>
        </div>
      </div>
    );
  }

  // Formulaire principal
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <InteliaLogo className="w-12 h-12" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {t("resetPassword.title")}
          </h1>
          <p className="text-gray-600 leading-relaxed">
            {t("resetPassword.description")}
          </p>
        </div>

        {/* Messages d'erreur */}
        {errors.length > 0 && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="text-sm text-red-800">
              {errors.map((error, index) => (
                <div key={index} className="flex items-start space-x-2">
                  <span className="text-red-500 font-bold">•</span>
                  <span>{error}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Formulaire */}
        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="space-y-6">
            {/* NOUVEAU: Champ email pour les codes OTP */}
            {isOtpToken && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t("forgotPassword.emailLabel")}
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange("email", e.target.value)}
                  className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  placeholder={t("forgotPassword.emailPlaceholder")}
                  disabled={isLoading}
                  autoComplete="email"
                />
                <p className="mt-1 text-xs text-gray-500">
                  {t("forgotPassword.otpEmailHint")}
                </p>
              </div>
            )}

            <PasswordField
              value={formData.newPassword}
              onChange={(value) => handleInputChange("newPassword", value)}
              label={t("resetPassword.newPassword")}
              placeholder={t("placeholder.createSecurePassword")}
              showStrength={true}
              disabled={isLoading}
              t={t}
            />

            <PasswordField
              value={formData.confirmPassword}
              onChange={(value) => handleInputChange("confirmPassword", value)}
              label={t("resetPassword.confirmPassword")}
              placeholder={t("placeholder.confirmNewPassword")}
              confirmValue={formData.newPassword}
              isConfirmField={true}
              disabled={isLoading}
              t={t}
            />

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !isFormValid()}
              className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>{t("resetPassword.updating")}</span>
                </div>
              ) : (
                t("resetPassword.updateButton")
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <div className="mt-6 text-center">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            <svg
              className="w-4 h-4 mr-1"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            {t("resetPassword.backToLogin")}
          </Link>
        </div>

        {/* Information sécurité */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500 leading-relaxed">
            🔒 {t("resetPassword.securityInfo")}
          </p>
        </div>

        {/* Support */}
        <div className="mt-4 p-3 bg-gray-50 rounded-lg text-center">
          <p className="text-xs text-gray-600">
            {t("resetPassword.needHelp")}{" "}
            <button
              type="button"
              onClick={() =>
                window.open(
                  "mailto:cognito@intelia.com?subject=Problème réinitialisation mot de passe",
                  "_blank",
                )
              }
              className="text-blue-600 hover:underline font-medium transition-colors"
            >
              {t("resetPassword.contactSupport")}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

// ==================== EXPORT PRINCIPAL ====================
export default function ResetPasswordPage() {
  const { t } = useTranslation();

  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
          <div className="text-center">
            <img
              src="/images/favicon.png"
              alt="Intelia Logo"
              className="w-16 h-16 mx-auto mb-4"
            />
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">
              {t ? t("common.loading") : "Chargement..."}
            </p>
          </div>
        </div>
      }
    >
      <ResetPasswordPageContent />
    </Suspense>
  );
}
