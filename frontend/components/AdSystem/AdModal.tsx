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
  const isMountedRef = React.useRef(true); // Protection démontage

  // Cleanup au démontage
  React.useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 backdrop-blur-sm">
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-4xl w-full mx-4 overflow-hidden">
        {/* Header avec timer */}
        <div className="flex justify-between items-center p-4 bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 text-white">
          <div className="flex items-center space-x-2">
            <Brain className="w-6 h-6 text-blue-200 animate-pulse" />
            <span className="font-bold text-lg">{adData.headerTitle || adData.title}</span>
          </div>

          <div className="flex items-center space-x-3">
            {!canClose ? (
              <div className="flex items-center space-x-2 bg-white bg-opacity-20 px-4 py-2 rounded-full">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-medium">{timeLeft}s</span>
              </div>
            ) : (
              <button
                onClick={handleClose}
                className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* Contenu principal */}
        <div className="p-8">
          <div className="flex flex-col lg:flex-row gap-8">
            {/* Image principale */}
            <div className="lg:w-1/2">
              <img
                src={adData.imageUrl}
                alt={adData.title}
                className="w-full h-full object-cover rounded-xl shadow-lg"
              />
            </div>

            {/* Contenu texte */}
            <div className="lg:w-1/2 space-y-6">
              <div>
                <h2 className="text-3xl font-bold text-gray-900 mb-4 leading-tight">
                  {adData.title}
                </h2>
                <p
                  className="text-gray-700 text-lg leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: adData.description }}
                />
              </div>

              {/* Points clés avec icônes */}
              <div className="space-y-3">
                {adData.features.slice(0, 3).map((feature, index) => {
                  const icons = [Zap, TrendingUp, Brain];
                  const colors = ["text-yellow-500", "text-green-500", "text-blue-500"];
                  const Icon = icons[index % icons.length];

                  return (
                    <div key={index} className="flex items-start space-x-3">
                      <Icon className={`w-5 h-5 ${colors[index % colors.length]} flex-shrink-0 mt-1`} />
                      <p className="text-gray-600">{feature}</p>
                    </div>
                  );
                })}
              </div>

              {/* CTA Button */}
              <button
                onClick={handleAdClick}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-4 px-8 rounded-xl font-bold text-lg hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 flex items-center justify-center space-x-3 shadow-xl hover:shadow-2xl transform hover:scale-105"
              >
                <span>{adData.ctaText}</span>
                <ArrowRight className="w-5 h-5" />
              </button>

              <p className="text-center text-sm text-gray-500">
                {adData.ctaSubtext || "📖"}
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-blue-50 border-t text-center">
          <p className="text-xs text-gray-600">
            {adData.company}
          </p>
        </div>
      </div>
    </div>
  );
};