export class AuthError extends Error {
  public readonly code: string
  public readonly statusCode: number
  public readonly isRetryable: boolean

  constructor(
    message: string, 
    code: string = 'AUTH_ERROR',
    statusCode: number = 401,
    isRetryable: boolean = false
  ) {
    super(message)
    this.name = 'AuthError'
    this.code = code
    this.statusCode = statusCode
    this.isRetryable = isRetryable
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, AuthError)
    }
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      statusCode: this.statusCode,
      isRetryable: this.isRetryable
    }
  }
}

export class InvalidCredentialsError extends AuthError {
  constructor() {
    super(
      'Email ou mot de passe incorrect',
      'INVALID_CREDENTIALS',
      401,
      false
    )
  }
}

export class EmailNotConfirmedError extends AuthError {
  constructor() {
    super(
      'Email non confirmé. Vérifiez votre boîte mail.',
      'EMAIL_NOT_CONFIRMED',
      403,
      false
    )
  }
}

export class TooManyRequestsError extends AuthError {
  constructor() {
    super(
      'Trop de tentatives. Réessayez dans quelques minutes.',
      'TOO_MANY_REQUESTS',
      429,
      true
    )
  }
}

export class NetworkError extends AuthError {
  constructor() {
    super(
      'Problème de connexion. Vérifiez votre internet.',
      'NETWORK_ERROR',
      0,
      true
    )
  }
}

export class AuthErrorFactory {
  static fromSupabaseError(error: any): AuthError {
    const message = error?.message || 'Erreur inconnue'
    
    switch (message) {
      case 'Invalid login credentials':
        return new InvalidCredentialsError()
      
      case 'Email not confirmed':
        return new EmailNotConfirmedError()
        
      case 'Too many requests':
        return new TooManyRequestsError()
        
      default:
        return new AuthError(
          `Erreur d'authentification: ${message}`,
          'UNKNOWN_AUTH_ERROR',
          500,
          false
        )
    }
  }
  
  static networkError(): NetworkError {
    return new NetworkError()
  }
}