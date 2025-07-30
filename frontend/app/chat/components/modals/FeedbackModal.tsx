import React, { useState } from 'react'

interface FeedbackModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (feedback: 'positive' | 'negative', comment?: string) => Promise<void>
  feedbackType: 'positive' | 'negative'
  isSubmitting?: boolean
}

export const FeedbackModal = ({ 
  isOpen, 
  onClose, 
  onSubmit, 
  feedbackType, 
  isSubmitting = false 
}: FeedbackModalProps) => {
  const [comment, setComment] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  if (!isOpen) return null

  const handleSubmit = async () => {
    setIsLoading(true)
    try {
      await onSubmit(feedbackType, comment.trim() || undefined)
      setComment('')
      onClose() // ✅ Fermer la modal après succès
    } catch (error) {
      console.error('Erreur envoi feedback:', error)
      // ✅ CORRECTION: Fermer la modal même en cas d'erreur
      setComment('')
      onClose()
      // Ne pas afficher d'alert ici, laisser la fonction parent gérer
    } finally {
      setIsLoading(false)
    }
  }

  const handleCancel = () => {
    setComment('')
    onClose()
  }

  const isPositive = feedbackType === 'positive'
  const title = isPositive ? 'Merci pour votre feedback positif !' : 'Aidez-nous à améliorer'
  const placeholder = isPositive 
    ? 'Qu\'avez-vous apprécié dans cette réponse ?'
    : 'Dans quelle mesure cette réponse était-elle satisfaisante ?'

  return (
    <>
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-50" 
        onClick={handleCancel}
      />
      
      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div 
          className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-6 pb-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                {isPositive ? (
                  <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                    {/* ✅ ICÔNE THUMBS UP CORRIGÉE */}
                    <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.5c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 012.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V3a.75.75 0 01.75-.75A2.25 2.25 0 0116.5 4.5c0 1.152-.26 2.243-.723 3.218-.266.558-.641 1.05-1.085 1.441-.807.71-1.96 1.398-3.092 1.75a4.5 4.5 0 00-2.592 1.33c-.284.29-.568.606-.725.936-.12.253-.18.526-.18.801 0 .546.146 1.069.378 1.526.209.417.49.777.84 1.047.35.27.747.447 1.177.447h.462c1.097 0 2.137.462 2.86 1.273a3.73 3.73 0 011.14 2.677v.462a.75.75 0 01-.75.75h-3.75a.75.75 0 01-.75-.75v-.462c0-.552-.11-1.098-.322-1.598-.202-.477-.497-.9-.878-1.235a3.75 3.75 0 01-1.28-2.83c0-.552.11-1.098.322-1.598.202-.477.497-.9.878-1.235z" />
                    </svg>
                  </div>
                ) : (
                  <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                    {/* ✅ ICÔNE THUMBS DOWN CORRIGÉE */}
                    <svg className="w-6 h-6 text-orange-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.498 15.25H4.372c-1.026 0-1.945-.694-2.054-1.715a12.137 12.137 0 01-.068-1.285c0-2.848.992-5.464 2.649-7.521C5.287 4.247 5.886 4 6.504 4h4.016a4.5 4.5 0 011.423.23l3.114 1.04a4.5 4.5 0 001.423.23h1.294M7.498 15.25c.618 0 .991.724.725 1.282A7.471 7.471 0 007.5 19.75 2.25 2.25 0 009.75 22a.75.75 0 00.75-.75v-.633c0-.573.11-1.14.322-1.672.304-.76.93-1.33 1.653-1.715a9.04 9.04 0 002.86-2.4c.498-.634 1.226-1.08 2.032-1.08h.384m-10.253 1.5H9.7m8.075-9.75c.01.05.027.1.05.148.593 1.2.925 2.55.925 3.977 0 1.487-.36 2.89-.999 4.125m.023-8.25c-.076-.365.183-.75.575-.75h.908c.889 0 1.713.518 1.972 1.368.339 1.11.521 2.287.521 3.507 0 1.553-.295 3.036-.831 4.398C20.613 14.547 19.833 15 19.05 15h-1.613m-6.844-13.5c.76.15 1.463.423 2.068.827.193.122.4.248.6.383.774.519 1.466 1.187 2.031 1.966a10.462 10.462 0 011.244 3.562c.06.369.09.742.09 1.115-.013 1.05-.313 2.047-.78 2.917-.512.95-1.234 1.793-2.137 2.453a1.507 1.507 0 01-1.556.008c-.784-.57-1.227-1.432-1.227-2.332v-.84c0-.769-.263-1.514-.74-2.101-.195-.24-.4-.458-.615-.652-.711-.642-1.518-1.113-2.384-1.399-.867-.286-1.77-.442-2.723-.442H2.255a.75.75 0 01-.75-.75 2.25 2.25 0 012.25-2.25Z" />
                    </svg>
                  </div>
                )}
                <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
              </div>
              
              <button
                onClick={handleCancel}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                disabled={isLoading}
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Description */}
            <p className="text-sm text-gray-600 mb-4">
              Veuillez fournir des détails : (facultatif)
            </p>

            {/* Textarea de commentaire */}
            <div className="mb-4">
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={placeholder}
                rows={4}
                maxLength={500}
                className="w-full px-4 py-3 border-2 border-blue-200 rounded-xl focus:border-blue-500 focus:ring-0 outline-none resize-none text-sm placeholder-gray-400 transition-colors"
                disabled={isLoading}
              />
              <div className="flex justify-between items-center mt-2">
                <div className="text-xs text-gray-400">
                  {comment.length}/500 caractères
                </div>
                {comment.length > 450 && (
                  <div className="text-xs text-orange-500">
                    Limite bientôt atteinte
                  </div>
                )}
              </div>
            </div>

            {/* Note de confidentialité */}
            <div className="mb-6">
              <p className="text-xs text-gray-500 leading-relaxed">
                En soumettant ce rapport, vous envoyez l'intégralité de la conversation actuelle à Intelia pour nous aider à améliorer nos modèles.{' '}
                <button 
                  type="button"
                  className="text-blue-600 hover:text-blue-700 underline font-medium"
                  onClick={() => window.open('https://intelia.com/privacy-policy/', '_blank')}
                >
                  En savoir plus
                </button>
              </p>
            </div>
          </div>

          {/* Footer avec boutons */}
          <div className="px-6 py-4 bg-gray-50 rounded-b-2xl">
            <div className="flex justify-end space-x-3">
              <button
                onClick={handleCancel}
                disabled={isLoading}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Annuler
              </button>
              
              <button
                onClick={handleSubmit}
                disabled={isLoading}
                className="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 min-w-[100px] justify-center"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Envoi...</span>
                  </>
                ) : (
                  <span>Envoyer</span>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}