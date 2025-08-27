// utils/safeUserHelpers.ts - Helpers sécurisés pour éviter React #300

export const getSafeName = (user: any): string => {
  if (!user?.name) return 'Utilisateur'
  const name = String(user.name).trim()
  return name.length >= 2 ? name : 'Utilisateur'
}

export const getSafeEmail = (user: any): string => {
  return user?.email ? String(user.email) : ''
}

export const getSafeUserType = (user: any): string => {
  const type = user?.user_type
  return typeof type === 'string' && type ? type : 'producer'
}

export const getSafePlan = (user: any): string => {
  const plan = user?.plan
  return typeof plan === 'string' && plan ? plan : 'essential'
}

export const getSafeCreatedDate = (user: any): Date | null => {
  if (!user?.created_at) return null
  try {
    const date = new Date(user.created_at)
    return isNaN(date.getTime()) ? null : date
  } catch {
    return null
  }
}

export const getSafeInitials = (user: any): string => {
  const safeName = getSafeName(user)
  const safeEmail = getSafeEmail(user)
  
  // Si c'est un nom d'utilisateur (pas "Utilisateur")
  if (safeName !== 'Utilisateur') {
    // Vérifier si c'est un email
    if (safeName.includes('@')) {
      const emailPart = safeName.split('@')[0]
      if (emailPart.includes('.')) {
        const parts = emailPart.split('.')
        return (parts[0][0] + parts[1][0]).toUpperCase()
      }
      return emailPart.substring(0, 2).toUpperCase()
    }
    
    // Traiter comme un nom normal
    const names = safeName.trim().split(' ')
    if (names.length >= 2) {
      return (names[0][0] + names[names.length - 1][0]).toUpperCase()
    }
    return names[0][0].toUpperCase()
  }
  
  // Fallback sur l'email
  if (safeEmail) {
    const emailPart = safeEmail.split('@')[0]
    if (emailPart.includes('.')) {
      const parts = emailPart.split('.')
      return (parts[0][0] + parts[1][0]).toUpperCase()
    }
    return emailPart.substring(0, 2).toUpperCase()
  }
  
  return 'U'
}

export const getBadgeColor = (userType: string): string => {
  switch (userType) {
    case 'professional': return 'bg-blue-100 text-blue-800'
    case 'producer': return 'bg-green-100 text-green-800'
    case 'super_admin': return 'bg-red-100 text-red-800'
    default: return 'bg-gray-100 text-gray-800'
  }
}

export const getUserTypeLabel = (userType: string): string => {
  switch (userType) {
    case 'professional': return 'Professionnel'
    case 'producer': return 'Producteur'
    case 'super_admin': return 'Super Admin'
    default: return 'Utilisateur'
  }
}