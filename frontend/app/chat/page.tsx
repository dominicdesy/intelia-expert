'use client'

// Forcer l'utilisation du runtime Node.js au lieu d'Edge Runtime
export const runtime = 'nodejs'

import React, { useState, useEffect, useRef } from 'react'
import Script from 'next/script'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useTranslation } from '../i18n'

// Instance Supabase
const supabase = createClientComponentClient()

// ==================== COMPOSANT ZOHO SALESIQ SOLIDE ====================
const ZohoSalesIQ = ({ user }: { user: any }) => {
  useEffect(() => {
    if (!user) return

    console.log('🚀 Initialisation Zoho SalesIQ pour:', user.email)
    
    // 1. Configuration globale AVANT le chargement du script
    const initializeZohoConfig = () => {
      console.log('🔧 Configuration initiale Zoho SalesIQ')
      
      // Configuration globale requise par Zoho
      ;(window as any).$zoho = (window as any).$zoho || {}
      ;(window as any).$zoho.salesiq = (window as any).$zoho.salesiq || {}
      ;(window as any).$zoho.salesiq.widgetcode = 'siq657f7803e2e48661958a7ad1d48f293e50d5ba705ca11222b8cc9df0c8d01f09'
      
      // Fonction ready qui sera appelée automatiquement par Zoho
      ;(window as any).$zoho.salesiq.ready = function() {
        console.log('✅ Zoho SalesIQ initialisé avec succès')
        
        try {
          // Configuration utilisateur
          if ((window as any).$zoho.salesiq.visitor) {
            ;(window as any).$zoho.salesiq.visitor.info({
              name: user.name || 'Utilisateur',
              email: user.email || ''
            })
            console.log('👤 Informations utilisateur configurées:', { 
              name: user.name || 'Utilisateur', 
              email: user.email || '' 
            })
          }
          
          // Activation du chat
          if ((window as any).$zoho.salesiq.chat) {
            ;(window as any).$zoho.salesiq.chat.start()
            console.log('💬 Chat démarré')
          }
          
          // S'assurer que le widget est visible
          if ((window as any).$zoho.salesiq.floatbutton) {
            ;(window as any).$zoho.salesiq.floatbutton.visible('show')
            console.log('👀 Widget rendu visible')
          }
          
        } catch (error) {
          console.error('❌ Erreur configuration Zoho:', error)
        }
      }
    }

    // 2. Chargement du script de manière propre
    const loadZohoScript = () => {
      console.log('📡 Chargement script Zoho SalesIQ')
      
      // Supprimer les anciens scripts pour éviter les conflits
      const existingScripts = document.querySelectorAll('script[src*="salesiq.zohopublic.com"]')
      existingScripts.forEach(script => script.remove())
      
      // Créer et configurer le nouveau script
      const script = document.createElement('script')
      script.type = 'text/javascript'
      script.async = true
      script.defer = true
      script.src = `https://salesiq.zohopublic.com/widget?wc=${(window as any).$zoho.salesiq.widgetcode}`
      
      // Gestion succès/erreur
      script.onload = () => {
        console.log('✅ Script Zoho SalesIQ chargé avec succès')
        
        // Vérification que tout fonctionne
        setTimeout(() => {
          const zohoElements = document.querySelectorAll('[id*="siq"], [class*="siq"]')
          console.log(`🔍 ${zohoElements.length} éléments Zoho détectés dans le DOM`)
          
          if (zohoElements.length === 0) {
            console.warn('⚠️ Aucun élément widget visible, tentative de force')
            if ((window as any).$zoho?.salesiq?.ready) {
              ;(window as any).$zoho.salesiq.ready()
            }
          } else {
            console.log('✅ Widget Zoho opérationnel!')
          }
        }, 2000)
      }
      
      script.onerror = (error) => {
        console.error('❌ Erreur chargement script Zoho:', error)
        console.error('🔍 Vérifiez la CSP et la connectivité réseau')
      }
      
      // Ajouter au DOM
      document.head.appendChild(script)
    }

    // 3. Exécution séquentielle
    initializeZohoConfig()
    
    // Délai pour s'assurer que la config est prête
    setTimeout(() => {
      loadZohoScript()
    }, 100)

    // 4. Diagnostic périodique pour le debug
    const diagnosticInterval = setInterval(() => {
      const zohoElements = document.querySelectorAll('[id*="siq"], [class*="siq"]')
      
      if (zohoElements.length > 0) {
        console.log('✅ Widget Zoho actif et visible')
        clearInterval(diagnosticInterval)
      }
    }, 5000)

    // Nettoyage
    return () => {
      clearInterval(diagnosticInterval)
    }
  }, [user])

  return null // Ce composant n'a pas de rendu visuel
}

// ==================== STORE D'AUTHENTIFICATION ====================
const useAuthStore = () => {
  const [user, setUser] = useState<any>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const handleProfileUpdate = (event: CustomEvent) => {
      console.log('🔄 Mise à jour profil reçue:', event.detail)
      setUser(event.detail)
    }

    window.addEventListener('userProfileUpdated', handleProfileUpdate as EventListener)
    
    return () => {
      window.removeEventListener('userProfileUpdated', handleProfileUpdate as EventListener)
    }
  }, [])

  useEffect(() => {
    const loadUser = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('❌ Erreur récupération session:', error)
          setIsAuthenticated(false)
          setIsLoading(false)
          return
        }

        if (session?.user) {
          console.log('✅ Utilisateur connecté:', session.user)
          
          const userData = {
            id: session.user.id,
            email: session.user.email,
            name: `${session.user.user_metadata?.first_name || ''} ${session.user.user_metadata?.last_name || ''}`.trim() || session.user.email?.split('@')[0],
            
            firstName: session.user.user_metadata?.first_name || '',
            lastName: session.user.user_metadata?.last_name || '',
            linkedinProfile: session.user.user_metadata?.linkedin_profile || '',
            
            country: session.user.user_metadata?.country || 'CA',
            phone: session.user.user_metadata?.phone || '',
            
            companyName: session.user.user_metadata?.company_name || '',
            companyWebsite: session.user.user_metadata?.company_website || '',
            linkedinCorporate: session.user.user_metadata?.company_linkedin || '',
            
            user_type: session.user.user_metadata?.role || 'producer',
            language: session.user.user_metadata?.language || 'fr',
            created_at: session.user.created_at,
            consentGiven: true,
            consentDate: new Date(session.user.created_at)
          }
          
          setUser(userData)
          setIsAuthenticated(true)
        } else {
          console.log('ℹ️ Aucun utilisateur connecté')
          setIsAuthenticated(false)
        }
      } catch (error) {
        console.error('❌ Erreur chargement utilisateur:', error)
        setIsAuthenticated(false)
      } finally {
        setIsLoading(false)
      }
    }

    loadUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('🔄 Changement auth:', event, session?.user?.email)
        
        if (event === 'SIGNED_OUT') {
          setUser(null)
          setIsAuthenticated(false)
        } else if (event === 'SIGNED_IN' && session?.user) {
          loadUser()
        }
      }
    )

    return () => {
      if (subscription?.unsubscribe) {
        subscription.unsubscribe()
      }
    }
  }, [])

  const logout = async () => {
    try {
      console.log('🚪 Déconnexion en cours...')
      const { error } = await supabase.auth.signOut()
      
      if (error) {
        console.error('❌ Erreur déconnexion:', error)
        return
      }
      
      setUser(null)
      setIsAuthenticated(false)
      window.location.href = '/'
    } catch (error) {
      console.error('❌ Erreur critique déconnexion:', error)
    }
  }

  const updateProfile = async (data: any) => {
    try {
      console.log('📝 Mise à jour profil:', data)
      
      const updates = {
        data: {
          first_name: data.firstName,
          last_name: data.lastName,
          linkedin_profile: data.linkedinProfile,
          country: data.country,
          phone: data.phone,
          company_name: data.companyName,
          company_website: data.companyWebsite,
          company_linkedin: data.linkedinCorporate,
          language: data.language
        }
      }
      
      const { error } = await supabase.auth.updateUser(updates)
      
      if (error) {
        console.error('❌ Erreur mise à jour profil:', error)
        return { success: false, error: error.message }
      }
      
      const updatedUser = {
        ...user,
        ...data,
        name: `${data.firstName} ${data.lastName}`.trim()
      }
      
      setUser(updatedUser)
      console.log('✅ Profil mis à jour localement:', updatedUser)
      
      return { success: true }
    } catch (error: any) {
      console.error('❌ Erreur critique mise à jour:', error)
      return { success: false, error: error.message }
    }
  }

  const changePassword = async (currentPassword: string, newPassword: string) => {
    try {
      console.log('🔑 Changement mot de passe demandé')
      
      const { error } = await supabase.auth.updateUser({
        password: newPassword
      })
      
      if (error) {
        console.error('❌ Erreur changement mot de passe:', error)
        return { success: false, error: error.message }
      }
      
      return { success: true }
    } catch (error: any) {
      console.error('❌ Erreur critique changement mot de passe:', error)
      return { success: false, error: error.message }
    }
  }

  const exportUserData = async () => {
    try {
      console.log('📤 Export données utilisateur...')
      
      if (!user) {
        console.warn('⚠️ Aucun utilisateur à exporter')
        return
      }
      
      const exportData = {
        user_info: user,
        export_date: new Date().toISOString(),
        export_type: 'user_data_export'
      }
      
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json'
      })
      
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `intelia_export_${user.email}_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      console.log('✅ Export réalisé avec succès')
    } catch (error) {
      console.error('❌ Erreur export données:', error)
    }
  }

  const deleteUserData = async () => {
    try {
      console.log('🗑️ Suppression données utilisateur...')
      
      if (!confirm('Êtes-vous sûr de vouloir supprimer définitivement votre compte ? Cette action est irréversible.')) {
        return
      }
      
      alert('Pour supprimer définitivement votre compte, veuillez contacter support@intelia.com')
      
    } catch (error) {
      console.error('❌ Erreur suppression données:', error)
    }
  }

  return {
    user,
    isAuthenticated,
    isLoading,
    logout,
    updateProfile,
    changePassword,
    exportUserData,
    deleteUserData
  }
}

// ==================== HOOK CHAT ====================
const useChatStore = () => ({
  conversations: [
    {
      id: '1',
      title: 'Problème poulets Ross 308',
      messages: [
        { id: '1', role: 'user', content: 'Mes poulets Ross 308 de 25 jours pèsent 800g, est-ce normal ?' },
        { id: '2', role: 'assistant', content: 'Selon notre base documentaire, pour les poulets Ross 308...' }
      ],
      updated_at: '2024-01-20',
      created_at: '2024-01-20'
    }
  ],
  currentConversation: null,
  loadConversations: () => {},
  loadConversation: async (id: string) => {},
  deleteConversation: async (id: string) => {
    console.log('Suppression conversation:', id)
  },
  clearAllConversations: async () => {
    console.log('Suppression toutes conversations')
  },
  createConversation: () => {}
})

// ==================== TYPES ====================
interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
}

// ==================== ICÔNES SVG ====================
const PaperAirplaneIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0 1 21.485 12 59.77 59.77 0 0 1 3.27 20.876L5.999 12zm0 0h7.5" />
  </svg>
)

const UserIcon = ({ className = "w-8 h-8" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
)

const PlusIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
  </svg>
)

const EllipsisVerticalIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
  </svg>
)

const ThumbUpIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
  </svg>
)

const ThumbDownIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.106-1.79l-.05-.025A4 4 0 0011.057 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
  </svg>
)

const TrashIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
  </svg>
)

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== COMPOSANTS MODAL ====================
const Modal = ({ isOpen, onClose, title, children }: {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}) => {
  if (!isOpen) return null

  return (
    <>
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-50" 
        onClick={onClose}
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div 
          className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>
          <div className="p-6">
            {children}
          </div>
        </div>
      </div>
    </>
  )
}

// ==================== MODAL PROFIL ====================
const UserInfoModal = ({ user, onClose }: { user: any, onClose: () => void }) => {
  const { updateProfile, changePassword } = useAuthStore()
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<'profile' | 'password'>('profile')
  const [isLoading, setIsLoading] = useState(false)
  
  const [formData, setFormData] = useState({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    linkedinProfile: user?.linkedinProfile || '',
    companyName: user?.companyName || '',
    companyWebsite: user?.companyWebsite || '',
    linkedinCorporate: user?.linkedinCorporate || '',
    email: user?.email || '',
    phone: user?.phone || '',
    country: user?.country || 'CA'
  })

  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })

  const [passwordErrors, setPasswordErrors] = useState<string[]>([])

  const countries = [
    { code: 'CA', name: t('country.canada'), format: '+1 (XXX) XXX-XXXX' },
    { code: 'US', name: t('country.usa'), format: '+1 (XXX) XXX-XXXX' },
    { code: 'FR', name: t('country.france'), format: '+33 X XX XX XX XX' },
    { code: 'BE', name: t('country.belgium'), format: '+32 XXX XX XX XX' },
    { code: 'CH', name: t('country.switzerland'), format: '+41 XX XXX XX XX' },
    { code: 'MX', name: t('country.mexico'), format: '+52 XXX XXX XXXX' },
    { code: 'BR', name: t('country.brazil'), format: '+55 (XX) XXXXX-XXXX' }
  ]

  const formatPhoneNumber = (phone: string, countryCode: string) => {
    const cleaned = phone.replace(/\D/g, '')
    
    switch (countryCode) {
      case 'CA':
      case 'US':
        if (cleaned.length >= 10) {
          return `+1 (${cleaned.slice(-10, -7)}) ${cleaned.slice(-7, -4)}-${cleaned.slice(-4)}`
        }
        break
      case 'FR':
        if (cleaned.length >= 9) {
          return `+33 ${cleaned.slice(-9, -8)} ${cleaned.slice(-8, -6)} ${cleaned.slice(-6, -4)} ${cleaned.slice(-4, -2)} ${cleaned.slice(-2)}`
        }
        break
      case 'BE':
        if (cleaned.length >= 8) {
          return `+32 ${cleaned.slice(-8, -5)} ${cleaned.slice(-5, -3)} ${cleaned.slice(-3, -1)} ${cleaned.slice(-1)}`
        }
        break
      case 'CH':
        if (cleaned.length >= 9) {
          return `+41 ${cleaned.slice(-9, -7)} ${cleaned.slice(-7, -4)} ${cleaned.slice(-4, -2)} ${cleaned.slice(-2)}`
        }
        break
      case 'MX':
        if (cleaned.length >= 10) {
          return `+52 ${cleaned.slice(-10, -7)} ${cleaned.slice(-7, -4)} ${cleaned.slice(-4)}`
        }
        break
      case 'BR':
        if (cleaned.length >= 10) {
          return `+55 (${cleaned.slice(-10, -8)}) ${cleaned.slice(-8, -3)}-${cleaned.slice(-3)}`
        }
        break
    }
    return phone
  }

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value, formData.country)
    setFormData(prev => ({ ...prev, phone: formatted }))
  }

  const handleCountryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newCountry = e.target.value
    setFormData(prev => ({ 
      ...prev, 
      country: newCountry,
      phone: formatPhoneNumber(prev.phone, newCountry)
    }))
  }

  const getCurrentCountryFormat = () => {
    return countries.find(c => c.code === formData.country)?.format || ''
  }

  const validatePassword = (password: string): string[] => {
    const errors: string[] = []
    if (password.length < 8) errors.push(t('form.passwordMinLength'))
    if (!/[A-Z]/.test(password)) errors.push(t('form.passwordUppercase'))
    if (!/[a-z]/.test(password)) errors.push(t('form.passwordLowercase'))
    if (!/[0-9]/.test(password)) errors.push(t('form.passwordNumber'))
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) errors.push(t('form.passwordSpecial'))
    return errors
  }

  const handlePasswordChange = async () => {
    const errors: string[] = []
    
    if (!passwordData.currentPassword) {
      errors.push(t('form.required'))
    }
    
    if (!passwordData.newPassword) {
      errors.push(t('form.required'))
    } else {
      const passwordValidationErrors = validatePassword(passwordData.newPassword)
      errors.push(...passwordValidationErrors)
    }
    
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      errors.push(t('form.passwordMismatch'))
    }

    setPasswordErrors(errors)

    if (errors.length === 0) {
      setIsLoading(true)
      try {
        const result = await changePassword(passwordData.currentPassword, passwordData.newPassword)
        if (result.success) {
          alert(t('success.passwordChanged'))
          setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' })
          setActiveTab('profile')
        } else {
          setPasswordErrors([t('error.changePassword')])
        }
      } catch (error) {
        setPasswordErrors([t('error.changePassword')])
      }
      setIsLoading(false)
    }
  }

  const handleProfileSave = async () => {
    setIsLoading(true)
    try {
      const result = await updateProfile(formData)
      if (result.success) {
        alert(t('success.profileUpdated'))
        
        const updatedName = `${formData.firstName} ${formData.lastName}`.trim()
        const updatedInitials = updatedName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
        
        document.querySelectorAll('[data-user-name]').forEach(el => {
          el.textContent = updatedName
        })
        document.querySelectorAll('[data-user-initials]').forEach(el => {
          el.textContent = updatedInitials
        })

        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (!error && session?.user) {
          console.log('🔄 Rechargement données utilisateur après mise à jour')
          
          const updatedUserData = {
            ...user,
            name: `${formData.firstName} ${formData.lastName}`.trim(),
            firstName: formData.firstName,
            lastName: formData.lastName,
            linkedinProfile: formData.linkedinProfile,
            country: formData.country,
            phone: formData.phone,
            companyName: formData.companyName,
            companyWebsite: formData.companyWebsite,
            linkedinCorporate: formData.linkedinCorporate,
            email: formData.email
          }
          
          window.dispatchEvent(new CustomEvent('userProfileUpdated', { 
            detail: updatedUserData 
          }))
        }
        
        onClose()
      } else {
        alert(t('error.updateProfile') + ': ' + (result.error || t('error.generic')))
      }
    } catch (error) {
      console.error('❌ Erreur mise à jour profil:', error)
      alert(t('error.updateProfile'))
    }
    setIsLoading(false)
  }

  return (
    <div className="space-y-4 max-h-[70vh] overflow-y-auto">
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('profile')}
          className={`px-4 py-2 text-sm font-medium ${activeTab === 'profile' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          {t('profile.personalInfo')}
        </button>
        <button
          onClick={() => setActiveTab('password')}
          className={`px-4 py-2 text-sm font-medium ${activeTab === 'password' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          {t('profile.password')}
        </button>
      </div>

      {activeTab === 'profile' && (
        <>
          <div className="border-b border-gray-200 pb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-3">{t('profile.personalInfo')}</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.firstName')}</label>
                <input
                  type="text"
                  value={formData.firstName}
                  onChange={(e) => setFormData(prev => ({ ...prev, firstName: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.lastName')}</label>
                <input
                  type="text"
                  value={formData.lastName}
                  onChange={(e) => setFormData(prev => ({ ...prev, lastName: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.linkedinProfile')}</label>
              <input
                type="url"
                value={formData.linkedinProfile}
                onChange={(e) => setFormData(prev => ({ ...prev, linkedinProfile: e.target.value }))}
                placeholder="https://linkedin.com/in/votre-profil"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="border-b border-gray-200 pb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-3">{t('profile.contact')}</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.email')}</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.country')}</label>
              <select 
                value={formData.country}
                onChange={handleCountryChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                {countries.map(country => (
                  <option key={country.code} value={country.code}>
                    {country.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('profile.phone')}
                <span className="text-xs text-gray-500 ml-2">{t('form.phoneFormat')}: {getCurrentCountryFormat()}</span>
              </label>
              <input
                type="tel"
                value={formData.phone}
                onChange={handlePhoneChange}
                placeholder={getCurrentCountryFormat()}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="pb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-3">{t('profile.company')}</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.companyName')}</label>
              <input
                type="text"
                value={formData.companyName}
                onChange={(e) => setFormData(prev => ({ ...prev, companyName: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.companyWebsite')}</label>
              <input
                type="url"
                value={formData.companyWebsite}
                onChange={(e) => setFormData(prev => ({ ...prev, companyWebsite: e.target.value }))}
                placeholder="https://www.exemple.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.companyLinkedin')}</label>
              <input
                type="url"
                value={formData.linkedinCorporate}
                onChange={(e) => setFormData(prev => ({ ...prev, linkedinCorporate: e.target.value }))}
                placeholder="https://linkedin.com/company/votre-entreprise"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
              disabled={isLoading}
            >
              {t('modal.cancel')}
            </button>
            <button
              onClick={handleProfileSave}
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? t('modal.loading') : t('modal.save')}
            </button>
          </div>
        </>
      )}

      {activeTab === 'password' && (
        <>
          <div className="pb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-3">{t('profile.password')}</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.currentPassword')}</label>
                <input
                  type="password"
                  value={passwordData.currentPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, currentPassword: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.newPassword')}</label>
                <input
                  type="password"
                  value={passwordData.newPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, newPassword: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <div className="mt-2 text-xs text-gray-600">
                  <p>{t('profile.passwordRequirements')}</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>{t('form.passwordMinLength')}</li>
                    <li>{t('form.passwordUppercase')}</li>
                    <li>{t('form.passwordLowercase')}</li>
                    <li>{t('form.passwordNumber')}</li>
                    <li>{t('form.passwordSpecial')}</li>
                  </ul>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.confirmPassword')}</label>
                <input
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              {passwordErrors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <div className="text-sm text-red-800">
                    <p className="font-medium">{t('profile.passwordErrors')}</p>
                    <ul className="list-disc list-inside mt-1">
                      {passwordErrors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
            <button
              onClick={() => setActiveTab('profile')}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
              disabled={isLoading}
            >
              {t('modal.back')}
            </button>
            <button
              onClick={handlePasswordChange}
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? t('modal.updating') : t('profile.password')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

const AccountModal = ({ user, onClose }: { user: any, onClose: () => void }) => {
  const { t } = useTranslation()
  
  // Simuler le forfait utilisateur (à remplacer par les vraies données)
  const currentPlan = user?.plan || 'essential'
  
  const plans = {
    essential: {
      name: t('plan.essential'),
      price: 'Gratuit',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      features: [
        '50 questions par mois',
        'Accès aux documents publics',
        'Support par email',
        'Interface web'
      ]
    },
    pro: {
      name: t('plan.pro'),
      price: '29$ / mois',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      features: [
        'Questions illimitées',
        'Accès documents confidentiels',
        'Support prioritaire',
        'Interface web + mobile',
        'Analytics avancées'
      ]
    },
    max: {
      name: t('plan.max'),
      price: 'Sur mesure',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
      features: [
        'Tout du forfait Pro',
        'Documents privés personnalisés',
        'Support téléphonique dédié',
        'Intégrations API',
        'Formation équipe',
        'SLA garanti'
      ]
    }
  }

  const userPlan = plans[currentPlan as keyof typeof plans]

  return (
    <div className="space-y-6">
      {/* Forfait actuel */}
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('subscription.currentPlan')}</h3>
        <div className={`inline-flex items-center px-4 py-2 rounded-full ${userPlan.bgColor} ${userPlan.borderColor} border`}>
          <span className={`font-medium ${userPlan.color}`}>{userPlan.name}</span>
          <span className="mx-2 text-gray-400">•</span>
          <span className={`font-bold ${userPlan.color}`}>{userPlan.price}</span>
        </div>
      </div>

      {/* Fonctionnalités du forfait actuel */}
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

      {/* Options d'upgrade */}
      {currentPlan !== 'max' && (
        <div className="space-y-3">
          <h4 className="font-medium text-gray-900">{t('subscription.modify')}</h4>
          
          {currentPlan === 'essential' && (
            <div className="p-4 border border-blue-200 rounded-lg bg-blue-50">
              <div className="flex justify-between items-center">
                <div>
                  <h5 className="font-medium text-blue-900">Forfait Pro</h5>
                  <p className="text-sm text-blue-700">Questions illimitées + fonctionnalités avancées</p>
                </div>
                <button
                  onClick={() => {
                    console.log('Upgrade vers Pro demandé')
                    // Logique d'upgrade à implémenter
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
                >
                  {t('subscription.update')}
                </button>
              </div>
            </div>
          )}

          <div className="p-4 border border-purple-200 rounded-lg bg-purple-50">
            <div className="flex justify-between items-center">
              <div>
                <h5 className="font-medium text-purple-900">Forfait Max</h5>
                <p className="text-sm text-purple-700">Solution personnalisée pour votre organisation</p>
              </div>
              <button
                onClick={() => {
                  console.log('Contact commercial demandé')
                  window.open('mailto:sales@intelia.com?subject=Demande forfait Max', '_blank')
                }}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors text-sm"
              >
                {t('nav.contact')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Utilisation du mois (simulation) */}
      <div className="p-4 border border-gray-200 rounded-lg bg-gray-50">
        <h4 className="font-medium text-gray-900 mb-2">Utilisation ce mois-ci</h4>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Questions posées :</span>
          <span className="font-medium text-gray-900">
            {currentPlan === 'essential' ? '23 / 50' : 'Illimité'}
          </span>
        </div>
        {currentPlan === 'essential' && (
          <div className="mt-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full" style={{ width: '46%' }}></div>
            </div>
          </div>
        )}
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
  )
}

const ContactModal = ({ onClose }: { onClose: () => void }) => {
  const { t } = useTranslation()
  
  return (
    <div className="space-y-4">
      {/* Call Us */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">{t('contact.phone')}</h3>
          <p className="text-sm text-gray-600 mb-2">
            {t('contact.phoneDescription')}
          </p>
          <a 
            href="tel:+18666666221"
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            +1 (866) 666 6221
          </a>
        </div>
      </div>

      {/* Email Us */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">{t('contact.email')}</h3>
          <p className="text-sm text-gray-600 mb-2">
            {t('contact.emailDescription')}
          </p>
          <a 
            href="mailto:support@intelia.com"
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            support@intelia.com
          </a>
        </div>
      </div>

      {/* Visit our website */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3s-4.5 4.03-4.5 9 2.015 9 4.5 9zm0 0c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3s4.5 4.03 4.5 9-2.015 9-4.5 9z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">{t('contact.website')}</h3>
          <p className="text-sm text-gray-600 mb-2">
            {t('contact.websiteDescription')}
          </p>
          <a 
            href="https://www.intelia.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            www.intelia.com
          </a>
        </div>
      </div>

      <div className="flex justify-end pt-3">
        <button
          onClick={onClose}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          {t('modal.close')}
        </button>
      </div>
    </div>
  )
}

// ==================== MENU HISTORIQUE ====================
const HistoryMenu = () => {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const { conversations, deleteConversation, clearAllConversations } = useChatStore()

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        title={t('nav.history')}
      >
        <EllipsisVerticalIcon className="w-5 h-5" />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          <div className="absolute left-0 top-full mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-96 overflow-y-auto">
            <div className="p-4 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">{t('nav.history')}</h3>
                <button
                  onClick={() => {
                    clearAllConversations()
                    setIsOpen(false)
                  }}
                  className="text-red-600 hover:text-red-700 text-sm"
                >
                  {t('nav.clearAll')}
                </button>
              </div>
            </div>
            
            <div className="max-h-64 overflow-y-auto">
              {conversations.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  {t('chat.noConversations')}
                </div>
              ) : (
                conversations.map((conv) => (
                  <div key={conv.id} className="p-3 hover:bg-gray-50 border-b border-gray-50 last:border-b-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {conv.title}
                        </h4>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(conv.updated_at).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                      <button
                        onClick={() => deleteConversation(conv.id)}
                        className="ml-2 p-1 text-gray-400 hover:text-red-600 transition-colors"
                        title="Supprimer"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ==================== MENU UTILISATEUR ====================
const UserMenuButton = () => {
  const { user, logout } = useAuthStore()
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [showUserInfoModal, setShowUserInfoModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)
  const [showAccountModal, setShowAccountModal] = useState(false)

  const userName = user?.name || user?.email || 'Utilisateur'
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
  
  // Déterminer le forfait et ses couleurs
  const currentPlan = user?.plan || 'essential'
  const planConfig = {
    essential: { name: t('plan.essential'), bgColor: 'bg-green-50', textColor: 'text-green-600', borderColor: 'border-green-200' },
    pro: { name: t('plan.pro'), bgColor: 'bg-blue-50', textColor: 'text-blue-600', borderColor: 'border-blue-200' },
    max: { name: t('plan.max'), bgColor: 'bg-purple-50', textColor: 'text-purple-600', borderColor: 'border-purple-200' }
  }
  const plan = planConfig[currentPlan as keyof typeof planConfig] || planConfig.essential

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

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors"
        >
          <span className="text-white text-xs font-medium" data-user-initials>{userInitials}</span>
        </button>

        {isOpen && (
          <>
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setIsOpen(false)}
            />
            
            <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900" data-user-name>{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
                <div className="mt-2">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${plan.bgColor} ${plan.textColor} border ${plan.borderColor}`}>
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

      {/* Modals */}
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
        isOpen={showContactModal}
        onClose={() => setShowContactModal(false)}
        title={t('contact.title')}
      >
        <ContactModal onClose={() => setShowContactModal(false)} />
      </Modal>
    </>
  )
}

// ==================== COMPOSANT PRINCIPAL ====================
export default function ChatInterface() {
  const { user, isAuthenticated, isLoading } = useAuthStore()
  const { t } = useTranslation()
  
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoadingChat, setIsLoadingChat] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll automatique
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Message de bienvenue
  useEffect(() => {
    if (isAuthenticated && messages.length === 0) {
      const welcomeMessage: Message = {
        id: '1',
        content: t('chat.welcome'),
        isUser: false,
        timestamp: new Date()
      }
      setMessages([welcomeMessage])
    }
  }, [isAuthenticated, messages.length, t])

  // Afficher un loader pendant le chargement
  if (isLoading) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">{t('chat.loading')}</p>
        </div>
      </div>
    )
  }

  // Rediriger si pas connecté
  if (!isAuthenticated) {
    window.location.href = '/'
    return null
  }

  // Générer réponse RAG
  const generateAIResponse = async (question: string): Promise<string> => {
    const apiUrl = 'https://expert-app-cngws.ondigitalocean.app/api/api/v1/expert/ask-public'
    
    try {
      console.log('🤖 Envoi question au RAG Intelia:', question)
      console.log('📡 URL API:', apiUrl)
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          text: `${question.trim()}\n\nRépondez de manière concise et directe.`,
          language: user?.language || 'fr',
          speed_mode: 'balanced',
          max_tokens: 150,
          temperature: 0.7,
          response_format: 'concise'
        })
      })

      console.log('📊 Statut réponse API:', response.status, response.statusText)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Erreur API détaillée:', errorText)
        throw new Error(`Erreur API: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('✅ Réponse RAG reçue:', data)
      
      if (data.response || data.answer || data.message) {
        return data.response || data.answer || data.message
      } else {
        console.warn('⚠️ Structure de réponse inattendue:', data)
        return 'Le système RAG a répondu mais dans un format inattendu.'
      }
      
    } catch (error: any) {
      console.error('❌ Erreur lors de l\'appel au RAG:', error)
      
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        return `Erreur de connexion au serveur RAG. 

🔧 **Vérifications suggérées :**
- Le serveur expert-app-cngws.ondigitalocean.app est-il accessible ?
- Y a-t-il des problèmes de CORS ?
- Le service est-il en cours d'exécution ?

**Erreur technique :** ${error.message}`
      }
      
      return `Erreur technique avec l'API : ${error.message}

**URL testée :** ${apiUrl}
**Type d'erreur :** ${error.name}

Consultez la console développeur (F12) pour plus de détails.`
    }
  }

  // Envoi message
  const handleSendMessage = async (text: string = inputMessage) => {
    if (!text.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text.trim(),
      isUser: true,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoadingChat(true)

    try {
      const response = await generateAIResponse(text.trim())
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response,
        isUser: false,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      console.error('❌ Error generating response:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: t('chat.errorMessage'),
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoadingChat(false)
    }
  }

  // Gestion feedback
  const handleFeedback = (messageId: string, feedback: 'positive' | 'negative') => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, feedback } : msg
    ))
    console.log(`📊 Feedback ${feedback} pour le message ${messageId}`)
  }

  const handleNewConversation = () => {
    setMessages([{
      id: '1',
      content: t('chat.welcome'),
      isUser: false,
      timestamp: new Date()
    }])
  }

  const getCurrentDate = () => {
    return new Date().toLocaleDateString(t('date.format'), { 
      day: 'numeric', 
      month: 'long', 
      year: 'numeric' 
    })
  }

  return (
    <>
      {/* Zoho SalesIQ Component */}
      <ZohoSalesIQ user={user} />

      <div className="h-screen bg-gray-50 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-100 px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Boutons à gauche */}
            <div className="flex items-center space-x-2">
              <HistoryMenu />
              <button
                onClick={handleNewConversation}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title={t('nav.newConversation')}
              >
                <PlusIcon className="w-5 h-5" />
              </button>
            </div>

            {/* Titre centré avec logo */}
            <div className="flex-1 flex justify-center items-center space-x-3">
              <InteliaLogo className="w-8 h-8" />
              <div className="text-center">
                <h1 className="text-lg font-medium text-gray-900">Intelia Expert</h1>
              </div>
            </div>
            
            {/* Avatar utilisateur à droite */}
            <div className="flex items-center">
              <UserMenuButton />
            </div>
          </div>
        </header>

        {/* Zone de messages */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto px-4 py-6">
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Date */}
              {messages.length > 0 && (
                <div className="text-center">
                  <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                    {getCurrentDate()}
                  </span>
                </div>
              )}

              {messages.map((message, index) => (
                <div key={message.id}>
                  <div className={`flex items-start space-x-3 ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                    {!message.isUser && (
                      <div className="relative">
                        <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                      </div>
                    )}
                    
                    <div className="max-w-xs lg:max-w-2xl">
                      <div className={`px-4 py-3 rounded-2xl ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
                        <p className="whitespace-pre-wrap leading-relaxed text-sm">
                          {message.content}
                        </p>
                      </div>
                      
                      {/* Boutons de feedback */}
                      {!message.isUser && index > 0 && (
                        <div className="flex items-center space-x-2 mt-2 ml-2">
                          <button
                            onClick={() => handleFeedback(message.id, 'positive')}
                            className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'positive' ? 'text-green-600 bg-green-50' : 'text-gray-400'}`}
                            title={t('chat.helpfulResponse')}
                          >
                            <ThumbUpIcon />
                          </button>
                          <button
                            onClick={() => handleFeedback(message.id, 'negative')}
                            className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'negative' ? 'text-red-600 bg-red-50' : 'text-gray-400'}`}
                            title={t('chat.notHelpfulResponse')}
                          >
                            <ThumbDownIcon />
                          </button>
                        </div>
                      )}
                    </div>

                    {message.isUser && (
                      <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                        <UserIcon className="w-5 h-5 text-white" />
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Indicateur de frappe */}
              {isLoadingChat && (
                <div className="flex items-start space-x-3">
                  <div className="relative">
                    <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                  </div>
                  <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Zone de saisie */}
          <div className="px-4 py-4 bg-white border-t border-gray-100">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                  title={t('chat.voiceRecording')}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                  </svg>
                </button>
                
                <div className="flex-1">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSendMessage()
                      }
                    }}
                    placeholder={t('chat.placeholder')}
                    className="w-full px-4 py-3 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm"
                    disabled={isLoadingChat}
                  />
                </div>
                
                <button
                  onClick={() => handleSendMessage()}
                  disabled={isLoadingChat || !inputMessage.trim()}
                  className="flex-shrink-0 p-2 text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors"
                >
                  <PaperAirplaneIcon />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}