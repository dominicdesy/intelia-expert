'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useAuthStore } from '@/lib/stores/auth' // ← Retour au store Supabase original
import type { User } from '@/types'

// ==================== VALIDATION MOT DE PASSE ====================
const validatePassword = (password: string): string[] => {
  const errors: string[] = []
  
  if (password.length < 8) {
    errors.push('Le mot de passe doit contenir au moins 8 caractères')
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('Le mot de passe doit contenir au moins une majuscule')
  }
  if (!/[a-z]/.test(password)) {
    errors.push('Le mot de passe doit contenir au moins une minuscule')
  }
  if (!/\d/.test(password)) {
    errors.push('Le mot de passe doit contenir au moins un chiffre')
  }
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('Le mot de passe doit contenir au moins un caractère spécial')
  }
  
  return errors
}

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-16 h-16" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== ICÔNES ====================
const EyeIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
  </svg>
)

const EyeSlashIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.34 6.34m6.822 10.565l-3.536-3.536" />
  </svg>
)

// ==================== COMPOSANT CHAMP MOT DE PASSE ====================
interface PasswordFieldProps {
  value: string
  onChange: (value: string) => void
  placeholder: string
  label: string
  disabled?: boolean
  showStrength?: boolean
  showRequirements?: boolean
  confirmValue?: string
  isConfirmField?: boolean
}

const PasswordField: React.FC<PasswordFieldProps> = ({
  value,
  onChange,
  placeholder,
  label,
  disabled = false,
  showStrength = false,
  showRequirements = false,
  confirmValue,
  isConfirmField = false
}) => {
  const [showPassword, setShowPassword] = useState(false)
  
  const passwordErrors = validatePassword(value)
  const strength = value ? 4 - passwordErrors.length : 0
  
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>
      <div className="relative">
        <input
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 pr-10 transition-colors"
          placeholder={placeholder}
          disabled={disabled}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-600 transition-colors"
          disabled={disabled}
        >
          {showPassword ? (
            <EyeSlashIcon className="h-5 w-5 text-gray-400" />
          ) : (
            <EyeIcon className="h-5 w-5 text-gray-400" />
          )}
        </button>
      </div>
      
      {/* Indicateur de force du mot de passe */}
      {showStrength && value && (
        <div className="mt-2">
          <div className="text-xs text-gray-600 mb-1">Force du mot de passe :</div>
          <div className="flex space-x-1">
            {[1, 2, 3, 4].map((level) => (
              <div
                key={level}
                className={`h-1 flex-1 rounded ${
                  level <= strength
                    ? strength <= 1
                      ? 'bg-red-500'
                      : strength <= 2
                      ? 'bg-yellow-500'
                      : strength <= 3
                      ? 'bg-blue-500'
                      : 'bg-green-500'
                    : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
        </div>
      )}
      
      {/* Indicateur de correspondance pour confirmation */}
      {isConfirmField && value && confirmValue && (
        <div className="mt-1 text-xs">
          {confirmValue === value ? (
            <span className="text-green-600">✓ Les mots de passe correspondent</span>
          ) : (
            <span className="text-red-600">✗ Les mots de passe ne correspondent pas</span>
          )}
        </div>
      )}
      
      {/* Exigences du mot de passe */}
      {showRequirements && (
        <div className="mt-3 bg-gray-50 rounded-lg p-3">
          <h5 className="text-sm font-medium text-gray-900 mb-2">Exigences du mot de passe :</h5>
          <ul className="text-xs text-gray-600 space-y-1">
            <li className="flex items-center space-x-2">
              <span className={value.length >= 8 ? 'text-green-600' : 'text-gray-400'}>
                {value.length >= 8 ? '✓' : '○'}
              </span>
              <span>Au moins 8 caractères</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className={/[A-Z]/.test(value) ? 'text-green-600' : 'text-gray-400'}>
                {/[A-Z]/.test(value) ? '✓' : '○'}
              </span>
              <span>Au moins une majuscule</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className={/[a-z]/.test(value) ? 'text-green-600' : 'text-gray-400'}>
                {/[a-z]/.test(value) ? '✓' : '○'}
              </span>
              <span>Au moins une minuscule</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className={/\d/.test(value) ? 'text-green-600' : 'text-gray-400'}>
                {/\d/.test(value) ? '✓' : '○'}
              </span>
              <span>Au moins un chiffre</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className={/[!@#$%^&*(),.?":{}|<>]/.test(value) ? 'text-green-600' : 'text-gray-400'}>
                {/[!@#$%^&*(),.?":{}|<>]/.test(value) ? '✓' : '○'}
              </span>
              <span>Au moins un caractère spécial</span>
            </li>
          </ul>
        </div>
      )}
    </div>
  )
}

// ==================== PAGE CRÉATION DE COMPTE ====================
export default function SignupPage() {
  // 🔄 RETOUR : Utiliser le store Supabase avec timeout amélioré
  const { register, isLoading } = useAuthStore()
  
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
    acceptTerms: false
  })
  const [localErrors, setLocalErrors] = useState<string[]>([])

  // 🔍 DEBUG : Log au chargement de la page
  useEffect(() => {
    console.log('🚨 FICHIER UTILISÉ: Page signup AVEC Store Supabase + timeout')
    console.log('=== DEBUG: Page Signup Supabase timeout ===')
    console.log('Store utilisé: Supabase auth.ts avec timeout 10s')
  }, [])

  // Pas besoin de clearError pour le store Supabase
  const handleInputChange = (field: string, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (localErrors.length > 0) {
      setLocalErrors([])
    }
  }

  const handleSubmit = async () => {
    console.log('🚨 DEBUG: handleSubmit SUPABASE avec timeout appelé')
    console.log('=== DEBUG: handleSubmit Supabase ===')

    const validationErrors: string[] = []
    
    // Validations...
    if (!formData.firstName.trim()) {
      validationErrors.push('Le prénom est requis')
    }
    if (!formData.lastName.trim()) {
      validationErrors.push('Le nom est requis')
    }
    if (!formData.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      validationErrors.push('Veuillez entrer une adresse email valide')
    }
    if (!formData.password) {
      validationErrors.push('Le mot de passe est requis')
    }
    if (formData.password !== formData.confirmPassword) {
      validationErrors.push('Les mots de passe ne correspondent pas')
    }
    if (!formData.acceptTerms) {
      validationErrors.push('Vous devez accepter les conditions d\'utilisation')
    }
    
    const passwordValidationErrors = validatePassword(formData.password)
    validationErrors.push(...passwordValidationErrors)
    
    if (validationErrors.length > 0) {
      setLocalErrors(validationErrors)
      return
    }
    
    setLocalErrors([])
    
    try {
      console.log('🔍 DÉBUT: Création compte via Supabase avec timeout')
      
      const userData = {
        name: `${formData.firstName.trim()} ${formData.lastName.trim()}`,
        user_type: 'producer' as const,
        language: 'fr' as const
      }
      
      console.log('🔍 Appel register() du store Supabase...')
      await register(formData.email.trim(), formData.password, userData)
      
      console.log('✅ Inscription réussie via Supabase!')
      
      // Réinitialiser le formulaire en cas de succès
      setFormData({
        firstName: '',
        lastName: '',
        email: '',
        password: '',
        confirmPassword: '',
        acceptTerms: false
      })
      
    } catch (error: any) {
      console.error('❌ Erreur inscription Supabase:', error)
      setLocalErrors([error.message || 'Erreur lors de la création du compte'])
    }
  }

  const isFormValid = () => {
    const valid = (
      formData.firstName.trim() &&
      formData.lastName.trim() &&
      formData.email.trim() &&
      /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email) &&
      formData.password &&
      formData.confirmPassword &&
      formData.password === formData.confirmPassword &&
      formData.acceptTerms &&
      validatePassword(formData.password).length === 0
    )
    
    return valid
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <InteliaLogo className="w-16 h-16" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
          Créer votre compte Intelia Expert
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Rejoignez notre communauté d'experts en santé animale
        </p>
      </div>

      {/* Formulaire */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
          
          {/* 🔍 PANNEAU DE DEBUG */}
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs">
            <div className="font-bold text-blue-800 mb-1">🔍 DEBUG - Store Supabase avec timeout</div>
            <div className="text-blue-700">
              • Page: {typeof window !== 'undefined' ? window.location.pathname : 'N/A'}<br/>
              • Supabase: Direct avec timeout de 10s<br/>
              • Store: Supabase auth.ts avec timeout<br/>
              • Architecture: Frontend → Supabase (timeout 10s)
            </div>
          </div>
          
          {/* Affichage des erreurs */}
          {localErrors.length > 0 && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="text-sm text-red-800">
                {localErrors.map((error, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <span className="text-red-500 font-bold">•</span>
                    <span>{error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-6">
            {/* Nom et Prénom */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Prénom
                </label>
                <input
                  type="text"
                  value={formData.firstName}
                  onChange={(e) => handleInputChange('firstName', e.target.value)}
                  className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  placeholder="Jean"
                  disabled={isLoading}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nom
                </label>
                <input
                  type="text"
                  value={formData.lastName}
                  onChange={(e) => handleInputChange('lastName', e.target.value)}
                  className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  placeholder="Dupont"
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Adresse email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="jean.dupont@exemple.com"
                disabled={isLoading}
              />
            </div>

            {/* Mot de passe avec validation */}
            <PasswordField
              value={formData.password}
              onChange={(value) => handleInputChange('password', value)}
              label="Mot de passe"
              placeholder="Créez un mot de passe sécurisé"
              showStrength={true}
              showRequirements={true}
              disabled={isLoading}
            />

            {/* Confirmation mot de passe */}
            <PasswordField
              value={formData.confirmPassword}
              onChange={(value) => handleInputChange('confirmPassword', value)}
              label="Confirmer le mot de passe"
              placeholder="Confirmez votre mot de passe"
              confirmValue={formData.password}
              isConfirmField={true}
              disabled={isLoading}
            />

            {/* Acceptation des conditions */}
            <div className="flex items-start space-x-3">
              <div className="flex items-center h-5">
                <input
                  type="checkbox"
                  checked={formData.acceptTerms}
                  onChange={(e) => handleInputChange('acceptTerms', e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  disabled={isLoading}
                />
              </div>
              <div className="text-sm">
                <label className="text-gray-700">
                  J'accepte les{' '}
                  <a href="/terms" className="text-blue-600 hover:text-blue-500 font-medium transition-colors">
                    conditions d'utilisation
                  </a>{' '}
                  et la{' '}
                  <a href="/privacy" className="text-blue-600 hover:text-blue-500 font-medium transition-colors">
                    politique de confidentialité
                  </a>
                </label>
              </div>
            </div>

            {/* Bouton de soumission */}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !isFormValid()}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Création en cours...</span>
                </div>
              ) : (
                'Créer mon compte'
              )}
            </button>
          </div>

          {/* Lien retour vers connexion */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Vous avez déjà un compte ?{' '}
              <Link href="/auth/login" className="font-medium text-blue-600 hover:text-blue-500 transition-colors">
                Se connecter
              </Link>
            </p>
          </div>

          {/* Information RGPD */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center leading-relaxed">
              🔒 Vos données sont protégées et supprimées automatiquement après 30 jours d'inactivité.
              <br />
              Conformité RGPD garantie.
            </p>
          </div>
        </div>
      </div>

      {/* Footer avec support */}
      <div className="mt-8 text-center">
        <p className="text-xs text-gray-500">
          Besoin d'aide ?{' '}
          <button
            type="button"
            onClick={() => window.open('mailto:support@intelia.com', '_blank')}
            className="text-blue-600 hover:underline font-medium"
          >
            Contactez le support
          </button>
        </p>
      </div>
    </div>
  )
}