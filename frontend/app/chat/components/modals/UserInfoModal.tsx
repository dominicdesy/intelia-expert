import React, { useState } from 'react'
import { useAuthStore } from '@/lib/stores/auth'
import { useTranslation } from '../../hooks/useTranslation'
// ✅ CHANGEMENT: Utiliser le singleton au lieu de createClientComponentClient
import { getSupabaseClient } from '@/lib/supabase/singleton'
import { UserInfoModalProps } from '@/types'
import { PhoneInput, usePhoneValidation } from '../PhoneInput'

// ✅ CHANGEMENT: Utiliser le singleton au lieu de createClientComponentClient
const supabase = getSupabaseClient()

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
      return
    }

    setIsLoading(true)
    try {
      // ✅ Le client singleton est déjà initialisé plus haut
      const { error } = await supabase.auth.updateUser({
        password: passwordData.newPassword
      })
      
      if (error) {
        setPasswordErrors([error.message || 'Erreur lors du changement de mot de passe'])
        return
      }
      
      alert('Mot de passe changé avec succès!')
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      })
      setPasswordErrors([])
      onClose()
      
    } catch (error: any) {
      setPasswordErrors([error.message || 'Erreur technique lors du changement de mot de passe'])
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
                      <input
                        type="password"
                        value={passwordData.currentPassword}
                        onChange={(e) => setPasswordData(prev => ({ ...prev, currentPassword: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.newPassword')} <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="password"
                        value={passwordData.newPassword}
                        onChange={(e) => setPasswordData(prev => ({ ...prev, newPassword: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                      />
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
                      <input
                        type="password"
                        value={passwordData.confirmPassword}
                        onChange={(e) => setPasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                      />
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