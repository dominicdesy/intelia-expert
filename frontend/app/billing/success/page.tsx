"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function BillingSuccessPage() {
  const router = useRouter();
  const [countdown, setCountdown] = useState(5);

  useEffect(() => {
    // Countdown avant redirection
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          router.push("/chat");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-xl p-8 text-center">
        {/* Icône de succès */}
        <div className="mb-6">
          <div className="mx-auto w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
            <svg
              className="w-12 h-12 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </div>

        {/* Titre */}
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          🎉 Paiement réussi !
        </h1>

        {/* Message */}
        <p className="text-gray-600 mb-6">
          Votre abonnement a été activé avec succès. Vous pouvez maintenant
          profiter de toutes les fonctionnalités de votre nouveau plan !
        </p>

        {/* Informations */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <span className="text-green-600 text-xl mr-3">✓</span>
            <div className="text-sm text-left text-green-900">
              <p className="font-medium mb-1">Abonnement activé</p>
              <ul className="list-disc list-inside space-y-1 text-green-800">
                <li>Accès immédiat à toutes les fonctionnalités</li>
                <li>Facturation mensuelle automatique</li>
                <li>Email de confirmation envoyé</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Countdown */}
        <p className="text-sm text-gray-500 mb-6">
          Redirection automatique dans {countdown} seconde
          {countdown > 1 ? "s" : ""}...
        </p>

        {/* Boutons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => router.push("/chat")}
            className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
          >
            Commencer maintenant
          </button>
          <button
            onClick={() => router.push("/profile")}
            className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
          >
            Voir mon profil
          </button>
        </div>
      </div>
    </div>
  );
}
