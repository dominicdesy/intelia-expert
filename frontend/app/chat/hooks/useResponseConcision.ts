// =============================================================================
// 1. HOOK REACT POUR CONCISION DES RÉPONSES
// =============================================================================

// hooks/useResponseConcision.ts
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
// 2. FONCTIONS DE TRAITEMENT DES RÉPONSES
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
  
  // Fallback: première phrase avec chiffres
  const sentences = response.split('.');
  for (const sentence of sentences) {
    if (/\d+/.test(sentence) && sentence.trim().length > 10) {
      return sentence.trim() + '.';
    }
  }
  
  // Ultime fallback: première phrase
  return sentences[0]?.trim() + '.' || response;
}

// Rendre concis (enlever conseils mais garder info principale)
function makeConcise(response: string, question: string): string {
  // Patterns de phrases à supprimer (conseils non demandés)
  const verbosePatterns = [
    /\.?\s*Il est essentiel de[^.]*\./gi,
    /\.?\s*Assurez-vous de[^.]*\./gi,
    /\.?\s*N'hésitez pas à[^.]*\./gi,
    /\.?\s*Pour garantir[^.]*\./gi,
    /\.?\s*À ce stade[^.]*\./gi,
    /\.?\s*pour favoriser le bien-être[^.]*\./gi,
    /\.?\s*en termes de[^.]*\./gi,
    
    // Anglais
    /\.?\s*It is essential to[^.]*\./gi,
    /\.?\s*Make sure to[^.]*\./gi,
    /\.?\s*Don't hesitate to[^.]*\./gi,
    
    // Espagnol
    /\.?\s*Es esencial[^.]*\./gi,
    /\.?\s*Asegúrese de[^.]*\./gi
  ];
  
  let cleaned = response;
  
  // Supprimer les patterns verbeux
  verbosePatterns.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '.');
  });
  
  // Nettoyer les doubles points et espaces
  cleaned = cleaned.replace(/\.+/g, '.').replace(/\s+/g, ' ').trim();
  
  // Si c'est une question de poids et que c'est encore long, extraire la phrase principale
  if (['poids', 'weight'].some(word => question.toLowerCase().includes(word)) && cleaned.length > 100) {
    const weightSentence = cleaned.split('.').find(sentence => 
      /\d+/.test(sentence) && ['gram', 'poids', 'weight'].some(word => 
        sentence.toLowerCase().includes(word)
      )
    );
    if (weightSentence) {
      return weightSentence.trim() + '.';
    }
  }
  
  return cleaned;
}

// Enlever seulement les conseils excessifs (mode standard)
function removeExcessiveAdvice(response: string): string {
  const excessivePatterns = [
    /\.?\s*N'hésitez pas à[^.]*\./gi,
    /\.?\s*Pour des conseils plus personnalisés[^.]*\./gi,
    /\.?\s*Don't hesitate to[^.]*\./gi,
    /\.?\s*For more personalized advice[^.]*\./gi
  ];
  
  let cleaned = response;
  excessivePatterns.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '.');
  });
  
  return cleaned.replace(/\.+/g, '.').replace(/\s+/g, ' ').trim();
}

// =============================================================================
// 3. COMPOSANT UI POUR CONTRÔLER LA CONCISION
// =============================================================================

// components/ConcisionControl.tsx
import React from 'react';
import { ConcisionLevel, useResponseConcision } from '../hooks/useResponseConcision';

interface ConcisionControlProps {
  className?: string;
  compact?: boolean;
}

export const ConcisionControl: React.FC<ConcisionControlProps> = ({ 
  className = '', 
  compact = false 
}) => {
  const { config, updateConcisionLevel } = useResponseConcision();

  const levels = [
    { 
      level: ConcisionLevel.ULTRA_CONCISE, 
      label: 'Minimal', 
      description: 'Juste l\'essentiel (ex: "410-450g")',
      icon: '⚡'
    },
    { 
      level: ConcisionLevel.CONCISE, 
      label: 'Concis', 
      description: 'Information principale (ex: "Le poids se situe entre 410-450g.")',
      icon: '🎯'
    },
    { 
      level: ConcisionLevel.STANDARD, 
      label: 'Standard', 
      description: 'Réponse normale sans conseils excessifs',
      icon: '📝'
    },
    { 
      level: ConcisionLevel.DETAILED, 
      label: 'Détaillé', 
      description: 'Réponse complète avec conseils',
      icon: '📚'
    }
  ];

  if (compact) {
    return (
      <div className={`flex gap-1 ${className}`}>
        {levels.map(({ level, icon, label }) => (
          <button
            key={level}
            onClick={() => updateConcisionLevel(level)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              config.level === level
                ? 'bg-green-100 text-green-800 border border-green-300'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            title={label}
          >
            {icon}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <label className="text-sm font-medium text-gray-700">
        Niveau de détail des réponses
      </label>
      <div className="grid grid-cols-2 gap-2">
        {levels.map(({ level, label, description, icon }) => (
          <button
            key={level}
            onClick={() => updateConcisionLevel(level)}
            className={`p-3 text-left rounded-lg border transition-all ${
              config.level === level
                ? 'bg-green-50 border-green-300 text-green-800'
                : 'bg-white border-gray-200 hover:border-gray-300 text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span>{icon}</span>
              <span className="font-medium">{label}</span>
            </div>
            <p className="text-xs text-gray-600">{description}</p>
          </button>
        ))}
      </div>
    </div>
  );
};

// =============================================================================
// 4. COMPOSANT CHAT AVEC CONCISION INTÉGRÉE
// =============================================================================

// components/ChatInterface.tsx (modification de votre composant existant)
import React, { useState } from 'react';
import { useResponseConcision } from '../hooks/useResponseConcision';
import { ConcisionControl } from './ConcisionControl';

interface ChatMessage {
  question: string;
  response: string;
  originalResponse?: string; // Garder l'original pour pouvoir basculer
  timestamp: string;
}

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showConcisionSettings, setShowConcisionSettings] = useState(false);
  
  const { processResponse, config } = useResponseConcision();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;

    setIsLoading(true);
    
    try {
      // Votre appel API existant (pas de modification côté backend)
      const response = await fetch('/api/v1/expert/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: question })
      });
      
      const data = await response.json();
      
      // Traiter la réponse avec le système de concision
      const processedResponse = processResponse(data.response, question);
      
      setMessages(prev => [...prev, {
        question,
        response: processedResponse,
        originalResponse: data.response, // Garder l'original
        timestamp: new Date().toISOString()
      }]);
      
      setQuestion('');
    } catch (error) {
      console.error('Erreur:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Fonction pour reprocesser tous les messages avec nouveau niveau
  const reprocessAllMessages = () => {
    setMessages(prev => prev.map(msg => ({
      ...msg,
      response: processResponse(msg.originalResponse || msg.response, msg.question)
    })));
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      {/* Header avec contrôles */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <div className="flex justify-between items-start mb-4">
          <h1 className="text-xl font-bold text-gray-800">Intelia Expert</h1>
          <div className="flex gap-2">
            <ConcisionControl compact />
            <button
              onClick={() => setShowConcisionSettings(!showConcisionSettings)}
              className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
            >
              ⚙️ Détail
            </button>
          </div>
        </div>
        
        {showConcisionSettings && (
          <div className="mt-4 p-4 bg-white rounded border">
            <ConcisionControl />
            <button
              onClick={reprocessAllMessages}
              className="mt-3 px-4 py-2 bg-green-100 text-green-700 rounded hover:bg-green-200 text-sm"
            >
              🔄 Appliquer à toutes les réponses
            </button>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="space-y-4 mb-6">
        {messages.map((msg, index) => (
          <div key={index} className="space-y-2">
            <div className="bg-blue-50 p-3 rounded-lg">
              <p className="text-blue-800">{msg.question}</p>
            </div>
            <div className="bg-green-50 p-3 rounded-lg">
              <p className="text-green-800">{msg.response}</p>
              {msg.originalResponse && msg.originalResponse !== msg.response && (
                <details className="mt-2">
                  <summary className="text-xs text-gray-500 cursor-pointer">
                    Voir la réponse complète
                  </summary>
                  <p className="text-xs text-gray-600 mt-1">{msg.originalResponse}</p>
                </details>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Formulaire */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Posez votre question..."
          className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !question.trim()}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? '...' : 'Envoyer'}
        </button>
      </form>
    </div>
  );
};

// =============================================================================
// 5. EXEMPLE D'UTILISATION DANS L'APP PRINCIPALE
// =============================================================================

// App.tsx
import React from 'react';
import { ChatInterface } from './components/ChatInterface';

function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <ChatInterface />
    </div>
  );
}

export default App;