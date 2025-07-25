'use client'

import { useState } from 'react'
import Link from 'next/link'

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
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
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

// ==================== PAGE SUCCÈS ====================
const SuccessPage = () => (
  <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center p-6">
    <div className="w-full max-w-md text-center">
      <div className="bg-white p-8 rounded-lg shadow-lg border border-gray-200">
        <div className="text-6xl mb-4">✅</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Mot de passe modifié !
        </h1>
        <p className="text-gray-600 mb-6 leading-relaxed">
          Votre mot de passe a été mis à jour avec succès. Vous allez être redirigé vers la page de connexion dans quelques secondes.
        </p>
        <div className="flex justify-center">
          <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full"></div>
        </div>
      </div>
    </div>
  </div>
)

// ==================== PAGE RÉINITIALISATION ====================
export default function ResetPasswordPage() {
  const [formData, setFormData] = useState({
    newPassword: '',
    confirmPassword: ''
  })
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [success, setSuccess] = useState(false)

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (errors.length > 0) {
      setErrors([])
    }
  }

  const handleSubmit = async () => {
    const validationErrors: string[] = []
    
    // Validations
    if (!formData.newPassword) {
      validationErrors.push('Le nouveau mot de passe est requis')
    }
    if (!formData.confirmPassword) {
      validationErrors.push('La confirmation du mot de passe est requise')
    }
    if (formData.newPassword !== formData.confirmPassword) {
      validationErrors.push('Les mots de passe ne correspondent pas')
    }
    
    // Validation de la force du mot de passe
    const passwordValidationErrors = validatePassword(formData.newPassword)
    validationErrors.push(...passwordValidationErrors)
    
    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      return
    }
    
    setIsLoading(true)
    setErrors([])
    
    try {
      // TODO: Intégrer avec Supabase
      // const { error } = await supabase.auth.updateUser({
      //   password: formData.newPassword
      // })
      
      console.log('🔐 Réinitialisation mot de passe avec standards sécurisés')
      
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      setSuccess(true)
      
      // Redirection après 3 secondes
      setTimeout(() => {
        window.location.href = '/auth/login'
      }, 3000)
      
    } catch (error: any) {
      console.error('❌ Erreur lors de la réinitialisation:', error)
      setErrors([error.message || 'Erreur lors de la réinitialisation du mot de passe'])
    } finally {
      setIsLoading(false)
    }
  }

  const isFormValid = () => {
    return (
      formData.newPassword &&
      formData.confirmPassword &&
      formData.newPassword === formData.confirmPassword &&
      validatePassword(formData.newPassword).length === 0
    )
  }

  // Affichage de la page de succès
  if (success) {
    return <SuccessPage />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <InteliaLogo className="w-12 h-12" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Nouveau mot de passe
          </h1>
          <p className="text-gray-600 leading-relaxed">
            Choisissez un nouveau mot de passe sécurisé pour votre compte Intelia Expert
          </p>
        </div>

        {/* Messages d'erreur */}
        {errors.length > 0 && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="text-sm text-red-800">
              {errors.map((error, index) => (
                <div key={index} className="flex items-start space-x-2">
                  <span className="text-red-500 font-bold">•</span>
                  <span>{error}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Formulaire */}
        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="space-y-6">
            {/* Nouveau mot de passe */}
            <PasswordField
              value={formData.newPassword}
              onChange={(value) => handleInputChange('newPassword', value)}
              label="Nouveau mot de passe"
              placeholder="Créez un mot de passe sécurisé"
              showStrength={true}
              showRequirements={true}
              disabled={isLoading}
            />

            {/* Confirmation */}
            <PasswordField
              value={formData.confirmPassword}
              onChange={(value) => handleInputChange('confirmPassword', value)}
              label="Confirmer le nouveau mot de passe"
              placeholder="Confirmez votre nouveau mot de passe"
              confirmValue={formData.newPassword}
              isConfirmField={true}
              disabled={isLoading}
            />

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !isFormValid()}
              className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Mise à jour...</span>
                </div>
              ) : (
                'Mettre à jour le mot de passe'
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <div className="mt-6 text-center">
          <Link
            href="/auth/login"
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Retour à la connexion
          </Link>
        </div>

        {/* Information sécurité */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500 leading-relaxed">
            🔒 Votre nouveau mot de passe respecte les plus hauts standards de sécurité.
            <br />
            Il sera automatiquement chiffré et stocké de manière sécurisée.
          </p>
        </div>

        {/* Support */}
        <div className="mt-4 p-3 bg-gray-50 rounded-lg text-center">
          <p className="text-xs text-gray-600">
            Problème avec la réinitialisation ?{' '}
            <button
              type="button"
              onClick={() => window.open('mailto:support@intelia.com', '_blank')}
              className="text-blue-600 hover:underline font-medium transition-colors"
            >
              Contactez le support
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}