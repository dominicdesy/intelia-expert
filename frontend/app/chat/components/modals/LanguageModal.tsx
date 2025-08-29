import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from '../../hooks/useTranslation'
import { useAuthStore } from '@/lib/stores/auth' 
import { CheckIcon } from '../../utils/icons'

export const LanguageModal = ({ onClose }: { onClose: () => void }) => {
  const { t, changeLanguage, currentLanguage } = useTranslation()
  const { updateProfile } = useAuthStore() 
  const [isUpdating, setIsUpdating] = useState(false)
  const [showReloadPrompt, setShowReloadPrompt] = useState(false)
  const [selectedLanguage, setSelectedLanguage] = useState<string | null>(null)
  const overlayRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const updateTimeoutRef = useRef<NodeJS.Timeout>()
  
  // Nettoyer les timeouts au démontage
  useEffect(() => {
    return () => {
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current)
      }
    }
  }, [])
  
  // Forcer les styles au montage pour contourner les problèmes CSS
  useEffect(() => {
    const overlay = overlayRef.current
    
    if (overlay) {
      // Forcer les dimensions de l'overlay
      overlay.style.setProperty('width', '100vw', 'important')
      overlay.style.setProperty('height', '100vh', 'important')
      overlay.style.setProperty('top', '0', 'important')
      overlay.style.setProperty('left', '0', 'important')
      overlay.style.setProperty('right', '0', 'important')
      overlay.style.setProperty('bottom', '0', 'important')
      
      // BACKDROP GRISÉ avec flou
      overlay.style.setProperty('background-color', 'rgba(0, 0, 0, 0.5)', 'important')
      overlay.style.setProperty('backdrop-filter', 'blur(2px)', 'important')
      overlay.style.setProperty('animation', 'fadeIn 0.2s ease-out', 'important')
      overlay.style.setProperty('display', 'flex', 'important')
      overlay.style.setProperty('align-items', 'center', 'important')
      overlay.style.setProperty('justify-content', 'center', 'important')
      overlay.style.setProperty('padding', '16px', 'important')
      
      // Animation pour le contenu
      const content = overlay.querySelector('.bg-white') as HTMLElement
      if (content) {
        content.style.setProperty('animation', 'modalSlideIn 0.3s ease-out', 'important')
        content.style.setProperty('width', '95vw', 'important')
        content.style.setProperty('max-width', '700px', 'important')
        content.style.setProperty('max-height', '85vh', 'important')
        content.style.setProperty('min-width', '320px', 'important')
      }
    }
  }, [])
  
  const languages = [
    { 
      code: 'fr', 
      name: 'Français', 
      region: 'France', 
      flag: '🇫🇷',
      description: 'Interface en français'
    },
    { 
      code: 'en', 
      name: 'English', 
      region: 'United States', 
      flag: '🇺🇸',
      description: 'Interface in English'
    },
    { 
      code: 'es', 
      name: 'Español', 
      region: 'Latinoamérica', 
      flag: '🇪🇸',
      description: 'Interfaz en español'
    }
  ]

  const handleLanguageChange = useCallback(async (languageCode: string) => {
    if (languageCode === currentLanguage || isUpdating) return

    setIsUpdating(true)
    setSelectedLanguage(languageCode)
    
    try {
      console.log('🔄 [LanguageModal] Début changement langue:', currentLanguage, '→', languageCode)
      
      // 1. Délai pour éviter les conflits de re-render
      await new Promise(resolve => {
        updateTimeoutRef.current = setTimeout(resolve, 100)
      })
      
      // 2. Changer la langue dans le store
      changeLanguage(languageCode)
      console.log('✅ [LanguageModal] Langue changée dans le store:', languageCode)
      
      // 3. Délai avant mise à jour du profil
      await new Promise(resolve => {
        updateTimeoutRef.current = setTimeout(resolve, 200)
      })
      
      // 4. Sauvegarder dans le profil utilisateur
      await updateProfile({ language: languageCode } as any)
      console.log('✅ [LanguageModal] Profil sauvegardé')
      
      // 5. Marquer pour le rechargement du widget Zoho
      if (typeof window !== 'undefined') {
        localStorage.setItem('intelia_language_changed', 'true')
        localStorage.setItem('intelia_new_language', languageCode)
        localStorage.setItem('intelia_previous_language', currentLanguage)
        console.log('💾 [LanguageModal] Marqueur de rechargement créé')
      }
      
      // 6. Afficher l'invite de rechargement après un délai
      await new Promise(resolve => {
        updateTimeoutRef.current = setTimeout(resolve, 300)
      })
      
      setShowReloadPrompt(true)
      
    } catch (error) {
      console.error('❌ [LanguageModal] Erreur changement langue:', error)
      // Réinitialiser l'état en cas d'erreur
      setIsUpdating(false)
      setSelectedLanguage(null)
    }
  }, [currentLanguage, isUpdating, changeLanguage, updateProfile])

  const handleReloadPage = useCallback(() => {
    console.log('🔄 [LanguageModal] Rechargement page pour widget Zoho')
    
    // Nettoyer les timeouts avant rechargement
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current)
    }
    
    // Marquer que le rechargement est en cours
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelia_reload_in_progress', 'true')
    }
    
    window.location.reload()
  }, [])

  const handleSkipReload = useCallback(() => {
    console.log('⭐️ [LanguageModal] Rechargement ignoré - widget restera en ancienne langue')
    
    // Nettoyer les marqueurs
    if (typeof window !== 'undefined') {
      localStorage.removeItem('intelia_language_changed')
      localStorage.removeItem('intelia_new_language')
      localStorage.removeItem('intelia_previous_language')
    }
    
    setShowReloadPrompt(false)
    setIsUpdating(false)
    setSelectedLanguage(null)
    
    // Fermer avec un délai pour éviter les conflits
    setTimeout(() => {
      onClose()
    }, 100)
  }, [onClose])

  const handleOverlayClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !showReloadPrompt && !isUpdating) {
      onClose()
    }
  }, [showReloadPrompt, isUpdating, onClose])

  const handleClose = useCallback(() => {
    if (isUpdating || showReloadPrompt) return
    
    // Nettoyer les timeouts
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current)
    }
    
    onClose()
  }, [isUpdating, showReloadPrompt, onClose])

  // Interface de rechargement
  if (showReloadPrompt) {
    return (
      <>
        <style jsx>{`
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          
          @keyframes modalSlideIn {
            from { 
              opacity: 0; 
              transform: translateY(-20px) scale(0.95); 
            }
            to { 
              opacity: 1; 
              transform: translateY(0) scale(1); 
            }
          }
        `}</style>

        <div 
          ref={overlayRef}
          className="fixed inset-0 z-50"
        >
          <div 
            ref={contentRef}
            className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="p-6">
              <div className="flex items-center justify-center mb-6">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
              </div>

              <h2 className="text-2xl font-bold text-gray-900 text-center mb-4">
                {t('language.changeSuccess')}
              </h2>

              <div className="text-center text-gray-600 mb-6">
                <p className="mb-3">
                  {t('language.interfaceUpdated')}
                </p>
                <p className="text-sm">
                  {t('language.reloadForWidget')}
                </p>
              </div>

              <div className="flex flex-col space-y-3">
                <button
                  onClick={handleReloadPage}
                  className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 font-medium"
                >
                  {t('language.reloadNow')}
                </button>
                
                <button
                  onClick={handleSkipReload}
                  className="w-full px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                >
                  {t('language.continueWithoutReload')}
                </button>
              </div>
            </div>
          </div>
        </div>
      </>
    )
  }

  // Interface principale de sélection de langue
  return (
    <>
      {/* Styles CSS pour les animations */}
      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes modalSlideIn {
          from { 
            opacity: 0; 
            transform: translateY(-20px) scale(0.95); 
          }
          to { 
            opacity: 1; 
            transform: translateY(0) scale(1); 
          }
        }
        
        .language-option-disabled {
          pointer-events: none;
          opacity: 0.6;
        }
      `}</style>

      <div 
        ref={overlayRef}
        className="fixed inset-0 z-50"
        onClick={handleOverlayClick}
      >
        <div 
          ref={contentRef}
          className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        >
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">
                {t('language.title')}
              </h2>
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600 transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center disabled:opacity-50"
                disabled={isUpdating || showReloadPrompt}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Indicateur de mise à jour globale */}
            {isUpdating && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center space-x-3">
                  <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span className="text-blue-700 font-medium">
                    {t('language.updating')} {selectedLanguage && languages.find(l => l.code === selectedLanguage)?.name}...
                  </span>
                </div>
              </div>
            )}

            <div className="space-y-3">
              {languages.map((lang) => (
                <div
                  key={lang.code}
                  onClick={() => handleLanguageChange(lang.code)}
                  className={`
                    relative p-4 rounded-lg border-2 transition-all duration-200 hover:shadow-md
                    ${currentLanguage === lang.code 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 hover:border-blue-300 bg-white'
                    }
                    ${isUpdating 
                      ? 'language-option-disabled cursor-not-allowed' 
                      : 'cursor-pointer hover:bg-blue-50'
                    }
                  `}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <span className="text-2xl">{lang.flag}</span>
                      <div>
                        <div className="font-semibold text-gray-900">{lang.name}</div>
                        <div className="text-sm text-gray-600">{lang.region}</div>
                        <div className="text-xs text-gray-500 mt-1">{lang.description}</div>
                      </div>
                    </div>
                    
                    {/* Langue actuelle */}
                    {currentLanguage === lang.code && !isUpdating && (
                      <div className="flex items-center text-blue-600">
                        <CheckIcon className="w-5 h-5" />
                      </div>
                    )}

                    {/* Langue en cours de sélection */}
                    {selectedLanguage === lang.code && isUpdating && (
                      <div className="flex items-center text-blue-600">
                        <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 flex justify-end space-x-3">
              <button
                onClick={handleClose}
                className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isUpdating || showReloadPrompt}
              >
                {t('modal.close')}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}