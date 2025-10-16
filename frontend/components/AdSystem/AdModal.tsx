"use client";

import React, { useState, useEffect } from "react";
import { X, ExternalLink, Star, Users, Clock, ArrowRight, Zap, TrendingUp, Brain } from "lucide-react";

interface AdData {
  id: string;
  title: string;
  description: string;
  imageUrl: string;
  ctaText: string;
  ctaUrl: string;
  company: string;
  rating?: number;
  users?: string;
  duration?: string;
  features: string[];
  headerTitle?: string;
  ctaSubtext?: string;
}

interface AdModalProps {
  isOpen: boolean;
  onClose: () => void;
  adData: AdData;
  onAdClick: (adId: string) => void;
}

export const AdModal: React.FC<AdModalProps> = ({
  isOpen,
  onClose,
  adData,
  onAdClick,
}) => {
  const [timeLeft, setTimeLeft] = useState(4);
  const [canClose, setCanClose] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const isMountedRef = React.useRef(true); // Protection démontage

  // Cleanup au démontage
  React.useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Détection mobile
  useEffect(() => {
    const detectMobile = () => {
      const userAgent = navigator.userAgent.toLowerCase();
      const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
      const isSmallScreen = window.innerWidth <= 768;
      const hasTouchScreen = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      const isIPadOS = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;

      return (isMobileUA || isIPadOS || (isSmallScreen && hasTouchScreen));
    };

    setIsMobile(detectMobile());

    const handleResize = () => {
      if (isMountedRef.current) {
        setIsMobile(detectMobile());
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (isOpen && timeLeft > 0) {
      const timer = setTimeout(() => {
        // PROTECTION: Vérifier que le composant est toujours monté
        if (!isMountedRef.current) return;

        setTimeLeft((prev) => {
          if (prev <= 1) {
            setCanClose(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      return () => clearTimeout(timer);
    }
  }, [isOpen, timeLeft]);

  useEffect(() => {
    if (isOpen) {
      setTimeLeft(4);
      setCanClose(false);
    }
  }, [isOpen]);

  const handleAdClick = () => {
    onAdClick(adData.id);
    window.open("https://zurl.co/xfmd9", "_blank");
  };

  const handleClose = () => {
    if (canClose) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 backdrop-blur-sm p-0">
      <div
        className={`relative bg-white shadow-2xl w-full overflow-hidden ${
          isMobile
            ? 'h-full max-h-full rounded-none'
            : 'rounded-2xl max-w-4xl mx-4'
        }`}
      >
        {/* Header avec timer */}
        <div className={`flex justify-between items-center bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 text-white ${
          isMobile ? 'p-3' : 'p-4'
        }`}>
          <div className="flex items-center space-x-2">
            <Brain className={`text-blue-200 animate-pulse ${isMobile ? 'w-5 h-5' : 'w-6 h-6'}`} />
            <span className={`font-bold ${isMobile ? 'text-sm truncate max-w-[180px]' : 'text-lg'}`}>
              {adData.headerTitle || adData.title}
            </span>
          </div>

          <div className="flex items-center space-x-3">
            {!canClose ? (
              <div className={`flex items-center space-x-2 bg-white bg-opacity-20 rounded-full ${
                isMobile ? 'px-3 py-1.5' : 'px-4 py-2'
              }`}>
                <Clock className="w-4 h-4" />
                <span className="text-sm font-medium">{timeLeft}s</span>
              </div>
            ) : (
              <button
                onClick={handleClose}
                className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors"
              >
                <X className={isMobile ? 'w-5 h-5' : 'w-5 h-5'} />
              </button>
            )}
          </div>
        </div>

        {/* Contenu principal - Scrollable sur mobile */}
        <div className={`${isMobile ? 'h-[calc(100vh-60px)] overflow-y-auto' : ''}`}>
          <div className={isMobile ? 'p-4' : 'p-8'}>
            <div className={`flex gap-6 ${isMobile ? 'flex-col' : 'flex-col lg:flex-row gap-8'}`}>
              {/* Image principale */}
              <div className={isMobile ? 'w-full' : 'lg:w-1/2'}>
                <img
                  src={adData.imageUrl}
                  alt={adData.title}
                  className={`w-full object-cover rounded-xl shadow-lg ${
                    isMobile ? 'h-48 max-h-48' : 'h-full'
                  }`}
                />
              </div>

              {/* Contenu texte */}
              <div className={`space-y-4 ${isMobile ? 'w-full' : 'lg:w-1/2 space-y-6'}`}>
                <div>
                  <h2 className={`font-bold text-gray-900 leading-tight ${
                    isMobile ? 'text-xl mb-2' : 'text-3xl mb-4'
                  }`}>
                    {adData.title}
                  </h2>
                  <p
                    className={`text-gray-700 leading-relaxed ${
                      isMobile ? 'text-sm' : 'text-lg'
                    }`}
                    dangerouslySetInnerHTML={{ __html: adData.description }}
                  />
                </div>

                {/* Points clés avec icônes */}
                <div className={isMobile ? 'space-y-2' : 'space-y-3'}>
                  {adData.features.slice(0, 3).map((feature, index) => {
                    const icons = [Zap, TrendingUp, Brain];
                    const colors = ["text-yellow-500", "text-green-500", "text-blue-500"];
                    const Icon = icons[index % icons.length];

                    return (
                      <div key={index} className="flex items-start space-x-3">
                        <Icon className={`${colors[index % colors.length]} flex-shrink-0 mt-1 ${
                          isMobile ? 'w-4 h-4' : 'w-5 h-5'
                        }`} />
                        <p className={`text-gray-600 ${isMobile ? 'text-sm' : ''}`}>{feature}</p>
                      </div>
                    );
                  })}
                </div>

                {/* CTA Button */}
                <button
                  onClick={handleAdClick}
                  className={`w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-bold hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 flex items-center justify-center space-x-3 shadow-xl hover:shadow-2xl transform hover:scale-105 ${
                    isMobile ? 'py-3 px-6 text-base' : 'py-4 px-8 text-lg'
                  }`}
                >
                  <span>{adData.ctaText}</span>
                  <ArrowRight className={isMobile ? 'w-4 h-4' : 'w-5 h-5'} />
                </button>

                <p className={`text-center text-gray-500 ${
                  isMobile ? 'text-xs' : 'text-sm'
                }`}>
                  {adData.ctaSubtext || "📖"}
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className={`bg-gradient-to-r from-gray-50 to-blue-50 border-t text-center ${
            isMobile ? 'px-4 py-3' : 'px-6 py-4'
          }`}>
            <p className="text-xs text-gray-600">
              {adData.company}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};