/**
 * Useauthstore
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
// lib/hooks/useAuthStore.ts - Hooks optimisés pour éviter les re-renders
import { useAuthStore as useAuthStoreBase } from "@/lib/stores/auth";

// Hook pour récupérer SEULEMENT les données utilisateur
// Ne se re-rend que si user, isAuthenticated ou hasHydrated changent
export const useUser = () => {
  return useAuthStoreBase((state) => ({
    user: state.user,
    isAuthenticated: state.isAuthenticated,
    hasHydrated: state.hasHydrated,
  }));
};

// Hook pour récupérer SEULEMENT l'état de chargement
// Ne se re-rend que si isLoading ou hasHydrated changent
export const useAuthLoading = () => {
  return useAuthStoreBase((state) => ({
    isLoading: state.isLoading,
    hasHydrated: state.hasHydrated,
  }));
};

// Hook pour récupérer SEULEMENT les actions d'authentification
// Les fonctions sont stables, donc pas de re-renders
export const useAuth = () => {
  return useAuthStoreBase((state) => ({
    login: state.login,
    register: state.register,
    logout: state.logout,
    initializeSession: state.initializeSession,
    checkAuth: state.checkAuth,
    updateProfile: state.updateProfile,
    updateConsent: state.updateConsent,
    deleteUserData: state.deleteUserData,
    exportUserData: state.exportUserData,
    getAuthToken: state.getAuthToken,
    setHasHydrated: state.setHasHydrated,
  }));
};

// Hook pour récupérer SEULEMENT les erreurs
// Ne se re-rend que si les erreurs changent
export const useAuthErrors = () => {
  return useAuthStoreBase((state) => ({
    authErrors: state.authErrors,
    handleAuthError: state.handleAuthError,
    clearAuthErrors: state.clearAuthErrors,
  }));
};

// Hook pour récupérer le timestamp de dernière vérification
export const useAuthCheck = () => {
  return useAuthStoreBase((state) => state.lastAuthCheck);
};

// Hook complet (à éviter dans les composants performants)
// Utilisez les hooks spécialisés ci-dessus à la place
export const useAuthStore = useAuthStoreBase;
