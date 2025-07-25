// components/UserMenu.tsx - VERSION CORRIGÉE STRUCTURE
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'

// Icônes
const ChevronDownIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
  </svg>
)

const UserCircleIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
)

const CogIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
)

const ArrowRightOnRectangleIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
  </svg>
)

const GlobeAltIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3s-4.5 4.03-4.5 9 2.015 9 4.5 9z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.485 0 4.5 4.03 4.5 9s-2.015 9-4.5 9S7.5 16.97 7.5 12 9.515 3 12 3z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h18" />
  </svg>
)

const ScaleIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75L6 21A8.954 8.954 0 014.5 15h.5V13.5l1.5-1.5L9 10.5l3 3.75 3-3.75 2.5 1.5L19 13.5V15h.5c0 2.143-.831 4.089-2.185 5.25L15.815 21c-1.303-.485-2.713-.75-4.185-.75z" />
  </svg>
)

const TrashIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
  </svg>
)

interface UserMenuProps {
  className?: string
}

export default function UserMenu({ className = '' }: UserMenuProps) {
  const router = useRouter()
  const { user, logout, exportUserData, deleteUserData, updateProfile } = useAuthStore()
  
  // États pour les modals
  const [isOpen, setIsOpen] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [activeModal, setActiveModal] = useState<'profile' | 'settings' | 'legal' | null>(null)

  const userName = user?.name || user?.email || 'Utilisateur'
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

  const handleLogout = async () => {
    try {
      await logout()
      window.location.href = '/'
    } catch (error) {
      console.error('Erreur déconnexion:', error)
      window.location.href = '/'
    }
  }

  const handleAboutIntelia = () => {
    setIsOpen(false)
    window.open('https://intelia.com', '_blank')
  }

  const handleLegal = () => {
    setIsOpen(false)
    setActiveModal('legal')
  }

  const handleDeleteData = async () => {
    try {
      await deleteUserData()
      setShowDeleteConfirm(false)
      setIsOpen(false)
      window.location.href = '/'
    } catch (error) {
      console.error('Erreur suppression:', error)
      alert('Erreur lors de la suppression du compte')
    }
  }

  return (
    <div className={`relative ${className}`}>
      {/* Bouton utilisateur */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
      >
        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
          <span className="text-white text-xs font-medium">{userInitials}</span>
        </div>
        <span className="hidden sm:inline font-medium">{userName}</span>
        <ChevronDownIcon className="w-4 h-4 text-gray-500" />
      </button>

      {/* Menu déroulant */}
      {isOpen && (
        <>
          {/* Overlay */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Menu */}
          <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-20">
            {/* Header utilisateur */}
            <div className="px-4 py-3 border-b border-gray-100">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-sm font-medium">{userInitials}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{userName}</p>
                  <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                  <p className="text-xs text-green-600 capitalize">{user?.user_type || 'Producteur'}</p>
                </div>
              </div>
            </div>

            {/* Options du menu */}
            <div className="py-2">
              {/* Mon profil */}
              <button
                onClick={() => {
                  setIsOpen(false)
                  setActiveModal('profile')
                }}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <UserCircleIcon className="w-5 h-5 text-gray-500" />
                <span>Mon profil</span>
              </button>

              {/* Paramètres */}
              <button
                onClick={() => {
                  setIsOpen(false)
                  setActiveModal('settings')
                }}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <CogIcon className="w-5 h-5 text-gray-500" />
                <span>Paramètres</span>
              </button>

              {/* Séparateur */}
              <div className="my-2 border-t border-gray-100" />

              {/* About Intelia */}
              <button
                onClick={handleAboutIntelia}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <GlobeAltIcon className="w-5 h-5 text-gray-500" />
                <span>About Intelia</span>
              </button>

              {/* Legal */}
              <button
                onClick={handleLegal}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <ScaleIcon className="w-5 h-5 text-gray-500" />
                <span>Legal</span>
              </button>

              {/* Supprimer compte */}
              <button
                onClick={() => {
                  setIsOpen(false)
                  setShowDeleteConfirm(true)
                }}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <TrashIcon className="w-5 h-5 text-red-500" />
                <span>Supprimer mon compte</span>
              </button>

              {/* Séparateur */}
              <div className="my-2 border-t border-gray-100" />

              {/* Déconnexion */}
              <button
                onClick={handleLogout}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <ArrowRightOnRectangleIcon className="w-5 h-5 text-gray-500" />
                <span>Déconnexion</span>
              </button>
            </div>

            {/* Footer RGPD */}
            <div className="px-4 py-3 border-t border-gray-100">
              <p className="text-xs text-gray-500">
                Vos données seront automatiquement supprimées après 30 jours d'inactivité.
              </p>
            </div>
          </div>
        </>
      )}

      {/* Modal Mon Profil */}
      {activeModal === 'profile' && (
        <ProfileModal 
          user={user!}
          onClose={() => setActiveModal(null)}
          onSave={updateProfile}
        />
      )}

      {/* Modal Paramètres */}
      {activeModal === 'settings' && (
        <SettingsModal 
          onClose={() => setActiveModal(null)}
        />
      )}

      {/* Modal Legal */}
      {activeModal === 'legal' && (
        <LegalModal 
          onClose={() => setActiveModal(null)}
        />
      )}

      {/* Modal Suppression */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <TrashIcon className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-bold text-gray-900">
                Supprimer mon compte
              </h3>
            </div>
            
            <p className="text-gray-700 mb-6">
              Êtes-vous sûr de vouloir supprimer définitivement votre compte ? 
              Cette action est irréversible et toutes vos données seront supprimées.
            </p>
            
            <div className="flex space-x-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-gray-700"
              >
                Annuler
              </button>
              <button
                onClick={handleDeleteData}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Supprimer définitivement
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Modal Mon Profil
interface ProfileModalProps {
  user: any
  onClose: () => void
  onSave: (data: any) => Promise<void>
}

function ProfileModal({ user, onClose, onSave }: ProfileModalProps) {
  const [formData, setFormData] = useState({
    name: user.name || '',
    email: user.email || '',
    user_type: user.user_type || 'producer',
    language: user.language || 'fr'
  })
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    setSuccess('')

    try {
      await onSave(formData)
      setSuccess('Profil mis à jour avec succès !')
      setTimeout(() => {
        onClose()
      }, 1500)
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la mise à jour')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-gray-900">Mon Profil</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Nom complet */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nom complet
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          {/* Email (lecture seule) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Adresse email
            </label>
            <input
              type="email"
              value={formData.email}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              L'email ne peut pas être modifié pour des raisons de sécurité
            </p>
          </div>

          {/* Type d'utilisateur */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type de profil
            </label>
            <select
              value={formData.user_type}
              onChange={(e) => setFormData(prev => ({ ...prev, user_type: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="producer">Producteur agricole</option>
              <option value="professional">Professionnel santé animale</option>
            </select>
          </div>

          {/* Langue */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Langue préférée
            </label>
            <select
              value={formData.language}
              onChange={(e) => setFormData(prev => ({ ...prev, language: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="fr">Français</option>
              <option value="en">English</option>
              <option value="es">Español</option>
            </select>
          </div>

          {/* Informations compte */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Informations du compte</h4>
            <div className="space-y-1 text-xs text-gray-600">
              <p><strong>Membre depuis :</strong> {user.created_at ? new Date(user.created_at).toLocaleDateString('fr-FR') : 'N/A'}</p>
              <p><strong>Rétention des données :</strong> 30 jours après la dernière activité</p>
            </div>
          </div>

          {/* Boutons */}
          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              disabled={isLoading}
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
            >
              {isLoading ? 'Sauvegarde...' : 'Sauvegarder'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Modal Paramètres
interface SettingsModalProps {
  onClose: () => void
}

function SettingsModal({ onClose }: SettingsModalProps) {
  const [settings, setSettings] = useState({
    notifications: true,
    emailUpdates: false,
    darkMode: false,
    autoSave: true,
    language: 'fr'
  })

  const handleSave = () => {
    localStorage.setItem('intelia-settings', JSON.stringify(settings))
    alert('Paramètres sauvegardés avec succès !')
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-gray-900">Paramètres</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="space-y-6">
          {/* Notifications */}
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Notifications</h4>
            <div className="space-y-3">
              <label className="flex items-center justify-between">
                <span className="text-sm text-gray-700">Notifications push</span>
                <input
                  type="checkbox"
                  checked={settings.notifications}
                  onChange={(e) => setSettings(prev => ({ ...prev, notifications: e.target.checked }))}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
              </label>
              <label className="flex items-center justify-between">
                <span className="text-sm text-gray-700">Emails de mise à jour</span>
                <input
                  type="checkbox"
                  checked={settings.emailUpdates}
                  onChange={(e) => setSettings(prev => ({ ...prev, emailUpdates: e.target.checked }))}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
              </label>
            </div>
          </div>

          {/* Interface */}
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Interface</h4>
            <div className="space-y-3">
              <label className="flex items-center justify-between">
                <span className="text-sm text-gray-700">Mode sombre</span>
                <input
                  type="checkbox"
                  checked={settings.darkMode}
                  onChange={(e) => setSettings(prev => ({ ...prev, darkMode: e.target.checked }))}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
              </label>
              <label className="flex items-center justify-between">
                <span className="text-sm text-gray-700">Sauvegarde automatique</span>
                <input
                  type="checkbox"
                  checked={settings.autoSave}
                  onChange={(e) => setSettings(prev => ({ ...prev, autoSave: e.target.checked }))}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
              </label>
            </div>
          </div>

          {/* Stockage */}
          <div className="bg-blue-50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Gestion des données</h4>
            <div className="space-y-1 text-xs text-blue-700">
              <p>• Conversations supprimées après 30 jours</p>
              <p>• Données anonymisées pour les analytics</p>
              <p>• Sauvegardes chiffrées et sécurisées</p>
            </div>
          </div>
        </div>

        {/* Boutons */}
        <div className="flex space-x-3 pt-6">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={handleSave}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Sauvegarder
          </button>
        </div>
      </div>
    </div>
  )
}

// Modal Legal
interface LegalModalProps {
  onClose: () => void
}

function LegalModal({ onClose }: LegalModalProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-gray-900">Mentions Légales</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="prose prose-sm max-w-none">
          <h4 className="text-md font-semibold text-gray-900 mb-3">Informations légales</h4>
          
          <div className="space-y-4 text-sm text-gray-700">
            <div>
              <h5 className="font-medium text-gray-900 mb-2">Éditeur du site</h5>
              <p>
                <strong>Intelia Expert</strong><br />
                Société : Intelia Inc.<br />
                Adresse : [À compléter]<br />
                Téléphone : [À compléter]<br />
                Email : contact@intelia.com
              </p>
            </div>

            <div>
              <h5 className="font-medium text-gray-900 mb-2">Hébergement</h5>
              <p>
                Ce site est hébergé par :<br />
                <strong>DigitalOcean</strong><br />
                101 Avenue of the Americas, 10th Floor<br />
                New York, NY 10013, États-Unis
              </p>
            </div>

            <div>
              <h5 className="font-medium text-gray-900 mb-2">Protection des données</h5>
              <p>
                Conformément au RGPD et à la loi informatique et libertés, vous disposez d'un droit 
                d'accès, de rectification et de suppression des données vous concernant. 
                Les données sont automatiquement supprimées après 30 jours d'inactivité.
              </p>
            </div>

            <div>
              <h5 className="font-medium text-gray-900 mb-2">Utilisation de l'IA</h5>
              <p>
                Intelia Expert utilise des modèles d'intelligence artificielle pour fournir des 
                conseils en santé et nutrition animale. Ces conseils sont fournis à titre informatif 
                et ne remplacent pas l'avis d'un vétérinaire qualifié.
              </p>
            </div>
          </div>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <p className="text-xs text-blue-700">
              <strong>Note :</strong> Ces mentions légales sont en cours de finalisation. 
              Pour toute question juridique, contactez notre service juridique à legal@intelia.com
            </p>
          </div>
        </div>

        <div className="flex justify-end pt-6 border-t">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  )
}