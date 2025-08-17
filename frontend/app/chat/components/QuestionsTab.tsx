import React from 'react'
// 🚀 AUCUNE DÉPENDANCE EXTERNE - Utilise uniquement les APIs natives du navigateur

interface QuestionLog {
  id: string
  timestamp: string
  user_email: string
  user_name: string
  question: string
  response: string
  response_source: 'rag' | 'openai_fallback' | 'table_lookup' | 'validation_rejected' | 'quota_exceeded' | 'unknown'
  confidence_score: number
  response_time: number
  language: string
  session_id: string
  feedback: number | null
  feedback_comment: string | null
}

interface QuestionsTabProps {
  questionLogs: QuestionLog[]
  questionFilters: {
    search: string
    source: string
    confidence: string
    feedback: string
    user: string
  }
  setQuestionFilters: React.Dispatch<React.SetStateAction<{
    search: string
    source: string
    confidence: string
    feedback: string
    user: string
  }>>
  selectedTimeRange: 'day' | 'week' | 'month' | 'year'
  setSelectedTimeRange: React.Dispatch<React.SetStateAction<'day' | 'week' | 'month' | 'year'>>
  currentPage: number
  setCurrentPage: React.Dispatch<React.SetStateAction<number>>
  questionsPerPage: number
  setSelectedQuestion: React.Dispatch<React.SetStateAction<QuestionLog | null>>
  isLoading?: boolean
  totalQuestions?: number
}

interface ConversationExport {
  session_id: string
  user_email: string
  user_name: string
  start_time: string
  end_time: string
  total_questions: number
  questions: string[]
  responses: string[]
  sources: string[]
  confidence_scores: number[]
  response_times: number[]
  feedback_scores: (number | null)[]
  feedback_comments: (string | null)[]
}

export const QuestionsTab: React.FC<QuestionsTabProps> = ({
  questionLogs,
  questionFilters,
  setQuestionFilters,
  selectedTimeRange,
  setSelectedTimeRange,
  currentPage,
  setCurrentPage,
  questionsPerPage,
  setSelectedQuestion,
  isLoading = false,
  totalQuestions = 0
}) => {
  
  // 🎨 Fonctions utilitaires pour le styling - Style Compass
  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return 'text-emerald-700 bg-emerald-100 border-emerald-200'
    if (score >= 0.7) return 'text-amber-700 bg-amber-100 border-amber-200'
    return 'text-red-700 bg-red-100 border-red-200'
  }

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'rag': return 'text-blue-700 bg-blue-100 border-blue-200'
      case 'openai_fallback': return 'text-purple-700 bg-purple-100 border-purple-200'
      case 'table_lookup': return 'text-emerald-700 bg-emerald-100 border-emerald-200'
      case 'validation_rejected': return 'text-red-700 bg-red-100 border-red-200'
      case 'quota_exceeded': return 'text-orange-700 bg-orange-100 border-orange-200'
      default: return 'text-gray-700 bg-gray-100 border-gray-200'
    }
  }

  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'rag': return 'RAG'
      case 'openai_fallback': return 'OpenAI'
      case 'table_lookup': return 'Table'
      case 'validation_rejected': return 'Rejeté'
      case 'quota_exceeded': return 'Quota'
      default: return 'Inconnu'
    }
  }

  const getFeedbackIcon = (feedback: number | null) => {
    if (feedback === 1) return '👍'
    if (feedback === -1) return '👎'
    return '❓'
  }

  // 🚀 FONCTION CSV AVANCÉE - CONVERSATIONS EN LIGNES (format demandé)
  const groupQuestionsByConversation = (questions: QuestionLog[]): ConversationExport[] => {
    const conversationMap = new Map<string, QuestionLog[]>()
    
    questions.forEach(question => {
      const sessionId = question.session_id
      if (!conversationMap.has(sessionId)) {
        conversationMap.set(sessionId, [])
      }
      conversationMap.get(sessionId)!.push(question)
    })
    
    const conversations: ConversationExport[] = []
    
    conversationMap.forEach((sessionQuestions, sessionId) => {
      sessionQuestions.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      
      const firstQuestion = sessionQuestions[0]
      const lastQuestion = sessionQuestions[sessionQuestions.length - 1]
      
      conversations.push({
        session_id: sessionId,
        user_email: firstQuestion.user_email,
        user_name: firstQuestion.user_name,
        start_time: firstQuestion.timestamp,
        end_time: lastQuestion.timestamp,
        total_questions: sessionQuestions.length,
        questions: sessionQuestions.map(q => q.question),
        responses: sessionQuestions.map(q => q.response),
        sources: sessionQuestions.map(q => getSourceLabel(q.response_source)),
        confidence_scores: sessionQuestions.map(q => q.confidence_score),
        response_times: sessionQuestions.map(q => q.response_time),
        feedback_scores: sessionQuestions.map(q => q.feedback),
        feedback_comments: sessionQuestions.map(q => q.feedback_comment)
      })
    })
    
    return conversations
  }

  // 🚀 EXPORT CSV CONVERSATIONS avec choix de scope
  const exportConversationsToCSV = () => {
    try {
      // 🤔 DEMANDER À L'UTILISATEUR LE SCOPE D'EXPORT
      const shouldExportAll = window.confirm(
        `🤔 Choix de l'export :\n\n` +
        `• OUI = Exporter TOUTES les ${totalQuestions} questions de la base\n` +
        `• NON = Exporter seulement les ${filteredQuestions.length} questions affichées\n\n` +
        `Voulez-vous exporter TOUTES les questions ?`
      )

      let questionsToExport: QuestionLog[]
      let exportScope: string

      if (shouldExportAll) {
        // Exporter toutes les questions
        questionsToExport = questionLogs // Toutes les questions chargées
        exportScope = 'TOUTES'
        
        // ⚠️ Vérifier si on a bien toutes les données
        if (questionLogs.length < totalQuestions) {
          const proceed = window.confirm(
            `⚠️ Attention :\n\n` +
            `• Total questions dans la base : ${totalQuestions}\n` +
            `• Questions actuellement chargées : ${questionLogs.length}\n\n` +
            `L'export contiendra seulement les ${questionLogs.length} questions chargées.\n\n` +
            `Continuer l'export ?`
          )
          if (!proceed) return
        }
      } else {
        // Exporter seulement les questions filtrées
        questionsToExport = filteredQuestions
        exportScope = 'FILTRÉES'
      }

      if (questionsToExport.length === 0) {
        alert('❌ Aucune question à exporter dans la sélection')
        return
      }

      const conversations = groupQuestionsByConversation(questionsToExport)
      const maxQuestions = Math.max(...conversations.map(c => c.total_questions))
      
      console.log(`📊 Export CSV ${exportScope} de ${conversations.length} conversations, max ${maxQuestions} questions`)

      // Créer les en-têtes
      const headers = [
        'N°', 'Session ID', 'Utilisateur', 'Email', 'Début', 'Fin', 'Nb Questions', 'Durée (min)'
      ]
      
      // Ajouter les colonnes dynamiques Q1, R1, Q2, R2...
      for (let i = 0; i < maxQuestions; i++) {
        headers.push(
          `Q${i + 1}`, `R${i + 1}`, `Source${i + 1}`, 
          `Confiance${i + 1}`, `Temps${i + 1}`, `Feedback${i + 1}`, `Commentaire${i + 1}`
        )
      }

      // Fonction pour échapper les chaînes CSV
      const escapeCSV = (value: any): string => {
        if (value === null || value === undefined) return ''
        const str = String(value)
        if (str.includes('"') || str.includes(',') || str.includes('\n') || str.includes('\r')) {
          return `"${str.replace(/"/g, '""')}"`
        }
        return str
      }

      // Construire les données
      let csvContent = headers.map(escapeCSV).join(',') + '\n'
      
      conversations.forEach((conv, index) => {
        const rowData: any[] = [
          index + 1,
          conv.session_id.substring(0, 12) + '...',
          conv.user_name,
          conv.user_email,
          new Date(conv.start_time).toLocaleString('fr-FR'),
          new Date(conv.end_time).toLocaleString('fr-FR'),
          conv.total_questions,
          Math.max(1, Math.round((new Date(conv.end_time).getTime() - new Date(conv.start_time).getTime()) / 60000))
        ]
        
        // Ajouter les Q&R
        for (let i = 0; i < maxQuestions; i++) {
          rowData.push(
            conv.questions[i] || '',
            conv.responses[i] || '',
            conv.sources[i] || '',
            conv.confidence_scores[i] ? `${(conv.confidence_scores[i] * 100).toFixed(1)}%` : '',
            conv.response_times[i] ? `${conv.response_times[i]}s` : '',
            conv.feedback_scores[i] !== null ? (conv.feedback_scores[i] === 1 ? 'Positif' : 'Négatif') : '',
            conv.feedback_comments[i] || ''
          )
        }
        
        csvContent += rowData.map(escapeCSV).join(',') + '\n'
      })

      // Télécharger le fichier
      const scopeSuffix = shouldExportAll ? 'TOUTES' : 'FILTREES'
      const fileName = `conversations_${scopeSuffix}_${new Date().toISOString().split('T')[0]}_${Date.now()}.csv`
      
      // Ajouter BOM pour Excel français
      const bom = '\uFEFF'
      const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8' })
      const url = window.URL.createObjectURL(blob)
      
      const link = document.createElement('a')
      link.href = url
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      console.log(`✅ Export CSV conversations ${exportScope} réussi: ${fileName}`)
      
      const uniqueUsers = new Set(questionsToExport.map(q => q.user_email)).size
      const summary = `✅ Export CSV ${exportScope} réussi !

📊 Scope: ${exportScope} les questions
• ${conversations.length} conversations (lignes)
• ${questionsToExport.length} questions au total
• ${uniqueUsers} utilisateurs uniques
• ${maxQuestions} questions max par conversation

📁 Fichier: ${fileName}

📋 Format: Une ligne par conversation
• Colonnes fixes: Session, Utilisateur, Dates...
• Colonnes dynamiques: Q1, R1, Q2, R2, Q3, R3...

💡 Ouvrir avec Excel pour format tabulaire !`

      alert(summary)
      
    } catch (error) {
      console.error('❌ Erreur export CSV conversations:', error)
      alert(`❌ Erreur export CSV: ${error}`)
    }
  }

  // 🔍 Filtrage côté client (inchangé)
  const filteredQuestions = questionLogs.filter(q => {
    if (questionFilters.search && !q.question.toLowerCase().includes(questionFilters.search.toLowerCase()) && 
        !q.response.toLowerCase().includes(questionFilters.search.toLowerCase()) &&
        !q.user_email.toLowerCase().includes(questionFilters.search.toLowerCase())) {
      return false
    }
    if (questionFilters.source !== 'all' && q.response_source !== questionFilters.source) return false
    if (questionFilters.confidence !== 'all') {
      const score = q.confidence_score
      if (questionFilters.confidence === 'high' && score < 0.9) return false
      if (questionFilters.confidence === 'medium' && (score < 0.7 || score >= 0.9)) return false
      if (questionFilters.confidence === 'low' && score >= 0.7) return false
    }
    if (questionFilters.feedback !== 'all') {
      if (questionFilters.feedback === 'positive' && q.feedback !== 1) return false
      if (questionFilters.feedback === 'negative' && q.feedback !== -1) return false
      if (questionFilters.feedback === 'none' && q.feedback !== null) return false
      if (questionFilters.feedback === 'with_comments' && !q.feedback_comment) return false
      if (questionFilters.feedback === 'no_comments' && q.feedback_comment) return false
    }
    if (questionFilters.user !== 'all' && q.user_email !== questionFilters.user) return false
    return true
  })

  // 📊 Calculs statistiques (inchangés)
  const uniqueUsers = Array.from(new Set(questionLogs.map(q => q.user_email)))
  const feedbackStats = {
    total: questionLogs.filter(q => q.feedback !== null).length,
    positive: questionLogs.filter(q => q.feedback === 1).length,
    negative: questionLogs.filter(q => q.feedback === -1).length,
    withComments: questionLogs.filter(q => q.feedback_comment).length,
    satisfactionRate: questionLogs.filter(q => q.feedback !== null).length > 0 ? 
      ((questionLogs.filter(q => q.feedback === 1).length / 
        questionLogs.filter(q => q.feedback !== null).length) * 100) : 0
  }

  const sourceStats = questionLogs.reduce((acc, q) => {
    acc[q.response_source] = (acc[q.response_source] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  if (isLoading && questionLogs.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement des questions...</p>
          <p className="text-sm text-gray-400 mt-2">Récupération des données depuis la base</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 📊 Statistiques en en-tête - Style Compass */}
      <div className="bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50 rounded-xl border border-blue-200 p-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mx-auto mb-3">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div className="text-3xl font-bold text-blue-700">{totalQuestions}</div>
            <div className="text-sm font-medium text-blue-600">Questions Totales</div>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center mx-auto mb-3">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM9 3a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div className="text-3xl font-bold text-emerald-700">{uniqueUsers.length}</div>
            <div className="text-sm font-medium text-emerald-600">Utilisateurs Uniques</div>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center mx-auto mb-3">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="text-3xl font-bold text-purple-700">{feedbackStats.satisfactionRate.toFixed(1)}%</div>
            <div className="text-sm font-medium text-purple-600">Satisfaction</div>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center mx-auto mb-3">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </div>
            <div className="text-3xl font-bold text-orange-700">{questionLogs.length}</div>
            <div className="text-sm font-medium text-orange-600">Affichées</div>
          </div>
        </div>
      </div>

      {/* 🔧 Filtres et Recherche - Style Compass */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">🔍 Filtres et Recherche</h3>
          {isLoading && (
            <div className="flex items-center text-blue-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-sm font-medium">Actualisation...</span>
            </div>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">🔎 Recherche</label>
            <input
              type="text"
              value={questionFilters.search}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, search: e.target.value }))}
              placeholder="Rechercher dans questions/réponses..."
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            />
          </div>
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">🎯 Source</label>
            <select
              value={questionFilters.source}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, source: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            >
              <option value="all">Toutes les sources</option>
              <option value="rag">RAG</option>
              <option value="openai_fallback">OpenAI Fallback</option>
              <option value="table_lookup">Table Lookup</option>
              <option value="validation_rejected">Rejeté</option>
              <option value="quota_exceeded">Quota Dépassé</option>
              <option value="unknown">Inconnu</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">📊 Confiance</label>
            <select
              value={questionFilters.confidence}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, confidence: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            >
              <option value="all">Tous niveaux</option>
              <option value="high">Élevée (≥90%)</option>
              <option value="medium">Moyenne (70-89%)</option>
              <option value="low">Faible (&lt;70%)</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">💬 Feedback</label>
            <select
              value={questionFilters.feedback}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, feedback: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            >
              <option value="all">Tous feedback</option>
              <option value="positive">Positif 👍</option>
              <option value="negative">Négatif 👎</option>
              <option value="none">Aucun feedback</option>
              <option value="with_comments">Avec commentaires 📝</option>
              <option value="no_comments">Sans commentaires</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">👤 Utilisateur</label>
            <select
              value={questionFilters.user}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, user: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            >
              <option value="all">Tous utilisateurs</option>
              {uniqueUsers.map(email => (
                <option key={email} value={email}>
                  {email.length > 25 ? email.substring(0, 25) + '...' : email}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">📅 Période</label>
            <select
              value={selectedTimeRange}
              onChange={(e) => setSelectedTimeRange(e.target.value as any)}
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            >
              <option value="day">Aujourd'hui</option>
              <option value="week">Cette semaine</option>
              <option value="month">Ce mois</option>
              <option value="year">Cette année</option>
            </select>
          </div>
        </div>
        
        <div className="mt-6 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <p className="text-sm text-gray-600">
              <span className="font-semibold">{filteredQuestions.length}</span> question(s) trouvée(s) 
              sur <span className="font-semibold">{questionLogs.length}</span> affichées
              {totalQuestions > questionLogs.length && (
                <span className="text-blue-600 font-medium"> (Total: {totalQuestions})</span>
              )}
            </p>
            {filteredQuestions.length !== questionLogs.length && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700 border border-blue-200">
                Filtré
              </span>
            )}
          </div>
          <button
            onClick={() => {
              setQuestionFilters({
                search: '',
                source: 'all',
                confidence: 'all',
                feedback: 'all',
                user: 'all'
              })
              setCurrentPage(1)
            }}
            className="text-sm text-blue-600 hover:text-blue-800 font-semibold transition-colors hover:underline"
          >
            🔄 Réinitialiser les filtres
          </button>
        </div>
      </div>

      {/* 📈 Section Analyse des Feedback et Sources - Style Compass */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Analyse des Commentaires */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">💬 Analyse des Commentaires</h3>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
              <span className="text-xs text-gray-500 font-medium">Feedback actifs</span>
            </div>
          </div>
          
          <div className="space-y-6">
            {/* Statistiques des commentaires */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-emerald-50 to-green-100 rounded-xl p-4 border border-emerald-200">
                <div className="text-2xl font-bold text-emerald-700">{feedbackStats.positive}</div>
                <div className="text-sm font-medium text-emerald-600">Feedback Positifs</div>
              </div>
              <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-xl p-4 border border-red-200">
                <div className="text-2xl font-bold text-red-700">{feedbackStats.negative}</div>
                <div className="text-sm font-medium text-red-600">Feedback Négatifs</div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-600">Total des feedback:</span>
                <span className="font-bold text-gray-900">{feedbackStats.total}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-600">Avec commentaires:</span>
                <span className="font-bold text-gray-900">{feedbackStats.withComments}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-600">Taux de satisfaction:</span>
                <span className={`font-bold ${feedbackStats.satisfactionRate >= 80 ? 'text-emerald-600' : feedbackStats.satisfactionRate >= 60 ? 'text-amber-600' : 'text-red-600'}`}>
                  {feedbackStats.satisfactionRate.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Barre de progression satisfaction */}
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div 
                className={`h-3 rounded-full transition-all duration-700 ease-out ${
                  feedbackStats.satisfactionRate >= 80 ? 'bg-gradient-to-r from-emerald-500 to-green-500' : 
                  feedbackStats.satisfactionRate >= 60 ? 'bg-gradient-to-r from-amber-500 to-orange-500' : 'bg-gradient-to-r from-red-500 to-red-600'
                }`}
                style={{ width: `${feedbackStats.satisfactionRate}%` }}
              ></div>
            </div>
          </div>

          {/* Commentaires récents */}
          <div className="mt-8 pt-6 border-t border-gray-100">
            <h4 className="text-md font-semibold text-gray-800 mb-4">📝 Commentaires Récents</h4>
            <div className="space-y-3 max-h-48 overflow-y-auto">
              {questionLogs
                .filter(q => q.feedback_comment)
                .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                .slice(0, 3)
                .map((question) => (
                  <div key={question.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500">{question.user_email}</span>
                      <span className="text-lg">{getFeedbackIcon(question.feedback)}</span>
                    </div>
                    <p className="text-sm text-gray-700 italic line-clamp-2">"{question.feedback_comment}"</p>
                    <p className="text-xs text-gray-500 mt-2">
                      {new Date(question.timestamp).toLocaleDateString('fr-FR')}
                    </p>
                  </div>
                ))}
              
              {questionLogs.filter(q => q.feedback_comment).length === 0 && (
                <p className="text-sm text-gray-500 italic text-center py-8">Aucun commentaire disponible</p>
              )}
            </div>
          </div>
        </div>

        {/* Distribution des Sources */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">🎯 Distribution des Sources</h3>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="text-xs text-gray-500 font-medium">Répartition actuelle</span>
            </div>
          </div>
          
          <div className="space-y-4">
            {Object.entries(sourceStats)
              .sort(([,a], [,b]) => b - a)
              .map(([source, count]) => {
                const percentage = questionLogs.length > 0 ? (count / questionLogs.length * 100) : 0
                
                const getSourceGradient = (source: string) => {
                  switch (source) {
                    case 'rag': return 'from-blue-500 to-blue-600'
                    case 'openai_fallback': return 'from-purple-500 to-purple-600'
                    case 'table_lookup': return 'from-emerald-500 to-emerald-600'
                    case 'validation_rejected': return 'from-red-500 to-red-600'
                    case 'quota_exceeded': return 'from-orange-500 to-orange-600'
                    default: return 'from-gray-400 to-gray-500'
                  }
                }
                
                return (
                  <div key={source} className="flex items-center space-x-4">
                    <div className="w-24">
                      <span className={`inline-flex items-center px-3 py-2 rounded-full text-xs font-medium border ${getSourceColor(source)}`}>
                        {getSourceLabel(source)}
                      </span>
                    </div>
                    <div className="flex-1 mx-4">
                      <div className="bg-gray-100 rounded-full h-3 overflow-hidden">
                        <div 
                          className={`h-3 rounded-full transition-all duration-700 ease-out bg-gradient-to-r ${getSourceGradient(source)}`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                    <div className="w-20 text-right">
                      <div className="text-sm font-bold text-gray-900">{count}</div>
                      <div className="text-xs text-gray-500">({percentage.toFixed(1)}%)</div>
                    </div>
                  </div>
                )
              })}
          </div>

          {/* Métriques de qualité */}
          <div className="mt-8 pt-6 border-t border-gray-100">
            <h4 className="text-md font-semibold text-gray-800 mb-4">📊 Métriques de Qualité</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-xl p-4 border border-blue-200 text-center">
                <div className="text-xl font-bold text-blue-700">
                  {questionLogs.length > 0 ? 
                    (questionLogs.reduce((sum, q) => sum + q.confidence_score, 0) / questionLogs.length * 100).toFixed(1) 
                    : '0.0'}%
                </div>
                <div className="text-xs font-medium text-blue-600">Confiance Moyenne</div>
              </div>
              <div className="bg-gradient-to-br from-emerald-50 to-green-100 rounded-xl p-4 border border-emerald-200 text-center">
                <div className="text-xl font-bold text-emerald-700">
                  {questionLogs.length > 0 ? 
                    (questionLogs.reduce((sum, q) => sum + q.response_time, 0) / questionLogs.length).toFixed(1) 
                    : '0.0'}s
                </div>
                <div className="text-xs font-medium text-emerald-600">Temps Moyen</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 💾 Boutons d'Export - Style Compass */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">💾 Export des Données</h3>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-xs text-gray-500 font-medium">Prêt à exporter</span>
          </div>
        </div>
        
        {/* 🚀 BOUTON CSV CONVERSATIONS (format Excel-like) avec choix de scope */}
        <div className="mb-6">
          <button
            onClick={() => exportConversationsToCSV()}
            disabled={questionLogs.length === 0}
            className="bg-gradient-to-r from-emerald-600 to-green-600 text-white px-8 py-4 rounded-xl hover:from-emerald-700 hover:to-green-700 transition-all duration-200 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
          >
            📊 Exporter Conversations (CSV Excel-like)
          </button>
          
          {/* Description détaillée du format CSV avec choix */}
          <div className="mt-4 p-4 bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-200 rounded-xl">
            <h4 className="text-sm font-semibold text-emerald-800 mb-3">📊 Export CSV avec choix de portée :</h4>
            <ul className="text-xs text-emerald-700 space-y-2">
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                <span><strong>🤔 Choix automatique :</strong> Questions filtrées ({filteredQuestions.length}) ou toutes ({totalQuestions})</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                <span><strong>Format ligne par conversation :</strong> Q1, R1, Source1, Q2, R2, Source2...</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                <span><strong>Compatible Excel :</strong> Encodage UTF-8 avec BOM</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                <span><strong>🚀 Aucune dépendance :</strong> Code natif, déploiement garanti</span>
              </li>
            </ul>
            
            {/* Indicateurs visuels du scope */}
            <div className="mt-4 flex items-center justify-between text-xs">
              <div className="flex items-center space-x-4">
                <span className="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-700 border border-blue-200 font-medium">
                  📋 Filtrées: {filteredQuestions.length}
                </span>
                <span className="inline-flex items-center px-3 py-1 rounded-full bg-purple-100 text-purple-700 border border-purple-200 font-medium">
                  🗃️ Total base: {totalQuestions}
                </span>
              </div>
              
              {questionLogs.length === 0 && (
                <p className="text-emerald-600 italic font-medium">⚠️ Aucune question chargée</p>
              )}
            </div>
          </div>
        </div>

        {/* Boutons d'export existants (CSV classiques) - Style Compass */}
        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => {
              const commentsData = questionLogs
                .filter(q => q.feedback_comment)
                .map(q => ({
                  date: new Date(q.timestamp).toLocaleDateString('fr-FR'),
                  user: q.user_email,
                  question: q.question.substring(0, 100) + '...',
                  feedback: q.feedback === 1 ? 'Positif' : 'Négatif',
                  comment: q.feedback_comment,
                  source: getSourceLabel(q.response_source),
                  confidence: (q.confidence_score * 100).toFixed(1) + '%'
                }))
              
              const csvContent = "data:text/csv;charset=utf-8," + 
                "Date,Utilisateur,Question,Feedback,Commentaire,Source,Confiance\n" +
                commentsData.map(row => 
                  Object.values(row).map(field => `"${field}"`).join(',')
                ).join('\n')
              
              const encodedUri = encodeURI(csvContent)
              const link = document.createElement("a")
              link.setAttribute("href", encodedUri)
              link.setAttribute("download", `commentaires_feedback_${new Date().toISOString().split('T')[0]}.csv`)
              document.body.appendChild(link)
              link.click()
              document.body.removeChild(link)
            }}
            className="bg-gradient-to-r from-green-600 to-emerald-600 text-white px-6 py-3 rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all duration-200 text-sm font-medium shadow-md hover:shadow-lg"
          >
            📊 Exporter Commentaires (CSV)
          </button>
          
          <button
            onClick={() => {
              const questionsData = filteredQuestions.map(q => ({
                date: new Date(q.timestamp).toLocaleDateString('fr-FR'),
                user: q.user_email,
                question: q.question,
                response: q.response.substring(0, 200) + '...',
                source: getSourceLabel(q.response_source),
                confidence: (q.confidence_score * 100).toFixed(1) + '%',
                response_time: q.response_time + 's',
                feedback: q.feedback === 1 ? 'Positif' : q.feedback === -1 ? 'Négatif' : 'Aucun'
              }))
              
              const csvContent = "data:text/csv;charset=utf-8," + 
                "Date,Utilisateur,Question,Réponse,Source,Confiance,Temps,Feedback\n" +
                questionsData.map(row => 
                  Object.values(row).map(field => `"${field}"`).join(',')
                ).join('\n')
              
              const encodedUri = encodeURI(csvContent)
              const link = document.createElement("a")
              link.setAttribute("href", encodedUri)
              link.setAttribute("download", `questions_export_${new Date().toISOString().split('T')[0]}.csv`)
              document.body.appendChild(link)
              link.click()
              document.body.removeChild(link)
            }}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 text-sm font-medium shadow-md hover:shadow-lg"
          >
            📋 Exporter Questions Filtrées (CSV)
          </button>

          <button
            onClick={() => {
              const statsData = {
                export_date: new Date().toISOString(),
                total_questions: totalQuestions,
                displayed_questions: questionLogs.length,
                filtered_questions: filteredQuestions.length,
                unique_users: uniqueUsers.length,
                feedback_stats: feedbackStats,
                source_distribution: sourceStats,
                filters_applied: questionFilters
              }
              
              const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(statsData, null, 2))
              const link = document.createElement("a")
              link.setAttribute("href", dataStr)
              link.setAttribute("download", `stats_export_${new Date().toISOString().split('T')[0]}.json`)
              document.body.appendChild(link)
              link.click()
              document.body.removeChild(link)
            }}
            className="bg-gradient-to-r from-purple-600 to-violet-600 text-white px-6 py-3 rounded-lg hover:from-purple-700 hover:to-violet-700 transition-all duration-200 text-sm font-medium shadow-md hover:shadow-lg"
          >
            📈 Exporter Statistiques (JSON)
          </button>
        </div>
      </div>

      {/* 📋 Liste des Questions - Style Compass */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-8 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-blue-50">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">💬 Questions et Réponses</h3>
            <div className="flex items-center space-x-3">
              {isLoading && (
                <div className="flex items-center text-blue-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                  <span className="text-sm font-medium">Actualisation...</span>
                </div>
              )}
              <span className="text-sm font-medium text-gray-500 px-3 py-1 bg-white rounded-full border border-gray-200">
                {filteredQuestions.length} questions affichées
              </span>
            </div>
          </div>
        </div>
        
        {filteredQuestions.length === 0 ? (
          <div className="p-16 text-center">
            <div className="text-gray-300 text-8xl mb-6">🔍</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Aucune question trouvée</h3>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">
              {questionFilters.search || questionFilters.source !== 'all' || questionFilters.confidence !== 'all' || questionFilters.feedback !== 'all' || questionFilters.user !== 'all'
                ? 'Essayez de modifier vos filtres pour voir plus de résultats.'
                : 'Il n\'y a pas encore de questions dans cette période.'}
            </p>
            {(questionFilters.search || questionFilters.source !== 'all' || questionFilters.confidence !== 'all' || questionFilters.feedback !== 'all' || questionFilters.user !== 'all') && (
              <button
                onClick={() => {
                  setQuestionFilters({
                    search: '',
                    source: 'all',
                    confidence: 'all',
                    feedback: 'all',
                    user: 'all'
                  })
                }}
                className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 font-medium shadow-lg"
              >
                Réinitialiser les filtres
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredQuestions.map((question) => (
              <div key={question.id} className="p-8 hover:bg-gradient-to-r hover:from-gray-50 hover:to-blue-50 transition-all duration-200">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {/* En-tête de la question - Style Compass */}
                    <div className="flex items-center space-x-4 mb-4">
                      <div className="flex-shrink-0">
                        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center border-2 border-white shadow-lg">
                          <span className="text-white text-sm font-bold">
                            {question.user_name.split(' ').map(n => n[0]).join('').toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-gray-900">{question.user_name}</p>
                        <p className="text-xs text-gray-500">{question.user_email}</p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${getSourceColor(question.response_source)}`}>
                          {getSourceLabel(question.response_source)}
                        </span>
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${getConfidenceColor(question.confidence_score)}`}>
                          {(question.confidence_score * 100).toFixed(0)}%
                        </span>
                        <span 
                          className="text-xl cursor-help" 
                          title={`Feedback: ${question.feedback === 1 ? 'Positif' : question.feedback === -1 ? 'Négatif' : 'Aucun'}`}
                        >
                          {getFeedbackIcon(question.feedback)}
                        </span>
                        {question.feedback_comment && (
                          <span 
                            className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700 border border-purple-200" 
                            title="Contient un commentaire détaillé"
                          >
                            💬
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* Question */}
                    <div className="mb-4">
                      <p className="text-sm font-semibold text-gray-900 mb-2">❓ Question:</p>
                      <p className="text-sm text-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-lg border-l-4 border-blue-400">
                        {question.question}
                      </p>
                    </div>
                    
                    {/* Réponse */}
                    <div className="mb-4">
                      <p className="text-sm font-semibold text-gray-900 mb-2">💬 Réponse:</p>
                      <div className="text-sm text-gray-700 bg-gray-50 p-4 rounded-lg max-h-48 overflow-y-auto border border-gray-200">
                        {question.response.split('\n').map((line, index) => (
                          <p key={index} className={line.startsWith('**') ? 'font-semibold' : ''}>
                            {line}
                          </p>
                        ))}
                      </div>
                    </div>
                    
                    {/* Métadonnées - Style Compass */}
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
                      <div className="flex items-center space-x-6">
                        <span className="flex items-center space-x-1">
                          <span>🕒</span>
                          <span>{new Date(question.timestamp).toLocaleString('fr-FR')}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <span>⚡</span>
                          <span>{question.response_time}s</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <span>🌐</span>
                          <span>{question.language.toUpperCase()}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <span>🔗</span>
                          <span>{question.session_id.substring(0, 8)}...</span>
                        </span>
                      </div>
                      <button
                        onClick={() => setSelectedQuestion(question)}
                        className="text-blue-600 hover:text-blue-800 font-semibold transition-colors hover:underline bg-blue-50 px-3 py-1 rounded-full border border-blue-200"
                      >
                        Voir détails →
                      </button>
                    </div>
                    
                    {/* Commentaire de feedback - Style Compass */}
                    {question.feedback_comment && (
                      <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50 border-l-4 border-blue-400 rounded-r-xl">
                        <div className="flex items-start space-x-3">
                          <div className="flex-shrink-0">
                            <span className="text-2xl">{getFeedbackIcon(question.feedback)}</span>
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-semibold text-blue-900 mb-1">💬 Commentaire utilisateur:</p>
                            <p className="text-sm text-blue-800 italic leading-relaxed">
                              "{question.feedback_comment}"
                            </p>
                            <p className="text-xs text-blue-600 mt-2 font-medium">
                              Feedback {question.feedback === 1 ? 'positif' : 'négatif'} • {new Date(question.timestamp).toLocaleDateString('fr-FR')}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Pagination - Style Compass */}
        {filteredQuestions.length > 0 && (
          <div className="px-8 py-6 border-t border-gray-100 flex items-center justify-between bg-gradient-to-r from-gray-50 to-blue-50">
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors font-medium"
              >
                ← Précédent
              </button>
              <span className="text-sm font-medium text-gray-600 px-3 py-1 bg-white rounded-full border border-gray-200">
                Page {currentPage}
              </span>
              <button
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={filteredQuestions.length < questionsPerPage}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors font-medium"
              >
                Suivant →
              </button>
            </div>
            <div className="text-sm font-medium text-gray-600">
              {filteredQuestions.length} question(s) affichée(s)
              {totalQuestions > questionLogs.length && (
                <span className="text-blue-600"> sur {totalQuestions} au total</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}