import React, { useState } from 'react'
import { useTranslation } from '../hooks/useTranslation'
import {
  useConversationGroups,
  useConversationActions,
  useCurrentConversation
} from '../hooks/useChatStore'
import { useAuthStore } from '@/lib/stores/auth'
import { ClockIcon, TrashIcon, PlusIcon, MessageCircleIcon } from '../utils/icons'
import { Conversation, ConversationGroup } from '../types'

// ==================== MENU HISTORIQUE CONVERSATIONS ====================
export const HistoryMenu = () => {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const { user } = useAuthStore()

  // Hooks pour conversations
  const { conversationGroups, isLoadingHistory, loadConversations } = useConversationGroups()
  const {
    deleteConversation,
    clearAllConversations,
    refreshConversations,
    createNewConversation
  } = useConversationActions()
  const { currentConversation, loadConversation } = useCurrentConversation()

  const handleToggle = async () => {
    if (!isOpen && user) {
      await loadConversations(user.email || user.id)
    }
    setIsOpen(!isOpen)
  }

  const handleRefresh = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!user) return
    await refreshConversations(user.email || user.id)
  }

  const handleClearAll = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!user) return
    if (!confirm('Supprimer toutes les conversations ?')) return
    await clearAllConversations(user.email || user.id)
  }

  const handleDeleteSingle = async (conversationId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    await deleteConversation(conversationId)
    if (user) await refreshConversations(user.email || user.id)
  }

  const handleConversationClick = async (conv: Conversation, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    // ✅ Corrigé: on charge la conversation complète (avec messages) pour mettre à jour le store
    await loadConversation(conv.id)
    setIsOpen(false)
  }

  const handleNewConversation = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    createNewConversation()
    setIsOpen(false)
  }

  // Affichage hh:mm local simple avec fallback
  const formatConversationTime = (timestamp: string): string => {
    try {
      let ts = timestamp
      if (ts && !ts.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(ts)) ts = ts + 'Z'
      const d = new Date(ts)
      if (isNaN(d.getTime())) return '—'
      const h = d.getHours().toString().padStart(2, '0')
      const m = d.getMinutes().toString().padStart(2, '0')
      return `${h}:${m}`
    } catch {
      return '—'
    }
  }

  const totalConversations = conversationGroups.reduce(
    (acc: number, g: ConversationGroup) => acc + g.conversations.length,
    0
  )

  return (
    <div className="relative header-icon-container">
      {/* Bouton : icône horloge + badge externe (pas de pastille interne) */}
      <button
        onClick={handleToggle}
        className="w-10 h-10 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center border border-gray-200"
        title={t('nav.history')}
        aria-label={t('nav.history')}
      >
        <ClockIcon className="w-5 h-5" />
      </button>
      {totalConversations > 0 && (
        <span className="notification-badge">{totalConversations}</span>
      )}

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />

          {/* Fenêtre historique */}
          <div className="absolute left-0 top-full mt-2 w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-[70vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="p-3 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ClockIcon className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-700">Historique</span>
                <span className="text-xs text-gray-400">({totalConversations})</span>
              </div>
              <div className="flex items-center space-x-2">
                {/* actions header optionnelles */}
              </div>
            </div>

            {/* Liste/groupes */}
            <div className="flex-1 overflow-y-auto">
              {isLoadingHistory ? (
                <div className="p-6 text-center text-gray-500">
                  <div className="flex items-center justify-center space-x-3 mb-2">
                    <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    <span>Chargement des conversations...</span>
                  </div>
                  <p className="text-xs text-gray-400">Récupération de votre historique</p>
                </div>
              ) : conversationGroups.length === 0 ? (
                <div className="p-6 text-center text-gray-500">
                  <div className="mb-3">
                    <MessageCircleIcon className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                  </div>
                  <div className="text-sm font-medium text-gray-600 mb-1">Aucune conversation</div>
                  <div className="text-xs text-gray-400 mb-4">Commencez par poser une question</div>

                  <button
                    onClick={handleNewConversation}
                    className="inline-flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors"
                  >
                    <PlusIcon className="w-4 h-4" />
                    <span>Nouvelle conversation</span>
                  </button>

                  {user && (
                    <button
                      onClick={handleRefresh}
                      className="ml-2 text-blue-600 hover:text-blue-700 text-xs underline"
                      disabled={isLoadingHistory}
                    >
                      Actualiser
                    </button>
                  )}
                </div>
              ) : (
                conversationGroups.map((group: ConversationGroup, groupIndex: number) => (
                  <div key={groupIndex} className="border-b border-gray-100 last:border-b-0">
                    {/* En-tête de groupe */}
                    <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
                      <div className="flex items-center space-x-2">
                        <ClockIcon className="w-4 h-4 text-gray-400" />
                        <span className="text-sm font-medium text-gray-700">{group.title}</span>
                        <span className="text-xs text-gray-400">({group.conversations.length})</span>
                      </div>
                    </div>

                    {/* Conversations */}
                    <div className="divide-y divide-gray-50">
                      {group.conversations.map((conv: Conversation) => (
                        <div
                          key={conv.id}
                          className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors group ${
                            currentConversation?.id === conv.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                          }`}
                          onClick={(e) => handleConversationClick(conv, e)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0 pr-3">
                              {/* Titre */}
                              <h4 className="text-sm font-medium text-gray-900 truncate mb-2">
                                {conv.title}
                              </h4>

                              {/* Métadonnées */}
                              <div className="flex items-center space-x-3 text-xs text-gray-400">
                                <span>{formatConversationTime(conv.updated_at)}</span>
				{conv.message_count != null && <span>{conv.message_count} msg</span>}
                              </div>
                            </div>

                            {/* Actions à droite */}
                            <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => handleDeleteSingle(conv.id, e)}
                                className="text-red-600 hover:text-red-700 p-1 rounded"
                                title="Supprimer cette conversation"
                              >
                                <TrashIcon className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer (optionnel) */}
          </div>
        </>
      )}
    </div>
  )
}
