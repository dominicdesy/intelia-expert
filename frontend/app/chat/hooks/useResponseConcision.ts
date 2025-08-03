// hooks/useResponseConcision.ts - VERSION COMPLÈTE CORRIGÉE
import { useState, useCallback, useEffect } from 'react';

export enum ConcisionLevel {
  ULTRA_CONCISE = 'ultra_concise',  // Réponse minimale
  CONCISE = 'concise',              // Réponse courte  
  STANDARD = 'standard',            // Réponse normale
  DETAILED = 'detailed'             // Réponse complète
}

interface ConcisionConfig {
  level: ConcisionLevel;
  autoDetect: boolean;  // Détection automatique selon le type de question
  userPreference: boolean; // Sauvegarder préférence utilisateur
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

  // Détecter automatiquement le niveau selon la question
  const detectOptimalLevel = useCallback((question: string): ConcisionLevel => {
    if (!config.autoDetect) return config.level;

    const questionLower = question.toLowerCase();
    
    // Questions ultra-concises (poids, température, mesures)
    const ultraConciseKeywords = [
      'poids', 'weight', 'peso',
      'température', 'temperature', 'temperatura',
      'combien', 'how much', 'cuánto',
      'quel est', 'what is', 'cuál es'
    ];
    
    if (ultraConciseKeywords.some(keyword => questionLower.includes(keyword))) {
      return ConcisionLevel.ULTRA_CONCISE;
    }

    // Questions complexes (comment, pourquoi, procédure)
    const complexKeywords = [
      'comment', 'how to', 'cómo',
      'pourquoi', 'why', 'por qué',
      'expliquer', 'explain', 'explicar',
      'procédure', 'procedure', 'procedimiento'
    ];

    if (complexKeywords.some(keyword => questionLower.includes(keyword))) {
      return ConcisionLevel.DETAILED;
    }

    // Par défaut: concis
    return ConcisionLevel.CONCISE;
  }, [config.autoDetect, config.level]);

  // Traiter une réponse selon le niveau de concision
  const processResponse = useCallback((
    response: string, 
    question: string,
    forcedLevel?: ConcisionLevel
  ): string => {
    const level = forcedLevel || detectOptimalLevel(question);
    
    switch (level) {
      case ConcisionLevel.ULTRA_CONCISE:
        return extractEssentialInfo(response, question);
      
      case ConcisionLevel.CONCISE:
        return makeConcise(response, question);
      
      case ConcisionLevel.STANDARD:
        return removeExcessiveAdvice(response);
      
      case ConcisionLevel.DETAILED:
      default:
        return response; // Réponse complète
    }
  }, [detectOptimalLevel]);

  return {
    config,
    updateConcisionLevel,
    detectOptimalLevel,
    processResponse
  };
};

// =============================================================================
// FONCTIONS DE TRAITEMENT DES RÉPONSES (TOUTES INCLUSES)
// =============================================================================

// Extraire uniquement l'information essentielle
function extractEssentialInfo(response: string, question: string): string {
  const questionLower = question.toLowerCase();
  
  // Questions de poids → extraire juste les chiffres
  if (['poids', 'weight', 'peso'].some(word => questionLower.includes(word))) {
    const weightMatch = response.match(/(\d+(?:-\d+|[^\d]*\d+)?)\s*(?:grammes?|g\b)/i);
    if (weightMatch) {
      const value = weightMatch[1];
      if (value.includes('-') || response.toLowerCase().includes('entre')) {
        return `${value}g`;
      }
      return `~${value}g`;
    }
  }
  
  // Questions de température → extraire juste les degrés
  if (['température', 'temperature'].some(word => questionLower.includes(word))) {
    const tempMatch = response.match(/(\d+(?:-\d+)?)\s*°?C/i);
    if (tempMatch) {
      return `${tempMatch[1]}°C`;
    }
  }
  
  // Questions de quantité d'eau
  if (['eau', 'water', 'agua'].some(word => questionLower.includes(word))) {
    const waterMatch = response.match(/(\d+(?:\.\d+)?)\s*(?:litres?|l\b|ml|millilitres?)/i);
    if (waterMatch) {
      return `${waterMatch[1]}L/jour`;
    }
  }
  
  // Questions de mortalité
  if (['mortalité', 'mortality', 'mortalidad', 'morts', 'deaths'].some(word => questionLower.includes(word))) {
    const mortalityMatch = response.match(/(\d+(?:\.\d+)?)\s*%/i);
    if (mortalityMatch) {
      return `${mortalityMatch[1]}%`;
    }
  }
  
  // Questions oui/non
  const yesNoKeywords = ['oui', 'non', 'yes', 'no', 'sí', 'normal', 'anormal'];
  for (const keyword of yesNoKeywords) {
    if (response.toLowerCase().includes(keyword)) {
      const sentence = response.split('.').find(s => s.toLowerCase().includes(keyword));
      if (sentence && sentence.trim().length < 50) {
        return sentence.trim() + '.';
      }
    }
  }
  
  // Fallback: première phrase avec chiffres ou information clé
  const sentences = response.split('.');
  for (const sentence of sentences) {
    if ((/\d+/.test(sentence) || sentence.length < 50) && sentence.trim().length > 10) {
      return sentence.trim() + '.';
    }
  }
  
  // Ultime fallback: première phrase
  return sentences[0]?.trim() + '.' || response;
}

// Rendre concis (enlever conseils mais garder info principale) - VERSION AMÉLIORÉE
function makeConcise(response: string, question: string): string {
  const questionLower = question.toLowerCase();
  
  // ✅ NOUVEAU: Traitement spécialisé par type de question
  if (['poids', 'weight', 'peso'].some(word => questionLower.includes(word))) {
    return makeConciseForWeight(response, question);
  }
  
  if (['température', 'temperature', 'temperatura'].some(word => questionLower.includes(word))) {
    return makeConciseForTemperature(response, question);
  }
  
  if (['diagnostic', 'diagnosis', 'problème', 'problem'].some(word => questionLower.includes(word))) {
    return makeConciseForDiagnosis(response, question);
  }
  
  // Traitement général pour autres questions
  const verbosePatterns = [
    // Français - conseils non demandés
    /\.?\s*Il est essentiel de[^.]*\./gi,
    /\.?\s*Assurez-vous de[^.]*\./gi,
    /\.?\s*N'hésitez pas à[^.]*\./gi,
    /\.?\s*Pour garantir[^.]*\./gi,
    /\.?\s*À ce stade[^.]*\./gi,
    /\.?\s*pour favoriser le bien-être[^.]*\./gi,
    /\.?\s*en termes de[^.]*\./gi,
    /\.?\s*Il est recommandé de[^.]*\./gi,
    /\.?\s*Veillez à[^.]*\./gi,
    /\.?\s*Il convient de[^.]*\./gi,
    /\.?\s*Pour optimiser[^.]*\./gi,
    /\.?\s*Dans l'idéal[^.]*\./gi,
    
    // Anglais
    /\.?\s*It is essential to[^.]*\./gi,
    /\.?\s*Make sure to[^.]*\./gi,
    /\.?\s*Don't hesitate to[^.]*\./gi,
    /\.?\s*It is recommended to[^.]*\./gi,
    /\.?\s*Be sure to[^.]*\./gi,
    /\.?\s*To optimize[^.]*\./gi,
    /\.?\s*Ideally[^.]*\./gi,
    
    // Espagnol
    /\.?\s*Es esencial[^.]*\./gi,
    /\.?\s*Asegúrese de[^.]*\./gi,
    /\.?\s*Es recomendable[^.]*\./gi,
    /\.?\s*Para optimizar[^.]*\./gi,
    /\.?\s*Idealmente[^.]*\./gi,
    
    // Phrases génériques à supprimer
    /\.?\s*Pour plus d'informations[^.]*\./gi,
    /\.?\s*For more information[^.]*\./gi,
    /\.?\s*Para más información[^.]*\./gi,
    /\.?\s*En cas de doute[^.]*\./gi,
    /\.?\s*If in doubt[^.]*\./gi,
    /\.?\s*En caso de duda[^.]*\./gi
  ];
  
  let cleaned = response;
  
  // Supprimer les patterns verbeux
  verbosePatterns.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '.');
  });
  
  // Supprimer les répétitions et phrases redondantes
  const redundantPatterns = [
    /\.?\s*Cela dit[^.]*\./gi,
    /\.?\s*Cependant[^.]*\./gi,
    /\.?\s*Néanmoins[^.]*\./gi,
    /\.?\s*However[^.]*\./gi,
    /\.?\s*Nevertheless[^.]*\./gi,
    /\.?\s*Sin embargo[^.]*\./gi
  ];
  
  redundantPatterns.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '.');
  });
  
  // Nettoyer les doubles points et espaces
  cleaned = cleaned.replace(/\.+/g, '.').replace(/\s+/g, ' ').trim();
  
  return cleaned;
}

// ✅ NOUVELLE FONCTION: Concision spécialisée pour questions de poids
function makeConciseForWeight(response: string, question: string): string {
  const sentences = response.split('.').map(s => s.trim()).filter(s => s.length > 0);
  
  // Chercher les phrases contenant des informations de poids importantes
  const weightSentences = sentences.filter(sentence => {
    const hasWeight = /\d+\s*(?:grammes?|g\b)/i.test(sentence);
    const isRelevant = [
      'poids', 'weight', 'varie', 'entre', 'normal', 'age', 'âge', 'jours', 'days',
      'ross', 'souche', 'strain', 'considéré', 'considered', 'standard'
    ].some(word => sentence.toLowerCase().includes(word));
    const isNotAdvice = ![
      'recommandé', 'essentiel', 'important', 'devrait', 'doit',
      'recommended', 'essential', 'important', 'should', 'must'
    ].some(word => sentence.toLowerCase().includes(word));
    
    return (hasWeight || isRelevant) && isNotAdvice;
  });
  
  // Si on trouve des phrases pertinentes, les combiner intelligemment
  if (weightSentences.length > 0) {
    // Prendre les 2 premières phrases les plus informatives
    let result = weightSentences.slice(0, 2).join('. ');
    
    // S'assurer qu'on a une phrase complète
    if (!result.endsWith('.')) {
      result += '.';
    }
    
    return result;
  }
  
  // Fallback: première phrase avec poids + contexte
  const firstWeightSentence = sentences.find(s => /\d+\s*(?:grammes?|g\b)/i.test(s));
  if (firstWeightSentence) {
    // Essayer d'ajouter une phrase de contexte si disponible
    const contextSentence = sentences.find(s => 
      s !== firstWeightSentence && 
      ['normal', 'age', 'âge', 'souche', 'strain'].some(word => s.toLowerCase().includes(word))
    );
    
    if (contextSentence) {
      return firstWeightSentence + '. ' + contextSentence + '.';
    }
    
    return firstWeightSentence + '.';
  }
  
  // Ultime fallback: traitement général
  return sentences.slice(0, 2).join('. ') + '.';
}

// ✅ NOUVELLE FONCTION: Concision spécialisée pour questions de température
function makeConciseForTemperature(response: string, question: string): string {
  const sentences = response.split('.').map(s => s.trim()).filter(s => s.length > 0);
  
  // Chercher les phrases contenant des informations de température
  const tempSentences = sentences.filter(sentence => {
    const hasTemp = /\d+\s*°?C/i.test(sentence);
    const isRelevant = [
      'température', 'temperature', 'optimale', 'optimal', 'chaud', 'froid', 
      'hot', 'cold', 'maintenir', 'maintain', 'idéale', 'ideal'
    ].some(word => sentence.toLowerCase().includes(word));
    const isNotAdvice = ![
      'recommandé', 'essentiel', 'surveiller', 'vérifier'
    ].some(word => sentence.toLowerCase().includes(word));
    
    return (hasTemp || isRelevant) && isNotAdvice;
  });
  
  if (tempSentences.length > 0) {
    return tempSentences.slice(0, 2).join('. ') + '.';
  }
  
  return sentences.slice(0, 2).join('. ') + '.';
}

// ✅ NOUVELLE FONCTION: Concision spécialisée pour questions de diagnostic
function makeConciseForDiagnosis(response: string, question: string): string {
  const sentences = response.split('.').map(s => s.trim()).filter(s => s.length > 0);
  
  // Garder les phrases qui contiennent le diagnostic principal
  const diagnosticSentences = sentences.filter((sentence, index) => {
    const isDiagnostic = [
      'symptôme', 'cause', 'indicateur', 'signe', 'symptom', 'cause', 'sign',
      'problème', 'problem', 'maladie', 'disease', 'infection'
    ].some(word => sentence.toLowerCase().includes(word));
    const isEarly = index < 3; // Premières phrases seulement
    const isNotAdvice = ![
      'recommandé', 'consulter', 'contacter', 'surveillance'
    ].some(word => sentence.toLowerCase().includes(word));
    
    return (isDiagnostic || isEarly) && isNotAdvice;
  });
  
  return diagnosticSentences.slice(0, 2).join('. ') + '.';
}

// Enlever seulement les conseils excessifs (mode standard)
function removeExcessiveAdvice(response: string): string {
  const excessivePatterns = [
    // Phrases trop génériques
    /\.?\s*N'hésitez pas à[^.]*\./gi,
    /\.?\s*Pour des conseils plus personnalisés[^.]*\./gi,
    /\.?\s*Don't hesitate to[^.]*\./gi,
    /\.?\s*For more personalized advice[^.]*\./gi,
    /\.?\s*No dude en[^.]*\./gi,
    /\.?\s*Para consejos más personalizados[^.]*\./gi,
    
    // Répétitions de contact
    /\.?\s*Contactez votre vétérinaire[^.]*\./gi,
    /\.?\s*Contact your veterinarian[^.]*\./gi,
    /\.?\s*Contacte a su veterinario[^.]*\./gi,
    
    // Disclaimers excessifs
    /\.?\s*Il est toujours préférable de[^.]*\./gi,
    /\.?\s*It is always better to[^.]*\./gi,
    /\.?\s*Siempre es mejor[^.]*\./gi
  ];
  
  let cleaned = response;
  excessivePatterns.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '.');
  });
  
  return cleaned.replace(/\.+/g, '.').replace(/\s+/g, ' ').trim();
}

// Fonction utilitaire pour détecter le type de question
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

// Fonction pour analyser la complexité d'une réponse
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