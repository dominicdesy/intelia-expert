import React, { useState } from 'react'
import { useTranslation } from '../../hooks/useTranslation'
import { useAuthStore } from '@/lib/stores/auth' 
import { CheckIcon } from '../../utils/icons'

export const LanguageModal = ({ onClose }: { onClose: () => void }) => {
  const { t, changeLanguage, currentLanguage } = useTranslation()
  const { updateProfile } = useAuthStore() 
  const [isUpdating, setIsUpdating] = useState(false)
  
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
    if (languageCode === currentLanguage || isUpdating) {
      return
    }

    setIsUpdating(true)
    
    try {
      console.log('🔄 [LanguageModal] Changement langue:', currentLanguage, '→', languageCode)
      
      // 1. Changer la langue immédiatement
      changeLanguage(languageCode)
      
      // 2. Sauvegarder dans le profil
      await updateProfile({ language: languageCode })
      
      console.log('✅ [LanguageModal] Changement terminé')
      
      // 3. Fermer la modal
      onClose()
      
    } catch (error) {
      console.error('❌ [LanguageModal] Erreur:', error)
      setIsUpdating(false)
    }
  }

  return (
    <div 
      className="fixed inset-0 z-50"
      style={{
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px'
      }}
      onClick={(e) => e.target === e.currentTarget && !isUpdating && onClose()}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {t('language.title')}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center"
              disabled={isUpdating}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {isUpdating && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center space-x-3">
                <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="text-blue-700 font-medium">
                  Changement en cours...
                </span>
              </div>
            </div>
          )}

          <div className="space-y-3">
            {languages.map((lang) => (
              <div
                key={lang.code}
                onClick={() => !isUpdating && handleLanguageChange(lang.code)}
                className={`
                  relative p-4 rounded-lg border-2 transition-all duration-200 hover:shadow-md cursor-pointer
                  ${currentLanguage === lang.code 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-200 hover:border-blue-300 bg-white hover:bg-blue-50'
                  }
                  ${isUpdating ? 'opacity-50 cursor-not-allowed' : ''}
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
  )
}