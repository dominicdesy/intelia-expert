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
  
  // 🎨 Fonctions utilitaires pour le styling (inchangées)
  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600 bg-green-100'
    if (score >= 0.7) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'rag': return 'text-blue-600 bg-blue-100'
      case 'openai_fallback': return 'text-purple-600 bg-purple-100'
      case 'table_lookup': return 'text-green-600 bg-green-100'
      case 'validation_rejected': return 'text-red-600 bg-red-100'
      case 'quota_exceeded': return 'text-orange-600 bg-orange-100'
      default: return 'text-gray-600 bg-gray-100'
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

  // 🚀 EXPORT CSV CONVERSATIONS (format Excel-like en CSV)
  const exportConversationsToCSV = (questions: QuestionLog[]) => {
    try {
      if (questions.length === 0) {
        alert('❌ Aucune question à exporter')
        return
      }

      const conversations = groupQuestionsByConversation(questions)
      const maxQuestions = Math.max(...conversations.map(c => c.total_questions))
      
      console.log(`📊 Export CSV de ${conversations.length} conversations, max ${maxQuestions} questions`)

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
      const fileName = `conversations_export_${new Date().toISOString().split('T')[0]}_${Date.now()}.csv`
      
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
      
      console.log(`✅ Export CSV conversations réussi: ${fileName}`)
      
      const uniqueUsers = new Set(questions.map(q => q.user_email)).size
      const summary = `✅ Export CSV réussi !

📊 Format "Excel-like" en CSV :
• ${conversations.length} conversations (lignes)
• ${questions.length} questions au total
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
      {/* 📊 Statistiques en en-tête (inchangées) */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border border-blue-200">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{totalQuestions}</div>
            <div className="text-sm text-blue-700">Questions Totales</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{uniqueUsers.length}</div>
            <div className="text-sm text-green-700">Utilisateurs Uniques</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{feedbackStats.satisfactionRate.toFixed(1)}%</div>
            <div className="text-sm text-purple-700">Satisfaction</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{questionLogs.length}</div>
            <div className="text-sm text-orange-700">Affichées</div>
          </div>
        </div>
      </div>

      {/* 🔧 Filtres et Recherche (inchangés) */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">🔍 Filtres et Recherche</h3>
          {isLoading && (
            <div className="flex items-center text-blue-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-sm">Actualisation...</span>
            </div>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">🔎 Recherche</label>
            <input
              type="text"
              value={questionFilters.search}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, search: e.target.value }))}
              placeholder="Rechercher dans questions/réponses..."
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">🎯 Source</label>
            <select
              value={questionFilters.source}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, source: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
            <label className="block text-sm font-medium text-gray-700 mb-2">📊 Confiance</label>
            <select
              value={questionFilters.confidence}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, confidence: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">Tous niveaux</option>
              <option value="high">Élevée (≥90%)</option>
              <option value="medium">Moyenne (70-89%)</option>
              <option value="low">Faible (&lt;70%)</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">💬 Feedback</label>
            <select
              value={questionFilters.feedback}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, feedback: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
            <label className="block text-sm font-medium text-gray-700 mb-2">👤 Utilisateur</label>
            <select
              value={questionFilters.user}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, user: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
            <label className="block text-sm font-medium text-gray-700 mb-2">📅 Période</label>
            <select
              value={selectedTimeRange}
              onChange={(e) => setSelectedTimeRange(e.target.value as any)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="day">Aujourd'hui</option>
              <option value="week">Cette semaine</option>
              <option value="month">Ce mois</option>
              <option value="year">Cette année</option>
            </select>
          </div>
        </div>
        
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <p className="text-sm text-gray-600">
              <span className="font-medium">{filteredQuestions.length}</span> question(s) trouvée(s) 
              sur <span className="font-medium">{questionLogs.length}</span> affichées
              {totalQuestions > questionLogs.length && (
                <span className="text-blue-600"> (Total: {totalQuestions})</span>
              )}
            </p>
            {filteredQuestions.length !== questionLogs.length && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
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
            className="text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors"
          >
            🔄 Réinitialiser les filtres
          </button>
        </div>
      </div>

      {/* 📈 Section Analyse des Feedback et Sources (inchangées) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Analyse des Commentaires */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">💬 Analyse des Commentaires</h3>
          
          <div className="space-y-4">
            {/* Statistiques des commentaires */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-green-50 p-3 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{feedbackStats.positive}</div>
                <div className="text-sm text-green-700">Feedback Positifs</div>
              </div>
              <div className="bg-red-50 p-3 rounded-lg">
                <div className="text-2xl font-bold text-red-600">{feedbackStats.negative}</div>
                <div className="text-sm text-red-700">Feedback Négatifs</div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Total des feedback:</span>
                <span className="font-medium">{feedbackStats.total}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Avec commentaires:</span>
                <span className="font-medium">{feedbackStats.withComments}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Taux de satisfaction:</span>
                <span className={`font-medium ${feedbackStats.satisfactionRate >= 80 ? 'text-green-600' : feedbackStats.satisfactionRate >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                  {feedbackStats.satisfactionRate.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Barre de progression satisfaction */}
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className={`h-3 rounded-full transition-all duration-300 ${
                  feedbackStats.satisfactionRate >= 80 ? 'bg-green-500' : 
                  feedbackStats.satisfactionRate >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${feedbackStats.satisfactionRate}%` }}
              ></div>
            </div>
          </div>

          {/* Commentaires récents */}
          <div className="mt-6 pt-4 border-t border-gray-200">
            <h4 className="text-md font-medium text-gray-800 mb-3">📝 Commentaires Récents</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {questionLogs
                .filter(q => q.feedback_comment)
                .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                .slice(0, 3)
                .map((question) => (
                  <div key={question.id} className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-500">{question.user_email}</span>
                      <span className="text-lg">{getFeedbackIcon(question.feedback)}</span>
                    </div>
                    <p className="text-sm text-gray-700 italic line-clamp-2">"{question.feedback_comment}"</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(question.timestamp).toLocaleDateString('fr-FR')}
                    </p>
                  </div>
                ))}
              
              {questionLogs.filter(q => q.feedback_comment).length === 0 && (
                <p className="text-sm text-gray-500 italic text-center py-4">Aucun commentaire disponible</p>
              )}
            </div>
          </div>
        </div>

        {/* Distribution des Sources */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 Distribution des Sources</h3>
          
          <div className="space-y-3">
            {Object.entries(sourceStats)
              .sort(([,a], [,b]) => b - a)
              .map(([source, count]) => {
                const percentage = questionLogs.length > 0 ? (count / questionLogs.length * 100) : 0
                return (
                  <div key={source} className="flex items-center">
                    <div className="w-20 text-sm">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getSourceColor(source)}`}>
                        {getSourceLabel(source)}
                      </span>
                    </div>
                    <div className="flex-1 mx-3">
                      <div className="bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full transition-all duration-300 ${
                            source === 'rag' ? 'bg-blue-500' :
                            source === 'openai_fallback' ? 'bg-purple-500' :
                            source === 'table_lookup' ? 'bg-green-500' :
                            source === 'validation_rejected' ? 'bg-red-500' :
                            source === 'quota_exceeded' ? 'bg-orange-500' :
                            'bg-gray-500'
                          }`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                    <div className="w-20 text-sm text-gray-900 font-medium text-right">
                      {count} ({percentage.toFixed(1)}%)
                    </div>
                  </div>
                )
              })}
          </div>

          {/* Métriques de qualité */}
          <div className="mt-6 pt-4 border-t border-gray-200">
            <h4 className="text-md font-medium text-gray-800 mb-3">📊 Métriques de Qualité</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-lg font-bold text-blue-600">
                  {questionLogs.length > 0 ? 
                    (questionLogs.reduce((sum, q) => sum + q.confidence_score, 0) / questionLogs.length * 100).toFixed(1) 
                    : '0.0'}%
                </div>
                <div className="text-xs text-blue-700">Confiance Moyenne</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-green-600">
                  {questionLogs.length > 0 ? 
                    (questionLogs.reduce((sum, q) => sum + q.response_time, 0) / questionLogs.length).toFixed(1) 
                    : '0.0'}s
                </div>
                <div className="text-xs text-green-700">Temps Moyen</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 💾 Boutons d'Export - VERSION FINALE CSV UNIQUEMENT */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">💾 Export des Données</h3>
        
        {/* 🚀 BOUTON CSV CONVERSATIONS (format Excel-like) */}
        <div className="mb-4">
          <button
            onClick={() => exportConversationsToCSV(filteredQuestions)}
            disabled={filteredQuestions.length === 0}
            className="bg-emerald-600 text-white px-6 py-3 rounded-lg hover:bg-emerald-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
          >
            📊 Exporter Conversations (CSV Excel-like) - {filteredQuestions.length} questions
          </button>
          
          {/* Description détaillée du format CSV */}
          <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
            <h4 className="text-sm font-medium text-emerald-800 mb-2">📊 Format CSV "Excel-like" - Une ligne par conversation :</h4>
            <ul className="text-xs text-emerald-700 space-y-1">
              <li><strong>• Colonnes fixes :</strong> N°, Session, Utilisateur, Email, Début, Fin, Durée</li>
              <li><strong>• Colonnes dynamiques :</strong> Q1, R1, Source1, Q2, R2, Source2...</li>
              <li><strong>• Compatible Excel :</strong> Encodage UTF-8 avec BOM</li>
              <li><strong>🚀 Aucune dépendance :</strong> Code natif, déploiement garanti</li>
            </ul>
            {filteredQuestions.length === 0 && (
              <p className="text-xs text-emerald-600 mt-2 italic">⚠️ Aucune question à exporter avec les filtres actuels</p>
            )}
          </div>
        </div>

        {/* Boutons d'export existants (CSV classiques) - INCHANGÉS */}
        <div className="flex flex-wrap gap-3">
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
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm"
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
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm"
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
            className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors text-sm"
          >
            📈 Exporter Statistiques (JSON)
          </button>
        </div>
      </div>

      {/* 📋 Liste des Questions (inchangée) */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">💬 Questions et Réponses</h3>
            <div className="flex items-center space-x-2">
              {isLoading && (
                <div className="flex items-center text-blue-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                  <span className="text-sm">Actualisation...</span>
                </div>
              )}
              <span className="text-sm text-gray-500">
                {filteredQuestions.length} questions affichées
              </span>
            </div>
          </div>
        </div>
        
        {filteredQuestions.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-gray-400 text-6xl mb-4">🔍</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Aucune question trouvée</h3>
            <p className="text-gray-500 mb-4">
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
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Réinitialiser les filtres
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredQuestions.map((question) => (
              <div key={question.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {/* En-tête de la question */}
                    <div className="flex items-center space-x-3 mb-3">
                      <div className="flex-shrink-0">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full flex items-center justify-center border-2 border-blue-200">
                          <span className="text-blue-600 text-sm font-bold">
                            {question.user_name.split(' ').map(n => n[0]).join('').toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900">{question.user_name}</p>
                        <p className="text-xs text-gray-500">{question.user_email}</p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getSourceColor(question.response_source)}`}>
                          {getSourceLabel(question.response_source)}
                        </span>
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(question.confidence_score)}`}>
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
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 border border-purple-300" 
                            title="Contient un commentaire détaillé"
                          >
                            💬
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* Question */}
                    <div className="mb-4">
                      <p className="text-sm font-medium text-gray-900 mb-2">❓ Question:</p>
                      <p className="text-sm text-gray-700 bg-blue-50 p-4 rounded-md border-l-4 border-blue-400">
                        {question.question}
                      </p>
                    </div>
                    
                    {/* Réponse */}
                    <div className="mb-4">
                      <p className="text-sm font-medium text-gray-900 mb-2">💬 Réponse:</p>
                      <div className="text-sm text-gray-700 bg-gray-50 p-4 rounded-md max-h-48 overflow-y-auto border border-gray-200">
                        {question.response.split('\n').map((line, index) => (
                          <p key={index} className={line.startsWith('**') ? 'font-semibold' : ''}>
                            {line}
                          </p>
                        ))}
                      </div>
                    </div>
                    
                    {/* Métadonnées */}
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
                      <div className="flex items-center space-x-4">
                        <span className="flex items-center">
                          <span className="mr-1">🕐</span>
                          {new Date(question.timestamp).toLocaleString('fr-FR')}
                        </span>
                        <span className="flex items-center">
                          <span className="mr-1">⚡</span>
                          {question.response_time}s
                        </span>
                        <span className="flex items-center">
                          <span className="mr-1">🌐</span>
                          {question.language.toUpperCase()}
                        </span>
                        <span className="flex items-center">
                          <span className="mr-1">🔗</span>
                          {question.session_id.substring(0, 8)}...
                        </span>
                      </div>
                      <button
                        onClick={() => setSelectedQuestion(question)}
                        className="text-blue-600 hover:text-blue-800 font-medium transition-colors hover:underline"
                      >
                        Voir détails →
                      </button>
                    </div>
                    
                    {/* Commentaire de feedback */}
                    {question.feedback_comment && (
                      <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-400 rounded-r-lg">
                        <div className="flex items-start space-x-3">
                          <div className="flex-shrink-0">
                            <span className="text-2xl">{getFeedbackIcon(question.feedback)}</span>
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-medium text-blue-900 mb-1">💬 Commentaire utilisateur:</p>
                            <p className="text-sm text-blue-800 italic leading-relaxed">
                              "{question.feedback_comment}"
                            </p>
                            <p className="text-xs text-blue-600 mt-2">
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
        
        {/* Pagination (inchangée) */}
        {filteredQuestions.length > 0 && (
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
              >
                ← Précédent
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage}
              </span>
              <button
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={filteredQuestions.length < questionsPerPage}
                className="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
              >
                Suivant →
              </button>
            </div>
            <div className="text-sm text-gray-600">
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