'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/stores/auth';
import type { AdData, AdTriggerCriteria, UserSessionStats, User } from '@/types';
import { AD_CONFIG } from '@/types';

export const useAdSystem = () => {
  const { user, isAuthenticated } = useAuthStore();
  const [sessionStats, setSessionStats] = useState<UserSessionStats | null>(null);
  const [showAd, setShowAd] = useState(false);
  const [currentAd, setCurrentAd] = useState<AdData | null>(null);

  // Utiliser la configuration depuis types/index.ts
  const AD_CRITERIA = AD_CONFIG.TRIGGERS;

  // Vérifier les critères d'affichage de publicité
  const checkAdEligibility = useCallback(async () => {
    if (!isAuthenticated || !user) return;

    try {
      // Utiliser votre API client existant
      const authData = localStorage.getItem('intelia-expert-auth');
      if (!authData) return;

      const token = JSON.parse(authData).access_token;
      
      const response = await fetch('/api/v1/logging/analytics/my-sessions?days=7', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        const stats: UserSessionStats = {
          totalSessions: data.total_sessions || 0,
          averageSessionDuration: data.average_duration || 0,
          lastAdShown: localStorage.getItem('lastAdShown'),
          qualifiesForAd: false
        };

        // Vérifier les critères en utilisant les noms corrects
        const meetsSessionCriteria = stats.totalSessions >= AD_CRITERIA.MIN_SESSIONS;
        const meetsDurationCriteria = stats.averageSessionDuration >= AD_CRITERIA.MIN_DURATION_PER_SESSION;
        
        // Vérifier le cooldown
        const lastAdTime = stats.lastAdShown ? new Date(stats.lastAdShown) : null;
        const now = new Date();
        const cooldownExpired = !lastAdTime || 
          (now.getTime() - lastAdTime.getTime()) > (AD_CRITERIA.COOLDOWN_PERIOD * 60 * 60 * 1000);

        stats.qualifiesForAd = meetsSessionCriteria && meetsDurationCriteria && cooldownExpired;
        
        setSessionStats(stats);

        // Déclencher la publicité si éligible
        if (stats.qualifiesForAd) {
          await triggerAd();
        }
      }
    } catch (error) {
      console.error('Erreur lors de la vérification de l\'éligibilité publicitaire:', error);
    }
  }, [isAuthenticated, user, AD_CRITERIA]);

  // Obtenir une publicité personnalisée
  const getPersonalizedAd = useCallback(async (): Promise<AdData> => {
    const baseAd: AdData = {
      id: 'farming-pro-2024',
      title: 'FarmPro Analytics',
      description: 'Optimisez vos performances agricoles avec notre plateforme IA spécialisée en élevage avicole. Analyses prédictives, suivi en temps réel et conseils personnalisés pour maximiser vos rendements.',
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

    // Personnalisation selon le type d'utilisateur
    if (user?.user_type === 'veterinary') {
      baseAd.title = 'VetPro Clinical';
      baseAd.description = 'Plateforme de diagnostic vétérinaire avicole avec IA. Aide au diagnostic, base de données médicamenteuse et suivi clinique intégré.';
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
  }, [user]);

  // Déclencher l'affichage de la publicité
  const triggerAd = useCallback(async () => {
    try {
      const adData = await getPersonalizedAd();
      setCurrentAd(adData);
      setShowAd(true);
    } catch (error) {
      console.error('Erreur lors du chargement de la publicité:', error);
    }
  }, [getPersonalizedAd]);

  // Gérer la fermeture de la publicité
  const handleAdClose = useCallback(() => {
    setShowAd(false);
    setCurrentAd(null);
    
    // Enregistrer le timestamp pour le cooldown
    localStorage.setItem('lastAdShown', new Date().toISOString());
    
    // Log local optionnel (pour debug)
    console.log('Ad closed:', { timestamp: new Date().toISOString() });
  }, []);

  // Gérer le clic sur la publicité
  const handleAdClick = useCallback((adId: string) => {
    // Log local optionnel (pour debug)
    console.log('Ad clicked:', { adId, timestamp: new Date().toISOString() });
    
    // Enregistrer le timestamp pour le cooldown
    localStorage.setItem('lastAdShown', new Date().toISOString());
    
    // Fermer la modal
    setTimeout(() => {
      setShowAd(false);
      setCurrentAd(null);
    }, 1000);
  }, []);

  // Vérifier l'éligibilité au démarrage et périodiquement
  useEffect(() => {
    if (isAuthenticated) {
      // Délai initial pour laisser le temps aux sessions de se charger
      const initialDelay = setTimeout(() => {
        checkAdEligibility();
      }, AD_CRITERIA.INITIAL_CHECK_DELAY || 3000);

      // Puis vérifier selon l'intervalle configuré
      const interval = setInterval(checkAdEligibility, AD_CRITERIA.CHECK_INTERVAL || 5 * 60 * 1000);
      
      return () => {
        clearTimeout(initialDelay);
        clearInterval(interval);
      };
    }
  }, [isAuthenticated, checkAdEligibility, AD_CRITERIA]);

  return {
    sessionStats,
    showAd,
    currentAd,
    handleAdClose,
    handleAdClick,
    checkAdEligibility,
    triggerAd
  };
};