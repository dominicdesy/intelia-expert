/**
 * TypewriterMessage.tsx - Message component with typewriter effect
 *
 * Displays LLM response with smooth typing animation
 */

import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { useTypewriter } from '../hooks/useTypewriter';
import { parseCotResponse } from '@/lib/utils/cotParser';
import { CotReasoning } from '@/components/CotReasoning';

interface TypewriterMessageProps {
  content: string;
  isStreaming?: boolean; // True while receiving from API
  speed?: number;
}

export const TypewriterMessage: React.FC<TypewriterMessageProps> = ({
  content,
  isStreaming = false,
  speed = 3
}) => {
  // Parse CoT sections
  const cotSections = useMemo(() => parseCotResponse(content || ''), [content]);

  // Apply typewriter effect only to final answer
  const { displayedText, isTyping } = useTypewriter({
    text: cotSections.answer,
    speed,
    enabled: !isStreaming && cotSections.answer.length > 0
  });

  return (
    <>
      {/* Display CoT reasoning (collapsible) - No typewriter effect */}
      {cotSections.hasStructure && !isTyping && (
        <CotReasoning sections={cotSections} />
      )}

      {/* Display main answer with typewriter effect */}
      <ReactMarkdown
        className="prose prose-sm max-w-none break-words prose-p:my-3 prose-li:my-1 prose-ul:my-4 prose-strong:text-gray-900 prose-headings:font-bold prose-headings:text-gray-900"
        components={{
          h2: ({ node, ...props }) => (
            <h2
              className="text-xl font-bold text-blue-900 mt-8 mb-6 border-b-2 border-blue-200 pb-3 bg-blue-50 px-4 py-2 rounded-t-lg"
              {...props}
            />
          ),
          h3: ({ node, ...props }) => (
            <h3
              className="text-lg font-semibold text-gray-800 mt-6 mb-4 border-l-4 border-blue-400 pl-4 bg-gray-50 py-2"
              {...props}
            />
          ),
          p: ({ node, ...props }) => (
            <p
              className="leading-relaxed text-gray-800 my-4 text-justify"
              {...props}
            />
          ),
          ul: ({ node, ...props }) => (
            <ul
              className="list-disc list-outside space-y-3 text-gray-800 my-6 ml-6 pl-2"
              {...props}
            />
          ),
          li: ({ node, ...props }) => (
            <li className="leading-relaxed pl-2 my-2" {...props} />
          ),
          strong: ({ node, ...props }) => (
            <strong
              className="font-bold text-blue-800 bg-blue-50 px-1 rounded"
              {...props}
            />
          ),
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-6 -mx-1 sm:mx-0">
              <table
                className="min-w-full border border-gray-300 rounded-lg shadow-sm"
                {...props}
              />
            </div>
          ),
          th: ({ node, ...props }) => (
            <th
              className="border border-gray-300 px-4 py-3 bg-blue-100 font-bold text-left text-blue-900"
              {...props}
            />
          ),
          td: ({ node, ...props }) => (
            <td
              className="border border-gray-300 px-4 py-3 hover:bg-gray-50"
              {...props}
            />
          ),
        }}
      >
        {displayedText}
      </ReactMarkdown>

      {/* Typing cursor */}
      {isTyping && (
        <span className="inline-block w-0.5 h-4 bg-blue-600 ml-0.5 animate-pulse"></span>
      )}
    </>
  );
};

export default TypewriterMessage;
