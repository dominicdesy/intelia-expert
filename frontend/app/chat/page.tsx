'use client'

// Forcer l'utilisation du runtime Node.js au lieu d'Edge Runtime
export const runtime = 'nodejs'

import React, { useState, useEffect, useRef } from 'react'

// ==================== STORES SIMULÉS ====================
const useAuthStore = () => ({
  user: {
    id: '1',
    name: 'Jean Dupont',
    email: 'jean.dupont@exemple.com',
    user_type: 'producer',
    language: 'fr',
    created_at: '2024-01-15',
    consentGiven: true,
    consentDate: new Date('2024-01-15')
  },
  isAuthenticated: true,
  logout: async () => {
    console.log('🚪 Déconnexion en cours...')
    // Redirection vers la page de login externe
    window.location.href = 'https://expert.intelia.com'
  },
  exportUserData: async () => {
    console.log('Export des données...')
  },
  deleteUserData: async () => {
    console.log('Suppression des données...')
  },
  updateProfile: async (data: any) => {
    console.log('Mise à jour profil:', data)
  }
})

const useChatStore = () => ({
  conversations: [
    {
      id: '1',
      title: 'Problème poulets Ross 308',
      messages: [
        { id: '1', role: 'user', content: 'Mes poulets Ross 308 de 25 jours pèsent 800g, est-ce normal ?' },
        { id: '2', role: 'assistant', content: 'Selon notre base documentaire, pour les poulets Ross 308...' }
      ],
      updated_at: '2024-01-20',
      created_at: '2024-01-20'
    }
  ],
  currentConversation: null,
  loadConversations: () => {},
  loadConversation: async (id: string) => {},
  deleteConversation: async (id: string) => {
    console.log('Suppression conversation:', id)
  },
  clearAllConversations: async () => {
    console.log('Suppression toutes conversations')
  },
  createConversation: () => {}
})

// ==================== TYPES ====================
interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
}

// ==================== ICÔNES SVG ====================
const PaperAirplaneIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0 1 21.485 12 59.77 59.77 0 0 1 3.27 20.876L5.999 12zm0 0h7.5" />
  </svg>
)

const UserIcon = ({ className = "w-8 h-8" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
)

const PlusIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
  </svg>
)

const EllipsisVerticalIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
  </svg>
)

const ThumbUpIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.5c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 712.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V3a.75.75 0 01.75-.75A2.25 2.25 0 0116.5 4.5c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 01-2.649 7.521c-.388.482-.987.729-1.605.729H13.48c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 00-1.423-.23H5.904M14.25 9h2.25M5.904 18.75c.083.205.173.405.27.602.398.83 1.169 1.448 2.126 1.448h.386c.114 0 .228-.007.34-.02a4.877 4.877 0 004.2-3.204 4.877 4.877 0 00.258-1.826v-1.25a1.125 1.125 0 00-1.125-1.125H5.904z" />
  </svg>
)

const ThumbDownIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 15h2.25m8.024-9.75c.011.05.028.1.052.148.591 1.2.924 2.55.924 3.977a8.96 8.96 0 01-.999 4.125m.023-8.25c-.076-.365.183-.75.575-.75h.908c.889 0 1.713.518 1.972 1.368.339 1.11.521 2.287.521 3.507 0 1.553-.295 3.036-.831 4.398C20.613 14.547 19.833 15 19 15h-1.053c-.472 0-.745-.556-.5-.96a8.95 8.95 0 00.303-.54m.023-8.25H16.48a4.5 4.5 0 01-1.423-.23l-3.114-1.04a4.5 4.5 0 00-1.423-.23H6.504c-.618 0-1.217.247-1.605.729A11.95 11.95 0 002.25 12c0 .434.023.863.068 1.285C2.427 14.306 3.346 15 4.372 15h3.126c.618 0 .991.724.725 1.282A7.471 7.471 0 007.5 19.5a2.25 2.25 0 002.25 2.25.75.75 0 00.75-.75v-.633c0-.573.11-1.14.322-1.672.304-.76.93-1.33 1.653-1.715a9.04 9.04 0 002.86-2.4c.498-.634 1.226-1.08 2.032-1.08h.384z" />
  </svg>
)

const TrashIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
  </svg>
)

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== COMPOSANTS MODAL ====================
const Modal = ({ isOpen, onClose, title, children }: {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}) => {
  if (!isOpen) return null

  return (
    <>
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-50" 
        onClick={onClose}
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div 
          className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>
          <div className="p-6">
            {children}
          </div>
        </div>
      </div>
    </>
  )
}

const UserInfoModal = ({ user, onClose }: { user: any, onClose: () => void }) => {
  const [formData, setFormData] = useState({
    firstName: user?.name?.split(' ')[0] || '',
    lastName: user?.name?.split(' ').slice(1).join(' ') || '',
    linkedinProfile: '',
    companyName: '',
    companyWebsite: '',
    linkedinCorporate: '',
    email: user?.email || '',
    phone: '',
    country: 'CA' // Default Canada
  })

  const countries = [
    { code: 'CA', name: 'Canada', format: '+1 (XXX) XXX-XXXX' },
    { code: 'US', name: 'États-Unis', format: '+1 (XXX) XXX-XXXX' },
    { code: 'FR', name: 'France', format: '+33 X XX XX XX XX' },
    { code: 'BE', name: 'Belgique', format: '+32 XXX XX XX XX' },
    { code: 'CH', name: 'Suisse', format: '+41 XX XXX XX XX' },
    { code: 'MX', name: 'Mexique', format: '+52 XXX XXX XXXX' },
    { code: 'BR', name: 'Brésil', format: '+55 (XX) XXXXX-XXXX' }
  ]

  const formatPhoneNumber = (phone: string, countryCode: string) => {
    const cleaned = phone.replace(/\D/g, '')
    
    switch (countryCode) {
      case 'CA':
      case 'US':
        if (cleaned.length >= 10) {
          return `+1 (${cleaned.slice(-10, -7)}) ${cleaned.slice(-7, -4)}-${cleaned.slice(-4)}`
        }
        break
      case 'FR':
        if (cleaned.length >= 9) {
          return `+33 ${cleaned.slice(-9, -8)} ${cleaned.slice(-8, -6)} ${cleaned.slice(-6, -4)} ${cleaned.slice(-4, -2)} ${cleaned.slice(-2)}`
        }
        break
      case 'BE':
        if (cleaned.length >= 8) {
          return `+32 ${cleaned.slice(-8, -5)} ${cleaned.slice(-5, -3)} ${cleaned.slice(-3, -1)} ${cleaned.slice(-1)}`
        }
        break
      case 'CH':
        if (cleaned.length >= 9) {
          return `+41 ${cleaned.slice(-9, -7)} ${cleaned.slice(-7, -4)} ${cleaned.slice(-4, -2)} ${cleaned.slice(-2)}`
        }
        break
      case 'MX':
        if (cleaned.length >= 10) {
          return `+52 ${cleaned.slice(-10, -7)} ${cleaned.slice(-7, -4)} ${cleaned.slice(-4)}`
        }
        break
      case 'BR':
        if (cleaned.length >= 10) {
          return `+55 (${cleaned.slice(-10, -8)}) ${cleaned.slice(-8, -3)}-${cleaned.slice(-3)}`
        }
        break
    }
    return phone
  }

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value, formData.country)
    setFormData(prev => ({ ...prev, phone: formatted }))
  }

  const handleCountryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newCountry = e.target.value
    setFormData(prev => ({ 
      ...prev, 
      country: newCountry,
      phone: formatPhoneNumber(prev.phone, newCountry)
    }))
  }

  const getCurrentCountryFormat = () => {
    return countries.find(c => c.code === formData.country)?.format || ''
  }

  return (
    <div className="space-y-4 max-h-[70vh] overflow-y-auto">
      {/* Informations personnelles */}
      <div className="border-b border-gray-200 pb-4">
        <h3 className="text-lg font-medium text-gray-900 mb-3">Informations personnelles</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Prénom *</label>
            <input
              type="text"
              value={formData.firstName}
              onChange={(e) => setFormData(prev => ({ ...prev, firstName: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Nom de famille *</label>
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
          <label className="block text-sm font-medium text-gray-700 mb-2">Profil LinkedIn personnel</label>
          <input
            type="url"
            value={formData.linkedinProfile}
            onChange={(e) => setFormData(prev => ({ ...prev, linkedinProfile: e.target.value }))}
            placeholder="https://linkedin.com/in/votre-profil"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Informations de contact */}
      <div className="border-b border-gray-200 pb-4">
        <h3 className="text-lg font-medium text-gray-900 mb-3">Contact</h3>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Email *</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Pays *</label>
          <select 
            value={formData.country}
            onChange={handleCountryChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
            {countries.map(country => (
              <option key={country.code} value={country.code}>
                {country.name}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Téléphone
            <span className="text-xs text-gray-500 ml-2">Format: {getCurrentCountryFormat()}</span>
          </label>
          <input
            type="tel"
            value={formData.phone}
            onChange={handlePhoneChange}
            placeholder={getCurrentCountryFormat()}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Informations entreprise */}
      <div className="pb-4">
        <h3 className="text-lg font-medium text-gray-900 mb-3">Entreprise</h3>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Nom de l'entreprise</label>
          <input
            type="text"
            value={formData.companyName}
            onChange={(e) => setFormData(prev => ({ ...prev, companyName: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Site web de l'entreprise</label>
          <input
            type="url"
            value={formData.companyWebsite}
            onChange={(e) => setFormData(prev => ({ ...prev, companyWebsite: e.target.value }))}
            placeholder="https://www.exemple.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Page LinkedIn de l'entreprise</label>
          <input
            type="url"
            value={formData.linkedinCorporate}
            onChange={(e) => setFormData(prev => ({ ...prev, linkedinCorporate: e.target.value }))}
            placeholder="https://linkedin.com/company/votre-entreprise"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button
          onClick={onClose}
          className="px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          Annuler
        </button>
        <button
          onClick={() => {
            console.log('Sauvegarde des informations utilisateur:', formData)
            // Ici vous pouvez ajouter la logique de sauvegarde
            onClose()
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Sauvegarder
        </button>
      </div>
    </div>
  )
}

const AccountModal = ({ user, onClose }: { user: any, onClose: () => void }) => {
  // Simuler le forfait utilisateur (à remplacer par les vraies données)
  const currentPlan = user?.plan || 'essentiel'
  
  const plans = {
    essentiel: {
      name: 'Essentiel',
      price: 'Gratuit',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      features: [
        '50 questions par mois',
        'Accès aux documents publics',
        'Support par email',
        'Interface web'
      ]
    },
    pro: {
      name: 'Pro',
      price: '29$ / mois',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      features: [
        'Questions illimitées',
        'Accès documents confidentiels',
        'Support prioritaire',
        'Interface web + mobile',
        'Analytics avancées'
      ]
    },
    entreprise: {
      name: 'Entreprise',
      price: 'Sur mesure',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
      features: [
        'Tout du forfait Pro',
        'Documents privés personnalisés',
        'Support téléphonique dédié',
        'Intégrations API',
        'Formation équipe',
        'SLA garanti'
      ]
    }
  }

  const userPlan = plans[currentPlan as keyof typeof plans]

  return (
    <div className="space-y-6">
      {/* Forfait actuel */}
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Mon forfait actuel</h3>
        <div className={`inline-flex items-center px-4 py-2 rounded-full ${userPlan.bgColor} ${userPlan.borderColor} border`}>
          <span className={`font-medium ${userPlan.color}`}>{userPlan.name}</span>
          <span className="mx-2 text-gray-400">•</span>
          <span className={`font-bold ${userPlan.color}`}>{userPlan.price}</span>
        </div>
      </div>

      {/* Fonctionnalités du forfait actuel */}
      <div className={`p-4 rounded-lg ${userPlan.bgColor} ${userPlan.borderColor} border`}>
        <h4 className="font-medium text-gray-900 mb-3">Fonctionnalités incluses :</h4>
        <ul className="space-y-2">
          {userPlan.features.map((feature, index) => (
            <li key={index} className="flex items-center text-sm text-gray-700">
              <span className="text-green-500 mr-2">✓</span>
              {feature}
            </li>
          ))}
        </ul>
      </div>

      {/* Options d'upgrade */}
      {currentPlan !== 'entreprise' && (
        <div className="space-y-3">
          <h4 className="font-medium text-gray-900">Mettre à niveau</h4>
          
          {currentPlan === 'essentiel' && (
            <div className="p-4 border border-blue-200 rounded-lg bg-blue-50">
              <div className="flex justify-between items-center">
                <div>
                  <h5 className="font-medium text-blue-900">Forfait Pro</h5>
                  <p className="text-sm text-blue-700">Questions illimitées + fonctionnalités avancées</p>
                </div>
                <button
                  onClick={() => {
                    console.log('Upgrade vers Pro demandé')
                    // Logique d'upgrade à implémenter
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
                >
                  Passer au Pro
                </button>
              </div>
            </div>
          )}

          <div className="p-4 border border-purple-200 rounded-lg bg-purple-50">
            <div className="flex justify-between items-center">
              <div>
                <h5 className="font-medium text-purple-900">Forfait Entreprise</h5>
                <p className="text-sm text-purple-700">Solution personnalisée pour votre organisation</p>
              </div>
              <button
                onClick={() => {
                  console.log('Contact commercial demandé')
                  window.open('mailto:sales@intelia.com?subject=Demande forfait Entreprise', '_blank')
                }}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors text-sm"
              >
                Nous contacter
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Utilisation du mois (simulation) */}
      <div className="p-4 border border-gray-200 rounded-lg bg-gray-50">
        <h4 className="font-medium text-gray-900 mb-2">Utilisation ce mois-ci</h4>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Questions posées :</span>
          <span className="font-medium text-gray-900">
            {currentPlan === 'essentiel' ? '23 / 50' : 'Illimité'}
          </span>
        </div>
        {currentPlan === 'essentiel' && (
          <div className="mt-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full" style={{ width: '46%' }}></div>
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-end pt-4">
        <button
          onClick={onClose}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Fermer
        </button>
      </div>
    </div>
  )
}

const ContactModal = ({ onClose }: { onClose: () => void }) => {
  return (
    <div className="space-y-4">
      {/* Chat with us */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">Discuter avec nous</h3>
          <p className="text-sm text-gray-600 mb-2">
            Contactez notre équipe de support via le chat intégré.
          </p>
          <button 
            onClick={() => {
              console.log('Chat support ouvert')
              onClose()
            }}
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            Contacter le support Intelia
          </button>
        </div>
      </div>

      {/* Call Us */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">Nous appeler</h3>
          <p className="text-sm text-gray-600 mb-2">
            Si vous ne trouvez pas de solution, appelez-nous pour parler directement avec notre équipe.
          </p>
          <a 
            href="tel:+18666666221"
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            +1 (866) 666 6221
          </a>
        </div>
      </div>

      {/* Email Us */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">Nous écrire</h3>
          <p className="text-sm text-gray-600 mb-2">
            Envoyez-nous un message détaillé et nous vous répondrons rapidement.
          </p>
          <a 
            href="mailto:support@intelia.com"
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            support@intelia.com
          </a>
        </div>
      </div>

      {/* Visit our website */}
      <div className="flex items-start space-x-4 p-3 hover:bg-gray-50 rounded-lg transition-colors">
        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3s-4.5 4.03-4.5 9 2.015 9 4.5 9zm0 0c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3s4.5 4.03 4.5 9-2.015 9-4.5 9z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">Visiter notre site web</h3>
          <p className="text-sm text-gray-600 mb-2">
            Pour en savoir plus sur nous et la plateforme Intelia, visitez notre site.
          </p>
          <a 
            href="https://www.intelia.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            www.intelia.com
          </a>
        </div>
      </div>

      <div className="flex justify-end pt-3">
        <button
          onClick={onClose}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Fermer
        </button>
      </div>
    </div>
  )
}

// ==================== MENU HISTORIQUE ====================
const HistoryMenu = () => {
  const [isOpen, setIsOpen] = useState(false)
  const { conversations, deleteConversation, clearAllConversations } = useChatStore()

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        title="Historique des conversations"
      >
        <EllipsisVerticalIcon className="w-5 h-5" />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          <div className="absolute left-0 top-full mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-96 overflow-y-auto">
            <div className="p-4 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">Historique</h3>
                <button
                  onClick={() => {
                    clearAllConversations()
                    setIsOpen(false)
                  }}
                  className="text-red-600 hover:text-red-700 text-sm"
                >
                  Tout effacer
                </button>
              </div>
            </div>
            
            <div className="max-h-64 overflow-y-auto">
              {conversations.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  Aucune conversation précédente
                </div>
              ) : (
                conversations.map((conv) => (
                  <div key={conv.id} className="p-3 hover:bg-gray-50 border-b border-gray-50 last:border-b-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {conv.title}
                        </h4>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(conv.updated_at).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                      <button
                        onClick={() => deleteConversation(conv.id)}
                        className="ml-2 p-1 text-gray-400 hover:text-red-600 transition-colors"
                        title="Supprimer"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ==================== MENU UTILISATEUR ====================
const UserMenuButton = () => {
  const { user, logout } = useAuthStore()
  const [isOpen, setIsOpen] = useState(false)
  const [showUserInfoModal, setShowUserInfoModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)
  const [showAccountModal, setShowAccountModal] = useState(false)

  const userName = user?.name || user?.email || 'Utilisateur'
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

  const handleContactClick = () => {
    setIsOpen(false)
    setShowContactModal(true)
  }

  const handleUserInfoClick = () => {
    setIsOpen(false)
    setShowUserInfoModal(true)
  }

  const handleAccountClick = () => {
    setIsOpen(false)
    setShowAccountModal(true)
  }

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors"
        >
          <span className="text-white text-xs font-medium">{userInitials}</span>
        </button>

        {isOpen && (
          <>
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setIsOpen(false)}
            />
            
            <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
                <p className="text-xs text-gray-400 mt-1">
                  Membre depuis {new Date(user?.created_at || '').toLocaleDateString('fr-FR')}
                </p>
              </div>

              <button
                onClick={handleAccountClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z" />
                </svg>
                <span>Mon compte</span>
              </button>

              <button
                onClick={handleUserInfoClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
                <span>Mes informations</span>
              </button>

              <button
                onClick={handleContactClick}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                </svg>
                <span>Nous joindre</span>
              </button>

              <button
                onClick={() => window.open('https://intelia.com/privacy-policy/', '_blank')}
                className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875v12.75c0 .621.504 1.125 1.125 1.125h2.25" />
                </svg>
                <span>Mentions légales</span>
              </button>
              
              <div className="border-t border-gray-100 mt-2 pt-2">
                <button
                  onClick={() => {
                    logout()
                    setIsOpen(false)
                  }}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
                  </svg>
                  <span>Déconnexion</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modals */}
      <Modal
        isOpen={showAccountModal}
        onClose={() => setShowAccountModal(false)}
        title="Mon compte"
      >
        <AccountModal user={user} onClose={() => setShowAccountModal(false)} />
      </Modal>

      <Modal
        isOpen={showUserInfoModal}
        onClose={() => setShowUserInfoModal(false)}
        title="Mes informations"
      >
        <UserInfoModal user={user} onClose={() => setShowUserInfoModal(false)} />
      </Modal>

      <Modal
        isOpen={showContactModal}
        onClose={() => setShowContactModal(false)}
        title="Nous joindre"
      >
        <ContactModal onClose={() => setShowContactModal(false)} />
      </Modal>
    </>
  )
}

// ==================== COMPOSANT PRINCIPAL ====================
export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [systemStatus, setSystemStatus] = useState({
    rag: false,
    supabase: false,
    overall: false
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { user } = useAuthStore()

  // Vérifier le statut des services
  const checkSystemStatus = async () => {
    try {
      let ragStatus = false
      let supabaseStatus = true // Simulé car on utilise des stores simulés
      let networkStatus = true

      // Test 1: API RAG - Test plus robuste
      try {
        const ragResponse = await fetch('https://expert-app-cngws.ondigitalocean.app/api/health', {
          method: 'GET',
          signal: AbortSignal.timeout(5000)
        })
        
        if (ragResponse.ok) {
          // Vérifier si la réponse contient des infos sur le fallback
          try {
            const healthData = await ragResponse.json()
            console.log('🔍 Health check RAG:', healthData)
            
            // Vérifier s'il y a un indicateur de fallback dans la réponse
            ragStatus = healthData.status === 'healthy' && !healthData.fallback_mode
            
            if (healthData.fallback_mode) {
              console.warn('⚠️ RAG en mode fallback détecté')
            }
          } catch (jsonError) {
            // Si pas de JSON, considérer comme OK si le status HTTP est 200
            ragStatus = true
          }
        } else {
          ragStatus = false
        }
      } catch (error) {
        console.warn('⚠️ RAG API non accessible:', error)
        ragStatus = false
      }

      // Test 2: Connectivité réseau générale
      try {
        await fetch('https://www.google.com/favicon.ico', {
          method: 'HEAD',
          mode: 'no-cors',
          signal: AbortSignal.timeout(3000)
        })
        networkStatus = true
      } catch (error) {
        console.warn('⚠️ Problème de connectivité réseau:', error)
        networkStatus = false
      }

      // Test 3: Supabase simulé (toujours true pour le moment)
      // Dans un vrai projet, vous testeriez la connexion Supabase ici

      // Statut global : tous les services doivent être opérationnels ET pas en fallback
      const overall = ragStatus && supabaseStatus && networkStatus

      setSystemStatus({
        rag: ragStatus,
        supabase: supabaseStatus,
        overall
      })

      // Log détaillé pour debug
      console.log('🔍 Status check détaillé:', {
        rag: ragStatus ? '✅ Opérationnel' : '❌ Problème/Fallback',
        supabase: supabaseStatus ? '✅' : '❌',
        network: networkStatus ? '✅' : '❌',
        overall: overall ? '🟢 SYSTÈME OK' : '🔴 PROBLÈME DÉTECTÉ'
      })

    } catch (error) {
      console.error('❌ Erreur vérification statut:', error)
      setSystemStatus({
        rag: false,
        supabase: true,
        overall: false
      })
    }
  }

  // Scroll automatique
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Message de bienvenue + vérification statut
  useEffect(() => {
    const initializeChat = async () => {
      await checkSystemStatus()

      const welcomeMessage: Message = {
        id: '1',
        content: "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
        isUser: false,
        timestamp: new Date()
      }
      setMessages([welcomeMessage])
    }

    initializeChat()
    
    // Vérifier le statut toutes les 30 secondes
    const statusInterval = setInterval(checkSystemStatus, 30000)
    
    return () => clearInterval(statusInterval)
  }, [])

  // Générer réponse RAG
  const generateAIResponse = async (question: string): Promise<string> => {
    // Définir l'URL en dehors du try/catch pour qu'elle soit accessible partout
    const apiUrl = 'https://expert-app-cngws.ondigitalocean.app/api/api/v1/expert/ask-public'
    
    try {
      console.log('🤖 Envoi question au RAG Intelia:', question)
      console.log('📡 URL API corrigée:', apiUrl)
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          text: question.trim(),
          language: user?.language || 'fr',
          speed_mode: 'balanced'
        })
      })

      console.log('📊 Statut réponse API:', response.status, response.statusText)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Erreur API détaillée:', errorText)
        
        // Mettre à jour le statut pour indiquer un problème RAG
        setSystemStatus(prev => ({
          ...prev,
          rag: false,
          overall: false
        }))
        
        throw new Error(`Erreur API: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('✅ Réponse RAG reçue:', data)
      
      // Vérifier si la réponse indique un mode fallback
      if (data.fallback_used || data.is_fallback || data.mode === 'fallback') {
        console.warn('⚠️ Réponse générée en mode fallback')
        setSystemStatus(prev => ({
          ...prev,
          rag: false, // Marquer comme problème si fallback utilisé
          overall: false
        }))
      } else {
        // Marquer comme OK si réponse normale
        setSystemStatus(prev => ({
          ...prev,
          rag: true,
          overall: true && prev.supabase // Garder l'état des autres services
        }))
      }
      
      if (data.response || data.answer || data.message) {
        return data.response || data.answer || data.message
      } else {
        console.warn('⚠️ Structure de réponse inattendue:', data)
        return 'Le système RAG a répondu mais dans un format inattendu.'
      }
      
    } catch (error: any) {
      console.error('❌ Erreur lors de l\'appel au RAG:', error)
      
      // Mettre à jour le statut pour indiquer un problème
      setSystemStatus(prev => ({
        ...prev,
        rag: false,
        overall: false
      }))
      
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        return `Erreur de connexion au serveur RAG. 

🔧 **Vérifications suggérées :**
- Le serveur expert-app-cngws.ondigitalocean.app est-il accessible ?
- Y a-t-il des problèmes de CORS ?
- Le service est-il en cours d'exécution ?

**Erreur technique :** ${error.message}`
      }
      
      return `Erreur technique avec l'API : ${error.message}

**URL testée :** ${apiUrl}
**Type d'erreur :** ${error.name}

Consultez la console développeur (F12) pour plus de détails.`
    }
  }

  // Envoi message
  const handleSendMessage = async (text: string = inputMessage) => {
    if (!text.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text.trim(),
      isUser: true,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      const response = await generateAIResponse(text.trim())
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response,
        isUser: false,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      console.error('❌ Error generating response:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "Désolé, je rencontre un problème technique. Veuillez réessayer dans quelques instants.",
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  // Gestion feedback
  const handleFeedback = (messageId: string, feedback: 'positive' | 'negative') => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, feedback } : msg
    ))
    console.log(`📊 Feedback ${feedback} pour le message ${messageId}`)
  }

  const handleNewConversation = () => {
    setMessages([{
      id: '1',
      content: "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
      isUser: false,
      timestamp: new Date()
    }])
  }

  const getCurrentDate = () => {
    return new Date().toLocaleDateString('fr-FR', { 
      day: 'numeric', 
      month: 'long', 
      year: 'numeric' 
    })
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 px-4 py-3">
        <div className="flex items-center justify-between">
          {/* Boutons à gauche */}
          <div className="flex items-center space-x-2">
            <HistoryMenu />
            <button
              onClick={handleNewConversation}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title="Nouvelle conversation"
            >
              <PlusIcon className="w-5 h-5" />
            </button>
          </div>

          {/* Titre centré avec logo */}
          <div className="flex-1 flex justify-center items-center space-x-3">
            <InteliaLogo className="w-8 h-8" />
            <div className="text-center">
              <h1 className="text-lg font-medium text-gray-900">Intelia Expert</h1>
            </div>
          </div>
          
          {/* Avatar utilisateur à droite */}
          <div className="flex items-center">
            <UserMenuButton />
          </div>
        </div>
      </header>

      {/* Zone de messages */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Date */}
            {messages.length > 0 && (
              <div className="text-center">
                <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                  {getCurrentDate()}
                </span>
              </div>
            )}

            {messages.map((message, index) => (
              <div key={message.id}>
                <div className={`flex items-start space-x-3 ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                  {!message.isUser && (
                    <div className="relative">
                      <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                    </div>
                  )}
                  
                  <div className="max-w-xs lg:max-w-2xl">
                    <div className={`px-4 py-3 rounded-2xl ${message.isUser ? 'bg-blue-600 text-white ml-auto' : 'bg-white border border-gray-200 text-gray-900'}`}>
                      <p className="whitespace-pre-wrap leading-relaxed text-sm">
                        {message.content}
                      </p>
                    </div>
                    
                    {/* Boutons de feedback */}
                    {!message.isUser && index > 0 && (
                      <div className="flex items-center space-x-2 mt-2 ml-2">
                        <button
                          onClick={() => handleFeedback(message.id, 'positive')}
                          className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'positive' ? 'text-green-600 bg-green-50' : 'text-gray-400'}`}
                          title="Réponse utile"
                        >
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleFeedback(message.id, 'negative')}
                          className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${message.feedback === 'negative' ? 'text-red-600 bg-red-50' : 'text-gray-400'}`}
                          title="Réponse non utile"
                        >
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.106-1.79l-.05-.025A4 4 0 0011.057 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </div>

                  {message.isUser && (
                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                      <UserIcon className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Indicateur de frappe */}
            {isLoading && (
              <div className="flex items-start space-x-3">
                <div className="relative">
                  <InteliaLogo className="w-8 h-8 flex-shrink-0 mt-1" />
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Zone de saisie */}
        <div className="px-4 py-4 bg-white border-t border-gray-100">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center space-x-3">
              <button
                type="button"
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Enregistrement vocal"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                </svg>
              </button>
              
              <div className="flex-1">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSendMessage()
                    }
                  }}
                  placeholder="Bonjour ! Comment puis-je vous aider aujourd'hui ?"
                  className="w-full px-4 py-3 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm"
                  disabled={isLoading}
                />
              </div>
              
              <button
                onClick={() => handleSendMessage()}
                disabled={isLoading || !inputMessage.trim()}
                className="flex-shrink-0 p-2 text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors"
              >
                <PaperAirplaneIcon />
              </button>
            </div>
            
            {/* Indicateur de statut système simplifié */}
            <div className="mt-2 text-center">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full text-xs bg-gray-100">
                <div className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full ${systemStatus.overall ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span className={systemStatus.overall ? 'text-green-700' : 'text-red-700'}>
                    {systemStatus.overall ? 'Système opérationnel' : 'Problème détecté'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}