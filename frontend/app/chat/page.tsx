'use client'

import React, { useState, useEffect, useRef } from 'react'

// ==================== STORES SIMULÉS ====================
const useAuthStore = () => ({
  user: {
    id: '1',
    name: 'Jean Dupont',
    email: 'jean.dupont@exemple.com',
    user_type: 'producer',
    language: 'fr',
    created_at: '2024-01-15',
    consentGiven: true,
    consentDate: new Date('2024-01-15')
  },
  isAuthenticated: true,
  logout: async () => {
    try {
      console.log('🚪 Déconnexion en cours...')
      await new Promise(resolve => setTimeout(resolve, 500))
      window.location.href = '/auth/login'
    } catch (error) {
      console.error('❌ Erreur lors de la déconnexion:', error)
      window.location.href = '/auth/login'
    }
  },
  exportUserData: async () => {
    console.log('Export des données...')
  },
  deleteUserData: async () => {
    console.log('Suppression des données...')
  },
  updateProfile: async (data: any) => {
    console.log('Mise à jour profil:', data)
  }
})

const useChatStore = () => ({
  conversations: [
    {
      id: '1',
      title: 'Problème poulets Ross 308',
      messages: [
        { id: '1', role: 'user', content: 'Mes poulets Ross 308 de 25 jours pèsent 800g, est-ce normal ?' },
        { id: '2', role: 'assistant', content: 'Selon notre base documentaire, pour les poulets Ross 308...' }
      ],
      updated_at: '2024-01-20',
      created_at