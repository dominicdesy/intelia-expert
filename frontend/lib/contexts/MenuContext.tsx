"use client";

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
} from "react";

/**
 * MenuContext - Gestionnaire centralisé de tous les menus de l'application
 *
 * Fonctionnalités:
 * - Un seul menu ouvert à la fois
 * - Overlay partagé (pas de conflits z-index)
 * - Fermeture avec ESC
 * - Touch-friendly (Android, iOS)
 * - Compatible React Native (future migration App Store/Google Play)
 *
 * Usage:
 * const { openMenu, closeMenu, isMenuOpen } = useMenu();
 * openMenu('user-menu');
 * if (isMenuOpen('user-menu')) { ... }
 */

interface MenuContextValue {
  openMenuId: string | null;
  openMenu: (menuId: string) => void;
  closeMenu: (menuId: string) => void;
  closeAllMenus: () => void;
  isMenuOpen: (menuId: string) => boolean;
  toggleMenu: (menuId: string) => void;
}

const MenuContext = createContext<MenuContextValue | undefined>(undefined);

export const MenuProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  // Cleanup au démontage
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Ouvrir un menu (ferme automatiquement les autres)
  const openMenu = useCallback((menuId: string) => {
    if (!isMountedRef.current) return;
    setOpenMenuId(menuId);
  }, []);

  // Fermer un menu spécifique
  const closeMenu = useCallback((menuId: string) => {
    if (!isMountedRef.current) return;
    setOpenMenuId((prev) => (prev === menuId ? null : prev));
  }, []);

  // Fermer tous les menus
  const closeAllMenus = useCallback(() => {
    if (!isMountedRef.current) return;
    setOpenMenuId(null);
  }, []);

  // Vérifier si un menu est ouvert
  const isMenuOpen = useCallback(
    (menuId: string) => {
      return openMenuId === menuId;
    },
    [openMenuId],
  );

  // Toggle un menu
  const toggleMenu = useCallback(
    (menuId: string) => {
      if (!isMountedRef.current) return;
      setOpenMenuId((prev) => (prev === menuId ? null : menuId));
    },
    [],
  );

  // Fermer avec ESC (accessibility)
  useEffect(() => {
    if (!openMenuId) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isMountedRef.current) {
        closeAllMenus();
      }
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [openMenuId, closeAllMenus]);

  const value: MenuContextValue = {
    openMenuId,
    openMenu,
    closeMenu,
    closeAllMenus,
    isMenuOpen,
    toggleMenu,
  };

  return (
    <MenuContext.Provider value={value}>
      {children}
    </MenuContext.Provider>
  );
};

/**
 * Hook pour utiliser le MenuContext
 *
 * @throws Error si utilisé en dehors de MenuProvider
 *
 * @example
 * const { openMenu, isMenuOpen, closeMenu } = useMenu();
 *
 * <button onClick={() => openMenu('user-menu')}>Open</button>
 * {isMenuOpen('user-menu') && <div>Menu content</div>}
 */
export const useMenu = (): MenuContextValue => {
  const context = useContext(MenuContext);
  if (!context) {
    throw new Error("useMenu must be used within MenuProvider");
  }
  return context;
};
