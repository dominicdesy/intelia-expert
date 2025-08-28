import React, { useState } from 'react'
import { useTranslation } from '../../hooks/useTranslation'
import { CheckIcon } from '../../utils/icons'

// ==================== VERSION STABLE SANS RELOAD ====================
export const LanguageModal = ({ onClose }: { onClose: () => void }) => {
  const { t, currentLanguage } = useTranslation()
  const [isUpdating, setIsUpdating] = useState(false)
  
  const languages = [
    { 
      code: 'fr', 
      name: 'Français', 
      flag: '🇫🇷',
      description: 'Interface en français'
    },
    { 
      code: 'en', 
      name: 'English', 
      flag: '🇺🇸',
      description: 'Interface in English'
    },
    { 
      code: 'es', 
      name: 'Español', 
      flag: '🇪🇸',
      description: 'Interfaz en español'
    }
  ]

  const handleLanguageChange = async (languageCode: string) => {
    if (languageCode === currentLanguage || isUpdating) return

    setIsUpdating(true)
    
    console.log('🔄 [LanguageModal] Changement de langue:', currentLanguage, '→', languageCode)
    
    try {
      // 1. Sauvegarder dans localStorage (le hook détecte déjà ce changement)
      localStorage.setItem('intelia-preferred-language', languageCode)
      localStorage.setItem('intelia_language', languageCode)
      
      // 2. Émettre l'événement pour déclencher la mise à jour
      window.dispatchEvent(new CustomEvent('languageChanged', { 
        detail: { language: languageCode } 
      }))
      
      console.log('✅ [LanguageModal] Langue changée avec succès')
      
      // 3. Fermer immédiatement la modal
      onClose()
      
      // 4. PAS DE RELOAD - laisser React gérer le changement naturellement
      // Le hook useTranslation va détecter le changement et mettre à jour tous les composants
      
    } catch (error) {
      console.error('⌐ [LanguageModal] Erreur changement langue:', error)
    } finally {
      // Reset de l'état après un court délai
      setTimeout(() => {
        setIsUpdating(false)
      }, 1000)
    }
  }

  return (
    // CORRECTION PRINCIPALE: UN SEUL OVERLAY au lieu de deux éléments fixed séparés
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header - code original conservé */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {t('language.title')}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
            aria-label="Fermer la modal"
            title="Fermer"
          >
            ×
          </button>
        </div>
        
        {/* Content - code original conservé intégralement */}
        <div className="p-6">
          <div className="space-y-4">
            <p className="text-sm text-gray-600 mb-4">
              {t('language.description')}
            </p>
            
            <div className="space-y-3">
              {languages.map((language) => (
                <button
                  key={language.code}
                  onClick={() => handleLanguageChange(language.code)}
                  disabled={isUpdating}
                  className={`w-full flex items-center justify-between p-4 rounded-xl border-2 transition-all duration-200 ${
                    currentLanguage === language.code
                      ? 'border-blue-500 bg-blue-50 text-blue-900 shadow-md'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  } ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <div className="flex items-center space-x-4">
                    <span className="text-3xl">{language.flag}</span>
                    <div className="text-left">
                      <div className="font-semibold text-base text-gray-900">
                        {language.name}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {language.description}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {currentLanguage === language.code && (
                      <div className="flex items-center space-x-2">
                        {isUpdating ? (
                          <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                        ) : (
                          <CheckIcon className="w-6 h-6 text-blue-600" />
                        )}
                        <span className="text-sm font-medium text-blue-600">
                          {isUpdating ? 'Mise à jour...' : 'Active'}
                        </span>
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>

            <div className="flex justify-end pt-4 border-t border-gray-200">
              <button
                onClick={onClose}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                disabled={isUpdating}
              >
                {t('modal.close')}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}