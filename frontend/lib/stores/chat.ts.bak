// lib/stores/chat.ts - VERSION FINALE AVEC API SÉCURISÉE + HYDRATATION
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { secureRequest } from '@/lib/supabase/client'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: string
  feedback?: 'positive' | 'negative' | null
  sources?: Array<{ title: string; url?: string }>
  metadata?: { response_time?: number; model_used?: string }
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at: string
  updated_at: string
}

interface TopicSuggestion {
  id: string
  title: string
  description: string
  category: string
  icon: string
  popular: boolean
}

interface ChatState {
  // État
  conversations: Conversation[]
  currentConversation: Conversation | null
  isLoading: boolean
  error: string | null
  hasHydrated: boolean // HYDRATATION

  // Actions hydratation
  setHasHydrated: (hasHydrated: boolean) => void

  // Actions conversations
  createConversation: () => void
  loadConversations: () => Promise<void>
  loadConversation: (id: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  clearAllConversations: () => Promise<void>

  // Actions messages
  sendMessage: (content: string) => Promise<void>
  giveFeedback: (messageId: string, feedback: { message_id: string; rating: 'positive' | 'negative'; category: string }) => Promise<void>

  // Actions suggestions
  loadTopicSuggestions: () => Promise<TopicSuggestion[]>
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // État initial
      conversations: [],
      currentConversation: null,
      isLoading: false,
      error: null,
      hasHydrated: false,

      // HYDRATATION - Marquer comme terminée
      setHasHydrated: (hasHydrated: boolean) => {
        set({ hasHydrated })
      },

      // Créer une nouvelle conversation
      createConversation: () => {
        const newConversation: Conversation = {
          id: `conv-${Date.now()}`,
          title: 'Nouvelle conversation',
          messages: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }

        set(state => ({
          currentConversation: newConversation,
          conversations: [newConversation, ...state.conversations]
        }))

        console.log('✅ Nouvelle conversation créée:', newConversation.id)
      },

      // Charger toutes les conversations
      loadConversations: async () => {
        try {
          console.log('📋 Chargement conversations sécurisé...')
          
          // API sécurisée (quand elle sera prête)
          /*
          const response = await secureRequest.get('/api/v1/conversations')
          const data = await response.json()
          
          if (response.ok) {
            set({ conversations: data.conversations || [] })
          } else {
            throw new Error(data.message || 'Erreur chargement conversations')
          }
          */
          
          // Pour l'instant, utiliser les conversations locales
          console.log('✅ Conversations chargées:', get().conversations.length)
          
        } catch (error: any) {
          console.error('❌ Erreur chargement conversations:', error)
          set({ error: 'Erreur lors du chargement des conversations' })
        }
      },

      // Charger une conversation spécifique
      loadConversation: async (id: string) => {
        try {
          console.log('📖 Chargement conversation sécurisé:', id)
          
          const conversations = get().conversations
          const conversation = conversations.find(c => c.id === id)
          
          if (conversation) {
            set({ currentConversation: conversation, error: null })
            console.log('✅ Conversation chargée:', conversation.title)
          } else {
            throw new Error('Conversation non trouvée')
          }
          
        } catch (error: any) {
          console.error('❌ Erreur chargement conversation:', error)
          set({ error: 'Conversation non trouvée' })
        }
      },

      // Supprimer une conversation
      deleteConversation: async (id: string) => {
        try {
          console.log('🗑️ Suppression conversation sécurisée:', id)
          
          // API sécurisée (quand elle sera prête)
          /*
          const response = await secureRequest.delete(`/api/v1/conversations/${id}`)
          if (!response.ok) {
            throw new Error('Erreur suppression serveur')
          }
          */
          
          set(state => ({
            conversations: state.conversations.filter(c => c.id !== id),
            currentConversation: state.currentConversation?.id === id ? null : state.currentConversation,
            error: null
          }))

          console.log('✅ Conversation supprimée')
          
        } catch (error: any) {
          console.error('❌ Erreur suppression conversation:', error)
          set({ error: 'Erreur lors de la suppression' })
        }
      },

      // Effacer toutes les conversations
      clearAllConversations: async () => {
        try {
          console.log('🧹 Suppression sécurisée toutes conversations...')
          
          // API sécurisée (quand elle sera prête)
          /*
          const response = await secureRequest.delete('/api/v1/conversations')
          if (!response.ok) {
            throw new Error('Erreur suppression serveur')
          }
          */
          
          set({
            conversations: [],
            currentConversation: null,
            error: null
          })

          console.log('✅ Toutes les conversations supprimées')
          
        } catch (error: any) {
          console.error('❌ Erreur suppression toutes conversations:', error)
          set({ error: 'Erreur lors de la suppression' })
        }
      },

      // Envoyer un message - Version sécurisée
      sendMessage: async (content: string) => {
        const startTime = Date.now()
        set({ isLoading: true, error: null })

        try {
          console.log('💬 Envoi message sécurisé:', content.substring(0, 50) + '...')

          // Créer le message utilisateur
          const userMessage: Message = {
            id: `user-${Date.now()}`,
            content,
            role: 'user',
            timestamp: new Date().toISOString()
          }

          // Ajouter à la conversation courante
          let currentConv = get().currentConversation
          if (!currentConv) {
            get().createConversation()
            currentConv = get().currentConversation!
          }

          // Mettre à jour avec message utilisateur
          const updatedConv = {
            ...currentConv,
            messages: [...currentConv.messages, userMessage],
            title: currentConv.messages.length === 0 ? content.substring(0, 50) : currentConv.title,
            updated_at: new Date().toISOString()
          }

          set(state => ({
            currentConversation: updatedConv,
            conversations: state.conversations.map(c => 
              c.id === updatedConv.id ? updatedConv : c
            )
          }))

          // Appel API sécurisé
          try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || '/api'
            const response = await secureRequest.post(`${apiUrl}/v1/expert/ask`, {
              question: content,
              conversation_id: currentConv.id,
              language: 'fr'
            })

            const data = await response.json()
            const responseTime = Date.now() - startTime

            if (!response.ok) {
              throw new Error(data.message || `Erreur API: ${response.status}`)
            }

            // Créer le message de réponse
            const assistantMessage: Message = {
              id: `ai-${Date.now()}`,
              content: data.answer || data.response || 'Réponse reçue avec succès.',
              role: 'assistant',
              timestamp: new Date().toISOString(),
              sources: data.sources || [],
              metadata: { 
                response_time: responseTime,
                model_used: data.model_used || 'gpt-4o'
              }
            }

            // Mettre à jour avec la réponse
            const finalConv = {
              ...updatedConv,
              messages: [...updatedConv.messages, assistantMessage],
              updated_at: new Date().toISOString()
            }

            set(state => ({
              currentConversation: finalConv,
              conversations: state.conversations.map(c => 
                c.id === finalConv.id ? finalConv : c
              )
            }))

            console.log('✅ Message envoyé et réponse reçue')

          } catch (apiError: any) {
            console.error('❌ Erreur API, passage en mode fallback:', apiError)
            
            // Mode fallback - Simulation réponse IA
            await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))

            const fallbackMessage: Message = {
              id: `ai-fallback-${Date.now()}`,
              content: `Merci pour votre question : "${content.substring(0, 100)}..."

En tant qu'expert en santé et nutrition animale, cette question est importante pour l'optimisation de vos élevages.

**Points clés à considérer :**
• Surveillance régulière des indicateurs de performance
• Adaptation de l'alimentation selon les conditions environnementales  
• Mise en place de protocoles préventifs adaptés
• Consultation vétérinaire en cas de doute

*Note : Le système fonctionne en mode dégradé. L'API sera bientôt disponible.*

Avez-vous d'autres questions spécifiques sur ce sujet ?`,
              role: 'assistant',
              timestamp: new Date().toISOString(),
              sources: [],
              metadata: { 
                response_time: Date.now() - startTime,
                model_used: 'fallback'
              }
            }

            const finalConv = {
              ...updatedConv,
              messages: [...updatedConv.messages, fallbackMessage],
              updated_at: new Date().toISOString()
            }

            set(state => ({
              currentConversation: finalConv,
              conversations: state.conversations.map(c => 
                c.id === finalConv.id ? finalConv : c
              )
            }))

            console.log('✅ Réponse fallback générée')
          }

        } catch (error: any) {
          console.error('❌ Erreur critique envoi message:', error)
          
          // Message d'erreur générique
          const errorMessage: Message = {
            id: `error-${Date.now()}`,
            content: 'Désolé, le système est temporairement indisponible. Veuillez réessayer dans quelques instants.',
            role: 'assistant',
            timestamp: new Date().toISOString(),
            metadata: { 
              response_time: Date.now() - startTime,
              model_used: 'error'
            }
          }

          const currentConv = get().currentConversation
          if (currentConv) {
            const updatedConv = {
              ...currentConv,
              messages: [...currentConv.messages, errorMessage],
              updated_at: new Date().toISOString()
            }

            set(state => ({
              currentConversation: updatedConv,
              conversations: state.conversations.map(c => 
                c.id === updatedConv.id ? updatedConv : c
              )
            }))
          }

          set({ error: 'Erreur lors de l\'envoi du message' })
          
        } finally {
          set({ isLoading: false })
        }
      },

      // Donner un feedback - Version sécurisée
      giveFeedback: async (messageId: string, feedback: { message_id: string; rating: 'positive' | 'negative'; category: string }) => {
        try {
          console.log('👍👎 Feedback sécurisé pour message:', messageId, feedback.rating)

          // Mettre à jour localement
          const currentConv = get().currentConversation
          if (currentConv) {
            const updatedMessages = currentConv.messages.map(msg =>
              msg.id === messageId
                ? { ...msg, feedback: feedback.rating }
                : msg
            )

            const updatedConv = {
              ...currentConv,
              messages: updatedMessages,
              updated_at: new Date().toISOString()
            }

            set(state => ({
              currentConversation: updatedConv,
              conversations: state.conversations.map(c => 
                c.id === updatedConv.id ? updatedConv : c
              )
            }))
          }

          // Envoyer au serveur (quand l'API sera prête)
          /*
          try {
            const response = await secureRequest.post('/api/v1/expert/feedback', feedback)
            if (!response.ok) {
              console.warn('⚠️ Erreur envoi feedback serveur, conservé localement')
            }
          } catch (apiError) {
            console.warn('⚠️ API feedback indisponible, conservé localement')
          }
          */

          console.log('✅ Feedback enregistré')
          
        } catch (error: any) {
          console.error('❌ Erreur feedback:', error)
        }
      },

      // Charger les suggestions de sujets
      loadTopicSuggestions: async (): Promise<TopicSuggestion[]> => {
        try {
          console.log('💡 Chargement suggestions sécurisé...')

          // Suggestions optimisées pour l'agriculture avec couleurs Intelia
          const suggestions: TopicSuggestion[] = [
            {
              id: '1',
              title: 'Problèmes de croissance poulets',
              description: 'Diagnostics et solutions pour optimiser la croissance',
              category: 'nutrition',
              icon: '🐓',
              popular: true
            },
            {
              id: '2',
              title: 'Conditions environnementales optimales',
              description: 'Température, ventilation et humidité',
              category: 'environnement',
              icon: '🌡️',
              popular: true
            },
            {
              id: '3',
              title: 'Protocoles de vaccination',
              description: 'Calendriers et bonnes pratiques',
              category: 'sante',
              icon: '💉',
              popular: false
            },
            {
              id: '4',
              title: 'Diagnostic des maladies',
              description: 'Symptômes et identification précoce',
              category: 'sante',
              icon: '🔬',
              popular: true
            },
            {
              id: '5',
              title: 'Nutrition et alimentation',
              description: 'Rations équilibrées et compléments',
              category: 'nutrition',
              icon: '🌾',
              popular: false
            },
            {
              id: '6',
              title: 'Gestion de la mortalité',
              description: 'Prévention et causes fréquentes',
              category: 'sante',
              icon: '⚠️',
              popular: true
            }
          ]

          console.log('✅ Suggestions chargées:', suggestions.length)
          return suggestions

        } catch (error: any) {
          console.error('❌ Erreur chargement suggestions:', error)
          return []
        }
      }
    }),
    {
      name: 'intelia-chat-storage',
      storage: createJSONStorage(() => {
        // HYDRATATION - Vérifier côté client
        if (typeof window !== 'undefined') {
          return localStorage
        }
        return {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {}
        }
      }),
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversation: state.currentConversation
      }),
      onRehydrateStorage: () => (state) => {
        // HYDRATATION - Marquer comme terminée
        if (state) {
          state.setHasHydrated(true)
        }
      }
    }
  )
)