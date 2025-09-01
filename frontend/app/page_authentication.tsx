'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
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
  const { user, isAuthenticated } = useUser()
  const { login, register } = useAuth()
  const { isLoading } = useAuthLoading()

  // États simples comme ContactModal
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

  // Fonction simple de redirection
  const redirectToChat = useCallback(() => {
    setTimeout(() => {
      router.push('/chat')
    }, 100)
  }, [router])

  // Gestion simple du signup
  const handleSignupChange = useCallback((field: keyof SignupData, value: string) => {
    setSignupData(prev => ({ ...prev, [field]: value }))
  }, [])

  // Validation simple du formulaire signup
  const validateSignupForm = useCallback((): string | null => {
    const { 
      email, password, confirmPassword, firstName, lastName, country, 
      countryCode, areaCode, phoneNumber,
      linkedinProfile, companyWebsite, companyLinkedin 
    } = signupData

    if (!email.trim()) return 'Email requis'
    if (!validateEmail(email)) return 'Email invalide'
    if (!password) return 'Mot de passe requis'
    
    const passwordValidation = validatePassword(password)
    if (!passwordValidation.isValid) return 'Mot de passe trop faible'
    
    if (password !== confirmPassword) return 'Mots de passe différents'
    if (!firstName.trim()) return 'Prénom requis'
    if (!lastName.trim()) return 'Nom requis'
    if (!country) return 'Pays requis'
    
    if (!validatePhone(countryCode, areaCode, phoneNumber)) {
      return 'Format de téléphone invalide'
    }
    
    if (linkedinProfile && !validateLinkedIn(linkedinProfile)) return 'Format LinkedIn invalide'
    if (companyWebsite && !validateWebsite(companyWebsite)) return 'Format de site web invalide'
    if (companyLinkedin && !validateLinkedIn(companyLinkedin)) return 'Format LinkedIn entreprise invalide'
    
    return null
  }, [signupData])

  // Fonction de login simple
  const handleLogin = useCallback(async (e: React.FormEvent, loginFormData: LoginData) => {
    e.preventDefault()

    if (!loginFormData.email.trim()) {
      throw new Error('Email requis')
    }

    if (!validateEmail(loginFormData.email)) {
      throw new Error('Email invalide')
    }

    if (!loginFormData.password) {
      throw new Error('Mot de passe requis')
    }

    try {
      await login(loginFormData.email.trim(), loginFormData.password)
      rememberMeUtils.save(loginFormData.email.trim(), loginFormData.rememberMe)
      redirectToChat()
      
    } catch (error: any) {
      if (error.message?.includes('Invalid login credentials')) {
        throw new Error('Email ou mot de passe incorrect')
      } else if (error.message?.includes('Email not confirmed')) {
        throw new Error('Email non confirmé. Vérifiez votre boîte mail.')
      } else if (error.message?.includes('Too many requests')) {
        throw new Error('Trop de tentatives. Attendez quelques minutes.')
      } else {
        throw new Error(error.message || 'Erreur de connexion')
      }
    }
  }, [login, redirectToChat])

  // Fonction de signup simple
  const handleSignup = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()

    const validationError = validateSignupForm()
    if (validationError) {
      throw new Error(validationError)
    }

    try {
      const userData: Partial<User> = {
        name: `${signupData.firstName.trim()} ${signupData.lastName.trim()}`,
        user_type: 'producer',
        language: currentLanguage
      }
      
      await register(signupData.email.trim(), signupData.password, userData)
      
      // Reset du formulaire
      setSignupData({
        email: '', password: '', confirmPassword: '',
        firstName: '', lastName: '', linkedinProfile: '',
        country: '', countryCode: '', areaCode: '', phoneNumber: '',
        companyName: '', companyWebsite: '', companyLinkedin: ''
      })
      
    } catch (error: any) {
      throw new Error(error.message || 'Erreur lors de la création du compte')
    }
  }, [signupData, currentLanguage, register, validateSignupForm])

  // Redirection automatique si connecté
  useEffect(() => {
    if (isAuthenticated && user) {
      redirectToChat()
    }
  }, [isAuthenticated, user, redirectToChat])

  // Retour simple comme ContactModal
  return useMemo(() => ({
    // États du formulaire
    signupData,
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    
    // Fonctions
    handleSignupChange,
    handleLogin,
    handleSignup,
    validateSignupForm,
    
    // Fonctions de validation
    validateEmail,
    validatePassword,
    validatePhone,
    validateLinkedIn,
    validateWebsite
  }), [
    signupData,
    showPassword,
    showConfirmPassword,
    isLoading,
    handleSignupChange,
    handleLogin,
    handleSignup,
    validateSignupForm
  ])
}