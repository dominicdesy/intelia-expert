/**
 * Configuration de la publicité "Why Poultry Industry Should Embrace AI"
 */

export const ad01Config = {
  id: "ad-01-poultry-ai-2024",
  imageUrl: "/images/poultry-ai-ad.jpg",
  ctaUrl: "https://zurl.co/xfmd9",

  // Métadonnées pour le tracking
  category: "education",
  targetAudience: ["farmer", "veterinary", "nutritionist"],
  priority: 1, // Plus le nombre est bas, plus la priorité est haute

  // Contrôle d'affichage
  isActive: true,
  startDate: "2024-01-01",
  endDate: null, // null = pas de date de fin
};
