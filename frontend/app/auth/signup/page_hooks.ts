// page_hooks.ts - Hooks et utilitaires pour la page d'authentification (nettoyé)
'use client'

import { useMemo } from 'react'
import type { Language } from '@/types'

// Traductions
export const translations = {
  fr: {
    title: 'Intelia Expert',
    email: 'Email',
    password: 'Mot de passe',
    confirmPassword: 'Confirmer le mot de passe',
    login: 'Se connecter',
    signup: 'Créer un compte',
    rememberMe: 'Se souvenir de mon email',
    forgotPassword: 'Mot de passe oublié ?',
    newToIntelia: 'Nouveau sur Intelia ?',
    connecting: 'Connexion en cours...',
    creating: 'Création en cours...',
    loginError: 'Erreur de connexion',
    signupError: 'Erreur de création',
    emailRequired: 'L\'adresse email est requise',
    emailInvalid: 'Veuillez entrer une adresse email valide',
    passwordRequired: 'Le mot de passe est requis',
    passwordTooShort: 'Le mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule, un chiffre et un caractère spécial',
    passwordMismatch: 'Les mots de passe ne correspondent pas',
    firstNameRequired: 'Le prénom est requis',
    lastNameRequired: 'Le nom de famille est requis',
    countryRequired: 'Le pays est requis',
    phoneInvalid: 'Format de téléphone invalide',
    terms: 'conditions d\'utilisation',
    privacy: 'politique de confidentialité',
    gdprNotice: 'En vous connectant, vous acceptez nos',
    needHelp: 'Besoin d\'aide ?',
    contactSupport: 'Contactez le support',
    createAccount: 'Créer un compte',
    backToLogin: 'Retour à la connexion',
    confirmationSent: 'Email de confirmation envoyé ! Vérifiez votre boîte mail.',
    accountCreated: 'Compte créé avec succès ! Vérifiez vos emails pour confirmer votre compte.',
    personalInfo: 'Informations personnelles',
    firstName: 'Prénom',
    lastName: 'Nom de famille',
    linkedinProfile: 'Profil LinkedIn personnel',
    contact: 'Contact',
    country: 'Pays',
    countryCode: 'Indicatif pays',
    areaCode: 'Indicatif régional',
    phoneNumber: 'Numéro de téléphone',
    company: 'Entreprise',
    companyName: 'Nom de l\'entreprise',
    companyWebsite: 'Site web de l\'entreprise',
    companyLinkedin: 'Page LinkedIn de l\'entreprise',
    optional: '(optionnel)',
    required: '*',
    close: 'Fermer',
    alreadyHaveAccount: 'Déjà un compte ?',
    authSuccess: 'Connexion réussie !',
    authError: 'Erreur de connexion, veuillez réessayer.',
    authIncomplete: 'Connexion incomplète, veuillez réessayer.',
    sessionCleared: 'Session précédente effacée',
    forceLogout: 'Déconnexion automatique',
    loadingCountries: 'Chargement des pays...',
    limitedCountryList: 'Liste de pays limitée (connexion API limitée)',
    selectCountry: 'Sélectionner un pays...'
  },
  en: {
    title: 'Intelia Expert',
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirm password',
    login: 'Sign in',
    signup: 'Create account',
    rememberMe: 'Remember my email',
    forgotPassword: 'Forgot password?',
    newToIntelia: 'New to Intelia?',
    connecting: 'Connecting...',
    creating: 'Creating...',
    loginError: 'Login error',
    signupError: 'Signup error',
    emailRequired: 'Email address is required',
    emailInvalid: 'Please enter a valid email address',
    passwordRequired: 'Password is required',
    passwordTooShort: 'Password must contain at least 8 characters, one uppercase, one lowercase, one number and one special character',
    passwordMismatch: 'Passwords do not match',
    firstNameRequired: 'First name is required',
    lastNameRequired: 'Last name is required',
    countryRequired: 'Country is required',
    phoneInvalid: 'Invalid phone format',
    terms: 'terms of service',
    privacy: 'privacy policy',
    gdprNotice: 'By signing in, you agree to our',
    needHelp: 'Need help?',
    contactSupport: 'Contact support',
    createAccount: 'Create account',
    backToLogin: 'Back to login',
    confirmationSent: 'Confirmation email sent! Check your mailbox.',
    accountCreated: 'Account created successfully! Check your emails to confirm your account.',
    personalInfo: 'Personal information',
    firstName: 'First name',
    lastName: 'Last name',
    linkedinProfile: 'Personal LinkedIn profile',
    contact: 'Contact',
    country: 'Country',
    countryCode: 'Country code',
    areaCode: 'Area code',
    phoneNumber: 'Phone number',
    company: 'Company',
    companyName: 'Company name',
    companyWebsite: 'Company website',
    companyLinkedin: 'Company LinkedIn page',
    optional: '(optional)',
    required: '*',
    close: 'Close',
    alreadyHaveAccount: 'Already have an account?',
    authSuccess: 'Login successful!',
    authError: 'Login error, please try again.',
    authIncomplete: 'Incomplete login, please try again.',
    sessionCleared: 'Previous session cleared',
    forceLogout: 'Automatic logout',
    loadingCountries: 'Loading countries...',
    limitedCountryList: 'Limited country list (limited internet connection)',
    selectCountry: 'Select a country...'
  }
}

// Fonctions de validation
export const validateEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

// Validation mot de passe
export const validatePassword = (password: string): { isValid: boolean; errors: string[] } => {
  const errors: string[] = []
  
  if (password.length < 8) {
    errors.push('Au moins 8 caractères')
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('Une majuscule')
  }
  if (!/[a-z]/.test(password)) {
    errors.push('Une minuscule')
  }
  if (!/[0-9]/.test(password)) {
    errors.push('Un chiffre')
  }
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('Un caractère spécial')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

// Validation téléphone
export const validatePhone = (countryCode: string, areaCode: string, phoneNumber: string): boolean => {
  // Si tous les champs sont vides, c'est valide (optionnel)
  if (!countryCode.trim() && !areaCode.trim() && !phoneNumber.trim()) {
    return true
  }
  
  // Si au moins un champ est rempli, tous doivent être remplis et valides
  if (countryCode.trim() || areaCode.trim() || phoneNumber.trim()) {
    // Vérifier que tous les champs sont remplis
    if (!countryCode.trim() || !areaCode.trim() || !phoneNumber.trim()) {
      return false
    }
    
    // Vérifier le format de chaque champ
    if (!/^\+[1-9]\d{0,3}$/.test(countryCode.trim())) {
      return false
    }
    
    if (!/^\d{3}$/.test(areaCode.trim())) {
      return false
    }
    
    if (!/^\d{7}$/.test(phoneNumber.trim())) {
      return false
    }
  }
  
  return true
}

// Validation LinkedIn
export const validateLinkedIn = (url: string): boolean => {
  if (!url.trim()) return true
  return /^(https?:\/\/)?(www\.)?linkedin\.com\/(in|company)\/[\w\-]+\/?$/.test(url)
}

// Validation site web
export const validateWebsite = (url: string): boolean => {
  if (!url.trim()) return true
  return /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/.test(url)
}

// Utilitaires Remember Me
export const rememberMeUtils = {
  save: (email: string, remember: boolean) => {
    try {
      if (remember && email) {
        localStorage.setItem('intelia_remember_email', email)
        localStorage.setItem('intelia_remember_flag', 'true')
        console.log('📄 [Init] Remember me sauvegardé:', { email, remember })
      } else {
        localStorage.removeItem('intelia_remember_email')
        localStorage.removeItem('intelia_remember_flag')
        console.log('📄 [Init] Remember me effacé')
      }
    } catch (error) {
      console.warn('⚠️ [Init] Erreur sauvegarde remember me:', error)
    }
  },

  load: () => {
    try {
      const savedEmail = localStorage.getItem('intelia_remember_email') || ''
      const rememberFlag = localStorage.getItem('intelia_remember_flag') === 'true'
      const hasRememberedEmail = !!(savedEmail && rememberFlag)
      
      const result = {
        rememberMe: rememberFlag,
        lastEmail: savedEmail,
        hasRememberedEmail
      }
      
      console.log('📄 [Init] Chargement remember me:', result)
      return result
    } catch (error) {
      console.warn('⚠️ [Init] Erreur chargement remember me:', error)
      return { rememberMe: false, lastEmail: '', hasRememberedEmail: false }
    }
  }
}