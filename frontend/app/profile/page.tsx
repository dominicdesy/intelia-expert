"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { useTranslation } from "react-i18next";
import Link from "next/link";
import {
  getSafeName,
  getSafeEmail,
  getSafeUserType,
  getSafeCreatedDate,
  getBadgeColor,
  getUserTypeLabel,
} from "../chat/utils/safeUserHelpers";

// Icônes SVG (inchangées)
const UserIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
    />
  </svg>
);

const CogIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
    />
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
    />
  </svg>
);

const ShieldCheckIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.623 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
    />
  </svg>
);

const ArrowLeftIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"
    />
  </svg>
);

const FingerprintIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M7.864 4.243A7.5 7.5 0 0119.5 10.5c0 2.92-.556 5.709-1.568 8.268M5.742 6.364A7.465 7.465 0 004.5 10.5a7.464 7.464 0 01-1.15 3.993m1.989 3.559A11.209 11.209 0 008.25 10.5a3.75 3.75 0 117.5 0c0 .527-.021 1.049-.064 1.565M12 10.5a14.94 14.94 0 01-3.6 9.75m6.633-4.596a18.666 18.666 0 01-2.485 5.33"
    />
  </svg>
);

// Fonction sécurisée pour les initiales
const getSecureInitials = (name: string): string => {
  if (!name || typeof name !== "string") return "U";
  const cleanName = name.trim();
  if (cleanName.length === 0) return "U";

  return (
    cleanName
      .split(" ")
      .map((word) => word[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) || "U"
  );
};

// Contenu de la page profil
function ProfilePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useTranslation();
  const { user, isLoading } = useAuthStore();
  const { updateProfile, exportUserData, deleteUserData } = useAuthStore();

  const [activeTab, setActiveTab] = useState("profile");
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    userType: "producer" as "producer" | "professional",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Initialisation sécurisée avec les données utilisateur
  useEffect(() => {
    if (!user) {
      router.push("/auth/login");
      return;
    }

    // Initialisation sécurisée avec fallbacks
    setFormData({
      fullName: getSafeName(user),
      email: getSafeEmail(user),
      userType: getSafeUserType(user) as "producer" | "professional",
    });

    // Gestion de l'onglet depuis l'URL
    const tab = searchParams.get("tab");
    if (tab && ["profile", "settings", "passkey", "privacy"].includes(tab)) {
      setActiveTab(tab);
    }
  }, [user, router, searchParams]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    setError("");
    setSuccess("");
  };

  // Fonction de soumission sécurisée avec validation
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    // Validation côté client AVANT d'envoyer
    const trimmedName = formData.fullName.trim();
    if (!trimmedName || trimmedName.length < 2) {
      setError(t("profile.error.nameMinLength"));
      return;
    }

    if (!["producer", "professional"].includes(formData.userType)) {
      setError(t("profile.error.invalidAccountType"));
      return;
    }

    try {
      // Données validées à envoyer
      const dataToUpdate = {
        name: trimmedName,
        user_type: formData.userType,
      };

      await updateProfile(dataToUpdate);
      setSuccess(t("profile.success.profileUpdated"));

      // Laisser le temps à l'UI de se stabiliser
      // Pas de redirection immédiate
    } catch (error: any) {
      setError(error.message || t("profile.error.updateFailed"));
    }
  };

  const handleExportData = async () => {
    try {
      const data = await exportUserData();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `intelia-expert-data-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setSuccess(t("profile.success.dataExported"));
    } catch (error: any) {
      setError(error.message || t("profile.error.exportFailed"));
    }
  };

  const handleDeleteAccount = async () => {
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true);
      return;
    }

    try {
      await deleteUserData();
      router.push("/");
    } catch (error: any) {
      setError(error.message || t("profile.error.deleteFailed"));
      setShowDeleteConfirm(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Variables sécurisées pour l'affichage
  const userName = getSafeName(user);
  const userEmail = getSafeEmail(user);
  const userType = getSafeUserType(user);
  const createdDate = getSafeCreatedDate(user);
  const userInitials = getSecureInitials(userName);

  const tabs = [
    { id: "profile", label: t("profile.tabs.personalInfo"), icon: UserIcon },
    { id: "settings", label: t("account.settings"), icon: CogIcon },
    { id: "passkey", label: t("passkey.title"), icon: FingerprintIcon },
    { id: "privacy", label: t("account.privacy"), icon: ShieldCheckIcon },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <Link
                href="/chat"
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeftIcon className="w-5 h-5 mr-2" />
                {t("profile.backToChat")}
              </Link>
              <div className="h-6 w-px bg-gray-300"></div>
              <h1 className="text-xl font-semibold text-gray-900">
                {t("profile.title")}
              </h1>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow">
          {/* Header du profil avec avatar sécurisé */}
          <div className="px-4 sm:px-6 py-6 sm:py-8 border-b border-gray-200">
            <div className="flex items-center space-x-3 sm:space-x-6">
              <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-xl sm:text-2xl">
                {userInitials}
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-xl sm:text-2xl font-bold text-gray-900 truncate">{userName}</h2>
                <p className="text-sm sm:text-base text-gray-600 truncate">{userEmail}</p>
                <div
                  className={`inline-block px-3 py-1 rounded-full text-sm font-medium mt-2 ${getBadgeColor(userType)}`}
                >
                  {getUserTypeLabel(userType)}
                </div>
              </div>
            </div>
          </div>

          {/* Navigation des onglets */}
          <div className="border-b border-gray-200">
            <nav className="flex space-x-4 sm:space-x-8 px-4 sm:px-6 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <tab.icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </div>
                </button>
              ))}
            </nav>
          </div>

          {/* Contenu des onglets */}
          <div className="p-6">
            {/* Messages d'erreur/succès */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                {error}
              </div>
            )}

            {success && (
              <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
                {success}
              </div>
            )}

            {/* Onglet Profil */}
            {activeTab === "profile" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    {t("profile.personalInfo")}
                  </h3>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <label
                        htmlFor="fullName"
                        className="block text-sm font-medium text-gray-700 mb-2"
                      >
                        {t("profile.fullName")}
                      </label>
                      <input
                        type="text"
                        id="fullName"
                        name="fullName"
                        value={formData.fullName || ""}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                      />
                    </div>

                    <div>
                      <label
                        htmlFor="email"
                        className="block text-sm font-medium text-gray-700 mb-2"
                      >
                        {t("profile.email")}
                      </label>
                      <input
                        type="email"
                        id="email"
                        name="email"
                        value={formData.email || ""}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                        disabled
                      />
                      <p className="text-sm text-gray-500 mt-1">
                        {t("profile.emailNotEditable")}
                      </p>
                    </div>

                    <div>
                      <label
                        htmlFor="userType"
                        className="block text-sm font-medium text-gray-700 mb-2"
                      >
                        {t("profile.accountType")}
                      </label>
                      <select
                        id="userType"
                        name="userType"
                        value={formData.userType}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="producer">{t("profile.accountType.producer")}</option>
                        <option value="professional">
                          {t("profile.accountType.professional")}
                        </option>
                      </select>
                    </div>

                    <button
                      type="submit"
                      disabled={isLoading}
                      className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {isLoading
                        ? t("profile.saving")
                        : t("profile.saveChanges")}
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* Onglet Paramètres */}
            {activeTab === "settings" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    {t("account.settings")}
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                      <div>
                        <h4 className="font-medium text-gray-900">
                          {t("profile.settings.interfaceLanguage")}
                        </h4>
                        <p className="text-sm text-gray-500">
                          {t("profile.settings.chooseLanguage")}
                        </p>
                      </div>
                      <select className="px-3 py-2 border border-gray-300 rounded-lg">
                        <option value="fr">Français</option>
                        <option value="en">English</option>
                        <option value="es">Español</option>
                      </select>
                    </div>

                    <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                      <div>
                        <h4 className="font-medium text-gray-900">
                          {t("profile.settings.notifications")}
                        </h4>
                        <p className="text-sm text-gray-500">
                          {t("profile.settings.receiveEmails")}
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Onglet Passkey */}
            {activeTab === "passkey" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    {t("passkey.title")}
                  </h3>
                  <p className="text-gray-600 mb-6">
                    {t("passkey.info.whatIs")}
                  </p>

                  {/* Setup Section */}
                  <div className="p-6 border border-blue-200 rounded-lg bg-blue-50 mb-6">
                    <div className="flex items-start space-x-4">
                      <FingerprintIcon className="w-8 h-8 text-blue-600 flex-shrink-0 mt-1" />
                      <div className="flex-1">
                        <h4 className="font-semibold text-blue-900 mb-2 text-lg">
                          {t("passkey.setupTitle")}
                        </h4>
                        <p className="text-sm text-blue-700 mb-4">
                          {t("passkey.description")}
                        </p>

                        <div className="bg-white bg-opacity-50 rounded-lg p-4 mb-4">
                          <h5 className="font-medium text-blue-900 mb-2">
                            {t("passkey.info.benefits")}
                          </h5>
                          <ul className="text-sm text-blue-700 space-y-2">
                            <li className="flex items-start">
                              <span className="mr-2">✓</span>
                              <span>{t("passkey.benefits.faster")}</span>
                            </li>
                            <li className="flex items-start">
                              <span className="mr-2">✓</span>
                              <span>{t("passkey.benefits.secure")}</span>
                            </li>
                            <li className="flex items-start">
                              <span className="mr-2">✓</span>
                              <span>{t("passkey.benefits.noPassword")}</span>
                            </li>
                          </ul>
                        </div>

                        <div className="bg-white bg-opacity-50 rounded-lg p-4 mb-4">
                          <h5 className="font-medium text-blue-900 mb-2">
                            {t("passkey.info.devices")}
                          </h5>
                          <p className="text-sm text-blue-700">
                            {t("passkey.devices.supported")}
                          </p>
                        </div>

                        <button
                          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
                        >
                          {t("passkey.setupButton")}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Registered Passkeys List (placeholder) */}
                  <div className="border border-gray-200 rounded-lg p-6">
                    <h4 className="font-medium text-gray-900 mb-3">
                      {t("passkey.registered")}
                    </h4>
                    <p className="text-sm text-gray-500">
                      {t("passkey.noPasskeys")}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Onglet Confidentialité */}
            {activeTab === "privacy" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    {t("profile.privacy.dataManagement")}
                  </h3>
                  <div className="space-y-4">
                    <div className="p-4 border border-gray-200 rounded-lg">
                      <h4 className="font-medium text-gray-900 mb-2">
                        {t("profile.privacy.exportData")}
                      </h4>
                      <p className="text-sm text-gray-600 mb-4">
                        {t("profile.privacy.exportDescription")}
                      </p>
                      <button
                        onClick={handleExportData}
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        {t("profile.privacy.downloadData")}
                      </button>
                    </div>

                    <div className="p-4 border border-red-200 rounded-lg bg-red-50">
                      <h4 className="font-medium text-red-900 mb-2">
                        {t("profile.privacy.deleteAccount")}
                      </h4>
                      <p className="text-sm text-red-700 mb-4">
                        {t("profile.privacy.deleteWarning")}
                      </p>
                      {!showDeleteConfirm ? (
                        <button
                          onClick={() => setShowDeleteConfirm(true)}
                          className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                        >
                          {t("profile.privacy.deleteAccount")}
                        </button>
                      ) : (
                        <div className="space-y-3">
                          <p className="text-sm font-medium text-red-800">
                            {t("profile.privacy.confirmDelete")}
                          </p>
                          <div className="flex space-x-3">
                            <button
                              onClick={() => setShowDeleteConfirm(false)}
                              className="bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400 transition-colors"
                            >
                              {t("profile.privacy.cancel")}
                            </button>
                            <button
                              onClick={handleDeleteAccount}
                              disabled={isLoading}
                              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                            >
                              {isLoading
                                ? t("profile.privacy.deleting")
                                : t("profile.privacy.yesDelete")}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="p-4 border border-gray-200 rounded-lg">
                      <h4 className="font-medium text-gray-900 mb-2">
                        {t("profile.privacy.retentionPolicy")}
                      </h4>
                      <p className="text-sm text-gray-600">
                        {t("profile.privacy.retentionDescription")}{" "}
                        {createdDate
                          ? createdDate.toLocaleDateString()
                          : "N/A"}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Export principal avec Suspense
export default function ProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      }
    >
      <ProfilePageContent />
    </Suspense>
  );
}
