// SERVICE D'INVITATION SIMPLIFIÉ
const invitationService = {
  isProcessing: false,
  
  async sendInvitation(emails: string[], personalMessage: string, inviterInfo: any) {
    if (invitationService.isProcessing) {
      throw new Error('Une invitation est déjà en cours d\'envoi')
    }

    invitationService.isProcessing = true
    
    try {
      console.log('📧 [InvitationService] Début envoi:', { 
        emails, 
        inviterEmail: inviterInfo.email 
      })
      
      // Récupération de session SIMPLIFIÉE
      const supabase = getSupabaseClient()
      const { data: sessionData, error: sessionError } = await supabase.auth.getSession()
      
      if (sessionError || !sessionData.session?.access_token) {
        console.error('❌ Session error:', sessionError)
        throw new Error('Session expirée - reconnexion nécessaire')
      }

      console.log('✅ Session validée')
      
      // URL d'API SIMPLIFIÉE
      const apiUrl = '/api/v1/invitations/send'
      console.log('🌐 URL d\'envoi:', apiUrl)
      
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionData.session.access_token}`
      }
      
      const requestBody = {
        emails,
        personal_message: personalMessage,
        inviter_name: inviterInfo.name,
        inviter_email: inviterInfo.email,
        language: inviterInfo.language || 'fr'
      }
      
      console.log('📋 Envoi requête:', requestBody)
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody)
      })

      console.log('📡 Réponse:', response.status, response.statusText)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Erreur HTTP:', response.status, errorText)
        
        if (response.status === 401) {
          throw new Error('Session expirée. Veuillez vous reconnecter.')
        }
        
        throw new Error(`Erreur ${response.status}: ${errorText}`)
      }

      const result = await response.json()
      console.log('✅ Invitations traitées:', result)
      return result
      
    } catch (error) {
      console.error('❌ Erreur envoi:', error)
      throw error
    } finally {
      invitationService.isProcessing = false
    }
  }
}

// Remplacez la fonction handleSendInvitations dans votre composant par :
const handleSendInvitations = async () => {
  console.log('🖱️ Bouton "Envoyer" cliqué')
  
  setErrors([])
  setResults(null)
  
  if (!currentUser?.email) {
    setErrors(['Vous devez être connecté'])
    return
  }

  if (!emails.trim()) {
    setErrors(['Au moins une adresse email est requise'])
    return
  }

  const { valid, invalid } = validateEmails(emails)
  
  if (invalid.length > 0) {
    setErrors([`Emails invalides: ${invalid.join(', ')}`])
    return
  }

  if (valid.length === 0) {
    setErrors(['Aucun email valide trouvé'])
    return
  }

  setIsLoading(true)
  
  try {
    const inviterInfo = {
      name: currentUser.name || currentUser.email?.split('@')[0] || 'Utilisateur',
      email: currentUser.email,
      language: 'fr'
    }
    
    console.log('🚀 Appel service simplifié')
    
    const result = await invitationService.sendInvitation(
      valid, 
      personalMessage.trim(), 
      inviterInfo
    )
    
    console.log('✅ Résultat reçu:', result)
    setResults(result)
    
  } catch (error) {
    console.error('❌ Erreur envoi:', error)
    
    let errorMessage = 'Erreur lors de l\'envoi des invitations'
    
    if (error instanceof Error) {
      errorMessage = error.message
    }
    
    setErrors([errorMessage])
  } finally {
    setIsLoading(false)
  }
}