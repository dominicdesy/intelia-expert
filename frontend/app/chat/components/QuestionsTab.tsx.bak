import React from 'react'

interface QuestionLog {
  id: string
  timestamp: string
  user_email: string
  user_name: string
  question: string
  response: string
  response_source: 'rag_retriever' | 'openai_fallback' | 'perfstore' | 'agricultural_validator'
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
  setSelectedQuestion
}) => {
  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600 bg-green-100'
    if (score >= 0.7) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'rag_retriever': return 'text-blue-600 bg-blue-100'
      case 'openai_fallback': return 'text-purple-600 bg-purple-100'
      case 'perfstore': return 'text-green-600 bg-green-100'
      case 'agricultural_validator': return 'text-orange-600 bg-orange-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getFeedbackIcon = (feedback: number | null) => {
    if (feedback === 1) return '👍'
    if (feedback === -1) return '👎'
    return '❓'
  }

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

  const paginatedQuestions = filteredQuestions.slice(
    (currentPage - 1) * questionsPerPage,
    currentPage * questionsPerPage
  )

  const totalPages = Math.ceil(filteredQuestions.length / questionsPerPage)
  const uniqueUsers = Array.from(new Set(questionLogs.map(q => q.user_email)))

  return (
    <div className="space-y-6">
      {/* Filtres */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Filtres et Recherche</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Recherche</label>
            <input
              type="text"
              value={questionFilters.search}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, search: e.target.value }))}
              placeholder="Rechercher dans questions/réponses..."
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Source</label>
            <select
              value={questionFilters.source}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, source: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">Toutes les sources</option>
              <option value="rag_retriever">RAG Retriever</option>
              <option value="openai_fallback">OpenAI Fallback</option>
              <option value="perfstore">PerfStore</option>
              <option value="agricultural_validator">Validator</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Confiance</label>
            <select
              value={questionFilters.confidence}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, confidence: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">Tous niveaux</option>
              <option value="high">Élevée (≥90%)</option>
              <option value="medium">Moyenne (70-89%)</option>
              <option value="low">Faible (&lt;70%)</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Feedback</label>
            <select
              value={questionFilters.feedback}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, feedback: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">Tous feedback</option>
              <option value="positive">Positif 👍</option>
              <option value="negative">Négatif 👎</option>
              <option value="none">Aucun feedback</option>
              <option value="with_comments">Avec commentaires 💬</option>
              <option value="no_comments">Sans commentaires</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Utilisateur</label>
            <select
              value={questionFilters.user}
              onChange={(e) => setQuestionFilters(prev => ({ ...prev, user: e.target.value }))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">Tous utilisateurs</option>
              {uniqueUsers.map(email => (
                <option key={email} value={email}>{email}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Période</label>
            <select
              value={selectedTimeRange}
              onChange={(e) => setSelectedTimeRange(e.target.value as any)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="day">Aujourd'hui</option>
              <option value="week">Cette semaine</option>
              <option value="month">Ce mois</option>
              <option value="year">Cette année</option>
            </select>
          </div>
        </div>
        
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            {filteredQuestions.length} question(s) trouvée(s) sur {questionLogs.length} au total
          </p>
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
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Réinitialiser les filtres
          </button>
        </div>
      </div>

      {/* Section Analyse des Commentaires */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">🔍 Analyse des Commentaires de Feedback</h3>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Statistiques des commentaires */}
          <div>
            <h4 className="text-md font-medium text-gray-800 mb-3">Statistiques Générales</h4>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Total des feedback:</span>
                <span className="font-medium">{questionLogs.filter(q => q.feedback !== null).length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Avec commentaires:</span>
                <span className="font-medium">{questionLogs.filter(q => q.feedback_comment).length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Feedback positifs:</span>
                <span className="font-medium text-green-600">{questionLogs.filter(q => q.feedback === 1).length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Feedback négatifs:</span>
                <span className="font-medium text-red-600">{questionLogs.filter(q => q.feedback === -1).length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Taux de satisfaction:</span>
                <span className="font-medium">
                  {questionLogs.filter(q => q.feedback !== null).length > 0 ? 
                    ((questionLogs.filter(q => q.feedback === 1).length / 
                      questionLogs.filter(q => q.feedback !== null).length) * 100).toFixed(1) + '%' 
                    : '0%'}
                </span>
              </div>
            </div>
          </div>

          {/* Commentaires récents */}
          <div>
            <h4 className="text-md font-medium text-gray-800 mb-3">Commentaires Récents</h4>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {questionLogs
                .filter(q => q.feedback_comment)
                .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                .slice(0, 5)
                .map((question) => (
                  <div key={question.id} className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-500">{question.user_email}</span>
                      <span className="text-lg">{getFeedbackIcon(question.feedback)}</span>
                    </div>
                    <p className="text-sm text-gray-700 italic">"{question.feedback_comment}"</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(question.timestamp).toLocaleDateString('fr-FR')}
                    </p>
                  </div>
                ))}
              
              {questionLogs.filter(q => q.feedback_comment).length === 0 && (
                <p className="text-sm text-gray-500 italic">Aucun commentaire disponible</p>
              )}
            </div>
          </div>
        </div>

        {/* Bouton pour exporter les commentaires */}
        <div className="mt-6 pt-4 border-t border-gray-200">
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
                  source: q.response_source,
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
            📊 Exporter les Commentaires (CSV)
          </button>
        </div>
      </div>

      {/* Liste des Questions */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Questions et Réponses</h3>
        </div>
        
        <div className="divide-y divide-gray-200">
          {paginatedQuestions.map((question) => (
            <div key={question.id} className="p-6 hover:bg-gray-50">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  {/* En-tête de la question */}
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-600 text-sm font-medium">
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
                        {question.response_source.replace('_', ' ')}
                      </span>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(question.confidence_score)}`}>
                        {(question.confidence_score * 100).toFixed(0)}%
                      </span>
                      <span className="text-lg" title={`Feedback: ${question.feedback === 1 ? 'Positif' : question.feedback === -1 ? 'Négatif' : 'Aucun'}`}>
                        {getFeedbackIcon(question.feedback)}
                      </span>
                      {/* Indicateur de commentaire */}
                      {question.feedback_comment && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 border border-purple-300" title="Contient un commentaire détaillé">
                          💬 Commentaire
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Question */}
                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-900 mb-2">❓ Question:</p>
                    <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded-md">
                      {question.question}
                    </p>
                  </div>
                  
                  {/* Réponse */}
                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-900 mb-2">💬 Réponse:</p>
                    <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded-md max-h-40 overflow-y-auto">
                      {question.response.split('\n').map((line, index) => (
                        <p key={index} className={line.startsWith('**') ? 'font-semibold' : ''}>
                          {line}
                        </p>
                      ))}
                    </div>
                  </div>
                  
                  {/* Métadonnées */}
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <div className="flex items-center space-x-4">
                      <span>🕒 {new Date(question.timestamp).toLocaleString('fr-FR')}</span>
                      <span>⚡ {question.response_time}s</span>
                      <span>🌐 {question.language.toUpperCase()}</span>
                      <span>🔗 {question.session_id}</span>
                    </div>
                    <button
                      onClick={() => setSelectedQuestion(question)}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Voir détails →
                    </button>
                  </div>
                  
                  {/* Commentaire de feedback */}
                  {question.feedback_comment && (
                    <div className="mt-3 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-400 rounded-r-lg">
                      <div className="flex items-start space-x-3">
                        <div className="flex-shrink-0">
                          <span className="text-2xl">{getFeedbackIcon(question.feedback)}</span>
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-blue-900 mb-1">Commentaire utilisateur:</p>
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
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Précédent
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage} sur {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Suivant
              </button>
            </div>
            <div className="text-sm text-gray-600">
              Affichage de {(currentPage - 1) * questionsPerPage + 1} à {Math.min(currentPage * questionsPerPage, filteredQuestions.length)} sur {filteredQuestions.length}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}