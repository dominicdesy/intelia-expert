"use client";

import React, {
  useState,
  useCallback,
  useMemo,
  useRef,
  useEffect,
} from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { logoutService } from "@/lib/services/logoutService";
import { useTranslation } from "@/lib/languages/i18n";
import { PLAN_CONFIGS } from "@/types";

// Import des modales avec leur structure complète
import { UserInfoModal } from "./modals/UserInfoModal";
import { AccountModal } from "./modals/AccountModal";
import { ContactModal } from "./modals/ContactModal";
import { LanguageModal } from "./modals/LanguageModal";
import { InviteFriendModal } from "./modals/InviteFriendModal";
import { secureLog } from "@/lib/utils/secureLogger";

// UserMenuButton - Version corrigée avec coordination auth store pour React #300
// Note: React.memo() retiré car le composant doit se re-render lors du changement de langue
export const UserMenuButton = () => {
  const router = useRouter();
  const { user } = useAuthStore(); // ✅ CORRECTION: Retiré 'logout' du destructuring
  const { t, currentLanguage } = useTranslation(); // currentLanguage suffit pour déclencher re-render
  // ✅ SOLUTION D: forceUpdate supprimé - Redondant avec currentLanguage dans les dépendances

  // États des modales
  const [isOpen, setIsOpen] = useState(false);
  const [showUserInfoModal, setShowUserInfoModal] = useState(false);
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [showContactModal, setShowContactModal] = useState(false);
  const [showLanguageModal, setShowLanguageModal] = useState(false);
  const [showInviteFriendModal, setShowInviteFriendModal] = useState(false);

  // Protection contre React #300 renforcée
  const isMountedRef = useRef(true);
  const logoutInProgressRef = useRef(false);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      secureLog.log("[UserMenuButton] Unmounting");
      isMountedRef.current = false;
    };
  }, []); // Pas de dépendances pour éviter re-mount intempestif

  // Fonction robuste pour obtenir les initiales utilisateur
  const getUserInitials = useCallback((user: any): string => {
    if (!user) return "U";

    // Vérifier si user.name est un email (contient @)
    if (user.name && user.name.includes("@")) {
      const emailPart = user.name.split("@")[0];
      if (emailPart.includes(".")) {
        const parts = emailPart.split(".");
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return emailPart.substring(0, 2).toUpperCase();
    }

    // Essayer depuis le nom complet
    if (user.name) {
      const names = user.name.trim().split(" ");
      if (names.length >= 2) {
        return (names[0][0] + names[names.length - 1][0]).toUpperCase();
      }
      return names[0][0].toUpperCase();
    }

    // Essayer depuis l'email
    if (user.email) {
      const emailPart = user.email.split("@")[0];
      if (emailPart.includes(".")) {
        const parts = emailPart.split(".");
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return emailPart.substring(0, 2).toUpperCase();
    }

    return "U";
  }, []);

  // CORRECTION: useMemo sans effet de bord et sans 't' dans les dépendances
  const userInitials = useMemo(() => {
    const initials = getUserInitials(user);

    // SUPPRESSION COMPLÈTE du debug qui modifie window - cause de la boucle
    // Plus de modification de variables globales dans useMemo !

    return initials;
  }, [user?.name, user?.email, getUserInitials]); // ← 't' supprimé !

  // DÉPLACEMENT du debug dans un useEffect séparé si nécessaire
  useEffect(() => {
    // Debug seulement en cas de changement réel des données utilisateur
    if (user?.name || user?.email) {
      secureLog.log("UserMenu user data:", {
        user_name: user?.name,
        user_email: user?.email,
        calculated_initials: getUserInitials(user),
        has_name: !!user?.name,
      });
    }
  }, [user?.name, user?.email, getUserInitials]); // Pas de 't' ici non plus

  // Mémorisation des variables de plan
  const { currentPlan, plan, isSuperAdmin } = useMemo(() => {
    const currentPlan = user?.plan || "essential";
    const plan =
      PLAN_CONFIGS[currentPlan as keyof typeof PLAN_CONFIGS] ||
      PLAN_CONFIGS.essential;
    const isSuperAdmin = user?.user_type === "super_admin";

    return { currentPlan, plan, isSuperAdmin };
  }, [user?.plan, user?.user_type]);

  // CORRECTION: Mémoriser l'objet user pour éviter les re-renders
  const stableUser = useMemo(() => {
    if (!user?.id) return user;

    // Créer un objet stable avec les propriétés essentielles seulement
    return {
      id: user.id,
      email: user.email,
      name: user.name,
      firstName: user.firstName,
      lastName: user.lastName,
      phone: user.phone,
      country: user.country,
      linkedinProfile: user.linkedinProfile,
      companyName: user.companyName,
      companyWebsite: user.companyWebsite,
      linkedinCorporate: user.linkedinCorporate,
      user_type: user.user_type,
      language: user.language,
      created_at: user.created_at,
      plan: user.plan,
      country_code: user.country_code,
      area_code: user.area_code,
      phone_number: user.phone_number,
      full_name: user.full_name,
      avatar_url: user.avatar_url,
      consent_given: user.consent_given,
      consent_date: user.consent_date,
      updated_at: user.updated_at,
      user_id: user.user_id,
      profile_id: user.profile_id,
      preferences: user.preferences,
      is_admin: user.is_admin,
    };
  }, [
    user?.id,
    user?.firstName,
    user?.lastName,
    user?.phone,
    user?.country,
    user?.linkedinProfile,
    user?.companyName,
    user?.companyWebsite,
    user?.linkedinCorporate,
    user?.country_code,
    user?.area_code,
    user?.phone_number,
  ]);

  // ✅ SOLUTION DÉFINITIVE: Service de logout indépendant
  const handleLogout = useCallback(async () => {
    if (logoutInProgressRef.current || !isMountedRef.current) return;

    try {
      secureLog.log(t("userMenu.debug.logoutViaService"));
      logoutInProgressRef.current = true;

      // Fermer le menu immédiatement
      setIsOpen(false);

      // ✅ CORRECTION: Passer l'objet user pour préserver la langue
      await logoutService.performLogout(user);
    } catch (error) {
      secureLog.error(t("userMenu.debug.logoutServiceError"), error);
      // En cas d'erreur, forcer quand même la redirection
      window.location.href = "/";
    }
  }, [t, user]); // ← Ajout de 'user' dans les dépendances

  // Handlers des modales avec protection renforcée
  const handleContactClick = useCallback(() => {
    if (!isMountedRef.current) return;
    setIsOpen(false);
    setTimeout(() => {
      if (isMountedRef.current) setShowContactModal(true);
    }, 50);
  }, []);

  const handleUserInfoClick = useCallback(() => {
    if (!isMountedRef.current) return;
    setIsOpen(false);
    setTimeout(() => {
      if (isMountedRef.current) setShowUserInfoModal(true);
    }, 50);
  }, []);

  const handleAccountClick = useCallback(() => {
    if (!isMountedRef.current) return;
    setIsOpen(false);
    setTimeout(() => {
      if (isMountedRef.current) setShowAccountModal(true);
    }, 50);
  }, []);

  const handleLanguageClick = useCallback(() => {
    if (!isMountedRef.current) return;
    setIsOpen(false);
    setTimeout(() => {
      if (isMountedRef.current) setShowLanguageModal(true);
    }, 50);
  }, []);

  const handleInviteFriendClick = useCallback(() => {
    if (!isMountedRef.current) return;
    setIsOpen(false);
    setTimeout(() => {
      if (isMountedRef.current) setShowInviteFriendModal(true);
    }, 50);
  }, []);

  const handleStatisticsClick = useCallback(() => {
    if (!isMountedRef.current) return;
    setIsOpen(false);
    window.open("/admin/statistics", "_blank");
  }, []);

  const openPrivacyPolicy = useCallback(() => {
    window.open("https://intelia.com/privacy-policy/", "_blank");
  }, []);

  const handleAboutClick = useCallback(() => {
    if (!isMountedRef.current) return;
    setIsOpen(false);
    router.push("/about");
  }, [router]);

  const toggleOpen = useCallback(() => {
    if (!isMountedRef.current) return;
    secureLog.log(`t("userMenu.debug.toggleOpen") ${isMountedRef.current} ${t("userMenu.debug.currentIsOpen")} ${isOpen}`);
    setIsOpen((prev) => !prev);
  }, [isOpen, t]);

  const closeMenu = useCallback(() => {
    if (!isMountedRef.current) return;
    setIsOpen(false);
  }, []);

  // Fonctions de fermeture des modales avec protection
  const closeUserInfoModal = useCallback(() => {
    if (!isMountedRef.current) return;
    setShowUserInfoModal(false);
  }, []);

  const closeAccountModal = useCallback(() => {
    if (!isMountedRef.current) return;
    setShowAccountModal(false);
  }, []);

  const closeContactModal = useCallback(() => {
    if (!isMountedRef.current) return;
    setShowContactModal(false);
  }, []);

  const closeLanguageModal = useCallback(() => {
    if (!isMountedRef.current) return;
    setShowLanguageModal(false);
  }, []);

  // Écouter le changement de langue pour fermer le menu principal
  useEffect(() => {
    const handleLanguageChanged = () => {
      if (!isMountedRef.current) return;
      secureLog.log("[UserMenuButton] Langue changée, fermeture du menu");
      setIsOpen(false);
    };

    window.addEventListener("languageChanged", handleLanguageChanged);

    return () => {
      window.removeEventListener("languageChanged", handleLanguageChanged);
    };
  }, []);

  // ✅ SOLUTION D: Debug du changement de langue (forceUpdate supprimé - redondant)
  useEffect(() => {
    secureLog.log(`[UserMenuButton] currentLanguage mis à jour: ${currentLanguage}`);
    secureLog.log(`[UserMenuButton] Sample translation 'nav.profile': ${t("nav.profile")}`);
    secureLog.log(`[UserMenuButton] Sample translation 'nav.language': ${t("nav.language")}`);
    // forceUpdate supprimé - Le changement de currentLanguage déclenche déjà un re-render
  }, [currentLanguage, t]);

  const closeInviteFriendModal = useCallback(() => {
    if (!isMountedRef.current) return;
    setShowInviteFriendModal(false);
  }, []);

  if (!user) return null;

  return (
    <>
      <div className="relative">
        <button
          onClick={toggleOpen}
          className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center hover:bg-blue-700 transition-colors"
          title={t("userMenu.openMenu")}
          aria-label={t("userMenu.openMenu")}
        >
          <span className="text-white text-xs font-medium">{userInitials}</span>
        </button>

        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={closeMenu} />

            <div
              key={currentLanguage}
              className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900">
                  {user?.name}
                </p>
                <p className="text-xs text-gray-500">{user?.email}</p>
                {user?.user_type && (
                  <div className="mt-2">
                    {!isSuperAdmin && (
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${plan.bgColor} ${plan.color} border ${plan.borderColor}`}
                      >
                        {plan.name}
                      </span>
                    )}
                    {isSuperAdmin && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-300">
                        {t("userMenu.superAdmin")}
                      </span>
                    )}
                  </div>
                )}
              </div>

              <div className="py-1">
                {isSuperAdmin && (
                  <button
                    onClick={handleStatisticsClick}
                    className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    <svg
                      className="w-5 h-5 text-blue-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
                      />
                    </svg>
                    <span>{t("nav.statistics")}</span>
                  </button>
                )}

                {!isSuperAdmin && (
                  <button
                    onClick={handleAccountClick}
                    className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    <svg
                      className="w-5 h-5 text-blue-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z"
                      />
                    </svg>
                    <span>{t("subscription.title")}</span>
                  </button>
                )}

                <button
                  onClick={handleUserInfoClick}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg
                    className="w-5 h-5 text-blue-600"
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
                  <span>{t("nav.profile")}</span>
                </button>

                <button
                  onClick={handleLanguageClick}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg
                    className="w-5 h-5 text-blue-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="m10.5 21 5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 0 1-3.827-5.802"
                    />
                  </svg>
                  <span>{t("nav.language")}</span>
                </button>

                <button
                  onClick={handleInviteFriendClick}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg
                    className="w-5 h-5 text-blue-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM3 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 019.374 21c-2.331 0-4.512-.645-6.374-1.766z"
                    />
                  </svg>
                  <span>{t("nav.inviteFriend")}</span>
                </button>

                <button
                  onClick={handleContactClick}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg
                    className="w-5 h-5 text-blue-600"
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
                  <span>{t("nav.contact")}</span>
                </button>

                <button
                  onClick={handleAboutClick}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg
                    className="w-5 h-5 text-blue-600"
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
                  <span>{t("nav.about")}</span>
                </button>

                <button
                  onClick={openPrivacyPolicy}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg
                    className="w-5 h-5 text-blue-600"
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
                  <span>{t("nav.legal")}</span>
                </button>
              </div>

              <div className="border-t border-gray-100 pt-1">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
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
                      d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75"
                    />
                  </svg>
                  <span>{t("nav.logout")}</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* MODALES DIRECTES - AVEC PROTECTION REACT #300 */}

      {/* Abonnement Modal */}
      {!isSuperAdmin && showAccountModal && (
        <AccountModal user={user} onClose={closeAccountModal} />
      )}

      {/* Profil Modal - CORRECTION APPLIQUÉE */}
      {showUserInfoModal && (
        <UserInfoModal user={stableUser} onClose={closeUserInfoModal} />
      )}

      {/* Langue Modal */}
      {showLanguageModal && <LanguageModal onClose={closeLanguageModal} />}

      {/* Contact Modal */}
      {showContactModal && <ContactModal onClose={closeContactModal} />}

      {/* Inviter ami Modal */}
      {showInviteFriendModal && (
        <InviteFriendModal onClose={closeInviteFriendModal} />
      )}
    </>
  );
};
