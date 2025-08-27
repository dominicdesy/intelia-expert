import React, { useState } from 'react'
import { useTranslation } from '../../hooks/useTranslation'
import { CheckIcon } from '../../utils/icons'

// ==================== VERSION DEBUG ====================
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
    
    console.log('🔄 [DEBUG] Changement de langue demandé:', { 
      from: currentLanguage, 
      to: languageCode 
    })
    
    try {
      // 1. Vérifier toutes les clés possibles dans localStorage
      console.log('📊 [DEBUG] État localStorage AVANT:', {
        'intelia-preferred-language': localStorage.getItem('intelia-preferred-language'),
        'intelia_language': localStorage.getItem('intelia_language'),
        'language': localStorage.getItem('language'),
        'user_language': localStorage.getItem('user_language')
      })
      
      // 2. Sauvegarder dans toutes les clés possibles pour être sûr
      localStorage.setItem('intelia-preferred-language', languageCode)
      localStorage.setItem('intelia_language', languageCode)
      localStorage.setItem('language', languageCode)
      localStorage.setItem('user_language', languageCode)
      
      console.log('💾 [DEBUG] Langues sauvegardées dans localStorage')
      
      // 3. Vérifier si le hook useTranslation a une fonction de changement
      console.log('🔍 [DEBUG] Hook useTranslation disponible:', {
        t: typeof t,
        currentLanguage,
        hookKeys: Object.keys({ t, currentLanguage })
      })
      
      // 4. Émettre tous les événements possibles
      window.dispatchEvent(new CustomEvent('languageChanged', { 
        detail: { language: languageCode } 
      }))
      window.dispatchEvent(new CustomEvent('language-changed', { 
        detail: { language: languageCode } 
      }))
      window.dispatchEvent(new Event('storageChanged'))
      
      console.log('📡 [DEBUG] Événements émis')
      
      // 5. Attendre et vérifier l'état
      await new Promise(resolve => setTimeout(resolve, 500))
      
      console.log('📊 [DEBUG] État localStorage APRÈS:', {
        'intelia-preferred-language': localStorage.getItem('intelia-preferred-language'),
        'intelia_language': localStorage.getItem('intelia_language'),
        'language': localStorage.getItem('language'),
        'user_language': localStorage.getItem('user_language')
      })
      
      // 6. Fermer la modal
      onClose()
      
      // 7. Reload en dernier recours
      console.log('🔄 [DEBUG] Reload dans 1 seconde...')
      setTimeout(() => {
        console.log('🔄 [DEBUG] Exécution du reload')
        window.location.reload()
      }, 1000)
      
    } catch (error) {
      console.error('❌ [DEBUG] Erreur changement langue:', error)
      setIsUpdating(false)
    }
  }

  // Debug: log de l'état actuel au render
  console.log('🎨 [DEBUG] Render LanguageModal:', { 
    currentLanguage,
    tFunction: typeof t,
    languageFromStorage: {
      'intelia-preferred-language': localStorage.getItem('intelia-preferred-language'),
      'intelia_language': localStorage.getItem('intelia_language'),
    }
  })

  return (
    <>
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-50" 
        onClick={onClose}
      />
      
      {/* Modal Container */}
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
          
          {/* DEBUG INFO */}
          <div className="p-4 bg-gray-50 border-b text-sm">
            <div className="font-mono text-xs">
              <div>🔍 DEBUG: currentLanguage = "{currentLanguage}"</div>
              <div>📁 localStorage keys: {Object.keys(localStorage).filter(k => k.includes('lang')).join(', ')}</div>
            </div>
          </div>
          
          {/* Content */}
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
    </>
  )
}