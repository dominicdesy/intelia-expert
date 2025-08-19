'use client'

import { useState, useEffect } from 'react'
import { useChatStore } from '@/lib/stores/chat'

// SOLUTION: Utiliser les types du store directement
type StoreConversation = {
  id: string
  title: string
  messages: Array<{
    id: string
    content: string
    role: 'user' | 'assistant'
    timestamp: string
    feedback?: 'positive' | 'negative' | null
    sources?: Array<{ title: string; url?: string }>
    metadata?: { response_time?: number; model_used?: string }
  }>
  created_at: string
  updated_at: string
}

// Icônes SVG
const ChatBubbleLeftRightIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.96 2.193-.34.027-.68.052-1.021.077-1.963.144-3.926.288-5.889.288-.427 0-.854-.003-1.28-.01V12.01c0-.3.12-.586.332-.796l5.25-5.25a2.25 2.25 0 113.182 3.182L14.5 15.5" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 15.488c-.884-.284-1.5-1.128-1.5-2.097V9.105c0-1.136.847-2.1 1.96-2.193.34-.027.68-.052 1.021-.077 1.963-.144 3.926-.288 5.889-.288.427 0 .854.003 1.28.01V12.01c0 .3-.12.586-.332.796l-5.25 5.25a2.25 2.25 0 11-3.182-3.182L9.5 8.5" />
  </svg>
)

const TrashIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
  </svg>
)

const XMarkIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
)

interface ConversationSidebarProps {
  isOpen: boolean
  onClose: () => void
}

export default function ConversationSidebar({ isOpen, onClose }: ConversationSidebarProps) {
  const { 
    conversations, 
    currentConversation, 
    loadConversations,
    loadConversation,
    deleteConversation,
    clearAllConversations,
    createConversation
  } = useChatStore()

  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null)
  const [showClearAllConfirm, setShowClearAllConfirm] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  // Charger les conversations au montage
  useEffect(() => {
    if (isOpen) {
      loadConversations()
    }
  }, [isOpen, loadConversations])

  // Gérer la sélection d'une conversation
  const handleSelectConversation = async (conversationId: string) => {
    if (isLoading) return
    
    try {
      setIsLoading(true)
      await loadConversation(conversationId)
      onClose()
    } catch (error) {
      console.error('Erreur lors du chargement de la conversation:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Gérer la suppression d'une conversation
  const handleDeleteConversation = async (conversationId: string) => {
    if (isLoading) return

    try {
      setIsLoading(true)
      await deleteConversation(conversationId)
      setShowDeleteConfirm(null)
    } catch (error) {
      console.error('Erreur lors de la suppression:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Gérer la suppression de toutes les conversations
  const handleClearAll = async () => {
    if (isLoading) return

    try {
      setIsLoading(true)
      await clearAllConversations()
      setShowClearAllConfirm(false)
    } catch (error) {
      console.error('Erreur lors de la suppression complète:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Créer une nouvelle conversation
  const handleNewConversation = () => {
    if (isLoading) return
    createConversation()
    onClose()
  }

  // Formater la date de manière lisible
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString)
      const now = new Date()
      const diffInMilliseconds = now.getTime() - date.getTime()
      const diffInDays = Math.floor(diffInMilliseconds / (1000 * 60 * 60 * 24))

      if (diffInDays === 0) {
        return "Aujourd'hui"
      } else if (diffInDays === 1) {
        return "Hier"
      } else if (diffInDays < 7) {
        return `Il y a ${diffInDays} jour${diffInDays > 1 ? 's' : ''}`
      } else if (diffInDays < 30) {
        const weeks = Math.floor(diffInDays / 7)
        return `Il y a ${weeks} semaine${weeks > 1 ? 's' : ''}`
      } else {
        return date.toLocaleDateString('fr-FR', { 
          day: 'numeric', 
          month: 'short',
          year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        })
      }
    } catch (error) {
      console.error('Erreur de formatage de date:', error)
      return 'Date inconnue'
    }
  }

  // Générer un aperçu de la conversation - TYPES ALIGNÉS
  const getConversationPreview = (conversation: StoreConversation): string => {
    try {
      // Vérifier si la conversation a des messages
      if (!conversation.messages || conversation.messages.length === 0) {
        return "Nouvelle conversation"
      }
      
      // Chercher le premier message utilisateur
      const firstUserMessage = conversation.messages.find(message => 
        message && message.role === 'user' && message.content
      )
      
      if (firstUserMessage && firstUserMessage.content) {
        const content = firstUserMessage.content.trim()
        if (content.length > 50) {
          return content.substring(0, 50) + "..."
        }
        return content
      }
      
      return conversation.title || "Conversation sans titre"
    } catch (error) {
      console.error('Erreur lors de la génération de l\'aperçu:', error)
      return "Conversation"
    }
  }

  // Compter les messages de manière sécurisée - TYPES ALIGNÉS
  const getMessageCount = (conversation: StoreConversation): number => {
    try {
      return conversation.messages?.length || 0
    } catch (error) {
      console.error('Erreur lors du comptage des messages:', error)
      return 0
    }
  }

  // Ne pas afficher si fermé
  if (!isOpen) return null

  return (
    <>
      {/* Overlay pour mobile */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Conteneur principal de la sidebar */}
      <div 
        className={`fixed left-0 top-0 h-full w-80 bg-white shadow-lg z-50 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:relative lg:translate-x-0`}
        role="complementary"
        aria-label="Sidebar des conversations"
      >
        
        {/* En-tête */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900">
            Conversations
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors lg:hidden"
            aria-label="Fermer la sidebar"
          >
            <XMarkIcon className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Actions principales */}
        <div className="p-4 border-b border-gray-100">
          <button
            onClick={handleNewConversation}
            disabled={isLoading}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg transition-colors font-medium"
            aria-label="Créer une nouvelle conversation"
          >
            <ChatBubbleLeftRightIcon className="w-4 h-4" />
            <span>Nouvelle conversation</span>
          </button>
        </div>

        {/* Liste des conversations */}
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              <ChatBubbleLeftRightIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <h3 className="text-sm font-medium text-gray-900 mb-1">
                Aucune conversation
              </h3>
              <p className="text-xs text-gray-500">
                Commencez par poser une question à l'expert !
              </p>
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {conversations.map((conversation) => {
                const isCurrentConversation = currentConversation?.id === conversation.id
                const messageCount = getMessageCount(conversation)
                const preview = getConversationPreview(conversation)
                const formattedDate = formatDate(conversation.updated_at)

                return (
                  <div
                    key={conversation.id}
                    className={`group relative rounded-lg border transition-all duration-200 ${
                      isCurrentConversation
                        ? 'bg-blue-50 border-blue-200 shadow-sm'
                        : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                    }`}
                  >
                    {/* Bouton principal de la conversation */}
                    <button
                      onClick={() => handleSelectConversation(conversation.id)}
                      disabled={isLoading}
                      className="w-full p-3 text-left disabled:opacity-50"
                      aria-label={`Ouvrir la conversation: ${preview}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0 pr-2">
                          <h3 className={`text-sm font-medium truncate ${
                            isCurrentConversation ? 'text-blue-900' : 'text-gray-900'
                          }`}>
                            {preview}
                          </h3>
                          <div className="flex items-center justify-between mt-2">
                            <span className="text-xs text-gray-500">
                              {formattedDate}
                            </span>
                            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
                              {messageCount} msg{messageCount > 1 ? 's' : ''}
                            </span>
                          </div>
                        </div>
                      </div>
                    </button>

                    {/* Bouton de suppression */}
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setShowDeleteConfirm(
                            showDeleteConfirm === conversation.id ? null : conversation.id
                          )
                        }}
                        disabled={isLoading}
                        className="p-1.5 hover:bg-red-100 rounded-md text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                        aria-label="Supprimer cette conversation"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Modal de confirmation de suppression */}
                    {showDeleteConfirm === conversation.id && (
                      <div className="absolute inset-0 bg-white border border-red-200 rounded-lg p-3 z-10 shadow-lg">
                        <h4 className="text-sm font-medium text-gray-900 mb-2">
                          Supprimer cette conversation ?
                        </h4>
                        <p className="text-xs text-gray-600 mb-3">
                          Cette action est irréversible.
                        </p>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => setShowDeleteConfirm(null)}
                            disabled={isLoading}
                            className="flex-1 px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors disabled:opacity-50"
                          >
                            Annuler
                          </button>
                          <button
                            onClick={() => handleDeleteConversation(conversation.id)}
                            disabled={isLoading}
                            className="flex-1 px-3 py-1.5 text-xs bg-red-600 hover:bg-red-700 text-white rounded transition-colors disabled:opacity-50"
                          >
                            {isLoading ? 'Suppression...' : 'Supprimer'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer avec action de nettoyage global */}
        {conversations.length > 0 && (
          <div className="p-4 border-t border-gray-200 bg-gray-50">
            {!showClearAllConfirm ? (
              <button
                onClick={() => setShowClearAllConfirm(true)}
                disabled={isLoading}
                className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 border border-red-200 rounded-lg transition-colors disabled:opacity-50"
                aria-label="Effacer tout l'historique des conversations"
              >
                <TrashIcon className="w-4 h-4" />
                <span>Effacer tout l'historique</span>
              </button>
            ) : (
              <div className="space-y-3">
                <div className="text-center">
                  <h4 className="text-sm font-medium text-gray-900 mb-1">
                    Supprimer toutes les conversations ?
                  </h4>
                  <p className="text-xs text-gray-600">
                    Cette action supprimera définitivement toutes vos conversations.
                  </p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setShowClearAllConfirm(false)}
                    disabled={isLoading}
                    className="flex-1 px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={handleClearAll}
                    disabled={isLoading}
                    className="flex-1 px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50"
                  >
                    {isLoading ? 'Suppression...' : 'Tout supprimer'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}