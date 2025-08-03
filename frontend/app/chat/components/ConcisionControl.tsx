// components/ConcisionControl.tsx - VERSION MISE À JOUR POUR BACKEND
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
      icon: '⚡',
      example: 'Réponse très courte, données clés uniquement'
    },
    { 
      level: ConcisionLevel.CONCISE, 
      label: 'Concis', 
      description: 'Information principale avec contexte minimum',
      icon: '🎯',
      example: 'Réponse courte avec explication essentielle'
    },
    { 
      level: ConcisionLevel.STANDARD, 
      label: 'Standard', 
      description: 'Réponse équilibrée avec conseils pratiques',
      icon: '📝',
      example: 'Réponse complète sans détails techniques'
    },
    { 
      level: ConcisionLevel.DETAILED, 
      label: 'Détaillé', 
      description: 'Réponse complète avec explications approfondies',
      icon: '📚',
      example: 'Réponse exhaustive avec conseils détaillés'
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
    <div className={`space-y-3 ${className}`}>
      <label className="text-sm font-medium text-gray-700">
        Niveau de détail des réponses
      </label>
      
      {/* 🚀 NOUVEAU : Information sur le fonctionnement */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start space-x-2">
          <span className="text-blue-600 text-sm">💡</span>
          <div className="text-xs text-blue-800">
            <strong>Nouveau :</strong> Le backend génère automatiquement toutes les versions. 
            Changez le niveau pour voir instantanément la réponse adaptée, sans nouvel appel API.
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {levels.map(({ level, label, description, icon, example }) => (
          <button
            key={level}
            onClick={() => updateConcisionLevel(level)}
            className={`p-4 text-left rounded-lg border-2 transition-all ${
              config.level === level
                ? 'bg-green-50 border-green-300 text-green-800'
                : 'bg-white border-gray-200 hover:border-gray-300 text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">{icon}</span>
              <span className="font-medium">{label}</span>
              {config.level === level && (
                <span className="ml-auto text-xs bg-green-200 text-green-800 px-2 py-1 rounded-full">
                  Actif
                </span>
              )}
            </div>
            <p className="text-xs text-gray-600 mb-2">{description}</p>
            <p className="text-xs text-gray-500 italic">{example}</p>
          </button>
        ))}
      </div>
      
      {/* 🚀 NOUVEAU : Indicateur de changement dynamique */}
      <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-700">
            <strong>Niveau actuel :</strong> {levels.find(l => l.level === config.level)?.label}
          </div>
          <div className="text-xs text-gray-500">
            🔄 Changement instantané
          </div>
        </div>
      </div>
    </div>
  );
};