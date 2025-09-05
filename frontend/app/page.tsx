"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslation } from "@/lib/languages/i18n";
import { useAuthStore } from "@/lib/stores/auth";
import { CheckCircle2, AlertCircle, Loader2, ArrowRight } from "lucide-react";

// ⬇️ Réutilisation de TES composants factorisés
import {
  InteliaLogo,
  LanguageSelector,
  AlertMessage,
  PasswordInput,
  LoadingSpinner,
  AuthFooter,
} from "./page_components";

/**
 * Modern Login UI (split)
 * - Réutilise tes composants: LanguageSelector, PasswordInput, AlertMessage, AuthFooter, InteliaLogo
 * - Compatible avec useTranslation + useAuthStore existants
 */

// --- Bannière de callback auth (gère ?auth=success|error|incomplete) ---
function AuthCallbackBanner() {
  const sp = useSearchParams();
  const { t } = useTranslation();
  const [msg, setMsg] = useState("");

  React.useEffect(() => {
    const s = sp?.get("auth");
    if (!s) return;
    const map: Record<string, string> = {
      success: t("auth.success"),
      error: t("auth.error"),
      incomplete: t("auth.incomplete"),
    };
    setMsg(map[s] || "");

    try {
      const url = new URL(window.location.href);
      url.searchParams.delete("auth");
      window.history.replaceState({}, "", url.pathname);
    } catch {}

    const timer = setTimeout(() => setMsg(""), 3000);
    return () => clearTimeout(timer);
  }, [sp, t]);

  if (!msg) return null;
  return (
    <div className="mb-4 p-3 bg-blue-50 border border-blue-200 text-blue-700 rounded text-sm">
      {msg}
    </div>
  );
}

// --- Panneau marque (gauche) ---
function BrandPanel() {
  const { t } = useTranslation();
  // Helper pour contourner la contrainte de type strict sur t()
  const tr = (key: string) => (t as unknown as (k: string) => string)(key);
  const subtitle = tr("page.subtitle");

  return (
    <div className="relative hidden w-0 flex-1 items-center justify-center overflow-hidden bg-gradient-to-br from-blue-600 via-indigo-600 to-emerald-500 p-12 text-white lg:flex">
      <div className="pointer-events-none absolute inset-0 opacity-20 [background:radial-gradient(600px_300px_at_10%_-10%,white,transparent_60%),radial-gradient(600px_300px_at_80%_110%,white,transparent_60%)]"/>
      <div className="relative z-10 max-w-xl">
        <div className="mb-6 inline-flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-2 backdrop-blur">
          <InteliaLogo className="h-8 w-8" />
          <span className="text-sm font-medium tracking-wide">Intelia Expert</span>
        </div>
        <h2 className="text-3xl font-semibold leading-tight sm:text-4xl">{t("page.title")}</h2>
        <p className="mt-4 text-white/90">
          {subtitle && subtitle !== "page.subtitle"
            ? subtitle
            : "Transform farm data into clear decisions — faster."}
        </p>
        <ul className="mt-6 space-y-3 text-white/90">
          {[t("benefit.fast"), t("benefit.secure"), t("benefit.multilingual")].map((b, i) => (
            <li key={i} className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0" />
              <span>{b}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// --- Carte de connexion (droite) ---
function LoginCard() {
  const router = useRouter();
  const { t } = useTranslation();
  const { login } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    setSuccess(null);
    if (!email.trim()) return setError(t("error.emailRequired"));
    if (!password) return setError(t("validation.required.password"));
    setLoading(true);
    try {
      await login(email.trim(), password);
      setSuccess(t("auth.success"));
      setTimeout(() => router.push("/chat"), 600);
    } catch (e: any) {
      if (e?.message?.includes("Invalid login credentials")) setError(t("auth.invalidCredentials"));
      else if (e?.message?.includes("Email not confirmed")) setError(t("auth.emailNotConfirmed"));
      else setError(e?.message || t("auth.error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white/80 p-6 shadow-xl backdrop-blur-md sm:p-8">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <InteliaLogo className="h-10 w-10" />
          <div>
            <h1 className="text-lg font-semibold leading-tight text-gray-900">Intelia Expert</h1>
            <p className="text-xs text-gray-500">AI Advisor</p>
          </div>
        </div>
        <LanguageSelector />
      </div>

      <Suspense fallback={null}>
        <AuthCallbackBanner />
      </Suspense>

      {error && (
        <AlertMessage type="error" title="" message={error} />
      )}
      {success && (
        <AlertMessage type="success" title="" message={success} />
      )}

      <div className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">
            {t("login.emailLabel")}
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            className="input-primary"
            placeholder={t("login.emailPlaceholder")}
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">
            {t("login.passwordLabel")}
          </label>
          <PasswordInput
            id="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t("login.passwordPlaceholder")}
          />
        </div>

        <div className="flex items-center justify-between pt-1">
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            {t("login.rememberMe")}
          </label>
          <Link href="/auth/forgot-password" className="text-sm font-medium text-blue-600 hover:text-blue-700">
            {t("auth.forgotPassword")}
          </Link>
        </div>

        <button
          onClick={submit}
          disabled={loading}
          className="btn-primary group flex w-full items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              {t("auth.connecting")}
            </>
          ) : (
            <>
              {t("auth.login")} <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </>
          )}
        </button>

        <div className="relative py-2 text-center text-xs text-gray-500">
          <span className="bg-white px-2">{t("common.or")}</span>
          <div className="absolute inset-x-0 top-1/2 -z-10 h-px -translate-y-1/2 bg-gray-200" />
        </div>

        {/* Boutons SSO placeholders – à connecter plus tard */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <button className="btn-secondary">LinkedIn</button>
          <button className="btn-secondary">Facebook</button>
        </div>

        <p className="pt-2 text-center text-sm text-gray-600">
          {t("auth.newToIntelia")} {" "}
          <Link href="#signup" onClick={(e) => { e.preventDefault(); const ev = new CustomEvent("openSignup"); window.dispatchEvent(ev); }} className="font-medium text-blue-600 hover:text-blue-700">
            {t("auth.createAccount")}
          </Link>
        </p>

        <AuthFooter />
      </div>
    </div>
  );
}

// --- Loading fallback ---
const PageLoading = () => <LoadingSpinner />;

// --- Page export ---
export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>      
      <main className="min-h-screen bg-[radial-gradient(40rem_40rem_at_100%_-10%,#dbeafe,transparent_60%),radial-gradient(40rem_40rem_at_-20%_110%,#dcfce7,transparent_60%)]">
        <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 items-center gap-0 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
          <BrandPanel />
          <div className="flex w-full items-center justify-center py-12 sm:py-16">
            <LoginCard />
          </div>
        </div>
      </main>
    </Suspense>
  );
}
