/**
 * Catalogue centralisé des publicités avec système de rotation
 */

import { ad01Config } from "./ad-01-poultry-ai/config";
import { ad01Translations, type SupportedLanguage } from "./ad-01-poultry-ai/translations";
import { ad02Config } from "./ad-02-smart-sensors/config";
import { ad02Translations } from "./ad-02-smart-sensors/translations";
import { PersistentJSONStorage } from "../utils/persistentStorage";

// Type pour une publicité complète
export interface Ad {
  id: string;
  imageUrl: string;
  ctaUrl: string;
  category: string;
  targetAudience: string[];
  priority: number;
  isActive: boolean;
  startDate: string;
  endDate: string | null;
  translations: Record<SupportedLanguage, any>;
}

// Catalogue de toutes les publicités disponibles
export const ADS_CATALOG: Ad[] = [
  {
    ...ad01Config,
    translations: ad01Translations,
  },
  {
    ...ad02Config,
    translations: ad02Translations,
  },
  // FUTURE: Ajoutez ici ad-03, ad-04, etc.
  // {
  //   ...ad03Config,
  //   translations: ad03Translations,
  // },
];

/**
 * Filtre les publicités actives
 */
export function getActiveAds(): Ad[] {
  const now = new Date();

  return ADS_CATALOG.filter((ad) => {
    if (!ad.isActive) return false;

    const startDate = new Date(ad.startDate);
    if (now < startDate) return false;

    if (ad.endDate) {
      const endDate = new Date(ad.endDate);
      if (now > endDate) return false;
    }

    return true;
  });
}

/**
 * Filtre les publicités par type d'utilisateur
 */
export function getAdsForUserType(userType?: string): Ad[] {
  const activeAds = getActiveAds();

  if (!userType) return activeAds;

  return activeAds.filter((ad) =>
    ad.targetAudience.includes(userType) || ad.targetAudience.includes("all")
  );
}

/**
 * Système de rotation intelligent avec stockage persistant multi-méthodes
 * Évite de montrer la même pub deux fois de suite
 */
const AD_HISTORY_KEY = "intelia_ad_history";
const MAX_HISTORY_SIZE = 10; // Garder les 10 dernières pubs montrées

// Utiliser le stockage persistant (cookie + localStorage + sessionStorage)
const adHistoryStorage = new PersistentJSONStorage<string[]>(AD_HISTORY_KEY);

function getAdHistory(): string[] {
  try {
    console.log(`[AdCatalog] 🔍 Lecture de la clé: ${AD_HISTORY_KEY}`);
    const history = adHistoryStorage.get();
    console.log(`[AdCatalog] 🔍 Historique récupéré:`, history);

    if (!history || !Array.isArray(history)) {
      console.log(`[AdCatalog] 🔍 Pas de données valides, retour tableau vide`);
      return [];
    }

    return history;
  } catch (error) {
    console.error(`[AdCatalog] ❌ Erreur lecture historique:`, error);
    return [];
  }
}

function addToHistory(adId: string): void {
  try {
    console.log(`[AdCatalog] 🔵 Début addToHistory pour: ${adId}`);
    const history = getAdHistory();
    console.log(`[AdCatalog] 🔵 Historique actuel:`, history);

    history.unshift(adId); // Ajouter au début
    console.log(`[AdCatalog] 🔵 Après ajout:`, history);

    // Garder seulement les N dernières
    const trimmedHistory = history.slice(0, MAX_HISTORY_SIZE);
    console.log(`[AdCatalog] 🔵 Après trim:`, trimmedHistory);

    // Sauvegarder avec le système persistant (cookie + localStorage + sessionStorage)
    adHistoryStorage.set(trimmedHistory);
    console.log(`[AdCatalog] 🔵 Sauvegarde persistante réussie`);

    // Vérification immédiate
    const verification = adHistoryStorage.get();
    console.log(`[AdCatalog] 🔵 Vérification immédiate:`, verification);
  } catch (error) {
    console.error("[AdCatalog] ❌ Erreur sauvegarde historique:", error);
  }
}

/**
 * Sélectionne la prochaine publicité à afficher
 * Logique de rotation stricte: jamais la même pub deux fois de suite
 * Alternance garantie: pub1 → pub2 → pub1 → pub2
 * NOTE: N'ajoute PAS à l'historique ici - l'historique est ajouté quand la pub est affichée
 */
export function selectNextAd(userType?: string): Ad | null {
  const eligibleAds = getAdsForUserType(userType);

  if (eligibleAds.length === 0) {
    console.warn("[AdCatalog] Aucune publicité active disponible");
    return null;
  }

  // Si une seule pub, pas de choix
  if (eligibleAds.length === 1) {
    return eligibleAds[0];
  }

  // Logique de rotation stricte
  const history = getAdHistory();
  const lastShownId = history[0]; // La dernière montrée

  console.log(`[AdCatalog] Dernière pub affichée: ${lastShownId}, Historique:`, history);

  // Trier par priorité (1 = haute, 2 = moyenne, etc.)
  const sortedAds = [...eligibleAds].sort((a, b) => a.priority - b.priority);

  // GARANTIE D'ALTERNANCE: Filtrer TOUTES les pubs différentes de la dernière
  const differentAds = sortedAds.filter((ad) => ad.id !== lastShownId);

  // S'il y a au moins une pub différente, la choisir
  if (differentAds.length > 0) {
    // Prendre la première (plus haute priorité) parmi les pubs différentes
    const selectedAd = differentAds[0];
    console.log(`[AdCatalog] Sélection alternance: ${lastShownId} → ${selectedAd.id}`);
    return selectedAd;
  }

  // Cas edge (ne devrait jamais arriver si eligibleAds.length > 1)
  // Si toutes les pubs sont identiques à la dernière (impossible normalement)
  const selectedAd = sortedAds[0];
  console.log(`[AdCatalog] Sélection par défaut: ${selectedAd.id}`);
  return selectedAd;
}

/**
 * Enregistre qu'une publicité a été affichée
 * À appeler UNIQUEMENT quand la pub est effectivement montrée à l'utilisateur
 */
export function markAdAsShown(adId: string): void {
  addToHistory(adId);
  console.log(`[AdCatalog] ✅ Pub marquée comme affichée: ${adId}`);
}

/**
 * Obtient les traductions d'une pub pour une langue donnée
 */
export function getAdTranslations(ad: Ad, language: string) {
  // Fallback vers anglais si la langue n'existe pas
  const lang = (ad.translations[language as SupportedLanguage]
    ? language
    : "en") as SupportedLanguage;

  return ad.translations[lang];
}

/**
 * Réinitialise l'historique (utile pour le dev/test)
 */
export function clearAdHistory(): void {
  try {
    adHistoryStorage.remove();
    console.log("[AdCatalog] Historique réinitialisé (cookie + localStorage + sessionStorage)");
  } catch (error) {
    console.error("[AdCatalog] Erreur réinitialisation historique:", error);
  }
}

/**
 * Debug: Affiche l'état du système de pubs
 */
export function debugAdSystem(): void {
  console.group("📊 [AdCatalog] État du système");
  console.log("Total pubs catalog:", ADS_CATALOG.length);
  console.log("Pubs actives:", getActiveAds().length);
  console.log("Historique:", getAdHistory());
  console.log("Prochaine pub:", selectNextAd()?.id);
  console.groupEnd();
}

// Export pour debug dans la console navigateur
if (typeof window !== "undefined") {
  (window as any).debugAdSystem = debugAdSystem;
  (window as any).clearAdHistory = clearAdHistory;
}
