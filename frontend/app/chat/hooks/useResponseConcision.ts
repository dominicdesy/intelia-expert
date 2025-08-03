// hooks/useResponseConcision.ts - VERSION SIMPLIFIÉE POUR SÉLECTION DE VERSIONS BACKEND
import { useState, useCallback, useEffect } from 'react';

export enum ConcisionLevel {
  ULTRA_CONCISE = 'ultra_concise',  
  CONCISE = 'concise',              
  STANDARD = 'standard',            
  DETAILED = 'detailed'             
}

interface ConcisionConfig {
  level: ConcisionLevel;
  autoDetect: boolean;
  userPreference: boolean;
}

export const useResponseConcision = () => {
  const [config, setConfig] = useState<ConcisionConfig>({
    level: ConcisionLevel.CONCISE,
    autoDetect: true,
    userPreference: true
  });

  // Charger préférence utilisateur au démarrage
  useEffect(() => {
    const savedLevel = localStorage.getItem('intelia_concision_level');
    if (savedLevel && Object.values(ConcisionLevel).includes(savedLevel as ConcisionLevel)) {
      setConfig(prev => ({ ...prev, level: savedLevel as ConcisionLevel }));
    }
  }, []);

  // Sauvegarder préférence
  const updateConcisionLevel = useCallback((level: ConcisionLevel) => {
    setConfig(prev => ({ ...prev, level }));
    if (config.userPreference) {
      localStorage.setItem('intelia_concision_level', level);
    }
  }, [config.userPreference]);

  // 🚀 NOUVELLE FONCTION : Sélectionner la version appropriée depuis response_versions
  const selectVersionFromResponse = useCallback((
    responseVersions: Record<string, string>,
    level?: ConcisionLevel
  ): string => {
    const targetLevel = level || config.level;
    
    // Retourner la version demandée si elle existe
    if (responseVersions[targetLevel]) {
      console.log(`📋 [selectVersionFromResponse] Version ${targetLevel} sélectionnée`);
      return responseVersions[targetLevel];
    }
    
    // Fallback intelligent si version manquante
    const fallbackOrder: ConcisionLevel[] = [
      ConcisionLevel.DETAILED,
      ConcisionLevel.STANDARD, 
      ConcisionLevel.CONCISE,
      ConcisionLevel.ULTRA_CONCISE
    ];
    
    for (const fallbackLevel of fallbackOrder) {
      if (responseVersions[fallbackLevel]) {
        console.warn(`⚠️ [selectVersionFromResponse] Fallback vers ${fallbackLevel} (${targetLevel} manquant)`);
        return responseVersions[fallbackLevel];
      }
    }
    
    // Ultime fallback - première version disponible
    const firstAvailable = Object.values(responseVersions)[0];
    console.warn('⚠️ [selectVersionFromResponse] Aucune version standard - utilisation première disponible');
    return firstAvailable || 'Réponse non disponible';
  }, [config.level]);

  // 🚀 NOUVELLE FONCTION : Détecter le niveau optimal pour l'envoi initial au backend
  const detectOptimalLevel = useCallback((question: string): ConcisionLevel => {
    if (!config.autoDetect) return config.level;

    const questionLower = question.toLowerCase();
    
    // Questions ultra-concises (poids, température, mesures simples)
    const ultraConciseKeywords = [
      'poids', 'weight', 'peso',
      'température', 'temperature', 'temperatura', 
      'combien', 'how much', 'cuánto',
      'quel est', 'what is', 'cuál es',
      'quelle est', 'âge', 'age'
    ];
    
    if (ultraConciseKeywords.some(keyword => questionLower.includes(keyword))) {
      return ConcisionLevel.ULTRA_CONCISE;
    }

    // Questions complexes (comment, pourquoi, procédures)
    const complexKeywords = [
      'comment', 'how to', 'cómo',
      'pourquoi', 'why', 'por qué', 
      'expliquer', 'explain', 'explicar',
      'procédure', 'procedure', 'procedimiento',
      'diagnostic', 'diagnosis', 'diagnóstico',
      'traitement', 'treatment', 'tratamiento'
    ];

    if (complexKeywords.some(keyword => questionLower.includes(keyword))) {
      return ConcisionLevel.DETAILED;
    }

    // Par défaut: concis pour questions générales
    return ConcisionLevel.CONCISE;
  }, [config.autoDetect, config.level]);

  return {
    config,
    updateConcisionLevel,
    detectOptimalLevel,
    selectVersionFromResponse
  };
};

// 🚀 FONCTION UTILITAIRE : Analyser la complexité d'une réponse
export function analyzeResponseComplexity(response: string): {
  wordCount: number;
  sentenceCount: number;
  hasNumbers: boolean;
  hasAdvice: boolean;
  complexity: 'simple' | 'moderate' | 'complex';
} {
  const wordCount = response.split(/\s+/).length;
  const sentenceCount = response.split('.').filter(s => s.trim().length > 0).length;
  const hasNumbers = /\d+/.test(response);
  
  const adviceKeywords = [
    'recommandé', 'essentiel', 'important', 'devrait', 'doit',
    'recommended', 'essential', 'important', 'should', 'must',
    'recomendado', 'esencial', 'importante', 'debería', 'debe'
  ];
  const hasAdvice = adviceKeywords.some(keyword => 
    response.toLowerCase().includes(keyword)
  );
  
  let complexity: 'simple' | 'moderate' | 'complex' = 'simple';
  if (wordCount > 100 || sentenceCount > 3) complexity = 'moderate';
  if (wordCount > 200 || sentenceCount > 6) complexity = 'complex';
  
  return {
    wordCount,
    sentenceCount,
    hasNumbers,
    hasAdvice,
    complexity
  };
}

// 🚀 FONCTION UTILITAIRE : Détecter le type de question
export function detectQuestionType(question: string): string {
  const questionLower = question.toLowerCase();
  
  if (['poids', 'weight', 'peso'].some(word => questionLower.includes(word))) {
    return 'weight';
  }
  
  if (['température', 'temperature', 'temperatura'].some(word => questionLower.includes(word))) {
    return 'temperature';
  }
  
  if (['mortalité', 'mortality', 'mortalidad'].some(word => questionLower.includes(word))) {
    return 'mortality';
  }
  
  if (['eau', 'water', 'agua'].some(word => questionLower.includes(word))) {
    return 'water';
  }
  
  if (['diagnostic', 'diagnosis', 'diagnóstico'].some(word => questionLower.includes(word))) {
    return 'diagnosis';
  }
  
  if (['comment', 'how', 'cómo'].some(word => questionLower.includes(word))) {
    return 'how-to';
  }
  
  if (['pourquoi', 'why', 'por qué'].some(word => questionLower.includes(word))) {
    return 'why';
  }
  
  return 'general';
}

// 🚀 FONCTION UTILITAIRE : Valider les versions de réponse reçues du backend
export function validateResponseVersions(responseVersions: any): boolean {
  if (!responseVersions || typeof responseVersions !== 'object') {
    return false;
  }
  
  const requiredLevels = [
    ConcisionLevel.ULTRA_CONCISE,
    ConcisionLevel.CONCISE,
    ConcisionLevel.STANDARD,
    ConcisionLevel.DETAILED
  ];
  
  // Vérifier qu'au moins une version est présente
  const hasAnyVersion = requiredLevels.some(level => 
    responseVersions[level] && typeof responseVersions[level] === 'string'
  );
  
  return hasAnyVersion;
}

// 🚀 FONCTION DEBUG : Afficher info sur les versions disponibles
export function debugResponseVersions(responseVersions: Record<string, string>) {
  console.group('🔍 [responseVersions] Versions disponibles');
  Object.entries(responseVersions).forEach(([level, content]) => {
    console.log(`${level}: ${content?.length || 0} caractères`);
    if (content) {
      console.log(`  Aperçu: "${content.substring(0, 50)}..."`);
    }
  });
  console.groupEnd();
}