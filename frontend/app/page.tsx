'use client'

import React, { Suspense, useMemo, useCallback, memo } from 'react'
import { useAuthenticationLogic } from './page_authentication'
import { LoginForm } from './page_login_form'
import { SignupModal } from './page_signup_modal'
import { usePageInitialization } from './page_initialization'
import { InteliaLogo, LanguageSelector, LoadingSpinner, AuthFooter } from './page_components'

// 🚀 Mémorisation des composants pour éviter les re-renders
const MemoizedLoginForm = memo(LoginForm)
const MemoizedSignupModal = memo(SignupModal)
const MemoizedInteliaLogo = memo(InteliaLogo)
const MemoizedLanguageSelector = memo(LanguageSelector)
const MemoizedAuthFooter = memo(AuthFooter)

// 🚀 Composant de chargement statique mémorisé
const LoadingContent = memo(() => (
  <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
    <div className="text-center">
      <MemoizedInteliaLogo className="w-16 h-16 mx-auto mb-4" />
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
      <p className="mt-4 text-gray-600">Initialisation...</p>
    </div>
  </div>
))

// 🚀 Contenu principal mémorisé
const PageContent = memo(() => {
  console.log('🚀 [PageContent] Composant PageContent rendu')
  
  // ✅ Récupération des données d'initialisation
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

  // ✅ Mémorisation stable des props pour éviter les re-renders du hook d'auth
  const authProps = useMemo(() => ({
    currentLanguage,
    t,
    isSignupMode,
    setCurrentLanguage
  }), [currentLanguage, t, isSignupMode, setCurrentLanguage])

  // ✅ Hook d'authentification avec props stables
  const authLogic = useAuthenticationLogic(authProps)

  // ✅ Gestionnaire de changement de langue mémorisé avec dépendances stables
  const handleLanguageChange = useCallback((newLanguage: any) => {
    setCurrentLanguage(newLanguage)
    localStorage.setItem('intelia-language', newLanguage)
  }, [setCurrentLanguage])

  // ✅ Mémorisation du contenu de chargement pour éviter les re-renders
  const loadingContent = useMemo(() => <LoadingContent />, [])

  // Affichage conditionnel avec contenu mémorisé
  if (!hasHydrated || !hasInitialized.current) {
    return loadingContent
  }

  console.log('🎨 [Render] Rendu de la page principale')

  return (
    <>
      {/* PAGE PRINCIPALE (LOGIN) */}
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
        
        {/* Sélecteur de langue */}
        <div className="absolute top-4 right-4">
          <MemoizedLanguageSelector 
            onLanguageChange={handleLanguageChange} 
            currentLanguage={currentLanguage} 
          />
        </div>
        
        {/* Logo et titre */}
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <MemoizedInteliaLogo className="w-16 h-16" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            {t.title}
          </h2>
        </div>

        {/* Formulaire de connexion */}
        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
            <MemoizedLoginForm 
              authLogic={authLogic}
              t={t}
              localError={localError}
              localSuccess={localSuccess}
              toggleMode={toggleMode}
            />
            <MemoizedAuthFooter t={t} />
          </div>
        </div>
      </div>

      {/* Modal d'inscription */}
      {isSignupMode && (
        <MemoizedSignupModal 
          authLogic={authLogic}
          t={t}
          localError={localError}
          localSuccess={localSuccess}
          toggleMode={toggleMode}
        />
      )}
    </>
  )
})

// ✅ Ajout du displayName pour le debugging
PageContent.displayName = 'PageContent'
LoadingContent.displayName = 'LoadingContent'

// Export principal avec Suspense
export default function Page() {
  console.log('🎯 [Page] Composant Page principal appelé')
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <PageContent />
    </Suspense>
  )