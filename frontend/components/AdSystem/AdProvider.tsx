'use client';

import React from 'react';
import { AdModal } from './AdModal';
import { useAdSystem } from '@/lib/hooks/useAdSystem';

export const AdProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { showAd, currentAd, handleAdClose, handleAdClick } = useAdSystem();

  return (
    <>
      {children}
      {showAd && currentAd && (
        <AdModal
          isOpen={showAd}
          onClose={handleAdClose}
          adData={currentAd}
          onAdClick={handleAdClick}
        />
      )}
    </>
  );
};