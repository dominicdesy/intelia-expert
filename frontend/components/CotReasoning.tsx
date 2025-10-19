/**
 * CotReasoning.tsx - Chain-of-Thought Reasoning Display Component
 *
 * Displays structured CoT reasoning in a collapsible, user-friendly format
 * Uses translation system - NO hardcoded text
 */

import React, { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import { useTranslation } from '@/lib/languages/i18n';
import ReactMarkdown from 'react-markdown';
import type { CotSections } from '@/lib/utils/cotParser';

interface CotReasoningProps {
  sections: CotSections;
  className?: string;
}

export const CotReasoning: React.FC<CotReasoningProps> = ({ sections, className = '' }) => {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);

  // Don't render if no structure
  if (!sections.hasStructure) {
    return null;
  }

  // Don't render if no thinking or analysis sections
  if (!sections.thinking && !sections.analysis) {
    return null;
  }

  return (
    <div className={`cot-reasoning-container ${className}`}>
      {/* Toggle Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors py-2 px-3 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20"
        aria-expanded={isExpanded}
        aria-label={isExpanded ? t('chat.cot.hideReasoning') : t('chat.cot.showReasoning')}
      >
        {isExpanded ? (
          <ChevronUpIcon className="w-4 h-4" />
        ) : (
          <ChevronDownIcon className="w-4 h-4" />
        )}
        <span className="font-medium">
          {isExpanded ? t('chat.cot.hideReasoning') : t('chat.cot.showReasoning')}
        </span>
      </button>

      {/* Collapsible Content */}
      {isExpanded && (
        <div className="cot-sections-container mt-3 space-y-4 border-l-4 border-blue-200 dark:border-blue-800 pl-4">

          {/* Thinking Section */}
          {sections.thinking && (
            <div className="cot-section">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-blue-500 rounded-full"></span>
                {t('chat.cot.thinking')}
              </h4>
              <div className="prose prose-sm dark:prose-invert max-w-none text-gray-600 dark:text-gray-400 bg-blue-50/50 dark:bg-blue-900/10 p-3 rounded-md">
                <ReactMarkdown>{sections.thinking}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Analysis Section */}
          {sections.analysis && (
            <div className="cot-section">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-green-500 rounded-full"></span>
                {t('chat.cot.analysis')}
              </h4>
              <div className="prose prose-sm dark:prose-invert max-w-none text-gray-600 dark:text-gray-400 bg-green-50/50 dark:bg-green-900/10 p-3 rounded-md">
                <ReactMarkdown>{sections.analysis}</ReactMarkdown>
              </div>
            </div>
          )}

        </div>
      )}

      <style jsx>{`
        .cot-reasoning-container {
          margin-top: 0.5rem;
          margin-bottom: 0.5rem;
        }

        .cot-section {
          animation: slideDown 0.2s ease-out;
        }

        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* Responsive adjustments */
        @media (max-width: 640px) {
          .cot-sections-container {
            padding-left: 0.75rem;
          }
        }
      `}</style>
    </div>
  );
};

export default CotReasoning;
