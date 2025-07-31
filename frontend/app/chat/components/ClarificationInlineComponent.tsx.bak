'use client'

import React, { useState, useEffect } from 'react'
import { ClarificationUtils, CLARIFICATION_TEXTS, CLARIFICATION_CONFIG } from '../types'

interface ClarificationInlineProps {
  questions: string[]
  originalQuestion: string
  language: string
  onSubmit: (answers: Record<string, string>) => Promise<void>
  onSkip: () => Promise<void>
  isSubmitting?: boolean
  conversationId?: string
}

export function ClarificationInline({ 
  questions, 
  originalQuestion, 
  language,
  onSubmit, 
  onSkip, 
  isSubmitting = false,
  conversationId
}: ClarificationInlineProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [validationResult, setValidationResult] = useState({ isValid: false, requiredCount: 0, answeredCount: 0 })
  const [isExpanded, setIsExpanded] = useState(true)
  
  const t = CLARIFICATION_TEXTS[language as keyof typeof CLARIFICATION_TEXTS] || CLARIFICATION_TEXTS.fr
  
  // Validation des réponses
  useEffect(() => {
    const validation = ClarificationUtils.validateClarificationAnswers(answers, questions)
    setValidationResult(validation)
  }, [answers, questions])
  
  const handleAnswerChange = (index: number, value: string) => {
    setAnswers(prev => ({
      ...prev,
      [index]: value
    }))
  }
  
  const handleSubmit = async () => {
    if (validationResult.isValid && !isSubmitting) {
      await onSubmit(answers)
    }
  }
  
  const handleSkip = async () => {
    if (!isSubmitting) {
      await onSkip()
    }
  }
  
  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (e.key === 'Enter' && e.ctrlKey && validationResult.isValid) {
      e.preventDefault()
      handleSubmit()
    }
  }
  
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 my-4 max-w-2xl">
      {/* En-tête avec possibilité de replier */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start space-x-3 flex-1">
          <div className="flex-shrink-0 mt-1">
            <span className="text-2xl">❓</span>
          </div>
          <div className="flex-1">
            <h4 className="text-base font-semibold text-yellow-800 mb-1">
              {t.title}
            </h4>
            <p className="text-sm text-yellow-700">
              {t.subtitle}
            </p>
            
            {/* Question originale en petit */}
            <div className="mt-2 p-2 bg-yellow-100 rounded-lg">
              <p className="text-xs text-yellow-700">
                <span className="font-medium">Question :</span> {originalQuestion}
              </p>
            </div>
          </div>
        </div>
        
        {/* Bouton pour replier/déplier */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-yellow-600 hover:text-yellow-800 p-1 ml-2"
          disabled={isSubmitting}
        >
          <svg 
            className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>
      
      {/* Contenu extensible */}
      {isExpanded && (
        <>
          {/* Questions de clarification */}
          <div className="space-y-3 mb-4">
            {questions.map((question, index) => (
              <div key={index} className="space-y-2">
                <label className="block text-sm font-medium text-gray-800">
                  <span className="inline-flex items-center justify-center w-5 h-5 bg-yellow-500 text-white text-xs font-bold rounded-full mr-2">
                    {index + 1}
                  </span>
                  {question}
                  {index >= validationResult.requiredCount && (
                    <span className="text-xs text-gray-500 ml-2">
                      {t.optional}
                    </span>
                  )}
                </label>
                <textarea
                  value={answers[index] || ''}
                  onChange={(e) => handleAnswerChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(e, index)}
                  placeholder={t.placeholder}
                  className="w-full px-3 py-2 border border-yellow-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent resize-none text-sm bg-white"
                  rows={2}
                  maxLength={CLARIFICATION_CONFIG.MAX_ANSWER_LENGTH}
                  disabled={isSubmitting}
                />
                {answers[index] && answers[index].length > 0 && (
                  <div className="text-xs text-gray-500 text-right">
                    {answers[index].length} / {CLARIFICATION_CONFIG.MAX_ANSWER_LENGTH}
                  </div>
                )}
              </div>
            ))}
          </div>
          
          {/* Barre de progression */}
          <div className="mb-4">
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>Progression des réponses</span>
              <span>{validationResult.answeredCount}/{questions.length}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${
                  validationResult.isValid ? 'bg-green-500' : 'bg-yellow-500'
                }`}
                style={{ 
                  width: `${(validationResult.answeredCount / questions.length) * 100}%` 
                }}
              ></div>
            </div>
          </div>
          
          {/* Message de validation */}
          {!validationResult.isValid && (
            <div className="mb-4 p-2 bg-yellow-100 border border-yellow-300 rounded-lg">
              <p className="text-sm text-yellow-700">
                💡 {t.validationError.replace('{count}', validationResult.requiredCount.toString())} 
                <span className="font-medium ml-1">
                  ({validationResult.answeredCount}/{validationResult.requiredCount})
                </span>
              </p>
            </div>
          )}
          
          {/* Boutons d'action */}
          <div className="flex flex-col sm:flex-row gap-2">
            <button
              onClick={handleSubmit}
              disabled={!validationResult.isValid || isSubmitting}
              className={`flex-1 px-4 py-2 rounded-lg font-medium transition-all ${
                validationResult.isValid && !isSubmitting
                  ? 'bg-yellow-600 text-white hover:bg-yellow-700 shadow-sm'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              {isSubmitting ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>{t.processing}</span>
                </div>
              ) : (
                <>
                  <span>{t.submit}</span>
                  {validationResult.isValid && (
                    <span className="text-xs ml-1">(Ctrl+Enter)</span>
                  )}
                </>
              )}
            </button>
            
            <button
              onClick={handleSkip}
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 border border-yellow-300 text-yellow-700 rounded-lg hover:bg-yellow-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t.skip}
            </button>
          </div>
          
          {/* Aide rapide */}
          <div className="mt-3 text-xs text-gray-500 text-center">
            💡 Plus vous donnez de détails, plus la réponse sera précise et adaptée à votre situation
          </div>
        </>
      )}
      
      {/* Version réduite quand replié */}
      {!isExpanded && (
        <div className="flex items-center justify-between text-sm text-yellow-700">
          <span>❓ {questions.length} questions de clarification</span>
          <span className="text-xs">
            {validationResult.answeredCount}/{questions.length} réponses
          </span>
        </div>
      )}
    </div>
  )
}