import React, { useState } from 'react'
import { useAuthStore } from '@/lib/stores/auth' 
import { useTranslation } from '../hooks/useTranslation'
import { Modal } from './Modal'
import { UserInfoModal } from './modals/UserInfoModal'
import { AccountModal } from './modals/AccountModal'
import { LanguageModal } from './modals/LanguageModal'
import { ContactModal } from './modals/ContactModal'
import { InviteFriendModal } from './modals/InviteFriendModal'
import { PLAN_CONFIGS } from '../types'

// ==================== MENU UTILISATEUR AVEC INVITATIONS ====================
export const UserMenuButton = () => {
  const { user } = useAuthStore() 
  const { logout } = useAuthStore() // ✅ CHANGÉ: useAuth pour les actions
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [showUserInfoModal, setShowUserInfoModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)
  const [showAccountModal, setShowAccountModal] = useState(false)
  const [showLanguageModal, setShowLanguageModal] = useState(false)
  const [showInviteFriendModal, setShowInviteFriendModal] = useState(false)

  const getUserInitials = (user: any) => {
    const email = user?.email || ''
    const namePart = email.split('@')[0]
    return namePart ? namePart.slice(0, 2).toUpperCase() : 'DD'
  }

  const userInitials = getUserInitials(user)

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

  const handleInviteFriendClick = () => {
    setIsOpen(false)
    setShowInviteFriendModal(true)
  }

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      console.error('Error during logout:', error)
    }
  }

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center hover:bg-blue-700 transition-colors"
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
              {/* En-tête compte */}
              <div className="px-3 pb-2 border-b border-gray-100">
                <div className="text-sm font-medium text-gray-900">
                  {user?.email || 'Utilisateur'}
                </div>
                <div className="text-xs text-gray-500">
                  {t('nav.account')}
                </div>
              </div>

              {/* Actions */}
              <div className="py-1">
                <button
                  onClick={handleAccountClick}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  {/* Icône */}
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.5 20.25a8.25 8.25 0 0115 0" />
                  </svg>
                  <span>{t('subscription.title')}</span>
                </button>

                <button
                  onClick={handleUserInfoClick}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 9.75A3 3 0 1112 6.75m3 3A3 3 0 0012 6.75m3 3V21m0 0H9m6 0h3m-9 0H6" />
                  </svg>
                  <span>{t('nav.profile')}</span>
                </button>

                <button
                  onClick={handleLanguageClick}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m6-6H6" />
                  </svg>
                  <span>{t('nav.language')}</span>
                </button>

                {/* ✅ Inviter un ami */}
                <button
                  onClick={handleInviteFriendClick}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 11.25v6m0 0l-3-3m3 3l3-3M15 8.25a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span>{t('nav.inviteFriend') || 'Invite a friend'}</span>
                </button>

                <button
                  onClick={handleContactClick}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75l8.954 5.372a2.25 2.25 0 002.292 0L22.5 6.75M3.75 18h16.5a1.5 1.5 0 001.5-1.5v-9" />
                  </svg>
                  <span>{t('nav.contact')}</span>
                </button>
              </div>

              {/* Footer */}
              <div className="border-t border-gray-100 pt-1">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m0-6l3 3m0 0l-3 3m3-3H9" />
                  </svg>
                  <span>{t('nav.logout')}</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modales */}
      <Modal
        isOpen={showAccountModal}
        onClose={() => setShowAccountModal(false)}
        title={t('subscription.title')}
      >
        <AccountModal user={user as any} onClose={() => setShowAccountModal(false)} />
      </Modal>

      <Modal
        isOpen={showUserInfoModal}
        onClose={() => setShowUserInfoModal(false)}
        title={t('profile.title')}
      >
        <UserInfoModal user={user as any} onClose={() => setShowUserInfoModal(false)} />
      </Modal>

      <Modal
        isOpen={showLanguageModal}
        onClose={() => setShowLanguageModal(false)}
        title={t('nav.language')}
      >
        <LanguageModal onClose={() => setShowLanguageModal(false)} />
      </Modal>

      <Modal
        isOpen={showContactModal}
        onClose={() => setShowContactModal(false)}
        title={t('nav.contact')}
      >
        <ContactModal onClose={() => setShowContactModal(false)} />
      </Modal>

      {/* ✅ NOUVELLE MODAL INVITER UN AMI */}
      <Modal
        isOpen={showInviteFriendModal}
        onClose={() => setShowInviteFriendModal(false)}
        title="Inviter des amis"
      >
        <InviteFriendModal onClose={() => setShowInviteFriendModal(false)} />
      </Modal>
    </>
  )
}
