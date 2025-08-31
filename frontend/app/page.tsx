'use client'

import React, { Suspense, useMemo, memo } from 'react'
import { useAuthenticationLogic } from './page_authentication'
import { LoginForm } from './page_login_form'
import { SignupModal } from './page_signup_modal'
import { usePageInitialization } from './page_initialization'
import { InteliaLogo, LanguageSelector, LoadingSpinner, AuthFooter } from './page_components'

// Skeleton du contenu avec textes par défaut pour éviter le FOUC
const ContentSkeleton = memo(() => (
  <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
    
    {/* Sélecteur de langue avec placeholder */}
    <div className="absolute top-4 right-4">
      <div className="w-32 h-10 bg-white/80 rounded-lg border border-gray-200 flex items-center justify-center">
        <span className="text-sm text-gray-500">🌐 FR</span>
      </div>
    </div>
    
    {/* Logo et titre avec texte par défaut */}
    <div className="sm:mx-auto sm:w-full sm:max-w-md">
      <div className="flex justify-center">
        <InteliaLogo className="w-16 h-16" />
      </div>
      <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
        Connexion à Intelia Expert
      </h2>
    </div>

    {/* Skeleton du formulaire avec structure complète */}
    <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
        <div className="space-y-6">
          
          {/* Email field skeleton */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <div className="h-10 bg-gray-100 rounded-md border border-gray-300 animate-pulse"></div>
          </div>
          
          {/* Password field skeleton */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Mot de passe
            </label>
            <div className="h-10 bg-gray-100 rounded-md border border-gray-300 animate-pulse"></div>
          </div>

          {/* Remember me skeleton */}
          <div className="flex items-center">
            <div className="w-4 h-4 bg-gray-200 rounded animate-pulse mr-2"></div>
            <span className="text-sm text-gray-600">Se souvenir de moi</span>
          </div>

          {/* Submit button skeleton */}
          <div className="h-10 bg-blue-500/50 rounded-md animate-pulse"></div>
          
          {/* Links skeleton */}
          <div className="text-center space-y-3">
            <div className="text-sm text-blue-600">
              Mot de passe oublié ?
            </div>
            <div className="text-sm text-gray-600">
              Pas encore de compte ? 
              <span className="text-blue-600 ml-1">S'inscrire</span>
            </div>
          </div>
        </div>
        
        {/* Footer skeleton */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="text-center space-y-2">
            <div className="text-xs text-gray-500">
              © 2024 Intelia Expert
            </div>
            <div className="flex justify-center space-x-4 text-xs">
              <span className="text-blue-600">Politique de confidentialité</span>
              <span className="text-blue-600">Conditions d'utilisation</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
))

// Composant de chargement initial amélioré
const InitialLoader = memo(() => (
  <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
    <div className="text-center">
      <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
      <p className="mt-4 text-gray-600 animate-pulse">Chargement...</p>
    </div>
  </div>
))

// Composant principal optimisé
const PageContent = memo(() => {
  console.log('🚀 [PageContent] Rendu du composant principal')
  
  // Récupération des données d'initialisation
  const initData = usePageInitialization()
  const {
    currentLanguage,
    setCurrentLanguage,
    t,
    localError,
    localSuccess,
    isSignupMode,
    toggleMode,
    hasHydrated,
    hasInitialized
  } = initData

  // Mémorisation stable des props d'authentification
  const authProps = useMemo(() => ({
    currentLanguage,
    t,
    isSignupMode,
    setCurrentLanguage
  }), [currentLanguage, t, isSignupMode, setCurrentLanguage])

  // Hook d'authentification avec props stables
  const authLogic = useAuthenticationLogic(authProps)

  // État de chargement : avant hydratation
  if (!hasHydrated) {
    return <InitialLoader />
  }

  // État de chargement : après hydratation mais avant initialisation complète
  if (!hasInitialized.current) {
    return <ContentSkeleton />
  }

  // Interface complètement chargée
  console.log('🎨 [Render] Interface complètement initialisée')

  return (
    <>
      {/* PAGE PRINCIPALE - Interface finale */}
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
        
        {/* Sélecteur de langue */}
        <div className="absolute top-4 right-4">
          <LanguageSelector />
        </div>
        
        {/* Logo et titre traduits */}
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <InteliaLogo className="w-16 h-16" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            {t('page.title')}
          </h2>
        </div>

        {/* Formulaire de connexion complet */}
        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
            <LoginForm 
              authLogic={authLogic}
              currentLanguage={currentLanguage}
              localError={localError}
              localSuccess={localSuccess}
              toggleMode={toggleMode}
            />
            <AuthFooter />
          </div>
        </div>
      </div>

      {/* Modal d'inscription conditionnelle */}
      {isSignupMode && (
        <SignupModal 
          authLogic={authLogic}
          localError={localError}
          localSuccess={localSuccess}
          toggleMode={toggleMode}
        />
      )}
    </>
  )
})

// Noms d'affichage pour le debugging
ContentSkeleton.displayName = 'ContentSkeleton'
InitialLoader.displayName = 'InitialLoader'
PageContent.displayName = 'PageContent'

// Export principal avec gestion d'erreur
export default function Page() {
  console.log('🎯 [Page] Initialisation de la page de connexion')
  
  return (
    <Suspense fallback={<InitialLoader />}>
      <PageContent />
    </Suspense>
  )
}

// CSS additionnels pour améliorer les transitions (à ajouter dans globals.css)
/*
.fade-in {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.skeleton-text {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
*/