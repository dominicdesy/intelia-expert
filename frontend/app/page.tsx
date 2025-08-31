'use client'

import React, { Suspense, useMemo, memo } from 'react'
import { useAuthenticationLogic } from './page_authentication'
import { LoginForm } from './page_login_form'
import { SignupModal } from './page_signup_modal'
import { usePageInitialization } from './page_initialization'
import { InteliaLogo, LanguageSelector, LoadingSpinner, AuthFooter } from './page_components'

// 🎯 SOLUTION RADICALE: Composant statique affiché immédiatement
const StaticLoginPage = memo(() => (
  <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
    
    {/* Sélecteur de langue statique */}
    <div className="absolute top-4 right-4">
      <div className="inline-flex items-center bg-white border border-gray-300 rounded-lg px-3 py-2 shadow-sm">
        <span className="text-sm font-medium text-gray-700">🌐 FR</span>
      </div>
    </div>
    
    {/* Logo et titre statiques */}
    <div className="sm:mx-auto sm:w-full sm:max-w-md">
      <div className="flex justify-center">
        <InteliaLogo className="w-16 h-16" />
      </div>
      <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
        Connexion à Intelia Expert
      </h2>
    </div>

    {/* Formulaire statique complet */}
    <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
        <form className="space-y-6">
          
          {/* Email field */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors text-base text-gray-900 bg-white"
              placeholder="votre@email.com"
            />
          </div>
          
          {/* Password field */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
              Mot de passe
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors text-base text-gray-900 bg-white pr-10"
                placeholder="••••••••"
              />
            </div>
          </div>

          {/* Remember me */}
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                Se souvenir de moi
              </label>
            </div>
            <button
              type="button"
              className="text-sm text-blue-600 hover:text-blue-500 transition-colors"
            >
              Mot de passe oublié ?
            </button>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-lg transition-colors duration-200"
          >
            Se connecter
          </button>
          
          {/* Signup link */}
          <div className="text-center">
            <span className="text-sm text-gray-600">
              Pas encore de compte ?{' '}
              <button
                type="button"
                className="text-blue-600 hover:text-blue-500 font-medium transition-colors"
              >
                S'inscrire
              </button>
            </span>
          </div>
        </form>
        
        {/* Footer statique */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="text-center space-y-3">
            <p className="text-xs text-gray-500">
              © 2024 Intelia Expert. Tous droits réservés.
            </p>
            <div className="flex justify-center space-x-4 text-xs">
              <button className="text-blue-600 hover:text-blue-500 transition-colors">
                Politique de confidentialité
              </button>
              <button className="text-blue-600 hover:text-blue-500 transition-colors">
                Conditions d'utilisation
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
))

// 🎯 Hook personnalisé pour détecter quand hydratation complète
const useIsHydrated = () => {
  const [isHydrated, setIsHydrated] = React.useState(false)
  
  React.useEffect(() => {
    // Marquer comme hydraté dès que ce useEffect s'exécute
    setIsHydrated(true)
  }, [])
  
  return isHydrated
}

// Composant dynamique qui remplace le statique
const DynamicLoginPage = memo(() => {
  console.log('🚀 [DynamicLoginPage] Rendu du composant dynamique')
  
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

  const authProps = useMemo(() => ({
    currentLanguage,
    t,
    isSignupMode,
    setCurrentLanguage
  }), [currentLanguage, t, isSignupMode, setCurrentLanguage])

  const authLogic = useAuthenticationLogic(authProps)

  // Ne pas afficher si pas prêt
  if (!hasHydrated || !hasInitialized.current) {
    return null // Ne rien afficher, laisser le statique
  }

  console.log('🎨 [Render] Interface dynamique prête')

  return (
    <>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
        
        <div className="absolute top-4 right-4">
          <LanguageSelector />
        </div>
        
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <InteliaLogo className="w-16 h-16" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            {t('page.title')}
          </h2>
        </div>

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

// Composant principal avec superposition
const PageContent = memo(() => {
  const isHydrated = useIsHydrated()
  
  return (
    <div className="relative">
      {/* 🎯 COUCHE 1: Interface statique (toujours visible au début) */}
      <div 
        className={`transition-opacity duration-300 ${
          isHydrated ? 'opacity-0 pointer-events-none absolute inset-0' : 'opacity-100'
        }`}
      >
        <StaticLoginPage />
      </div>
      
      {/* 🎯 COUCHE 2: Interface dynamique (fade in progressivement) */}
      <div 
        className={`transition-opacity duration-300 ${
          isHydrated ? 'opacity-100' : 'opacity-0'
        }`}
      >
        <DynamicLoginPage />
      </div>
    </div>
  )
})

// Noms d'affichage
StaticLoginPage.displayName = 'StaticLoginPage'
DynamicLoginPage.displayName = 'DynamicLoginPage'
PageContent.displayName = 'PageContent'

// Export principal
export default function Page() {
  console.log('🎯 [Page] Initialisation avec rendu immédiat')
  
  return (
    <Suspense fallback={<StaticLoginPage />}>
      <PageContent />
    </Suspense>
  )
}

// 🎯 CSS à ajouter dans globals.css pour la transition fluide
/*
.fade-transition {
  transition: opacity 300ms ease-in-out;
}

.static-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
}

.dynamic-content {
  position: relative;
  z-index: 2;
} 
*/