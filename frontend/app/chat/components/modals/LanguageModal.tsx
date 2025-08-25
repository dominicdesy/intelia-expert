import React, { useState, useCallback } from 'react'
import { useTranslation } from '../../hooks/useTranslation'
import { useAuthStore } from '@/lib/stores/auth' 
import { CheckIcon } from '../../utils/icons'

// ==================== MODAL LANGUE AVEC POSITIONNEMENT CORRIGÉ ====================
export const LanguageModal = ({ onClose }: { onClose: () => void }) => {
  const { t, changeLanguage, currentLanguage } = useTranslation()
  const { updateProfile } = useAuthStore() 
  const [isUpdating, setIsUpdating] = useState(false)
  
  const languages = [
    { 
      code: 'fr', 
      name: 'Francais', 
      flag: '🇫🇷',
      description: 'Interface en francais'
    },
    { 
      code: 'en', 
      name: 'English', 
      flag: '🇺🇸',
      description: 'Interface in English'
    },
    { 
      code: 'es', 
      name: 'Espanol', 
      flag: '🇪🇸',
      description: 'Interfaz en espanol'
    }
  ]

  const handleLanguageChange = useCallback(async (languageCode: string) => {
    if (languageCode === currentLanguage || isUpdating) return

    setIsUpdating(true)
    
    try {
      console.log('🔄 [LanguageModal] Début changement langue:', currentLanguage, '→', languageCode)
      
      // Sauvegarder dans le profil utilisateur seulement
      await updateProfile({ language: languageCode } as any)
      console.log('✅ [LanguageModal] updateProfile() terminé')
      
      // Fermer immédiatement sans appeler changeLanguage
      onClose()
      
      // Changer la langue après fermeture de la modal
      setTimeout(() => {
        changeLanguage(languageCode)
        console.log('✅ [LanguageModal] changeLanguage() appelée avec:', languageCode)
      }, 100)
      
    } catch (error) {
      console.error('❌ [LanguageModal] Erreur changement langue:', error)
      setIsUpdating(false)
    }
  }, [currentLanguage, isUpdating, updateProfile, onClose, changeLanguage])

  return (
    <>
      {/* Overlay - même style que UserInfoModal */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-50" 
        onClick={onClose}
      />
      
      {/* Modal Container - même style que UserInfoModal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div 
          className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
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
          
          {/* Content - contenu original inchangé */}
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
                        <div className="font-semibold text-base">{language.name}</div>
                        <div className="text-xs text-gray-400 mt-1">{language.description}</div>
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
                            {isUpdating ? 'Updating...' : 'Active'}
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
    </>
  )
}