import type { UserSessionStats, AdTriggerCriteria, AdData, User, AdEventData } from '@/types';

export const AdSystemUtils = {
  checkAdEligibility: (
    sessionStats: UserSessionStats,
    criteria: AdTriggerCriteria
  ): boolean => {
    const meetsSessionCriteria = sessionStats.totalSessions >= criteria.MIN_SESSIONS;
    const meetsDurationCriteria = sessionStats.averageSessionDuration >= criteria.MIN_DURATION_PER_SESSION;
    
    const lastAdTime = sessionStats.lastAdShown ? new Date(sessionStats.lastAdShown) : null;
    const now = new Date();
    const cooldownExpired = !lastAdTime || 
      (now.getTime() - lastAdTime.getTime()) > (criteria.COOLDOWN_PERIOD * 60 * 60 * 1000);
    
    return meetsSessionCriteria && meetsDurationCriteria && cooldownExpired;
  },

  generatePersonalizedAd: (userProfile?: User): AdData => {
    const baseAd: AdData = {
      id: 'farming-pro-2024',
      title: 'FarmPro Analytics',
      description: 'Optimisez vos performances agricoles avec notre plateforme IA spécialisée en élevage avicole.',
      imageUrl: '/images/logo.png',
      ctaText: 'Essai gratuit 30 jours',
      ctaUrl: 'https://farmpro-analytics.com/trial?ref=intelia',
      company: 'FarmPro Solutions',
      rating: 4.8,
      users: '10K+',
      duration: 'Essai gratuit',
      features: [
        'Analyses prédictives IA',
        'Suivi temps réel',
        'Rapports automatisés',
        'Support expert 24/7',
        'Intégration IoT',
        'Mobile & desktop'
      ]
    };

    if (userProfile?.user_type === 'veterinary') {
      baseAd.title = 'VetPro Clinical';
      baseAd.description = 'Plateforme de diagnostic vétérinaire avicole avec IA.';
      baseAd.features = [
        'Aide au diagnostic IA',
        'Base médicamenteuse',
        'Dossiers patients',
        'Analyses laboratoire',
        'Protocoles standards',
        'Téléconsultation'
      ];
    }

    return baseAd;
  },

  validateSessionStats: (data: any): data is UserSessionStats => {
    return (
      typeof data === 'object' &&
      data !== null &&
      typeof data.totalSessions === 'number' &&
      typeof data.averageSessionDuration === 'number' &&
      typeof data.qualifiesForAd === 'boolean'
    );
  }
};

export type AdSystemUtilsType = typeof AdSystemUtils;