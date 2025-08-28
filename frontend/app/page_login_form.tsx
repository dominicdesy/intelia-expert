'use client'

import React, { memo, useCallback } from 'react'
import Link from 'next/link'
import { AlertMessage, PasswordInput } from './page_components'

interface LoginFormProps {
  authLogic: any
  t: any
  localError: string
  localSuccess: string
  toggleMode: () => void
}

export const LoginForm = memo(function LoginForm({ 
  authLogic, 
  t, 
  localError, 
  localSuccess, 
  toggleMode 
}: LoginFormProps) {
  const {
    loginData,
    isLoading,
    passwordInputRef,
    handleLoginChange,
    handleLogin
  } = authLogic

  const [formError, setFormError] = React.useState('')
  const [formSuccess, setFormSuccess] = React.useState('')

  const onSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setFormSuccess('')

    try {
      await handleLogin(e)
      setFormSuccess(t.authSuccess)
    } catch (error: any) {
      setFormError(error.message)
    }
  }, [handleLogin, t.authSuccess])

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSubmit(e as any)
    }
  }, [onSubmit])

  const handleEmailChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleLoginChange('email', e.target.value)
  }, [handleLoginChange])

  const handlePasswordChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleLoginChange('password', e.target.value)
  }, [handleLoginChange])

  const handleRememberMeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('🛯 [Checkbox] Événement onChange déclenché!')
    console.log('🛯 [Checkbox] e.target.checked:', e.target.checked)
    console.log('🛯 [Checkbox] État actuel rememberMe:', loginData.rememberMe)
    
    handleLoginChange('rememberMe', e.target.checked)
  }, [handleLoginChange, loginData.rememberMe])

  return (
    <>
      {/* Messages d'erreur et succès pour login */}
      {(localError || formError) && (
        <AlertMessage 
          type="error" 
          title={t.loginError} 
          message={localError || formError} 
        />
      )}

      {(localSuccess || formSuccess) && (
        <AlertMessage 
          type="success" 
          title="" 
          message={localSuccess || formSuccess} 
        />
      )}

      {/* FORMULAIRE DE CONNEXION */}
      <form onSubmit={onSubmit} onKeyPress={handleKeyPress}>
        <div className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              {t.email}
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
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              {t.password}
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
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                checked={loginData.rememberMe}
                onChange={handleRememberMeChange}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                disabled={isLoading}
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                {t.rememberMe}
              </label>
            </div>

            <div className="text-sm">
              <Link 
                href="/auth/forgot-password" 
                className="font-medium text-blue-600 hover:text-blue-500 transition-colors"
              >
                {t.forgotPassword}
              </Link>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading || !loginData.email || !loginData.password}
              className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>{t.connecting}</span>
                </div>
              ) : (
                t.login
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Bouton pour ouvrir la modale d'inscription */}
      <div className="mt-6 text-center">
        <p className="text-sm text-gray-600">
          {t.newToIntelia}{' '}
          <button
            onClick={toggleMode}
            className="font-medium text-blue-600 hover:text-blue-500"
          >
            {t.createAccount}
          </button>
        </p>
      </div>
    </>
  )
})