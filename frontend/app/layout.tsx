// app/layout.tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/components/providers/AuthProvider'
import { LanguageProvider } from '@/components/providers/LanguageProvider'
import { Toaster } from 'react-hot-toast'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Intelia Expert - Assistant IA Agriculture',
  description: 'Assistant IA spécialisé en santé et nutrition animale pour les producteurs agricoles',
  keywords: 'agriculture, IA, santé animale, nutrition, élevage, expert',
  authors: [{ name: 'Intelia' }],
  creator: 'Intelia',
  publisher: 'Intelia',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'https://intelia-expert.com'),
  openGraph: {
    title: 'Intelia Expert - Assistant IA Agriculture',
    description: 'Assistant IA spécialisé en santé et nutrition animale',
    url: 'https://intelia-expert.com',
    siteName: 'Intelia Expert',
    locale: 'fr_CA',
    type: 'website',
  },
  manifest: '/manifest.json',
  icons: {
    icon: '/images/favicon.png',
    shortcut: '/images/favicon.png',
    apple: '/images/favicon.png',
    other: [
      {
        rel: 'icon',
        type: 'image/png',
        sizes: '32x32',
        url: '/images/favicon.png',
      },
      {
        rel: 'icon',
        type: 'image/png', 
        sizes: '16x16',
        url: '/images/favicon.png',
      },
    ],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fr" className="h-full">
      <head>
        <link rel="icon" href="/images/favicon.png" type="image/png" />
        <link rel="apple-touch-icon" href="/images/favicon.png" />
        <meta name="theme-color" content="#2563eb" />
      </head>
      <body className={`${inter.className} h-full antialiased`}>
        <AuthProvider>
          <LanguageProvider>
            {children}
            <Toaster position="top-center" />
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  )
}