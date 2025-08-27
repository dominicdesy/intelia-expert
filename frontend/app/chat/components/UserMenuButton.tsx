// UserMenuButton.tsx - VERSION CORRIGÉE React #300

import React, { useState, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore, markStoreUnmounted } from '@/lib/stores/auth'
import { useTranslation } from '../../hooks/useTranslation'
import { UserInfoModal } from './modals/UserInfoModal'
import { AccountModal } from './modals/AccountModal'
import { ContactModal } from './modals/ContactModal'
import { LanguageModal } from './modals/LanguageModal'
import { InviteFriendModal } from './modals/InviteFriendModal'

// Configuration des plans avec mémoisation
const PLAN_CONFIGS = {
  essential: { name: 'Essential', color: 'text-green-600', bgColor: 'bg-green-50', borderColor: 'border-green-200', features: ['Questions illimitées', 'Support par email'] },
  standard: { name: 'Standard', color: 'text-blue-600', bgColor: 'bg-blue-50', borderColor: 'border-blue-200', features: ['Tout Essential', 'Analyses avancées', 'Priorité support'] },
  premium: { name: 'Premium', color: 'text-purple-600', bgColor: 'bg-purple-50', borderColor: 'border-purple-200', features: ['Tout Standard', 'Consultations directes', 'Support 24/7'] },
  enterprise: { name: 'Enterprise', color: 'text-gray-800', bgColor: 'bg-gray-50', borderColor: 'border-gray-300', features: ['Solutions personnalisées', 'Équipe dédiée', 'SLA garanti'] }
} as const

export const UserMenuButton = () => {
  console.log('🔄 [DEBUG-UserMenu] Render - isMounted: true user: true')
  
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const { t } = useTranslation()

  // États des modales
  const [isOpen, setIsOpen] = useState(false)
  const [showUserInfoModal, setShowUserInfoModal] = useState(false)
  const [showAccountModal, setShowAccountModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)
  const [showLanguageModal, setShowLanguageModal] = useState(false)
  const [showInviteFriendModal, setShowInviteFriendModal] = useState(false)

  // PROTECTION CRITIQUE: Ref pour éviter les double logout
  const logoutInProgressRef = React.useRef(false)
  const isMountedRef = React.useRef(true)

  // Cleanup au démontage
  React.useEffect(() => {
    isMountedRef.current = true
    return () => {
      console.log('🧹 [DEBUG-UserMenu] Composant en cours de démontage')
      isMountedRef.current = false
    }
  }, [])

  // Mémoisation des initiales utilisateur
  const userInitials = useMemo(() => {
    if (!user?.name) return 'U'
    
    const nameParts = user.name.trim().split(' ')
    let initials = ''
    
    if (nameParts.length >= 2) {
      initials = nameParts[0][0] + nameParts[nameParts.length - 1][0]
    } else if (nameParts.length === 1) {
      initials = nameParts[0].substring(0, 2)
    } else if (user?.email) {
      const emailParts = user.email.split('@')[0].split('.')
      if (emailParts.length >= 2) {
        initials = emailParts[0][0] + emailParts[1][0]
      } else {
        initials = user.email.substring(0, 2)
      }
    }
    
    return initials.toUpperCase()
  }, [user?.name, user?.email])

  // Mémoisation des variables de plan
  const { currentPlan, plan, isSuperAdmin } = useMemo(() => {
    const currentPlan = user?.plan || 'essential'
    const plan = PLAN_CONFIGS[currentPlan as keyof typeof PLAN_CONFIGS] || PLAN_CONFIGS.essential
    const isSuperAdmin = user?.user_type === 'super_admin'
    
    return { currentPlan, plan, isSuperAdmin }
  }, [user?.plan, user?.user_type])

  // Handlers des modales mémorisés
  const handleContactClick = useCallback(() => {
    console.log('📞 [DEBUG-UserMenu] handleContactClick - isMounted:', isMountedRef.current)
    setIsOpen(false)
    setShowContactModal(true)
  }, [])

  const handleUserInfoClick = useCallback(() => {
    console.log('👤 [DEBUG-UserMenu] handleUserInfoClick - isMounted:', isMountedRef.current)
    setIsOpen(false)
    setShowUserInfoModal(true)
  }, [])

  const handleAccountClick = useCallback(() => {
    console.log('💳 [DEBUG-UserMenu] handleAccountClick - isMounted:', isMountedRef.current)
    setIsOpen(false)
    setShowAccountModal(true)
  }, [])

  const handleLanguageClick = useCallback(() => {
    console.log('🌍 [DEBUG-UserMenu] handleLanguageClick - isMounted:', isMountedRef.current)
    setIsOpen(false)
    setShowLanguageModal(true)
  }, [])

  const handleInviteFriendClick = useCallback(() => {
    console.log('👥 [DEBUG-UserMenu] handleInviteFriendClick - isMounted:', isMountedRef.current)
    setIsOpen(false)
    setShowInviteFriendModal(true)
  }, [])

  const handleStatisticsClick = useCallback(() => {
    console.log('📊 [DEBUG-UserMenu] handleStatisticsClick - isMounted:', isMountedRef.current)
    setIsOpen(false)
    window.open('/admin/statistics', '_blank')
  }, [])

  // CORRECTION FINALE: handleLogout avec markStoreUnmounted AVANT logout
  const handleLogout = useCallback(async () => {
    console.log('🚨 [DEBUG-LOGOUT] === DÉBUT DÉCONNEXION ORDRE CORRECT ===')
    console.log('🚨 [DEBUG-LOGOUT] 1. État initial - isMounted:', isMountedRef.current)
    console.log('🚨 [DEBUG-LOGOUT] 1. User présent:', !!user)
    console.log('🚨 [DEBUG-LOGOUT] 1. Menu ouvert:', isOpen)
    
    // PROTECTION: Éviter les doubles logout
    if (logoutInProgressRef.current) {
      console.log('🚨 [DEBUG-LOGOUT] Logout déjà en cours, ignoré')
      return
    }

    logoutInProgressRef.current = true
    console.log('🚨 [DEBUG-LOGOUT] Marquage début logout')

    try {
      console.log('🚨 [DEBUG-LOGOUT] 2. Fermeture du menu...')
      setIsOpen(false)

      // CORRECTION CRITIQUE: Marquer le store comme inactif AVANT l'appel logout
      console.log('🚨 [DEBUG-LOGOUT] 2.5. Marquage store inactif AVANT logout...')
      markStoreUnmounted()

      console.log('🚨 [DEBUG-LOGOUT] 3. Attente déconnexion Supabase...')
      await logout()

      console.log('🚨 [DEBUG-LOGOUT] 4. Redirection après logout réussi')
      router.replace('/')
      
      console.log('🚨 [DEBUG-LOGOUT] === DÉCONNEXION RÉUSSIE ===')
      
    } catch (error) {
      console.error('🚨 [DEBUG-LOGOUT] Erreur logout:', error)
      
      // En cas d'erreur, s'assurer que le store reste inactif et forcer la redirection
      markStoreUnmounted()
      router.replace('/')
      
      console.log('🚨 [DEBUG-LOGOUT] === DÉCONNEXION FORCÉE APRÈS ERREUR ===')
    }
  }, [user, isOpen, logout, router])

  const toggleOpen = useCallback(() => {
    console.log('🔀 [DEBUG-UserMenu] toggleOpen - isMounted:', isMountedRef.current, 'current isOpen:', isOpen)
    setIsOpen(prev => !prev)
  }, [isOpen])

  const closeMenu = useCallback(() => {
    setIsOpen(false)
  }, [])

  // Fonctions de fermeture des modales mémorisées
  const closeUserInfoModal = useCallback(() => setShowUserInfoModal(false), [])
  const closeAccountModal = useCallback(() => setShowAccountModal(false), [])
  const closeContactModal = useCallback(() => setShowContactModal(false), [])
  const closeLanguageModal = useCallback(() => setShowLanguageModal(false), [])
  const closeInviteFriendModal = useCallback(() => setShowInviteFriendModal(false), [])

  if (!user) return null

  return (
    <>
      <div className="relative">
        <button
          onClick={toggleOpen}
          className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors font-medium text-sm"
          title={user.name || user.email}
          aria-label="Menu utilisateur"
        >
          {userInitials}
        </button>

        {isOpen && (
          <>
            <div 
              className="fixed inset-0 z-40" 
              onClick={closeMenu}
            />
            
            <div className="absolute right-0 top-12 w-80 bg-white rounded-xl shadow-lg border border-gray-200 z-50">
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-medium">
                    {userInitials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 truncate">
                      {user.name || 'Utilisateur'}
                    </div>
                    <div className="text-sm text-gray-500 truncate">
                      {user.email}
                    </div>
                    <div className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${plan.color} ${plan.bgColor} ${plan.borderColor} border`}>
                      {plan.name}
                    </div>
                  </div>
                </div>
              </div>

              <div className="py-2">
                <button
                  onClick={handleUserInfoClick}
                  className="w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-50 flex items-center space-x-3"
                >
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span>{t('nav.profile')}</span>
                </button>

                <button
                  onClick={handleAccountClick}
                  className="w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-50 flex items-center space-x-3"
                >
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                  </svg>
                  <span>{t('nav.account')}</span>
                </button>

                <button
                  onClick={handleLanguageClick}
                  className="w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-50 flex items-center space-x-3"
                >
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                  </svg>
                  <span>{t('nav.language')}</span>
                </button>

                <div className="border-t border-gray-100 my-2"></div>

                <button
                  onClick={handleInviteFriendClick}
                  className="w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-50 flex items-center space-x-3"
                >
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                  <span>Inviter un ami</span>
                </button>

                <button
                  onClick={handleContactClick}
                  className="w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-50 flex items-center space-x-3"
                >
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <span>{t('nav.contact')}</span>
                </button>

                {isSuperAdmin && (
                  <>
                    <div className="border-t border-gray-100 my-2"></div>
                    <button
                      onClick={handleStatisticsClick}
                      className="w-full px-4 py-2 text-left text-red-600 hover:bg-red-50 flex items-center space-x-3"
                    >
                      <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                      <span>Statistiques Admin</span>
                    </button>
                  </>
                )}

                <div className="border-t border-gray-100 my-2"></div>

                <button
                  onClick={handleLogout}
                  className="w-full px-4 py-2 text-left text-red-600 hover:bg-red-50 flex items-center space-x-3"
                >
                  <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span>{t('nav.logout')}</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {showUserInfoModal && (
        <UserInfoModal 
          user={user} 
          onClose={closeUserInfoModal}
        />
      )}

      {showAccountModal && (
        <AccountModal 
          user={user} 
          onClose={closeAccountModal}
        />
      )}

      {showContactModal && (
        <ContactModal 
          onClose={closeContactModal}
        />
      )}

      {showLanguageModal && (
        <LanguageModal 
          onClose={closeLanguageModal}
        />
      )}

      {showInviteFriendModal && (
        <InviteFriendModal 
          onClose={closeInviteFriendModal}
        />
      )}
    </>
  )
}