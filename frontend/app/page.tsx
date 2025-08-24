'use client'

import React, { Suspense } from 'react'
import { useAuthenticationLogic } from './page_authentication'
import { LoginForm } from './page_login_form'
import { SignupModal } from './page_signup_modal'
import { usePageInitialization } from './page_initialization'
import { InteliaLogo, LanguageSelector, LoadingSpinner, AuthFooter } from './page_components.tsx'

// Contenu principal de la page
function PageContent() {
  console.log('🚀 [PageContent] Composant PageContent rendu')
  
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
  } = usePageInitialization()

  const authLogic = useAuthenticationLogic({
    currentLanguage,
    t,
    isSignupMode,
    setCurrentLanguage
  })

  // Affichage conditionnel avec spinner amélioré
  if (!hasHydrated || !hasInitialized.current) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Initialisation...</p>
        </div>
      </div>
    )
  }

  const handleLanguageChange = (newLanguage: any) => {
    setCurrentLanguage(newLanguage)
    localStorage.setItem('intelia-language', newLanguage)
  }

  console.log('🎨 [Render] Rendu de la page principale')

  return (
    <>
      {/* PAGE PRINCIPALE (LOGIN) */}
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
        
        {/* Sélecteur de langue */}
        <div className="absolute top-4 right-4">
          <LanguageSelector onLanguageChange={handleLanguageChange} currentLanguage={currentLanguage} />
        </div>
        
        {/* Logo et titre */}
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <InteliaLogo className="w-16 h-16" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            {t.title}
          </h2>
        </div>

        {/* Formulaire de connexion */}
        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
            <LoginForm 
              authLogic={authLogic}
              t={t}
              localError={localError}
              localSuccess={localSuccess}
              toggleMode={toggleMode}
            />
            <AuthFooter t={t} />
          </div>
        </div>
      </div>

      {/* Modal d'inscription */}
      {isSignupMode && (
        <SignupModal 
          authLogic={authLogic}
          t={t}
          localError={localError}
          localSuccess={localSuccess}
          toggleMode={toggleMode}
        />
      )}
    </>
  )
}

// Export principal avec Suspense
export default function Page() {
  console.log('🎯 [Page] Composant Page principal appelé')
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <PageContent />
    </Suspense>
  )
}