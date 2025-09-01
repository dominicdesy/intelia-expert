// app/layout.tsx
import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/components/providers/AuthProvider'
import { LanguageProvider } from '@/components/providers/LanguageProvider'
import { Toaster } from 'react-hot-toast'

const inter = Inter({ subsets: ['latin'] })

// Export séparé pour le viewport (nouvelle méthode)
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover'
}

export const metadata: Metadata = {
  title: 'Intelia Expert - AI Advisor',
  description: 'Assistant IA spécialisé pour les producteurs avicoles',
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
        {/* Meta tags critiques pour iOS */}
        <meta 
          name="viewport" 
          content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" 
        />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
        
        {/* Icons existants */}
        <link rel="icon" href="/images/favicon.png" type="image/png" />
        <link rel="apple-touch-icon" href="/images/favicon.png" />
        <meta name="theme-color" content="#2563eb" />
        

        
        {/* CSS inline critique pour éviter FOUC mobile */}
        <style dangerouslySetInnerHTML={{
          __html: `
            /* Corrections critiques iOS */
            @supports (-webkit-touch-callout: none) {
              .ios-input-fix {
                font-size: 16px !important;
                transform: translateZ(0);
                -webkit-appearance: none;
                border-radius: 0;
              }
            }
            
            /* Container mobile sécurisé */
            .mobile-safe-container {
              width: 100%;
              max-width: 100vw;
              overflow-x: hidden;
              box-sizing: border-box;
              position: relative;
            }
            
            /* Input container mobile */
            .mobile-input-container {
              display: flex;
              align-items: center;
              gap: 12px;
              width: 100%;
              max-width: 100%;
              box-sizing: border-box;
              padding: 0 16px;
              min-height: 60px;
            }
            
            .mobile-input-wrapper {
              flex: 1;
              min-width: 0;
              max-width: calc(100% - 60px);
            }
            
            .mobile-send-button {
              flex-shrink: 0;
              width: 48px;
              height: 48px;
              min-width: 48px;
            }
            
            /* Viewport dynamique pour clavier */
            .dynamic-viewport {
              height: 100vh;
              height: 100dvh;
              min-height: 100vh;
              min-height: 100dvh;
            }
            
            /* Correction spécifique iPhone */
            @media screen and (max-width: 768px) {
              body {
                position: fixed;
                width: 100%;
                height: 100%;
                overflow: hidden;
              }
              
              .chat-main-container {
                position: relative;
                width: 100vw;
                height: 100vh;
                height: 100dvh;
                overflow: hidden;
                display: flex;
                flex-direction: column;
              }
              
              .chat-scroll-area {
                flex: 1;
                overflow-y: auto;
                overflow-x: hidden;
                -webkit-overflow-scrolling: touch;
                overscroll-behavior: contain;
              }
              
              .chat-input-fixed {
                position: sticky;
                bottom: 0;
                left: 0;
                right: 0;
                z-index: 1000;
                background: white;
                border-top: 1px solid #e5e7eb;
                padding-bottom: env(safe-area-inset-bottom);
              }
            }
            
            /* Prévention zoom iOS sur focus input */
            @media screen and (max-width: 768px) {
              input[type="text"],
              input[type="email"],
              input[type="password"],
              textarea {
                font-size: 16px !important;
                -webkit-appearance: none;
                border-radius: 0;
              }
            }
          `
        }} />
      </head>
      <body className={`${inter.className} h-full antialiased mobile-safe-container`}>
        <AuthProvider>
          <LanguageProvider>
            {children}
            <Toaster 
              position="top-center"
              toastOptions={{
                style: {
                  zIndex: 9999,
                },
              }}
            />
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  )
}