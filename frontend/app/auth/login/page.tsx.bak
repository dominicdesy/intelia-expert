'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { useAuthStore } from '@/lib/stores/auth'
import { supabase } from '@/lib/supabase/client'
import { Eye, EyeOff, Mail, Lock, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore() // Données d'état
  const { login, isLoading } = useAuthStore() // Actions
  
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')

  // Redirection si déjà connecté
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/chat')
    }
  }, [isAuthenticated, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.email || !formData.password) {
      setError('Veuillez remplir tous les champs')
      return
    }

    try {
      await login(formData.email, formData.password)
      router.push('/chat')
    } catch (error: any) {
      setError(error.message || 'Erreur de connexion')
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    setError('')
  }

  // 🆕 NOUVEAU: Gestion de la connexion Google
  const handleGoogleLogin = async () => {
    try {
      setError('')
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`
        }
      })

      if (error) {
        setError(error.message)
      }
    } catch (error: any) {
      setError('Erreur lors de la connexion avec Google')
    }
  }

  // 🆕 NOUVEAU: Gestion de la connexion avec un lien magique
  const handleMagicLink = async () => {
    if (!formData.email) {
      setError('Veuillez entrer votre adresse email')
      return
    }

    try {
      setError('')
      const { error } = await supabase.auth.signInWithOtp({
        email: formData.email,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`
        }
      })

      if (error) {
        setError(error.message)
      } else {
        setError('') // Pas d'erreur
        // Afficher un message de succès
        alert(`Un lien de connexion a été envoyé à ${formData.email}`)
      }
    } catch (error: any) {
      setError('Erreur lors de l\'envoi du lien magique')
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Section gauche - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-600 via-blue-700 to-blue-800 relative overflow-hidden">
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="relative z-10 flex flex-col justify-center items-center px-12 text-white">
          <div className="max-w-md text-center">
            <div className="mb-8">
              <Image
                src="/images/intelia-logo-white.png"
                alt="Intelia"
                width={200}
                height={60}
                className="mx-auto mb-8"
                priority
              />
            </div>
            
            <div className="mb-8">
              <Image
                src="/images/chat-illustration.png"
                alt="Chat Illustration"
                width={300}
                height={250}
                className="mx-auto"
                priority
              />
            </div>
            
            <h1 className="text-3xl font-bold mb-4">
              Bienvenue sur Intelia Expert
            </h1>
            <p className="text-xl text-blue-100 leading-relaxed">
              Votre assistant IA spécialisé en santé et nutrition animale
            </p>
          </div>
        </div>
      </div>

      {/* Section droite - Formulaire */}
      <div className="w-full lg:w-1/2 flex items-center justify-center px-6 py-12 bg-gray-50">
        <div className="w-full max-w-md">
          {/* Header mobile */}
          <div className="lg:hidden text-center mb-8">
            <Image
              src="/images/intelia-logo.png"
              alt="Intelia"
              width={150}
              height={45}
              className="mx-auto mb-4"
              priority
            />
            <h2 className="text-2xl font-bold text-gray-900">Connexion</h2>
          </div>

          {/* Onglets */}
          <div className="hidden lg:flex mb-8 border-b border-gray-200">
            <button className="flex-1 py-3 text-center text-blue-600 border-b-2 border-blue-600 font-medium">
              Se connecter
            </button>
            <Link 
              href="/auth/signup" 
              className="flex-1 py-3 text-center text-gray-500 hover:text-gray-700 transition-colors"
            >
              S'inscrire
            </Link>
          </div>

          {/* Formulaire */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white"
                  placeholder="votre@email.com"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Mot de passe
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={handleInputChange}
                  className="block w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center space-x-2 text-red-600 bg-red-50 p-3 rounded-lg">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Connexion...</span>
                </div>
              ) : (
                'Se connecter'
              )}
            </button>
          </form>

          {/* 🆕 NOUVEAU: Actions sociales et lien magique */}
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-gray-50 text-gray-500">ou</span>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              <button 
                onClick={handleGoogleLogin}
                className="w-full flex justify-center items-center px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
              >
                Continuer avec Google
              </button>
              
              <button 
                onClick={handleMagicLink}
                disabled={!formData.email}
                className="w-full flex justify-center items-center px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Recevoir un lien de connexion
              </button>
            </div>
          </div>

          {/* Lien mot de passe oublié */}
          <div className="mt-6 text-center">
            <Link 
              href="/auth/forgot-password" 
              className="text-sm text-blue-600 hover:text-blue-500 transition-colors"
            >
              Mot de passe oublié ?
            </Link>
          </div>

          {/* Lien inscription mobile */}
          <div className="lg:hidden mt-8 text-center">
            <span className="text-sm text-gray-600">Pas encore de compte ? </span>
            <Link 
              href="/auth/signup" 
              className="text-sm text-blue-600 hover:text-blue-500 font-medium transition-colors"
            >
              S'inscrire
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}