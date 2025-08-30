import React, { useState, useCallback, useMemo } from 'react'
import { useTranslation } from '@/lib/languages/i18n'
import {
  useConversationGroups,
  useConversationActions,
  useCurrentConversation
} from '../hooks/useChatStore'
import { useAuthStore } from '@/lib/stores/auth'
import { TrashIcon, PlusIcon, MessageCircleIcon } from '../utils/icons'
import type { Conversation, ConversationGroup } from '../../../types'

export const HistoryMenu = React.memo(() => {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const { user } = useAuthStore()

  const { conversationGroups, isLoadingHistory, loadConversations } = useConversationGroups()
  const { deleteConversation, clearAllConversations, refreshConversations, createNewConversation } =
    useConversationActions()
  const { currentConversation, loadConversation } = useCurrentConversation()

  // Auto-refresh du compteur quand l'utilisateur change ou qu'une nouvelle conversation est créée
  React.useEffect(() => {
    if (user && !isLoadingHistory) {
      // Charger silencieusement pour mettre à jour le badge
      loadConversations(user.email || user.id).catch(console.error)
    }
  }, [user, loadConversations, isLoadingHistory])

  // Rafraîchir périodiquement le compteur
  React.useEffect(() => {
    if (!user) return

    const interval = setInterval(() => {
      if (!isOpen && !isLoadingHistory) {
        // Mise à jour silencieuse du badge seulement quand le menu est fermé
        loadConversations(user.email || user.id).catch(console.error)
      }
    }, 30000) // Toutes les 30 secondes

    return () => clearInterval(interval)
  }, [user, isOpen, isLoadingHistory, loadConversations])

  // CORRECTION CRITIQUE: Éviter la boucle infinie dans handleToggle
  const handleToggle = useCallback(async () => {
    console.log('[HistoryMenu] Toggle clicked, isOpen:', isOpen, 'user:', !!user)
    
    // Changer l'état AVANT de charger pour éviter les boucles
    const newIsOpen = !isOpen
    setIsOpen(newIsOpen)
    
    // Charger seulement si on OUVRE le menu et qu'on a un utilisateur
    if (newIsOpen && user && !isLoadingHistory) {
      console.log('[HistoryMenu] Chargement conversations pour:', user.email || user.id)
      try {
        await loadConversations(user.email || user.id)
        console.log('[HistoryMenu] Conversations chargées avec succès')
      } catch (error) {
        console.error('[HistoryMenu] Erreur chargement conversations:', error)
      }
    }
  }, [isOpen, user, isLoadingHistory, loadConversations])

  // Mémoisation des handlers pour éviter les re-créations
  const handleRefresh = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!user) return
    await refreshConversations(user.email || user.id)
  }, [user, refreshConversations])

  const handleClearAll = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!user) return
    if (!confirm('Supprimer toutes les conversations ?')) return
    await clearAllConversations(user.email || user.id)
  }, [user, clearAllConversations])

  const handleDeleteSingle = useCallback(async (conversationId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    await deleteConversation(conversationId)
    if (user) await refreshConversations(user.email || user.id)
  }, [deleteConversation, user, refreshConversations])

  const handleConversationClick = useCallback(async (conv: Conversation, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    await loadConversation(conv.id)
    setIsOpen(false)
  }, [loadConversation])

  const handleNewConversation = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    createNewConversation()
    setIsOpen(false)
  }, [createNewConversation])

  // Mémoisation de la fonction de formatage
  const formatConversationTime = useCallback((timestamp: string): string => {
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
  }, [])

  // Mémoisation du calcul du total de conversations
  const totalConversations = useMemo(() => {
    return conversationGroups.reduce(
      (acc: number, g: ConversationGroup) => acc + g.conversations.length,
      0
    )
  }, [conversationGroups])

  // Réduire la fréquence des logs de debug
  const debugState = useMemo(() => {
    const state = {
      isOpen,
      totalConversations,
      conversationGroupsLength: conversationGroups.length,
      isLoadingHistory,
      hasUser: !!user
    }
    
    console.log('[HistoryMenu] Render state:', state)
    
    return state
  }, [isOpen, totalConversations, conversationGroups.length, isLoadingHistory, user])

  // Mémoisation du rendu des conversations pour optimiser les performances
  const conversationsList = useMemo(() => {
    if (isLoadingHistory) {
      return (
        <div className="p-6 text-center text-gray-500">
          <div className="flex items-center justify-center space-x-3 mb-2">
            <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <span>Chargement des conversations...</span>
          </div>
          <p className="text-xs text-gray-400">Récupération de votre historique</p>
        </div>
      )
    }

    if (conversationGroups.length === 0) {
      return (
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
      )
    }

    return conversationGroups.map((group: ConversationGroup, groupIndex: number) => (
      <div key={groupIndex} className="border-b border-gray-100 last:border-b-0">
        {/* En-tête de groupe */}
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
          <div className="flex items-center space-x-2">
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
                  <h4 className="text-sm font-medium text-gray-900 truncate mb-2">
                    {conv.title}
                  </h4>

                  <div className="flex items-center space-x-3 text-xs text-gray-400">
                    <span>{formatConversationTime(conv.updated_at)}</span>
                    {conv.message_count != null && <span>{conv.message_count} msg</span>}
                  </div>
                </div>

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
  }, [isLoadingHistory, conversationGroups, user, currentConversation?.id, handleNewConversation, handleRefresh, handleConversationClick, handleDeleteSingle, formatConversationTime])

  // Mémoisation du badge de notification
  const notificationBadge = useMemo(() => {
    if (totalConversations <= 0) return null
    
    return (
      <span className="notification-badge">{totalConversations}</span>
    )
  }, [totalConversations])

  // Callback pour fermer le menu
  const handleCloseMenu = useCallback(() => {
    setIsOpen(false)
  }, [])

  return (
    <div className="relative header-icon-container">
      {/* Bouton 40×40 : icône "history" (SVG inline) + badge externe */}
      <button
        onClick={handleToggle}
        className="w-10 h-10 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center border border-gray-200"
        title={t('nav.history')}
        aria-label={t('nav.history')}
      >
        {/* Icône "history" (horloge avec flèche) */}
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          {/* flèche de retour en haut-gauche */}
          <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
                d="M8 7H5m0 0v3m0-3l2.2 2.2" />
          {/* cercle/horloge */}
          <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
                d="M21 12a9 9 0 10-9 9" />
          {/* aiguilles */}
          <path strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
                d="M12 7v5l3 3" />
        </svg>
      </button>

      {notificationBadge}

      {/* S'assurer que le menu s'affiche quand isOpen=true */}
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={handleCloseMenu} />
          <div className="absolute left-0 top-full mt-2 w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-[70vh] overflow-hidden flex flex-col">
            
            {/* Liste directement sans header */}
            <div className="flex-1 overflow-y-auto">
              {conversationsList}
            </div>
          </div>
        </>
      )}
    </div>
  )
})

// Ajouter le displayName pour le debugging
HistoryMenu.displayName = 'HistoryMenu'