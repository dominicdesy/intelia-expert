'use client'

import { useState, useEffect } from 'react'
import { useChatStore } from '@/lib/stores/chat'
import { Conversation } from '@/types'

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

const EllipsisVerticalIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
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

  useEffect(() => {
    if (isOpen) {
      loadConversations()
    }
  }, [isOpen, loadConversations])

  const handleSelectConversation = async (conversationId: string) => {
    try {
      await loadConversation(conversationId)
      onClose()
    } catch (error) {
      console.error('Error loading conversation:', error)
    }
  }

  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await deleteConversation(conversationId)
      setShowDeleteConfirm(null)
    } catch (error) {
      console.error('Error deleting conversation:', error)
    }
  }

  const handleClearAll = async () => {
    try {
      await clearAllConversations()
      setShowClearAllConfirm(false)
    } catch (error) {
      console.error('Error clearing conversations:', error)
    }
  }

  const handleNewConversation = () => {
    createConversation()
    onClose()
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) {
      return "Aujourd'hui"
    } else if (days === 1) {
      return "Hier"
    } else if (days < 7) {
      return `Il y a ${days} jours`
    } else {
      return date.toLocaleDateString('fr-FR', { 
        day: 'numeric', 
        month: 'short' 
      })
    }
  }

  // FONCTION CORRIGÉE - Type spécifique pour les propriétés utilisées
  const getConversationPreview = (conversation: Pick<Conversation, 'messages'>) => {
    if (conversation.messages.length === 0) {
      return "Nouvelle conversation"
    }
    
    const firstUserMessage = conversation.messages.find(m => m.role === 'user')
    if (firstUserMessage) {
      return firstUserMessage.content.length > 50 
        ? firstUserMessage.content.substring(0, 50) + "..."
        : firstUserMessage.content
    }
    
    return "Conversation"
  }

  if (!isOpen) return null

  return (
    <>
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
        onClick={onClose}
      />
      
      {/* Sidebar */}
      <div className={`fixed left-0 top-0 h-full w-80 bg-white shadow-lg z-50 transform transition-transform ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      } lg:relative lg:translate-x-0`}>
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Conversations</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg lg:hidden"
          >
            <XMarkIcon className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Actions */}
        <div className="p-4 border-b border-gray-100">
          <button
            onClick={handleNewConversation}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <ChatBubbleLeftRightIcon className="w-4 h-4" />
            <span>Nouvelle conversation</span>
          </button>
        </div>

        {/* Liste des conversations */}
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <ChatBubbleLeftRightIcon className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-sm">Aucune conversation</p>
              <p className="text-xs mt-1">Commencez par poser une question !</p>
            </div>
          ) : (
            <div className="p-2">
              {conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className={`group relative mb-2 rounded-lg border transition-colors ${
                    currentConversation?.id === conversation.id
                      ? 'bg-blue-50 border-blue-200'
                      : 'bg-white border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <button
                    onClick={() => handleSelectConversation(conversation.id)}
                    className="w-full p-3 text-left"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-900 truncate">
                          {getConversationPreview(conversation)}
                        </h3>
                        <div className="flex items-center justify-between mt-1">
                          <span className="text-xs text-gray-500">
                            {formatDate(conversation.updated_at)}
                          </span>
                          <span className="text-xs text-gray-400">
                            {conversation.messages.length} msg
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>

                  {/* Menu d'actions */}
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setShowDeleteConfirm(showDeleteConfirm === conversation.id ? null : conversation.id)
                      }}
                      className="p-1 hover:bg-gray-200 rounded text-gray-400 hover:text-red-600 transition-colors"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Confirmation de suppression */}
                  {showDeleteConfirm === conversation.id && (
                    <div className="absolute inset-0 bg-white border border-red-200 rounded-lg p-3 z-10">
                      <p className="text-sm text-gray-900 mb-3">
                        Supprimer cette conversation ?
                      </p>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setShowDeleteConfirm(null)}
                          className="flex-1 px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                        >
                          Annuler
                        </button>
                        <button
                          onClick={() => handleDeleteConversation(conversation.id)}
                          className="flex-1 px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
                        >
                          Supprimer
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer avec action de nettoyage */}
        {conversations.length > 0 && (
          <div className="p-4 border-t border-gray-200">
            {!showClearAllConfirm ? (
              <button
                onClick={() => setShowClearAllConfirm(true)}
                className="w-full flex items-center justify-center space-x-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 border border-red-200 rounded-lg transition-colors"
              >
                <TrashIcon className="w-4 h-4" />
                <span>Effacer tout l'historique</span>
              </button>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-gray-700 text-center">
                  Supprimer toutes les conversations ?
                </p>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setShowClearAllConfirm(false)}
                    className="flex-1 px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={handleClearAll}
                    className="flex-1 px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                  >
                    Tout supprimer
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