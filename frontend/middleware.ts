'use client'
import { useEffect, useState } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter } from 'next/navigation'

export default function ChatPage() {
  const [ready, setReady] = useState(false)
  const [session, setSession] = useState<any>(null)
  const router = useRouter()

  useEffect(() => {
    const supabase = createClientComponentClient()
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setReady(true)
    })
  }, [])

  if (!ready) return null // ou un loader

  // Si tu veux vraiment bloquer l'accès sans session :
  // if (!session) { router.replace('/'); return null }

  return <div>… ton chat …</div>
}
