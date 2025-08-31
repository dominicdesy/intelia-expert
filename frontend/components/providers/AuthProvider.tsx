// components/providers/AuthProvider.tsx
'use client'
export function AuthProvider({ children }: { children: React.ReactNode }) {
  console.log('[AuthProvider] Version vide - test')
  return <>{children}</>
}