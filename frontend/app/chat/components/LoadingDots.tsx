/**
 * LoadingDots Component - Mobile-optimized loading animation
 * Displays 3 animated dots for loading states
 */

import React from 'react';

interface LoadingDotsProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingDots: React.FC<LoadingDotsProps> = ({
  className = '',
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-3 h-3',
  };

  const dotSize = sizeClasses[size];

  return (
    <div className={`loading-dots ${className}`} aria-label="Chargement en cours">
      <div className={`loading-dot ${dotSize}`}></div>
      <div className={`loading-dot ${dotSize}`}></div>
      <div className={`loading-dot ${dotSize}`}></div>
    </div>
  );
};

/**
 * LoadingMessage Component - Message bubble with loading animation
 * Replaces the old LoadingMessage with new mobile design
 */
interface LoadingMessageProps {
  className?: string;
}

export const LoadingMessage: React.FC<LoadingMessageProps> = ({ className = '' }) => {
  return (
    <div className={`flex items-start space-x-3 message-bubble ${className}`}>
      {/* AI Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
        <svg
          className="w-5 h-5 text-white"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        </svg>
      </div>

      {/* Loading Bubble */}
      <div className="flex-1 max-w-[85%]">
        <div
          className="inline-block px-4 py-3 rounded-2xl bg-gray-100 dark:bg-gray-800"
          style={{ borderTopLeftRadius: '4px' }}
        >
          <LoadingDots />
        </div>
      </div>
    </div>
  );
};
