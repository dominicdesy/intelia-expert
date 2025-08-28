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
  
  const [loginData, setLoginData] = useState<LoginData>({
    email: '',
    password: '',
    rememberMe: false
  })

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

  const handleLoginChange = useCallback((field: keyof LoginData, value: string | boolean) => {
    setLoginData(prev => {
      const newData = { ...prev, [field]: value }
      
      if (field === 'rememberMe') {
        const isRememberChecked = value as boolean
        console.log('🛯 [HandleChange] RememberMe changé:', isRememberChecked)
        
        if (isRememberChecked && prev.email?.trim()) {
          rememberMeUtils.save(prev.email.trim(), true)
          console.log('✅ [HandleChange] Email sauvegardé immédiatement:', prev.email.trim())
        } else if (!isRememberChecked) {
          rememberMeUtils.save('', false)
          console.log('🗑️ [HandleChange] Remember Me désactivé')
        }
      }
      
      if (field === 'email' && prev.rememberMe) {
        const emailValue = (value as string).trim()
        if (emailValue && validateEmail(emailValue)) {
          rememberMeUtils.save(emailValue, true)
          console.log('✅ [HandleChange] Nouvel email sauvegardé:', emailValue)
        }
      }
      
      return newData
    })
  }, [])

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

  const handleLogin = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()

    if (!loginData.email.trim()) {
      throw new Error(t.emailRequired)
    }

    if (!validateEmail(loginData.email)) {
      throw new Error(t.emailInvalid)
    }

    if (!loginData.password) {
      throw new Error(t.passwordRequired)
    }

    if (loginData.password.length < 6) {
      throw new Error(t.passwordTooShort)
    }

    try {
      console.log('🔐 [Login] Tentative connexion...')
      
      await login(loginData.email.trim(), loginData.password)
      
      rememberMeUtils.save(loginData.email.trim(), loginData.rememberMe)
      console.log('✅ [Login] Confirmation persistence remember me:', loginData.rememberMe)
      
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
  }, [loginData, t, login])

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
    const { rememberMe, lastEmail } = rememberMeUtils.load()
    
    if (rememberMe && lastEmail && loginData.email && !loginData.password && passwordInputRef.current) {
      const timer = setTimeout(() => {
        passwordInputRef.current?.focus()
      }, 500)
      
      return () => clearTimeout(timer)
    }
  }, [loginData.email, loginData.password])

  useEffect(() => {
    if (!isSignupMode) {
      const { rememberMe, lastEmail } = rememberMeUtils.load()
      
      if (rememberMe && lastEmail) {
        setLoginData(prev => ({
          ...prev,
          email: lastEmail,
          rememberMe
        }))
      }
    }
  }, [isSignupMode])

  useEffect(() => {
    return () => {
      isMounted.current = false
    }
  }, [])

  // CORRECTION CRITIQUE : Mémoriser les handlers et données stables séparément
  const stableHandlers = useMemo(() => ({
    handleLoginChange,
    handleSignupChange,
    handleLogin,
    handleSignup,
    validateSignupForm,
    validateEmail,
    validatePassword,
    validatePhone,
    validateLinkedIn,
    validateWebsite
  }), [handleLoginChange, handleSignupChange, handleLogin, handleSignup, validateSignupForm])

  const stableFormStates = useMemo(() => ({
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    passwordInputRef
  }), [showPassword, showConfirmPassword, isLoading])

  // CORRECTION : Retour avec loginData et signupData séparés pour éviter re-renders
  return useMemo(() => ({
    // États des formulaires (changent souvent, mais isolés)
    loginData,
    signupData,
    
    // États stables (ne changent pas souvent)
    ...stableFormStates,
    ...stableHandlers
  }), [
    loginData,
    signupData,
    stableFormStates,
    stableHandlers
  ])
}