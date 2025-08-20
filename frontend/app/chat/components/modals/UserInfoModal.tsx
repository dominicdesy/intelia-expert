import React, { useState } from 'react'
import { useAuthStore } from '@/lib/stores/auth'
import { useTranslation } from '../../hooks/useTranslation'
import { UserInfoModalProps } from '@/types'
import { PhoneInput, usePhoneValidation } from '../PhoneInput'

// ==================== MODAL PROFIL REDESIGNÉ COMPLÈTEMENT ====================
export const UserInfoModal = ({ user, onClose }: UserInfoModalProps) => {
  const { updateProfile } = useAuthStore()
  const { t } = useTranslation()
  const { validatePhoneFields } = usePhoneValidation()
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')
  
  const [formData, setFormData] = useState({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    email: user?.email || '',
    country_code: user?.country_code || '',
    area_code: user?.area_code || '',
    phone_number: user?.phone_number || '',
    country: user?.country || '',
    linkedinProfile: user?.linkedinProfile || '',
    companyName: user?.companyName || '',
    companyWebsite: user?.companyWebsite || '',
    linkedinCorporate: user?.linkedinCorporate || ''
  })

  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })

  const [showPasswords, setShowPasswords] = useState({
    currentPassword: false,
    newPassword: false,
    confirmPassword: false
  })

  const [passwordErrors, setPasswordErrors] = useState<string[]>([])
  const [formErrors, setFormErrors] = useState<string[]>([])

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

  const handlePhoneChange = (phoneData: { country_code: string; area_code: string; phone_number: string }) => {
    setFormData(prev => ({
      ...prev,
      country_code: phoneData.country_code,
      area_code: phoneData.area_code,
      phone_number: phoneData.phone_number
    }))
  }

  const handleProfileSave = async () => {
    setIsLoading(true)
    setFormErrors([])
    
    try {
      const errors: string[] = []
      
      if (!formData.firstName.trim()) {
        errors.push('Le prénom est requis')
      }
      if (!formData.lastName.trim()) {
        errors.push('Le nom est requis')
      }
      if (!formData.email.trim()) {
        errors.push('L\'email est requis')
      }
      
      const phoneValidation = validatePhoneFields(
        formData.country_code, 
        formData.area_code, 
        formData.phone_number
      )
      
      if (!phoneValidation.isValid) {
        errors.push(...phoneValidation.errors.map(err => `Téléphone: ${err}`))
      }
      
      if (errors.length > 0) {
        setFormErrors(errors)
        return
      }

      // 🔧 CORRECTION: updateProfile retourne void, pas un objet
      try {
        await updateProfile(formData)
        alert(t('profile.title') + ' mis à jour avec succès!')
        onClose()
      } catch (error: any) {
        alert('Erreur lors de la mise à jour: ' + (error?.message || 'Erreur inconnue'))
      }
    } catch (error) {
      console.error('❌ Erreur mise à jour profil (singleton):', error)
      alert('Erreur lors de la mise à jour du profil')
    }
    setIsLoading(false)
  }

  const handlePasswordChange = async () => {
    console.log('🔄 [Password] Début changement mot de passe')
    const errors: string[] = []
    
    if (!passwordData.currentPassword) {
      errors.push('Le mot de passe actuel est requis')
    }
    if (!passwordData.newPassword) {
      errors.push('Le nouveau mot de passe est requis')
    }
    if (!passwordData.confirmPassword) {
      errors.push('La confirmation du mot de passe est requise')
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      errors.push('Les mots de passe ne correspondent pas')
    }
    
    const passwordValidationErrors = validatePassword(passwordData.newPassword)
    errors.push(...passwordValidationErrors)
    
    setPasswordErrors(errors)
    
    if (errors.length > 0) {
      console.log('❌ [Password] Erreurs de validation:', errors)
      return
    }

    setIsLoading(true)
    try {
      console.log('🔐 [Password] Appel à l\'API backend pour changement mot de passe')
      
      // ✅ CORRECTION: Utiliser l'API backend au lieu de Supabase direct
      const response = await fetch('/api/v1/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          current_password: passwordData.currentPassword,
          new_password: passwordData.newPassword
        })
      })

      const result = await response.json()
      
      if (!response.ok) {
        console.log('❌ [Password] Erreur API:', result.detail || result.message)
        setPasswordErrors([result.detail || result.message || 'Erreur lors du changement de mot de passe'])
        return
      }
      
      console.log('✅ [Password] Mot de passe changé avec succès via backend')
      
      // Réinitialiser les champs et fermer
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      })
      setPasswordErrors([])
      
      // Fermer d'abord la modal
      onClose()
      
      // Puis afficher le message de succès
      setTimeout(() => {
        alert('Mot de passe changé avec succès!')
      }, 100)
      
    } catch (error: any) {
      console.error('❌ [Password] Erreur technique:', error)
      setPasswordErrors(['Erreur de connexion au serveur. Veuillez réessayer.'])
    } finally {
      setIsLoading(false)
    }
  }

  const tabs = [
    { id: 'profile', label: t('nav.profile'), icon: '👤' },
    { id: 'password', label: t('profile.password'), icon: '🔑' }
  ]

  return (
    <>
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-50" 
        onClick={onClose}
      />
      
      {/* Modal Container - Taille fixe optimisée */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div 
          className="bg-white rounded-xl shadow-2xl w-full max-w-2xl h-[85vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header Fixe */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
            <h2 className="text-xl font-semibold text-gray-900">
              {t('profile.title')}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl font-light w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
            >
              ×
            </button>
          </div>

          {/* Onglets Fixes */}
          <div className="border-b border-gray-200 flex-shrink-0">
            <nav className="flex px-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-3 px-4 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Contenu Scrollable */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-6 space-y-6">
              {/* Erreurs globales */}
              {formErrors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="text-sm text-red-800">
                    <p className="font-medium mb-2">Erreurs de validation :</p>
                    <ul className="list-disc list-inside space-y-1">
                      {formErrors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {activeTab === 'profile' && (
                <div className="space-y-6">
                  {/* Informations Personnelles */}
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                      <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                      {t('profile.personalInfo')}
                      <span className="text-red-500 ml-1">*</span>
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('profile.firstName')} <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={formData.firstName}
                          onChange={(e) => setFormData(prev => ({ ...prev, firstName: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          required
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('profile.lastName')} <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={formData.lastName}
                          onChange={(e) => setFormData(prev => ({ ...prev, lastName: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          required
                        />
                      </div>
                    </div>

                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.email')} <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                      />
                    </div>

                    {/* Téléphone - Composant simplifié intégré */}
                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700 mb-3">
                        {t('profile.phone')} <span className="text-gray-500 text-sm">(optionnel)</span>
                      </label>
                      <PhoneInput
                        countryCode={formData.country_code}
                        areaCode={formData.area_code}
                        phoneNumber={formData.phone_number}
                        onChange={handlePhoneChange}
                      />
                    </div>

                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.country')} <span className="text-gray-500 text-sm">(optionnel)</span>
                      </label>
                      <select
                        value={formData.country}
                        onChange={(e) => setFormData(prev => ({ ...prev, country: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                      >
                        <option value="">Sélectionner un pays</option>
                        <option value="CA">🇨🇦 Canada</option>
                        <option value="US">🇺🇸 États-Unis</option>
                        <option value="FR">🇫🇷 France</option>
                        <option value="BE">🇧🇪 Belgique</option>
                        <option value="CH">🇨🇭 Suisse</option>
                        <option value="MX">🇲🇽 Mexique</option>
                        <option value="BR">🇧🇷 Brésil</option>
                        <option value="other">🌍 Autre</option>
                      </select>
                    </div>
                  </div>

                  {/* Informations Professionnelles */}
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                      <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                      Informations Professionnelles
                      <span className="text-gray-500 text-sm ml-2">(optionnel)</span>
                    </h3>
                    
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Profil LinkedIn Personnel
                        </label>
                        <input
                          type="url"
                          value={formData.linkedinProfile}
                          onChange={(e) => setFormData(prev => ({ ...prev, linkedinProfile: e.target.value }))}
                          placeholder="https://linkedin.com/in/votre-profil"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('profile.companyName')}
                        </label>
                        <input
                          type="text"
                          value={formData.companyName}
                          onChange={(e) => setFormData(prev => ({ ...prev, companyName: e.target.value }))}
                          placeholder="Nom de votre entreprise ou exploitation"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('profile.companyWebsite')}
                        </label>
                        <input
                          type="url"
                          value={formData.companyWebsite}
                          onChange={(e) => setFormData(prev => ({ ...prev, companyWebsite: e.target.value }))}
                          placeholder="https://www.votre-entreprise.com"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Page LinkedIn Entreprise
                        </label>
                        <input
                          type="url"
                          value={formData.linkedinCorporate}
                          onChange={(e) => setFormData(prev => ({ ...prev, linkedinCorporate: e.target.value }))}
                          placeholder="https://linkedin.com/company/votre-entreprise"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'password' && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                    {t('profile.password')}
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.currentPassword')} <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showPasswords.currentPassword ? "text" : "password"}
                          name="currentPassword"
                          autoComplete="current-password"
                          value={passwordData.currentPassword}
                          onChange={(e) => {
                            console.log('Current password change:', e.target.value);
                            setPasswordData(prev => ({ ...prev, currentPassword: e.target.value }))
                          }}
                          className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                          placeholder="Tapez votre mot de passe actuel"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowPasswords(prev => ({ ...prev, currentPassword: !prev.currentPassword }))}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                        >
                          {showPasswords.currentPassword ? (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 11-4.243-4.243m4.242 4.242L9.88 9.88" />
                            </svg>
                          ) : (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                          )}
                        </button>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Caractères tapés: {passwordData.currentPassword.length}
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.newPassword')} <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showPasswords.newPassword ? "text" : "password"}
                          name="newPassword"
                          autoComplete="new-password"
                          value={passwordData.newPassword}
                          onChange={(e) => {
                            console.log('New password change:', e.target.value);
                            setPasswordData(prev => ({ ...prev, newPassword: e.target.value }))
                          }}
                          className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                          placeholder="Tapez votre nouveau mot de passe"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowPasswords(prev => ({ ...prev, newPassword: !prev.newPassword }))}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                        >
                          {showPasswords.newPassword ? (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 11-4.243-4.243m4.242 4.242L9.88 9.88" />
                            </svg>
                          ) : (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                          )}
                        </button>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Caractères tapés: {passwordData.newPassword.length}
                      </div>
                      <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs font-medium text-gray-700 mb-2">Le mot de passe doit contenir :</p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-xs">
                          <div className={`flex items-center ${passwordData.newPassword.length >= 8 ? 'text-green-600' : 'text-gray-400'}`}>
                            <span className="mr-1">{passwordData.newPassword.length >= 8 ? '✅' : '⭕'}</span>
                            8+ caractères
                          </div>
                          <div className={`flex items-center ${/[A-Z]/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-400'}`}>
                            <span className="mr-1">{/[A-Z]/.test(passwordData.newPassword) ? '✅' : '⭕'}</span>
                            Une majuscule
                          </div>
                          <div className={`flex items-center ${/[a-z]/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-400'}`}>
                            <span className="mr-1">{/[a-z]/.test(passwordData.newPassword) ? '✅' : '⭕'}</span>
                            Une minuscule
                          </div>
                          <div className={`flex items-center ${/\d/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-400'}`}>
                            <span className="mr-1">{/\d/.test(passwordData.newPassword) ? '✅' : '⭕'}</span>
                            Un chiffre
                          </div>
                          <div className={`flex items-center ${/[!@#$%^&*(),.?":{}|<>]/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-400'} sm:col-span-2`}>
                            <span className="mr-1">{/[!@#$%^&*(),.?":{}|<>]/.test(passwordData.newPassword) ? '✅' : '⭕'}</span>
                            Un caractère spécial (!@#$%^&*...)
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.confirmPassword')} <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showPasswords.confirmPassword ? "text" : "password"}
                          name="confirmPassword"
                          autoComplete="new-password"
                          value={passwordData.confirmPassword}
                          onChange={(e) => {
                            console.log('Confirm password change:', e.target.value);
                            setPasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))
                          }}
                          className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                          placeholder="Confirmez votre nouveau mot de passe"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowPasswords(prev => ({ ...prev, confirmPassword: !prev.confirmPassword }))}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                        >
                          {showPasswords.confirmPassword ? (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 11-4.243-4.243m4.242 4.242L9.88 9.88" />
                            </svg>
                          ) : (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                          )}
                        </button>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Caractères tapés: {passwordData.confirmPassword.length}
                      </div>
                    </div>
                    
                    {passwordErrors.length > 0 && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <div className="text-sm text-red-800">
                          <p className="font-medium mb-2">Erreurs :</p>
                          <ul className="list-disc list-inside space-y-1">
                            {passwordErrors.map((error, index) => (
                              <li key={index}>{error}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer Fixe */}
          <div className="flex justify-end space-x-3 p-6 border-t border-gray-200 flex-shrink-0 bg-gray-50">
            <button
              onClick={onClose}
              className="px-5 py-2 text-gray-600 hover:text-gray-800 font-medium transition-colors"
              disabled={isLoading}
            >
              {t('modal.cancel')}
            </button>
            <button
              onClick={activeTab === 'profile' ? handleProfileSave : handlePasswordChange}
              disabled={isLoading}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center"
            >
              {isLoading && (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              )}
              {isLoading ? t('modal.loading') : t('modal.save')}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}