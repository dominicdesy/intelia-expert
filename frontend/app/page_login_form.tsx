'use client'

import React, { memo, useCallback, useState, useEffect, useMemo, useRef } from 'react'
import Link from 'next/link'
import { AlertMessage, PasswordInput } from './page_components'
import { validateEmail, rememberMeUtils, debugLog } from './page_hooks'
import { useTranslation } from '@/lib/languages/i18n'
import type { LoginData } from './page_types'
import type { Language } from '@/types'

interface LoginFormProps {
  authLogic: any
  currentLanguage: Language
  localError: string
  localSuccess: string
  toggleMode: () => void
}

export const LoginForm = memo(function LoginForm({ 
  authLogic, 
  currentLanguage,
  localError, 
  localSuccess, 
  toggleMode 
}: LoginFormProps) {
  debugLog('form', 'LoginForm rendered')
  
  // ✅ UTILISE DIRECTEMENT useTranslation au lieu de recevoir t comme prop
  const { t } = useTranslation()
  
  const {
    isLoading,
    passwordInputRef,
    handleLogin
  } = authLogic

  const [loginData, setLoginData] = useState<LoginData>({
    email: '',
    password: '',
    rememberMe: false
  })

  const [formError, setFormError] = useState('')
  const [formSuccess, setFormSuccess] = useState('')
  
  // CORRECTION 1: Référence pour éviter le focus automatique pendant la saisie
  const isInitialLoadRef = useRef(true)
  const hasAutoFocusedRef = useRef(false)
  const userIsTypingRef = useRef(false)

  // CORRECTION 2: Gestionnaire avec débounce pour éviter les sauvegardes à chaque caractère
  const saveRememberMeDebounced = useCallback(
    debounce((email: string, rememberMe: boolean) => {
      if (rememberMe && email && validateEmail(email)) {
        rememberMeUtils.save(email, true)
        debugLog('storage', 'Email saved (debounced)', email)
      }
    }, 500),
    []
  )

  const handleLoginChange = useCallback((field: keyof LoginData, value: string | boolean) => {
    // Marquer que l'utilisateur tape (pour éviter le focus automatique)
    if (field === 'email') {
      userIsTypingRef.current = true
      setTimeout(() => {
        userIsTypingRef.current = false
      }, 1000)
    }

    if (field === 'rememberMe') {
      debugLog('form', `RememberMe changed to: ${value}`)
    }
    
    setLoginData(prev => {
      const newData = { ...prev, [field]: value }
      
      // Gestion rememberMe
      if (field === 'rememberMe') {
        const isRememberChecked = value as boolean
        
        if (isRememberChecked && newData.email?.trim()) {
          rememberMeUtils.save(newData.email.trim(), true)
          debugLog('storage', 'Email saved immediately', newData.email.trim())
        } else if (!isRememberChecked) {
          rememberMeUtils.save('', false)
          debugLog('storage', 'RememberMe disabled - localStorage cleared')
        }
      }
      
      // CORRECTION 3: Sauvegarde différée pour l'email pour éviter le spam
      if (field === 'email' && newData.rememberMe) {
        const emailValue = (value as string).trim()
        // Utiliser le débounce pour éviter les sauvegardes à chaque caractère
        saveRememberMeDebounced(emailValue, true)
      }
      
      return newData
    })
  }, [saveRememberMeDebounced])

  // CORRECTION 4: Restauration RememberMe seulement au premier chargement
  useEffect(() => {
    if (!isInitialLoadRef.current) return

    debugLog('form', 'Initializing RememberMe restoration (first load only)')
    
    const { rememberMe, lastEmail } = rememberMeUtils.load()
    
    if (rememberMe && lastEmail) {
      setLoginData(prev => ({
        ...prev,
        email: lastEmail,
        rememberMe: true
      }))
      debugLog('form', 'RememberMe data restored', lastEmail)
    }

    isInitialLoadRef.current = false
  }, [])

  // CORRECTION 5: Focus automatique SEULEMENT si email pré-rempli ET utilisateur ne tape pas
  useEffect(() => {
    if (userIsTypingRef.current || hasAutoFocusedRef.current || !passwordInputRef.current) {
      return
    }

    if (loginData.rememberMe && loginData.email && !loginData.password) {
      const timer = setTimeout(() => {
        if (!userIsTypingRef.current && passwordInputRef.current) {
          passwordInputRef.current.focus()
          hasAutoFocusedRef.current = true
          debugLog('form', 'Auto-focus on password field (RememberMe)')
        }
      }, 800)
      
      return () => clearTimeout(timer)
    }
  }, [loginData.rememberMe, loginData.email, loginData.password, passwordInputRef])

  // Reset du flag de focus quand l'utilisateur change d'email
  useEffect(() => {
    if (loginData.email !== '') {
      hasAutoFocusedRef.current = false
    }
  }, [loginData.email])

  const onSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setFormSuccess('')

    try {
      debugLog('auth', 'Form submission', { email: loginData.email, rememberMe: loginData.rememberMe })
      await handleLogin(e, loginData)
      setFormSuccess(t('auth.success'))
    } catch (error: any) {
      debugLog('error', 'Login error', error.message)
      setFormError(error.message)
    }
  }, [handleLogin, loginData, t])

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSubmit(e as any)
    }
  }, [onSubmit])

  // Gestionnaires memoizés
  const handleEmailChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleLoginChange('email', e.target.value)
  }, [handleLoginChange])

  const handlePasswordChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleLoginChange('password', e.target.value)
  }, [handleLoginChange])

  const handleRememberMeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    debugLog('form', 'RememberMe checkbox event triggered', e.target.checked)
    handleLoginChange('rememberMe', e.target.checked)
  }, [handleLoginChange])

  // Memoization des messages pour éviter les re-renders
  const errorMessage = useMemo(() => localError || formError, [localError, formError])
  const successMessage = useMemo(() => localSuccess || formSuccess, [localSuccess, formSuccess])

  // État des boutons memoizé
  const isSubmitDisabled = useMemo(() => 
    isLoading || !loginData.email?.trim() || !loginData.password,
    [isLoading, loginData.email, loginData.password]
  )

  // Debug léger
  debugLog('form', 'Current state', { 
    hasEmail: !!loginData.email, 
    rememberMe: loginData.rememberMe,
    isLoading,
    userIsTyping: userIsTypingRef.current
  })

  return (
    <>
      {/* Messages d'erreur et succès */}
      {errorMessage && (
        <AlertMessage 
          type="error" 
          title={t('error.generic')} 
          message={errorMessage} 
        />
      )}

      {successMessage && (
        <AlertMessage 
          type="success" 
          title="" 
          message={successMessage} 
        />
      )}

      {/* FORMULAIRE DE CONNEXION */}
      <form onSubmit={onSubmit} onKeyPress={handleKeyPress}>
        <div className="space-y-6">
          {/* Champ Email */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              {t('login.emailLabel')}
            </label>
            <div className="mt-1">
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={loginData.email}
                onChange={handleEmailChange}
                className="block w-full rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                placeholder={t('login.emailPlaceholder')}
              />
            </div>
          </div>

          {/* Champ Mot de passe */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              {t('login.passwordLabel')}
            </label>
            <div className="mt-1">
              <PasswordInput
                id="password"
                name="password"
                ref={passwordInputRef}
                value={loginData.password}
                onChange={handlePasswordChange}
                autoComplete="current-password"
                required
                placeholder={t('login.passwordPlaceholder')}
              />
            </div>
          </div>

          {/* Section Remember Me et Mot de passe oublié */}
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                checked={loginData.rememberMe}
                onChange={handleRememberMeChange}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                disabled={isLoading}
              />
              <label 
                htmlFor="remember-me" 
                className="ml-2 block text-sm text-gray-900 cursor-pointer select-none"
              >
                {t('login.rememberMe')}
              </label>
            </div>

            <div className="text-sm">
              <Link 
                href="/auth/forgot-password"
                className="font-medium text-blue-600 hover:text-blue-500 transition-colors"
              >
                {t('auth.forgotPassword')}
              </Link>
            </div>
          </div>

          {/* Bouton de connexion */}
          <div>
            <button
              type="submit"
              disabled={isSubmitDisabled}
              className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>{t('auth.connecting')}</span>
                </div>
              ) : (
                t('auth.login')
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Séparateur */}
      <div className="mt-6">
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">{t('common.or')}</span>
          </div>
        </div>
      </div>

      {/* Bouton d'inscription */}
      <div className="mt-6 text-center">
        <p className="text-sm text-gray-600">
          {t('auth.newToIntelia')}{' '}
          <button
            type="button"
            onClick={toggleMode}
            className="font-medium text-blue-600 hover:text-blue-500 transition-colors"
          >
            {t('auth.createAccount')}
          </button>
        </p>
      </div>

      {/* Debug info simplifiée */}
      {process.env.NODE_ENV === 'development' && (
        <div className="mt-4 p-2 bg-gray-100 rounded text-xs opacity-50 hover:opacity-100 transition-opacity">
          <strong>Debug:</strong> Email: {loginData.email ? 'Présent' : 'Vide'} | 
          RememberMe: {loginData.rememberMe ? 'Oui' : 'Non'} | 
          Storage: {localStorage.getItem('intelia-remember-me-persist') ? 'OK' : 'Vide'} |
          UserTyping: {userIsTypingRef.current ? 'Oui' : 'Non'}
        </div>
      )}
    </>
  )
})

// Fonction utilitaire debounce pour éviter les appels trop fréquents
function debounce<T extends (...args: any[]) => any>(func: T, wait: number): T {
  let timeout: NodeJS.Timeout | null = null
  return ((...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }) as T
}