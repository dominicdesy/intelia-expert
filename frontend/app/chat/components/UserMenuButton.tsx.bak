import React, { useState } from 'react'
import { useAuthStore } from '../hooks/useAuthStore'
import { useTranslation } from '../hooks/useTranslation'
import { Modal } from './Modal'
import { UserInfoModal } from './modals/UserInfoModal'
import { AccountModal } from './modals/AccountModal'
import { LanguageModal } from './modals/LanguageModal'
import { ContactModal } from './modals/ContactModal'
import { PLAN_CONFIGS } from '../types'

// ==================== MENU UTILISATEUR ====================
export const UserMenuButton = () => {
  const { user, logout } = useAuthStore()
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [showUserInfoModal, setShowUserInfoModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)
  const [showAccountModal, setShowAccountModal] = useState(false)
  const [showLanguageModal, setShowLanguageModal] = useState(false)

  const userName = user?.name || user?.email || 'Utilisateur'
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
  
  const currentPlan = user?.plan || 'essential'
  const plan = PLAN_CONFIGS[currentPlan as keyof typeof PLAN_CONFIGS] || PLAN_CONFIGS.essential

  const handleContactClick = () => {
    setIsOpen(false)
    setShowContactModal(true)
  }

  const handleUserInfoClick = () => {
    setIsOpen(false)
    setShowUserInfoModal(true)
  }

  const handleAccountClick = () => {
    setIsOpen(false)
    setShowAccountModal(true)
  }

  const handleLanguageClick = () => {
    setIsOpen(false)
    setShowLanguageModal(true)
  }

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors"
        >
          <span className="text-white text-xs font-medium">{userInitials}</span>
        </button>

        {isOpen && (
          <>
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setIsOpen(false)}
            />
            
            <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
                <div className="mt-2">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${plan.bgColor} ${plan.color} border ${plan.borderColor}`}>
                    {plan.name}
                  </span>
                </div>
              </div>

              <button
                onClick={handleAccountClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z" />
                </svg>
                <span>{t('subscription.title')}</span>
              </button>

              <button
                onClick={handleUserInfoClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
                <span>{t('nav.profile')}</span>
              </button>

              <button
                onClick={handleLanguageClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m10.5 21 5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 0 1-3.827-5.802" />
                </svg>
                <span>{t('nav.language')}</span>
              </button>

              <button
                onClick={handleContactClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                </svg>
                <span>{t('nav.contact')}</span>
              </button>

              <button
                onClick={() => window.open('https://intelia.com/privacy-policy/', '_blank')}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875v12.75c0 .621.504 1.125 1.125 1.125h2.25" />
                </svg>
                <span>{t('nav.legal')}</span>
              </button>
              
              <div className="border-t border-gray-100 mt-2 pt-2">
                <button
                  onClick={() => {
                    logout()
                    setIsOpen(false)
                  }}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
                  </svg>
                  <span>{t('nav.logout')}</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <Modal
        isOpen={showAccountModal}
        onClose={() => setShowAccountModal(false)}
        title={t('subscription.title')}
      >
        <AccountModal user={user} onClose={() => setShowAccountModal(false)} />
      </Modal>

      <Modal
        isOpen={showUserInfoModal}
        onClose={() => setShowUserInfoModal(false)}
        title={t('profile.title')}
      >
        <UserInfoModal user={user} onClose={() => setShowUserInfoModal(false)} />
      </Modal>

      <Modal
        isOpen={showLanguageModal}
        onClose={() => setShowLanguageModal(false)}
        title={t('language.title')}
      >
        <LanguageModal onClose={() => setShowLanguageModal(false)} />
      </Modal>

      <Modal
        isOpen={showContactModal}
        onClose={() => setShowContactModal(false)}
        title={t('contact.title')}
      >
        <ContactModal onClose={() => setShowContactModal(false)} />
      </Modal>
    </>
  )
}