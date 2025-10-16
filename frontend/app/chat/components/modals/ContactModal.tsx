"use client";

import React from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { BaseDialog } from "../BaseDialog";

interface ContactModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ContactModal: React.FC<ContactModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { t, currentLanguage } = useTranslation();

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
    <BaseDialog isOpen={isOpen} onClose={onClose} title={t("nav.contact")}>
      <div className="space-y-4">
        {/* Call Us */}
        <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
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

        {/* Email Us */}
        <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
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

        {/* Visit our website */}
        <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
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
                d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3s-4.5 4.03-4.5 9 2.015 9 4.5 9zm0 0c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3s4.5 4.03 4.5 9-2.015 9-4.5 9z"
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

        <div className="flex justify-end pt-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            {t("modal.close")}
          </button>
        </div>
      </div>
    </BaseDialog>
  );
};
