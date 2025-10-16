// app/about/page.tsx
"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useTranslation } from "@/lib/languages/i18n";

const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <img src="/images/favicon.png" alt="Intelia Logo" className={className} />
);

export default function AboutPage() {
  const { t, currentLanguage } = useTranslation();

  // Fix: Ensure scroll is enabled (Radix Dialog may disable it)
  useEffect(() => {
    document.body.style.overflow = "auto";
    document.body.style.paddingRight = "0px";
    return () => {
      document.body.style.overflow = "";
      document.body.style.paddingRight = "";
    };
  }, []);

  // Générer l'URL en fonction de la langue
  const getWebsiteUrl = () => {
    const baseUrl = "https://intelia.com";

    switch (currentLanguage) {
      case "fr":
        return `${baseUrl}/fr/`;
      case "es":
        return `${baseUrl}/es/`;
      case "en":
      default:
        return baseUrl;
    }
  };

  const websiteUrl = getWebsiteUrl();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <Link
              href="/chat"
              className="flex items-center space-x-3 hover:opacity-80 transition-opacity"
            >
              <InteliaLogo className="w-8 h-8" />
              <span className="text-xl font-bold text-gray-900">
                {t("common.appName")}
              </span>
            </Link>
            <Link
              href="/chat"
              className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
            >
              {t("about.backToHome")}
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-lg border p-6 sm:p-8">
          {/* Header avec icône */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-blue-600"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
                />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {t("about.pageTitle")}
            </h1>
            <p className="text-gray-600">{t("about.introduction")}</p>
          </div>

          {/* Section Nous joindre */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <svg
                className="w-6 h-6 text-blue-600 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z"
                />
              </svg>
              {t("nav.contact")}
            </h2>

            <div className="space-y-4">
              {/* Téléphone */}
              <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200">
                <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                  <svg
                    className="w-6 h-6 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 mb-1">
                    {t("contact.phone")}
                  </h3>
                  <p className="text-sm text-gray-600 mb-2">
                    {t("contact.phoneDescription")}
                  </p>
                  <a
                    href="tel:+18666666221"
                    className="text-blue-600 hover:text-blue-700 font-medium text-sm transition-colors"
                  >
                    +1 (866) 666 6221
                  </a>
                </div>
              </div>

              {/* Email */}
              <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200">
                <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                  <svg
                    className="w-6 h-6 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 mb-1">
                    {t("contact.email")}
                  </h3>
                  <p className="text-sm text-gray-600 mb-2">
                    {t("contact.emailDescription")}
                  </p>
                  <a
                    href="mailto:support@intelia.com"
                    className="text-blue-600 hover:text-blue-700 font-medium text-sm transition-colors"
                  >
                    support@intelia.com
                  </a>
                </div>
              </div>

              {/* Site web */}
              <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200">
                <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                  <svg
                    className="w-6 h-6 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3s-4.5 4.03-4.5 9 2.015 9 4.5 9z"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 mb-1">
                    {t("contact.website")}
                  </h3>
                  <p className="text-sm text-gray-600 mb-2">
                    {t("contact.websiteDescription")}
                  </p>
                  <a
                    href={websiteUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-700 font-medium text-sm transition-colors"
                  >
                    {websiteUrl}
                  </a>
                </div>
              </div>
            </div>
          </section>

          {/* Section Mentions légales */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <svg
                className="w-6 h-6 text-blue-600 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875v12.75c0 .621.504 1.125 1.125 1.125h2.25"
                />
              </svg>
              {t("nav.legal")}
            </h2>

            <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-1">
                  {t("legal.privacy")}
                </h3>
                <p className="text-sm text-gray-600 mb-2">
                  {t("about.thirdPartyIntro")}
                </p>
                <a
                  href="https://intelia.com/privacy-policy/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-700 font-medium text-sm transition-colors inline-flex items-center"
                >
                  {t("legal.privacy")}
                  <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                  </svg>
                </a>
              </div>
            </div>
          </section>

          {/* Section Licences Open Source */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <svg
                className="w-6 h-6 text-blue-600 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
                />
              </svg>
              {t("about.openSourceLicenses")}
            </h2>

            <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-1">
                  {t("about.openSourceLicenses")}
                </h3>
                <p className="text-sm text-gray-600 mb-2">
                  {t("about.licensesUsed")}
                </p>
                <ul className="text-sm text-gray-600 space-y-1 mb-3">
                  <li>• MIT License</li>
                  <li>• Apache License 2.0</li>
                  <li>• BSD 3-Clause License</li>
                  <li>• ISC License</li>
                  <li>• Python Software Foundation License</li>
                </ul>
                <a
                  href="/THIRD_PARTY_NOTICES.md"
                  download
                  className="text-blue-600 hover:text-blue-700 font-medium text-sm transition-colors inline-flex items-center"
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {t("about.downloadFull")}
                </a>
              </div>
            </div>
          </section>

          {/* Section Information sur la version */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <svg
                className="w-6 h-6 text-blue-600 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
                />
              </svg>
              {t("about.versionInfo")}
            </h2>

            <div className="flex items-start space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 6h.008v.008H6V6z"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-1">
                  {t("about.versionInfo")}
                </h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p><span className="font-medium">{t("about.version")}:</span> 1.0.0</p>
                  <p><span className="font-medium">{t("about.lastUpdated")}:</span> January 2025</p>
                  <p><span className="font-medium">{t("about.license")}:</span> Proprietary</p>
                </div>
              </div>
            </div>
          </section>

          {/* Footer */}
          <div className="text-center pt-6 border-t border-gray-100">
            <Link
              href="/chat"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
              </svg>
              {t("about.backToHome")}
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
