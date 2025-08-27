import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore, markStoreUnmounted } from '@/lib/stores/auth' 
import { useTranslation } from '../hooks/useTranslation'
import { Modal } from './Modal'
import { UserInfoModal } from './modals/UserInfoModal'
import { AccountModal } from './modals/AccountModal'
import { LanguageModal } from './modals/LanguageModal'
import { ContactModal } from './modals/ContactModal'
import { InviteFriendModal } from './modals/InviteFriendModal'
import { PLAN_CONFIGS } from '../../../types'
import { getSafeName, getSafeEmail, getSafeUserType, getSafePlan, getSafeInitials } from '../utils/safeUserHelpers'

// ==================== MENU UTILISATEUR - VERSION CORRIGÉE REACT #300 ====================
export const UserMenuButton = React.memo(() => {
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [showUserInfoModal, setShowUserInfoModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)
  const [showAccountModal, setShowAccountModal] = useState(false)
  const [showLanguageModal, setShowLanguageModal] = useState(false)
  const [showInviteFriendModal, setShowInviteFriendModal] = useState(false)

  // Protection contre React #300
  const isMountedRef = useRef(true)
  
  useEffect(() => {
    isMountedRef.current = true
    console.log('🗝️ [DEBUG-UserMenu] Composant monté')
    return () => {
      console.log('🧹 [DEBUG-UserMenu] Composant en cours de démontage')
      isMountedRef.current = false
    }
  }, [])

  // Mémoisation sécurisée des données utilisateur
  const { safeName, safeEmail, safeUserType, userInitials } = useMemo(() => {
    console.log('🔄 [DEBUG-UserMenu] Recalcul des données utilisateur sécurisées')
    const safeName = getSafeName(user)
    const safeEmail = getSafeEmail(user)
    const safeUserType = getSafeUserType(user)
    const userInitials = getSafeInitials(user)
    
    return { safeName, safeEmail, safeUserType, userInitials }
  }, [user?.name, user?.email, user?.user_type])

  // Mémoisation des variables de plan avec protection
  const { currentPlan, plan, isSuperAdmin } = useMemo(() => {
    const safePlan = getSafePlan(user)
    const safeUserType = getSafeUserType(user)
    
    const currentPlan = safePlan
    const plan = PLAN_CONFIGS[currentPlan as keyof typeof PLAN_CONFIGS] || PLAN_CONFIGS.essential
    const isSuperAdmin = safeUserType === 'super_admin'
    
    return { currentPlan, plan, isSuperAdmin }
  }, [user?.plan, user?.user_type])

  // Handlers sécurisés avec protection de montage et debug
  const handleContactClick = useCallback(() => {
    console.log('📞 [DEBUG-UserMenu] handleContactClick - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setIsOpen(false)
    setShowContactModal(true)
  }, [])

  const handleUserInfoClick = useCallback(() => {
    console.log('👤 [DEBUG-UserMenu] handleUserInfoClick - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setIsOpen(false)
    setShowUserInfoModal(true)
  }, [])

  const handleAccountClick = useCallback(() => {
    console.log('💳 [DEBUG-UserMenu] handleAccountClick - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setIsOpen(false)
    setShowAccountModal(true)
  }, [])

  const handleLanguageClick = useCallback(() => {
    console.log('🌍 [DEBUG-UserMenu] handleLanguageClick - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setIsOpen(false)
    setShowLanguageModal(true)
  }, [])

  const handleInviteFriendClick = useCallback(() => {
    console.log('👥 [DEBUG-UserMenu] handleInviteFriendClick - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setIsOpen(false)
    setShowInviteFriendModal(true)
  }, [])

  const handleStatisticsClick = useCallback(() => {
    console.log('📊 [DEBUG-UserMenu] handleStatisticsClick - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setIsOpen(false)
    window.open('/admin/statistics', '_blank')
  }, [])

  // CORRECTION CRITIQUE: VERSION CORRIGÉE DE LA DÉCONNEXION avec markStoreUnmounted
  const handleLogout = useCallback(async () => {
    console.log('🚨 [DEBUG-LOGOUT] === DÉBUT DÉCONNEXION DÉTAILLÉE ===')
    console.log('🚨 [DEBUG-LOGOUT] 1. État initial - isMounted:', isMountedRef.current)
    console.log('🚨 [DEBUG-LOGOUT] 1. User présent:', !!user)
    console.log('🚨 [DEBUG-LOGOUT] 1. Menu ouvert:', isOpen)
    
    if (!isMountedRef.current) {
      console.log('🚨 [DEBUG-LOGOUT] ABORT - composant déjà démonté')
      return
    }
    
    try {
      console.log('🚨 [DEBUG-LOGOUT] 2. Fermeture immédiate du menu...')
      setIsOpen(false)
      
      // TECHNIQUE 1: Marquer comme démonté AVANT logout pour éviter les setState
      console.log('🚨 [DEBUG-LOGOUT] 3. Marquage composant comme démonté AVANT logout...')
      isMountedRef.current = false
      
      // CORRECTION CRITIQUE: Marquer le store comme démonté AVANT logout()
      console.log('🚨 [DEBUG-LOGOUT] 4. Marquage store comme démonté AVANT logout...')
      markStoreUnmounted()
      
      // TECHNIQUE 2: Petite attente pour que React traite le setState du menu
      console.log('🚨 [DEBUG-LOGOUT] 5. Attente traitement React setState...')
      await new Promise(resolve => setTimeout(resolve, 50))
      
      console.log('🚨 [DEBUG-LOGOUT] 6. Appel logout() du store...')
      const logoutStartTime = performance.now()
      
      await logout()
      
      const logoutEndTime = performance.now()
      console.log('🚨 [DEBUG-LOGOUT] 7. logout() terminé en', Math.round(logoutEndTime - logoutStartTime), 'ms')
      
      console.log('🚨 [DEBUG-LOGOUT] 8. Redirection via router.replace...')
      router.replace('/')
      
      console.log('🚨 [DEBUG-LOGOUT] === FIN DÉCONNEXION RÉUSSIE ===')
      
    } catch (error) {
      console.error('🚨 [DEBUG-LOGOUT] ERREUR pendant logout:', error)
      console.error('🚨 [DEBUG-LOGOUT] Stack trace:', error instanceof Error ? error.stack : 'Pas de stack')
      
      // Même en cas d'erreur, forcer la redirection
      console.log('🚨 [DEBUG-LOGOUT] Redirection d\'urgence après erreur...')
      router.replace('/')
    }
  }, [logout, router, user, isOpen])

  const toggleOpen = useCallback(() => {
    console.log('🔀 [DEBUG-UserMenu] toggleOpen - isMounted:', isMountedRef.current, 'current isOpen:', isOpen)
    if (!isMountedRef.current) return
    setIsOpen(prev => !prev)
  }, [isOpen])

  const closeMenu = useCallback(() => {
    console.log('❌ [DEBUG-UserMenu] closeMenu - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setIsOpen(false)
  }, [])

  // Fonctions de fermeture de modales avec protection et debug
  const closeUserInfoModal = useCallback(() => {
    console.log('❌ [DEBUG-UserMenu] closeUserInfoModal - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setShowUserInfoModal(false)
  }, [])
  
  const closeContactModal = useCallback(() => {
    console.log('❌ [DEBUG-UserMenu] closeContactModal - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setShowContactModal(false)
  }, [])
  
  const closeAccountModal = useCallback(() => {
    console.log('❌ [DEBUG-UserMenu] closeAccountModal - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setShowAccountModal(false)
  }, [])
  
  const closeLanguageModal = useCallback(() => {
    console.log('❌ [DEBUG-UserMenu] closeLanguageModal - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setShowLanguageModal(false)
  }, [])
  
  const closeInviteFriendModal = useCallback(() => {
    console.log('❌ [DEBUG-UserMenu] closeInviteFriendModal - isMounted:', isMountedRef.current)
    if (!isMountedRef.current) return
    setShowInviteFriendModal(false)
  }, [])

  const openPrivacyPolicy = useCallback(() => {
    console.log('📜 [DEBUG-UserMenu] openPrivacyPolicy')
    window.open('https://intelia.com/privacy-policy/', '_blank')
  }, [])

  console.log('🔄 [DEBUG-UserMenu] Render - isMounted:', isMountedRef.current, 'user:', !!user)

  return (
    <>
      <div className="relative">
        {/* Bouton utilisateur avec affichage sécurisé */}
        <button
          onClick={toggleOpen}
          className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center hover:bg-blue-700 transition-colors"
        >
          <span className="text-white text-xs font-medium">{userInitials}</span>
        </button>

        {isOpen && (
          <>
            <div 
              className="fixed inset-0 z-40" 
              onClick={closeMenu}
            />
            
            <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
              {/* En-tête enrichi avec badges sécurisés */}
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900">{safeName}</p>
                <p className="text-xs text-gray-500">{safeEmail}</p>
                {/* Affichage conditionnel sécurisé du plan et du rôle */}
                {user && (
                  <div className="mt-2">
                    {/* Affichage du plan pour les utilisateurs normaux seulement */}
                    {!isSuperAdmin && (
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${plan.bgColor} ${plan.color} border ${plan.borderColor}`}>
                        {plan.name}
                      </span>
                    )}
                    {/* Affichage du rôle super admin */}
                    {isSuperAdmin && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-300">
                        Super Admin
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="py-1">
                {/* Menu statistiques - Super admin uniquement */}
                {isSuperAdmin && (
                  <button
                    onClick={handleStatisticsClick}
                    className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                    </svg>
                    <span>Statistiques</span>
                  </button>
                )}

                {/* Menu abonnement - masqué pour super admin */}
                {!isSuperAdmin && (
                  <button
                    onClick={handleAccountClick}
                    className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z" />
                    </svg>
                    <span>{t('subscription.title')}</span>
                  </button>
                )}

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
                  onClick={handleInviteFriendClick}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM3 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 019.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
                  </svg>
                  <span>{t('nav.inviteFriend')}</span>
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
                  onClick={openPrivacyPolicy}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875v12.75c0 .621.504 1.125 1.125 1.125h2.25" />
                  </svg>
                  <span>{t('nav.legal')}</span>
                </button>
              </div>

              {/* Footer */}
              <div className="border-t border-gray-100 pt-1">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
                  </svg>
                  <span>{t('nav.logout')}</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modal abonnement - seulement si pas super admin */}
      {!isSuperAdmin && (
        <Modal
          isOpen={showAccountModal}
          onClose={closeAccountModal}
          title={t('subscription.title')}
        >
          <AccountModal user={user as any} onClose={closeAccountModal} />
        </Modal>
      )}

      <Modal
        isOpen={showUserInfoModal}
        onClose={closeUserInfoModal}
        title={t('profile.title')}
      >
        <UserInfoModal user={user as any} onClose={closeUserInfoModal} />
      </Modal>

      <Modal
        isOpen={showLanguageModal}
        onClose={closeLanguageModal}
        title={t('language.title')}
      >
        <LanguageModal onClose={closeLanguageModal} />
      </Modal>

      <Modal
        isOpen={showContactModal}
        onClose={closeContactModal}
        title={t('contact.title')}
      >
        <ContactModal onClose={closeContactModal} />
      </Modal>

      <Modal
        isOpen={showInviteFriendModal}
        onClose={closeInviteFriendModal}
        title={t('nav.inviteFriend')}
      >
        <InviteFriendModal onClose={closeInviteFriendModal} />
      </Modal>
    </>
  )
})

UserMenuButton.displayName = 'UserMenuButton'