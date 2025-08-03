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