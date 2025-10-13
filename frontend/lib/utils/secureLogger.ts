/**
 * Secure Logger Utility
 * Sanitizes sensitive data before logging to prevent exposure of confidential information
 */

const SENSITIVE_KEYS = [
  'password',
  'token',
  'access_token',
  'refresh_token',
  'oauth_token',
  'authorization',
  'email',
  'phone',
  'phoneNumber',
  'ssn',
  'creditCard',
  'apiKey',
  'api_key',
  'secret',
  'private_key',
  'privateKey',
];

/**
 * Sanitizes an object by redacting sensitive fields
 */
function sanitizeData(data: any): any {
  if (!data) return data;

  // Handle primitive types
  if (typeof data !== 'object') return data;

  // Handle arrays
  if (Array.isArray(data)) {
    return data.map(item => sanitizeData(item));
  }

  // Handle objects
  const sanitized: any = {};
  for (const [key, value] of Object.entries(data)) {
    const lowerKey = key.toLowerCase();
    const isSensitive = SENSITIVE_KEYS.some(sensitiveKey =>
      lowerKey.includes(sensitiveKey.toLowerCase())
    );

    if (isSensitive) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'object' && value !== null) {
      sanitized[key] = sanitizeData(value);
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

/**
 * Sanitizes error objects, preserving useful debugging info while redacting sensitive data
 */
function sanitizeError(error: any): any {
  if (!error) return error;

  // For Error objects, preserve message and stack but sanitize other properties
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      // Sanitize any additional properties
      ...sanitizeData({ ...error })
    };
  }

  return sanitizeData(error);
}

/**
 * Secure logging utility that redacts sensitive information
 * Only logs in development mode
 */
export const secureLog = {
  /**
   * Log general information (development only)
   */
  log: (message: string, data?: any) => {
    if (process.env.NODE_ENV === 'production') return;

    if (data !== undefined) {
      console.log(message, sanitizeData(data));
    } else {
      console.log(message);
    }
  },

  /**
   * Log errors with sanitized data
   */
  error: (message: string, error?: any) => {
    if (error !== undefined) {
      console.error(message, sanitizeError(error));
    } else {
      console.error(message);
    }
  },

  /**
   * Log warnings (development only)
   */
  warn: (message: string, data?: any) => {
    if (process.env.NODE_ENV === 'production') return;

    if (data !== undefined) {
      console.warn(message, sanitizeData(data));
    } else {
      console.warn(message);
    }
  },

  /**
   * Log debug information (development only)
   */
  debug: (message: string, data?: any) => {
    if (process.env.NODE_ENV === 'production') return;

    if (data !== undefined) {
      console.debug(message, sanitizeData(data));
    } else {
      console.debug(message);
    }
  }
};

/**
 * For backward compatibility - allows direct sanitization
 */
export const sanitize = sanitizeData;
