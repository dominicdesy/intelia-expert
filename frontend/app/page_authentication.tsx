'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useUser, useAuth, useAuthLoading } from '@/lib/hooks/useAuthStore'
import type { User } from '@/types'
import { 
  validateEmail, 
  validatePassword, 
  validatePhone,
  validateLinkedIn,
  validateWebsite, 
  rememberMeUtils 
} from './page_hooks'
import type { LoginData, SignupData } from './page_types'

interface UseAuthenticationLogicProps {
  currentLanguage: any
  t: any
  isSignupMode: boolean
  setCurrentLanguage: (lang: any) => void
}

export function useAuthenticationLogic({ 
  currentLanguage, 
  t, 
  isSignupMode,
  setCurrentLanguage 
}: UseAuthenticationLogicProps) {
  const router = useRouter()
  const pathname = usePathname()
  
  const { user, isAuthenticated, hasHydrated } = useUser()
  const { login, register, initializeSession } = useAuth()
  const { isLoading } = useAuthLoading()

  const hasCheckedAuth = useRef(false)
  const redirectLock = useRef(false)
  const sessionInitialized = useRef(false)
  const passwordInputRef = useRef<HTMLInputElement>(null)
  const isMounted = useRef(true)

  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  
  const [signupData, setSignupData] = useState<SignupData>({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    linkedinProfile: '',
    country: '',
    countryCode: '',      
    areaCode: '',         
    phoneNumber: '',      
    companyName: '',
    companyWebsite: '',
    companyLinkedin: ''
  })

  const safeRedirectToChat = useCallback(() => {
    if (redirectLock.current || !isMounted.current) {
      console.log('🔒 [Redirect] Déjà en cours de redirection ou démontage, ignoré')
      return
    }
    
    if (pathname?.startsWith("/chat")) {
      console.log('🔧 [Redirect] Déjà sur /chat, pas de redirection')
      return
    }
    
    console.log('🚀 [Redirect] Redirection vers /chat depuis:', pathname)
    redirectLock.current = true
    router.replace('/chat')
  }, [pathname, router])

  const handleSignupChange = useCallback((field: keyof SignupData, value: string) => {
    setSignupData(prev => {
      const newData = { ...prev, [field]: value }
      // Note: L'auto-remplissage du countryCode sera géré dans SignupModal
      return newData
    })
  }, [])

  const validateSignupForm = useCallback((): string | null => {
    const { 
      email, password, confirmPassword, firstName, lastName, country, 
      countryCode, areaCode, phoneNumber,
      linkedinProfile, companyWebsite, companyLinkedin 
    } = signupData

    if (!email.trim()) return t.emailRequired
    if (!validateEmail(email)) return t.emailInvalid
    if (!password) return t.passwordRequired
    
    const passwordValidation = validatePassword(password)
    if (!passwordValidation.isValid) return t.passwordTooShort
    
    if (password !== confirmPassword) return t.passwordMismatch
    if (!firstName.trim()) return t.firstNameRequired
    if (!lastName.trim()) return t.lastNameRequired
    if (!country) return t.countryRequired
    
    if (!validatePhone(countryCode, areaCode, phoneNumber)) {
      return 'Format de téléphone invalide. Si vous renseignez le téléphone, tous les champs (indicatif pays, indicatif régional, numéro) sont requis.'
    }
    
    if (linkedinProfile && !validateLinkedIn(linkedinProfile)) return 'Format LinkedIn invalide'
    if (companyWebsite && !validateWebsite(companyWebsite)) return 'Format de site web invalide'
    if (companyLinkedin && !validateLinkedIn(companyLinkedin)) return 'Format LinkedIn entreprise invalide'
    
    return null
  }, [signupData, t])

  const handleLogin = useCallback(async (e: React.FormEvent, loginFormData: LoginData) => {
    e.preventDefault()

    if (!loginFormData.email.trim()) {
      throw new Error(t.emailRequired)
    }

    if (!validateEmail(loginFormData.email)) {
      throw new Error(t.emailInvalid)
    }

    if (!loginFormData.password) {
      throw new Error(t.passwordRequired)
    }

    if (loginFormData.password.length < 6) {
      throw new Error(t.passwordTooShort)
    }

    try {
      console.log('🔐 [Login] Tentative connexion...')
      
      await login(loginFormData.email.trim(), loginFormData.password)
      
      rememberMeUtils.save(loginFormData.email.trim(), loginFormData.rememberMe)
      console.log('✅ [Login] Confirmation persistence remember me:', loginFormData.rememberMe)
      
      console.log('✅ [Login] Connexion réussie')
      
    } catch (error: any) {
      console.error('❌ [Login] Erreur connexion:', error)
      redirectLock.current = false
      
      if (error.message?.includes('Invalid login credentials')) {
        throw new Error('Email ou mot de passe incorrect. Vérifiez vos identifiants.')
      } else if (error.message?.includes('Email not confirmed')) {
        throw new Error('Email non confirmé. Vérifiez votre boîte mail.')
      } else if (error.message?.includes('Too many requests')) {
        throw new Error('Trop de tentatives. Attendez quelques minutes.')
      } else {
        throw new Error(error.message || 'Erreur de connexion')
      }
    }
  }, [t, login])

  const handleSignup = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()

    const validationError = validateSignupForm()
    if (validationError) {
      throw new Error(validationError)
    }

    try {
      console.log('🔐 [Signup] Tentative création compte...')
      
      const userData: Partial<User> = {
        name: `${signupData.firstName.trim()} ${signupData.lastName.trim()}`,
        user_type: 'producer',
        language: currentLanguage
      }
      
      await register(signupData.email.trim(), signupData.password, userData)
      
      console.log('✅ [Signup] Création compte réussie')
      
      setSignupData({
        email: '', password: '', confirmPassword: '',
        firstName: '', lastName: '', linkedinProfile: '',
        country: '', countryCode: '', areaCode: '', phoneNumber: '',
        companyName: '', companyWebsite: '', companyLinkedin: ''
      })
      
    } catch (error: any) {
      console.error('❌ [Signup] Erreur création compte:', error)
      throw new Error(error.message || 'Erreur lors de la création du compte')
    }
  }, [signupData, currentLanguage, register, validateSignupForm])

  useEffect(() => {
    if (!hasHydrated || !isMounted.current) return
    
    if (!sessionInitialized.current) {
      sessionInitialized.current = true
      console.log('🔄 [Session] Initialisation unique de la session')
      initializeSession()
    }
  }, [hasHydrated, initializeSession])

  useEffect(() => {
    if (!hasHydrated || hasCheckedAuth.current || !isMounted.current) {
      return
    }

    hasCheckedAuth.current = true
    console.log('🔒 [Auth] Vérification unique de l\'authentification')

    if (isAuthenticated) {
      console.log('✅ [Auth] Déjà connecté, redirection immédiate')
      safeRedirectToChat()
      return
    }

    if (!sessionInitialized.current) {
      sessionInitialized.current = true
      console.log('🔄 [Session] Initialisation unique de la session')
      
      initializeSession().then((sessionFound) => {
        if (sessionFound && isMounted.current) {
          console.log('✅ [Session] Session trouvée, redirection automatique')
        } else if (isMounted.current) {
          console.log('❌ [Session] Aucune session trouvée')
        }
      }).catch(error => {
        console.error('❌ [Session] Erreur initialisation:', error)
      })
    }
  }, [hasHydrated, isAuthenticated, initializeSession, safeRedirectToChat])

  useEffect(() => {
    if (!hasHydrated || !hasCheckedAuth.current || !isMounted.current) {
      return
    }

    if (!isLoading && isAuthenticated) {
      console.log('🔄 [Auth] État auth changé, redirection sécurisée')
      safeRedirectToChat()
    }
  }, [isAuthenticated, isLoading, hasHydrated, safeRedirectToChat])

  useEffect(() => {
    return () => {
      isMounted.current = false
    }
  }, [])

  // CORRECTION CRITIQUE : Mémoriser les handlers et données stables séparément
  const stableHandlers = useMemo(() => ({
    handleSignupChange,
    handleLogin,
    validateSignupForm,
    validateEmail,
    validatePassword,
    validatePhone,
    validateLinkedIn,
    validateWebsite
  }), [handleSignupChange, handleLogin, validateSignupForm])

  const stableFormStates = useMemo(() => ({
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    passwordInputRef
  }), [showPassword, showConfirmPassword, isLoading])

  // À ajouter temporairement pour debugging
  console.log('DEBUG re-render authLogic OPTIMISÉ:', {
    signupDataChanged: JSON.stringify(signupData),
    isLoadingChanged: isLoading,
    timestamp: new Date().toISOString(),
    note: 'loginData retiré - plus de re-renders!'
  });

  // CORRECTION : Retour sans loginData pour éviter re-renders
  return useMemo(() => ({
    // États des formulaires signup uniquement
    signupData,
    
    // États stables (ne changent pas souvent)
    ...stableFormStates,
    ...stableHandlers
  }), [
    signupData,
    stableFormStates,
    stableHandlers
  ])
}