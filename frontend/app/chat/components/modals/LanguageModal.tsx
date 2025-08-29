import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from '../../hooks/useTranslation'
import { useAuthStore } from '@/lib/stores/auth' 
import { CheckIcon } from '../../utils/icons'

export const LanguageModal = ({ onClose }: { onClose: () => void }) => {
  const { t, changeLanguage, currentLanguage } = useTranslation()
  const { updateProfile } = useAuthStore() 
  const [isUpdating, setIsUpdating] = useState(false)
  const overlayRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  
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

  const handleLanguageChange = async (languageCode: string) => {
    if (languageCode === currentLanguage) return

    setIsUpdating(true)
    try {
      console.log('🔄 [LanguageModal] Début changement langue:', currentLanguage, '→', languageCode)
      
      changeLanguage(languageCode)
      console.log('✅ [LanguageModal] changeLanguage() appelée avec:', languageCode)
      
      await updateProfile({ language: languageCode } as any)
      console.log('✅ [LanguageModal] updateProfile() terminé')
      
      setTimeout(() => {
        onClose()
      }, 500)
      
    } catch (error) {
      console.error('❌ [LanguageModal] Erreur changement langue:', error)
    } finally {
      setIsUpdating(false)
    }
  }

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

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
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-3">
              {languages.map((lang) => (
                <div
                  key={lang.code}
                  onClick={() => !isUpdating && handleLanguageChange(lang.code)}
                  className={`
                    relative p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md
                    ${currentLanguage === lang.code 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 hover:border-blue-300 bg-white'
                    }
                    ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-50'}
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
                    
                    {currentLanguage === lang.code && (
                      <div className="flex items-center text-blue-600">
                        <CheckIcon className="w-5 h-5" />
                        <span className="ml-2 text-sm font-medium">{t('language.selected')}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 flex justify-end space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                disabled={isUpdating}
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