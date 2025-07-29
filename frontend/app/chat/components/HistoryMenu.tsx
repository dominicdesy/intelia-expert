import React, { useState } from 'react'
import { useTranslation } from '../hooks/useTranslation'
import { useChatStore } from '../hooks/useChatStore'
import { useAuthStore } from '../hooks/useAuthStore'
import { EllipsisVerticalIcon, TrashIcon, RefreshIcon } from '../utils/icons'

// ==================== MENU HISTORIQUE AVEC LOGGING ====================
export const HistoryMenu = () => {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const { conversations, isLoading, deleteConversation, clearAllConversations, loadConversations, refreshConversations } = useChatStore()
  const { user } = useAuthStore()

  const handleToggle = async () => {
    if (!isOpen && user) {
      console.log('📂 [HistoryMenu] Ouverture menu - chargement conversations pour:', user.id)
      await loadConversations(user.id)
    }
    setIsOpen(!isOpen)
  }

  const handleRefresh = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (!user) return
    
    console.log('🔄 [HistoryMenu] Rechargement manuel des conversations')
    await refreshConversations(user.id)
  }

  const handleClearAll = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (!user) {
      console.error('❌ [HistoryMenu] Pas d\'utilisateur pour la suppression')
      return
    }
    
    try {
      console.log('🗑️ [HistoryMenu] Début suppression toutes conversations')
      
      // Confirmation utilisateur
      const confirmed = window.confirm('Êtes-vous sûr de vouloir supprimer toutes les conversations ? Cette action est irréversible.')
      
      if (!confirmed) {
        console.log('❌ [HistoryMenu] Suppression annulée par utilisateur')
        return
      }
      
      // Appeler la fonction de suppression avec userId
      await clearAllConversations(user.id)
      console.log('✅ [HistoryMenu] Toutes conversations supprimées')
      
      // Fermer le menu après suppression
      setIsOpen(false)
      
    } catch (error) {
      console.error('❌ [HistoryMenu] Erreur suppression conversations:', error)
      alert('Erreur lors de la suppression des conversations')
    }
  }

  const handleDeleteSingle = async (conversationId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    try {
      console.log('🗑️ [HistoryMenu] Suppression conversation:', conversationId)
      await deleteConversation(conversationId)
      console.log('✅ [HistoryMenu] Conversation supprimée:', conversationId)
    } catch (error) {
      console.error('❌ [HistoryMenu] Erreur suppression conversation:', error)
      alert('Erreur lors de la suppression de la conversation')
    }
  }

  return (
    <div className="relative">
      <button
        onClick={handleToggle}
        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        title={t('nav.history')}
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
                <div className="flex items-center space-x-2">
                  <h3 className="font-medium text-gray-900">{t('nav.history')}</h3>
                  {isLoading && (
                    <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleRefresh}
                    className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
                    title="Actualiser"
                    disabled={isLoading}
                  >
                    <RefreshIcon />
                  </button>
                  {conversations.length > 0 && (
                    <button
                      onClick={handleClearAll}
                      className="text-red-600 hover:text-red-700 text-sm font-medium hover:bg-red-50 px-2 py-1 rounded transition-colors"
                      title="Supprimer toutes les conversations"
                      disabled={isLoading}
                    >
                      {t('nav.clearAll')}
                    </button>
                  )}
                </div>
              </div>
            </div>
            
            <div className="max-h-64 overflow-y-auto">
              {isLoading ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    <span>Chargement...</span>
                  </div>
                </div>
              ) : conversations.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  <div className="mb-2">📭</div>
                  <div>{t('chat.noConversations')}</div>
                  {user && (
                    <button
                      onClick={handleRefresh}
                      className="mt-2 text-blue-600 hover:text-blue-700 text-xs underline"
                      disabled={isLoading}
                    >
                      Actualiser
                    </button>
                  )}
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
                          {new Date(conv.updated_at).toLocaleDateString('fr-FR', { 
                            day: 'numeric', 
                            month: 'short', 
                            hour: '2-digit', 
                            minute: '2-digit' 
                          })}
                        </p>
                        {conv.feedback && (
                          <div className="text-xs text-gray-400 mt-1">
                            {conv.feedback === 1 ? '👍 Apprécié' : '👎 Pas utile'}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={(e) => handleDeleteSingle(conv.id, e)}
                        className="ml-2 p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="Supprimer cette conversation"
                        disabled={isLoading}
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer avec statistiques */}
            {conversations.length > 0 && (
              <div className="p-3 border-t border-gray-100 bg-gray-50 text-xs text-gray-500 text-center">
                {conversations.length} conversation{conversations.length > 1 ? 's' : ''} • 
                <span className="ml-1">
                  Dernière : {new Date(Math.max(...conversations.map(c => new Date(c.updated_at).getTime()))).toLocaleDateString('fr-FR')}
                </span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}