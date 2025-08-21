import React from 'react'
import { useTranslation } from '../../hooks/useTranslation'
import { PLAN_CONFIGS } from '@/types'

// ==================== MODAL ABONNEMENT AVEC POSITIONNEMENT CORRIGÉ ====================
export const AccountModal = ({ user, onClose }: { user: any, onClose: () => void }) => {
  const { t } = useTranslation()
  
  const currentPlan = user?.plan || 'essential'
  const userPlan = PLAN_CONFIGS[currentPlan as keyof typeof PLAN_CONFIGS]

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
              {t('subscription.title')}
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
            <div className="space-y-6">
              <div className="text-center">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('subscription.currentPlan')}</h3>
                <div className={`inline-flex items-center px-4 py-2 rounded-full ${userPlan.bgColor} ${userPlan.borderColor} border`}>
                  <span className={`font-medium ${userPlan.color}`}>{userPlan.name}</span>
                  <span className="mx-2 text-gray-400">•</span>
                  <span className={`font-bold ${userPlan.color}`}>
                    {currentPlan === 'essential' ? 'Gratuit' : '29$ / mois'}
                  </span>
                </div>
              </div>

              <div className={`p-4 rounded-lg ${userPlan.bgColor} ${userPlan.borderColor} border`}>
                <h4 className="font-medium text-gray-900 mb-3">Fonctionnalités incluses :</h4>
                <ul className="space-y-2">
                  {userPlan.features.map((feature, index) => (
                    <li key={index} className="flex items-center text-sm text-gray-700">
                      <span className="text-green-500 mr-2">✓</span>
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex justify-end pt-4">
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
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