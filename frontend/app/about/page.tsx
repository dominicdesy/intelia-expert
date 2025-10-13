// app/about/page.tsx
"use client";

import React from "react";
import Link from "next/link";
import { useTranslation } from "@/lib/languages/i18n";

const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <img src="/images/favicon.png" alt="Intelia Logo" className={className} />
);

export default function AboutPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <Link
              href="/"
              className="flex items-center space-x-3 hover:opacity-80 transition-opacity"
            >
              <InteliaLogo className="w-8 h-8" />
              <span className="text-xl font-bold text-gray-900">
                {t("common.appName")}
              </span>
            </Link>
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
            >
              {t("about.backToHome")}
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-sm border p-8">
          <div className="prose prose-gray max-w-none">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">
              {t("about.pageTitle")}
            </h1>

            <p className="text-gray-700 leading-relaxed mb-6">
              {t("about.introduction")}
            </p>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                {t("about.companyInformation")}
              </h2>

              <div className="bg-gray-50 p-6 rounded-lg">
                <p className="font-semibold text-gray-900 mb-2">
                  {t("about.companyName")}
                </p>
                <p className="text-gray-700 mb-3">{t("about.location")}</p>

                <div className="space-y-1">
                  <p className="text-gray-700">
                    <span className="font-medium">{t("about.email")}:</span>{" "}
                    <a
                      href="mailto:confidentialite@intelia.com"
                      className="text-blue-600 hover:text-blue-700 underline"
                    >
                      confidentialite@intelia.com
                    </a>
                  </p>
                  <p className="text-gray-700">
                    <span className="font-medium">{t("about.website")}:</span>{" "}
                    <a
                      href="https://intelia.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-700 underline"
                    >
                      https://intelia.com
                    </a>
                  </p>
                </div>
              </div>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                {t("about.thirdPartyNotices")}
              </h2>

              <p className="text-gray-700 mb-4">
                {t("about.thirdPartyIntro")}
              </p>

              <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
                <p className="text-blue-800 font-semibold mb-2">
                  {t("about.openSourceLicenses")}
                </p>
                <p className="text-blue-700 text-sm mb-3">
                  {t("about.licensesUsed")}
                </p>
                <ul className="text-blue-700 text-sm space-y-1 list-disc pl-5">
                  <li>MIT License</li>
                  <li>Apache License 2.0</li>
                  <li>BSD 3-Clause License</li>
                  <li>ISC License</li>
                  <li>Python Software Foundation License</li>
                  <li>Other open source licenses</li>
                </ul>
              </div>

              <div className="flex space-x-4">
                <a
                  href="/THIRD_PARTY_NOTICES.md"
                  download
                  className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {t("about.downloadFull")}
                </a>
              </div>

              <p className="text-sm text-gray-500 mt-4">
                {t("about.downloadDescription")}
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                {t("about.technologyStack")}
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-2">{t("about.frontend")}</h3>
                  <ul className="text-gray-700 text-sm space-y-1">
                    <li>• Next.js (React)</li>
                    <li>• TypeScript</li>
                    <li>• Tailwind CSS</li>
                  </ul>
                </div>

                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-2">{t("about.backend")}</h3>
                  <ul className="text-gray-700 text-sm space-y-1">
                    <li>• Python</li>
                    <li>• FastAPI</li>
                    <li>• PostgreSQL</li>
                  </ul>
                </div>

                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-2">{t("about.aiml")}</h3>
                  <ul className="text-gray-700 text-sm space-y-1">
                    <li>• Anthropic Claude</li>
                    <li>• Sentence Transformers</li>
                    <li>• Weaviate Vector Database</li>
                  </ul>
                </div>

                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-2">{t("about.infrastructure")}</h3>
                  <ul className="text-gray-700 text-sm space-y-1">
                    <li>• Docker</li>
                    <li>• DigitalOcean</li>
                    <li>• CI/CD</li>
                  </ul>
                </div>
              </div>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                {t("about.versionInfo")}
              </h2>

              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-700 mb-2">
                  <span className="font-medium">{t("about.version")}:</span> 1.0.0
                </p>
                <p className="text-gray-700 mb-2">
                  <span className="font-medium">{t("about.lastUpdated")}:</span> January 2025
                </p>
                <p className="text-gray-700">
                  <span className="font-medium">{t("about.license")}:</span> Proprietary
                </p>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
