import React, { useState } from 'react'
import { useAuthStore } from '../../hooks/useAuthStore'
import { useTranslation } from '../../hooks/useTranslation'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { UserInfoModalProps } from '../../types'

const supabase = createClientComponentClient()

// ==================== MODAL PROFIL ÉTENDU AVEC ONGLETS ====================
export const UserInfoModal = ({ user, onClose }: UserInfoModalProps) => {
  const { updateProfile } = useAuthStore()
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')
  
  const [formData, setFormData] = useState({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    email: user?.email || '',
    phone: user?.phone || '',
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

  const handleProfileSave = async () => {
    setIsLoading(true)
    try {
      const result = await updateProfile(formData)
      if (result.success) {
        alert(t('profile.title') + ' mis à jour avec succès!')
        onClose()
      } else {
        alert('Erreur lors de la mise à jour: ' + (result.error || 'Erreur inconnue'))
      }
    } catch (error) {
      console.error('❌ Erreur mise à jour profil:', error)
      alert('Erreur lors de la mise à jour du profil')
    }
    setIsLoading(false)
  }

  const handlePasswordChange = async () => {
    // Validation des mots de passe
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
    
    // Validation de la complexité du nouveau mot de passe
    const passwordValidationErrors = validatePassword(passwordData.newPassword)
    errors.push(...passwordValidationErrors)
    
    setPasswordErrors(errors)
    
    if (errors.length > 0) {
      return
    }

    setIsLoading(true)
    try {
      console.log('🔒 Changement de mot de passe en cours...')
      
      const { error } = await supabase.auth.updateUser({
        password: passwordData.newPassword
      })
      
      if (error) {
        console.error('❌ Erreur changement mot de passe:', error)
        setPasswordErrors([error.message || 'Erreur lors du changement de mot de passe'])
        return
      }
      
      console.log('✅ Mot de passe changé avec succès')
      alert('Mot de passe changé avec succès!')
      
      // Réinitialiser le formulaire
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      })
      setPasswordErrors([])
      
      onClose()
      
    } catch (error: any) {
      console.error('❌ Erreur critique changement mot de passe:', error)
      setPasswordErrors([error.message || 'Erreur technique lors du changement de mot de passe'])
    } finally {
      setIsLoading(false)
    }
  }

  const tabs = [
    { id: 'profile', label: t('nav.profile'), icon: '👤' },
    { id: 'password', label: t('profile.password'), icon: '🔒' }
  ]

  return (
    <div className="space-y-4">
      {/* Onglets */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
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

      {/* Contenu des onglets */}
      <div className="space-y-6 max-h-[60vh] overflow-y-auto">
        {activeTab === 'profile' && (
          <>
            {/* Section Informations Personnelles */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 border-b border-gray-200 pb-2">
                {t('profile.personalInfo')}
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.firstName')}</label>
                  <input
                    type="text"
                    value={formData.firstName}
                    onChange={(e) => setFormData(prev => ({ ...prev, firstName: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.lastName')}</label>
                  <input
                    type="text"
                    value={formData.lastName}
                    onChange={(e) => setFormData(prev => ({ ...prev, lastName: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.email')}</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.phone')}</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                    placeholder="+1 (555) 123-4567"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.country')}</label>
                  <select
                    value={formData.country}
                    onChange={(e) => setFormData(prev => ({ ...prev, country: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Profil LinkedIn Personnel
                </label>
                <input
                  type="url"
                  value={formData.linkedinProfile}
                  onChange={(e) => setFormData(prev => ({ ...prev, linkedinProfile: e.target.value }))}
                  placeholder="https://linkedin.com/in/votre-profil"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Section Entreprise */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 border-b border-gray-200 pb-2">
                {t('profile.company')}
              </h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.companyName')}</label>
                <input
                  type="text"
                  value={formData.companyName}
                  onChange={(e) => setFormData(prev => ({ ...prev, companyName: e.target.value }))}
                  placeholder="Nom de votre entreprise ou exploitation"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.companyWebsite')}</label>
                <input
                  type="url"
                  value={formData.companyWebsite}
                  onChange={(e) => setFormData(prev => ({ ...prev, companyWebsite: e.target.value }))}
                  placeholder="https://www.votre-entreprise.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Page LinkedIn Entreprise
                </label>
                <input
                  type="url"
                  value={formData.linkedinCorporate}
                  onChange={(e) => setFormData(prev => ({ ...prev, linkedinCorporate: e.target.value }))}
                  placeholder="https://linkedin.com/company/votre-entreprise"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </>
        )}

        {activeTab === 'password' && (
          <div className="pb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4 border-b border-gray-200 pb-2">
              {t('profile.password')}
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.currentPassword')} *</label>
                <input
                  type="password"
                  value={passwordData.currentPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, currentPassword: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.newPassword')} *</label>
                <input
                  type="password"
                  value={passwordData.newPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, newPassword: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <div className="mt-2 text-xs text-gray-600">
                  <p className="font-medium mb-2">Le mot de passe doit contenir :</p>
                  <ul className="space-y-1">
                    <li className={`flex items-center ${passwordData.newPassword.length >= 8 ? 'text-green-600' : 'text-gray-500'}`}>
                      <span className="mr-2 text-sm">
                        {passwordData.newPassword.length >= 8 ? '✅' : '⭕'}
                      </span>
                      Au moins 8 caractères
                    </li>
                    <li className={`flex items-center ${/[A-Z]/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-500'}`}>
                      <span className="mr-2 text-sm">
                        {/[A-Z]/.test(passwordData.newPassword) ? '✅' : '⭕'}
                      </span>
                      Au moins une majuscule
                    </li>
                    <li className={`flex items-center ${/[a-z]/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-500'}`}>
                      <span className="mr-2 text-sm">
                        {/[a-z]/.test(passwordData.newPassword) ? '✅' : '⭕'}
                      </span>
                      Au moins une minuscule
                    </li>
                    <li className={`flex items-center ${/\d/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-500'}`}>
                      <span className="mr-2 text-sm">
                        {/\d/.test(passwordData.newPassword) ? '✅' : '⭕'}
                      </span>
                      Au moins un chiffre
                    </li>
                    <li className={`flex items-center ${/[!@#$%^&*(),.?":{}|<>]/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-500'}`}>
                      <span className="mr-2 text-sm">
                        {/[!@#$%^&*(),.?":{}|<>]/.test(passwordData.newPassword) ? '✅' : '⭕'}
                      </span>
                      Au moins un caractère spécial
                    </li>
                  </ul>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('profile.confirmPassword')} *</label>
                <input
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={(e) => setPasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              {passwordErrors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <div className="text-sm text-red-800">
                    <p className="font-medium">Erreurs :</p>
                    <ul className="list-disc list-inside mt-1">
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

      <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button
          onClick={onClose}
          className="px-4 py-2 text-gray-600 hover:text-gray-800"
          disabled={isLoading}
        >
          {t('modal.cancel')}
        </button>
        <button
          onClick={activeTab === 'profile' ? handleProfileSave : handlePasswordChange}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? t('modal.loading') : t('modal.save')}
        </button>
      </div>
    </div>
  )
}