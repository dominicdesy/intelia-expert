'use client';

import React, { useState, useEffect } from 'react';
import { X, ExternalLink, Star, Users, Clock } from 'lucide-react';

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
  onAdClick 
}) => {
  const [timeLeft, setTimeLeft] = useState(15); // 15 secondes minimum
  const [canClose, setCanClose] = useState(false);

  useEffect(() => {
    if (isOpen && timeLeft > 0) {
      const timer = setTimeout(() => {
        setTimeLeft(prev => {
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
      setTimeLeft(15);
      setCanClose(false);
    }
  }, [isOpen]);

  const handleAdClick = () => {
    onAdClick(adData.id);
    window.open(adData.ctaUrl, '_blank');
  };

  const handleClose = () => {
    if (canClose) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
      <div className="relative bg-white rounded-lg shadow-2xl max-w-2xl w-full mx-4 overflow-hidden">
        {/* Header avec timer */}
        <div className="flex justify-between items-center p-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white">
          <div className="flex items-center space-x-2">
            <Star className="w-5 h-5 text-yellow-300" />
            <span className="font-semibold">Recommandation Personnalisée</span>
          </div>
          
          <div className="flex items-center space-x-3">
            {!canClose ? (
              <div className="flex items-center space-x-2 bg-white bg-opacity-20 px-3 py-1 rounded-full">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-medium">{timeLeft}s</span>
              </div>
            ) : (
              <button
                onClick={handleClose}
                className="p-1 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* Contenu de la publicité */}
        <div className="p-6">
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Image/Logo */}
            <div className="lg:w-1/3">
              <img 
                src={adData.imageUrl} 
                alt={adData.title}
                className="w-full h-40 lg:h-full object-cover rounded-lg shadow-md"
              />
            </div>

            {/* Contenu */}
            <div className="lg:w-2/3 space-y-4">
              <div>
                <h3 className="text-2xl font-bold text-gray-900 mb-2">
                  {adData.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {adData.description}
                </p>
              </div>

              {/* Statistiques */}
              <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                {adData.rating && (
                  <div className="flex items-center space-x-1">
                    <Star className="w-4 h-4 text-yellow-500 fill-current" />
                    <span>{adData.rating}/5</span>
                  </div>
                )}
                {adData.users && (
                  <div className="flex items-center space-x-1">
                    <Users className="w-4 h-4" />
                    <span>{adData.users} utilisateurs</span>
                  </div>
                )}
                {adData.duration && (
                  <div className="flex items-center space-x-1">
                    <Clock className="w-4 h-4" />
                    <span>{adData.duration}</span>
                  </div>
                )}
              </div>

              {/* Fonctionnalités */}
              <div className="space-y-2">
                <h4 className="font-semibold text-gray-900">Fonctionnalités clés :</h4>
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-1">
                  {adData.features.map((feature, index) => (
                    <li key={index} className="flex items-center space-x-2 text-sm text-gray-600">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* CTA Button */}
              <button
                onClick={handleAdClick}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 transition-all duration-200 flex items-center justify-center space-x-2 shadow-lg"
              >
                <span>{adData.ctaText}</span>
                <ExternalLink className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-gray-50 border-t text-center">
          <p className="text-xs text-gray-500">
            Publicité • {adData.company} • Basée sur votre utilisation d'Intelia Expert
          </p>
        </div>
      </div>
    </div>
  );
};