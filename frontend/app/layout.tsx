// app/layout.tsx

import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/providers/AuthProvider";
import { LanguageProvider } from "@/components/providers/LanguageProvider";
import { AdProvider } from "@/components/AdSystem/AdProvider";
import { MenuProvider } from "@/lib/contexts/MenuContext";
import { Toaster } from "react-hot-toast";
import { VoiceRealtimeButton } from "@/components/VoiceRealtimeButton";

const inter = Inter({ subsets: ["latin"] });

// Export séparé pour le viewport (nouvelle méthode)
// FIX iOS fullscreen: viewport-fit=cover + safe-area-inset pour notch
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover", // Important pour fullscreen avec notch
};

export const metadata: Metadata = {
  title: "Intelia Expert - AI Advisor",
  description: "Assistant IA spécialisé pour les producteurs avicoles",
  keywords: "agriculture, IA, santé animale, nutrition, élevage, expert",
  authors: [{ name: "Intelia" }],
  creator: "Intelia",
  publisher: "Intelia",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://intelia-expert.com",
  ),
  openGraph: {
    title: "Intelia Expert - Assistant IA Agriculture",
    description: "Assistant IA spécialisé en santé et nutrition animale",
    url: "https://intelia-expert.com",
    siteName: "Intelia Expert",
    locale: "fr_CA",
    type: "website",
  },
  manifest: "/manifest.json",
  icons: {
    icon: "/images/favicon.png",
    shortcut: "/images/favicon.png",
    apple: "/images/favicon.png",
    other: [
      {
        rel: "icon",
        type: "image/png",
        sizes: "32x32",
        url: "/images/favicon.png",
      },
      {
        rel: "icon",
        type: "image/png",
        sizes: "16x16",
        url: "/images/favicon.png",
      },
    ],
  },
};

// Script de log de version - uniquement en développement
const versionLogScript = process.env.NODE_ENV === 'development' ? `
  console.log('Intelia Expert Frontend v1.0.0.25');
  console.log('Environment:', window.location.hostname === 'localhost' ? 'development' : 'production');

  // Force cache refresh
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(function(registrations) {
      for(let registration of registrations) {
        registration.update();
      }
    });
  }
` : '';

// Script pour masquer la barre d'adresse Safari/Edge sur iPhone
const hideAddressBarScript = `
  (function() {
    // Fonction pour masquer la barre d'adresse en scrollant
    function hideAddressBar() {
      if (window.scrollY === 0) {
        window.scrollTo(0, 1);
      }
    }

    // Masquer immédiatement si pas déjà scrollé
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }

    // Exécuter au chargement
    window.addEventListener('load', function() {
      setTimeout(hideAddressBar, 0);
    }, { once: true });

    // Exécuter après DOMContentLoaded aussi
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        setTimeout(hideAddressBar, 100);
      }, { once: true });
    } else {
      setTimeout(hideAddressBar, 0);
    }

    // Re-masquer après orientation change
    window.addEventListener('orientationchange', function() {
      setTimeout(hideAddressBar, 300);
    });
  })();
`;

// Script anti-flash - Initialisation langue et direction
const antiFlashScript = `
  (function() {

    // Fonction pour obtenir la langue préférée
    function getPreferredLanguage() {
      try {
        // 1. Priorité: localStorage Zustand
        const zustandData = localStorage.getItem('intelia-language');
        if (zustandData) {
          const parsed = JSON.parse(zustandData);
          const storedLang = parsed?.state?.currentLanguage;

          if (storedLang && ['ar', 'en', 'fr', 'es', 'de', 'pt', 'nl', 'pl', 'zh', 'hi', 'th', 'tr', 'vi', 'ja', 'id', 'it'].includes(storedLang)) {
            return storedLang;
          }
        }

        // 2. Fallback: langue du navigateur
        const browserLang = navigator.language.split('-')[0];
        if (['ar', 'en', 'fr', 'es', 'de', 'pt', 'nl', 'pl', 'zh', 'hi', 'th', 'tr', 'vi', 'ja', 'id', 'it'].includes(browserLang)) {
          return browserLang;
        }

        return 'fr';
      } catch (e) {
        return 'fr';
      }
    }

    // Fonction pour déterminer si la langue utilise RTL
    function isRTLLanguage(lang) {
      const rtlLanguages = ['ar', 'he', 'fa', 'ur'];
      return rtlLanguages.includes(lang);
    }

    // Initialisation immédiate
    const preferredLang = getPreferredLanguage();
    document.documentElement.setAttribute('lang', preferredLang);

    // Définir la direction RTL si nécessaire
    const direction = isRTLLanguage(preferredLang) ? 'rtl' : 'ltr';
    document.documentElement.setAttribute('dir', direction);

    // Écouter les changements de langue pour mettre à jour dir dynamiquement
    window.addEventListener('languageChanged', function(event) {
      const newLang = event.detail?.language;
      if (newLang) {
        const newDirection = isRTLLanguage(newLang) ? 'rtl' : 'ltr';
        document.documentElement.setAttribute('lang', newLang);
        document.documentElement.setAttribute('dir', newDirection);
      }
    });

    // Écouter les changements du localStorage (pour les autres onglets)
    window.addEventListener('storage', function(e) {
      if (e.key === 'intelia-language' && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue);
          const newLang = parsed?.state?.currentLanguage;
          if (newLang) {
            const newDirection = isRTLLanguage(newLang) ? 'rtl' : 'ltr';
            document.documentElement.setAttribute('lang', newLang);
            document.documentElement.setAttribute('dir', newDirection);
          }
        } catch (error) {
          // Silent fail
        }
      }
    });

    // Marquer comme prêt
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        document.documentElement.classList.add('language-ready');
      }, { once: true });
    } else {
      document.documentElement.classList.add('language-ready');
    }
  })();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" dir="ltr" className="h-full" suppressHydrationWarning>
      <head>
        {/* SCRIPT DE VERSION - S'exécute en premier */}
        <script dangerouslySetInnerHTML={{ __html: versionLogScript }} />

        {/* SCRIPT ANTI-FLASH - DOIT ÊTRE EN PREMIER */}
        <script dangerouslySetInnerHTML={{ __html: antiFlashScript }} />

        {/* SCRIPT POUR MASQUER LA BARRE D'ADRESSE - Pour fullscreen */}
        <script dangerouslySetInnerHTML={{ __html: hideAddressBarScript }} />

        {/* Meta tags PWA pour fullscreen - Safari iOS et Edge iOS */}
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Intelia Expert" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="format-detection" content="telephone=no" />

        {/* Meta tags pour Edge et autres navigateurs mobiles */}
        <meta name="application-name" content="Intelia Expert" />
        <meta name="msapplication-TileColor" content="#2563eb" />
        <meta name="msapplication-tap-highlight" content="no" />

        {/* Icons existants */}
        <link rel="icon" href="/images/favicon.png" type="image/png" />
        <link rel="apple-touch-icon" href="/images/favicon.png" />
        <meta name="theme-color" content="#2563eb" />

        {/* CSS inline critique pour éviter FOUC mobile + ANTI-FLASH */}
        <style
          dangerouslySetInnerHTML={{
            __html: `
            /* === SOLUTION ANTI-FLASH (FIX iOS) === */
            /* Ne plus cacher html (problème iOS), cacher seulement body */
            body {
              opacity: 0;
              visibility: hidden;
              transition: opacity 0.2s ease-in-out, visibility 0s linear 0.2s;
            }

            html.language-ready body {
              opacity: 1;
              visibility: visible;
              transition: opacity 0.2s ease-in-out;
            }

            /* Fallback CSS pur après 3s (secours si script bloqué sur iOS) */
            @keyframes revealFallback {
              to { opacity: 1; visibility: visible; }
            }
            body:not(.anti-flash-done) {
              animation: revealFallback 0s linear 3s forwards;
            }
            
            /* Loader élégant pendant l'initialisation */
            html:not(.language-ready) body::before {
              content: '';
              position: fixed;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              z-index: 999999;
              display: block;
            }
            
            html:not(.language-ready) body::after {
              content: 'Intelia Expert';
              position: fixed;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
              color: white;
              font-size: 24px;
              font-weight: 600;
              z-index: 1000000;
              opacity: 0.9;
              animation: pulse 1.5s ease-in-out infinite;
              pointer-events: none;
            }
            
            @keyframes pulse {
              0%, 100% { opacity: 0.5; }
              50% { opacity: 1; }
            }
            
            /* Responsive loader */
            @media (max-width: 768px) {
              html:not(.language-ready) body::after {
                font-size: 20px;
              }
            }
            
            /* === STYLES MOBILES EXISTANTS === */
            
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
            
            /* Viewport dynamique pour clavier - 100dvh pour fullscreen */
            .dynamic-viewport {
              height: 100dvh; /* Dynamic viewport height pour clavier mobile */
              min-height: 100dvh;
            }
            
            /* Chat-specific mobile styles moved to chat/page.tsx */
            
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
            
            /* Fallback si JavaScript désactivé */
            noscript {
              position: fixed;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              color: white;
              display: flex;
              align-items: center;
              justify-content: center;
              z-index: 9999999;
              font-size: 18px;
              text-align: center;
              flex-direction: column;
              gap: 1rem;
              padding: 2rem;
            }
            
            /* Animation réduite si préférence utilisateur */
            @media (prefers-reduced-motion: reduce) {
              html, html.language-ready {
                transition: none !important;
              }
              html:not(.language-ready) body::after {
                animation: none !important;
              }
            }

            /* === SUPPORT RTL (Right-to-Left) === */
            /* Pour l'arabe, l'hébreu, le persan, etc. */

            [dir="rtl"] {
              direction: rtl;
              text-align: right;
            }

            /* Inverser les marges horizontales en RTL */
            [dir="rtl"] .ml-1 { margin-right: 0.25rem; margin-left: 0; }
            [dir="rtl"] .mr-1 { margin-left: 0.25rem; margin-right: 0; }
            [dir="rtl"] .ml-2 { margin-right: 0.5rem; margin-left: 0; }
            [dir="rtl"] .mr-2 { margin-left: 0.5rem; margin-right: 0; }
            [dir="rtl"] .ml-3 { margin-right: 0.75rem; margin-left: 0; }
            [dir="rtl"] .mr-3 { margin-left: 0.75rem; margin-right: 0; }
            [dir="rtl"] .ml-4 { margin-right: 1rem; margin-left: 0; }
            [dir="rtl"] .mr-4 { margin-left: 1rem; margin-right: 0; }
            [dir="rtl"] .ml-6 { margin-right: 1.5rem; margin-left: 0; }
            [dir="rtl"] .mr-6 { margin-left: 1.5rem; margin-right: 0; }
            [dir="rtl"] .ml-8 { margin-right: 2rem; margin-left: 0; }
            [dir="rtl"] .mr-8 { margin-left: 2rem; margin-right: 0; }

            /* Inverser les paddings horizontaux en RTL */
            [dir="rtl"] .pl-1 { padding-right: 0.25rem; padding-left: 0; }
            [dir="rtl"] .pr-1 { padding-left: 0.25rem; padding-right: 0; }
            [dir="rtl"] .pl-2 { padding-right: 0.5rem; padding-left: 0; }
            [dir="rtl"] .pr-2 { padding-left: 0.5rem; padding-right: 0; }
            [dir="rtl"] .pl-3 { padding-right: 0.75rem; padding-left: 0; }
            [dir="rtl"] .pr-3 { padding-left: 0.75rem; padding-right: 0; }
            [dir="rtl"] .pl-4 { padding-right: 1rem; padding-left: 0; }
            [dir="rtl"] .pr-4 { padding-left: 1rem; padding-right: 0; }
            [dir="rtl"] .pl-6 { padding-right: 1.5rem; padding-left: 0; }
            [dir="rtl"] .pr-6 { padding-left: 1.5rem; padding-right: 0; }
            [dir="rtl"] .pl-8 { padding-right: 2rem; padding-left: 0; }
            [dir="rtl"] .pr-8 { padding-left: 2rem; padding-right: 0; }

            /* Inverser left/right en RTL */
            [dir="rtl"] .left-0 { right: 0; left: auto; }
            [dir="rtl"] .right-0 { left: 0; right: auto; }
            [dir="rtl"] .left-4 { right: 1rem; left: auto; }
            [dir="rtl"] .right-4 { left: 1rem; right: auto; }

            /* Inverser les flexbox en RTL */
            [dir="rtl"] .flex-row { flex-direction: row-reverse; }
            [dir="rtl"] .flex-row-reverse { flex-direction: row; }

            /* Inverser text-align en RTL */
            [dir="rtl"] .text-left { text-align: right; }
            [dir="rtl"] .text-right { text-align: left; }

            /* Inverser les border-radius en RTL */
            [dir="rtl"] .rounded-l { border-radius: 0 0.25rem 0.25rem 0; }
            [dir="rtl"] .rounded-r { border-radius: 0.25rem 0 0 0.25rem; }
            [dir="rtl"] .rounded-tl { border-top-right-radius: 0.25rem; border-top-left-radius: 0; }
            [dir="rtl"] .rounded-tr { border-top-left-radius: 0.25rem; border-top-right-radius: 0; }
            [dir="rtl"] .rounded-bl { border-bottom-right-radius: 0.25rem; border-bottom-left-radius: 0; }
            [dir="rtl"] .rounded-br { border-bottom-left-radius: 0.25rem; border-bottom-right-radius: 0; }

            /* Inverser les transformations en RTL */
            [dir="rtl"] .rotate-90 { transform: rotate(-90deg); }
            [dir="rtl"] .rotate-180 { transform: rotate(180deg); }

            /* Ajustements spécifiques pour les icônes */
            [dir="rtl"] .rtl-flip {
              transform: scaleX(-1);
            }
          `,
          }}
        />

        <noscript>
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              color: "white",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 9999999,
              fontSize: "18px",
              textAlign: "center",
              flexDirection: "column",
              gap: "1rem",
              padding: "2rem",
            }}
          >
            <div style={{ fontSize: "24px", fontWeight: 600 }}>
              Intelia Expert
            </div>
            <div>JavaScript est requis pour utiliser cette application</div>
          </div>
        </noscript>
      </head>
      <body
        className={`${inter.className} h-full antialiased mobile-safe-container`}
        suppressHydrationWarning
      >
        <AuthProvider>
          <LanguageProvider>
            <MenuProvider>
              <AdProvider>
                {children}
                <Toaster
                  position="top-center"
                  toastOptions={{
                    style: {
                      zIndex: 9999,
                    },
                  }}
                />
                <VoiceRealtimeButton />
              </AdProvider>
            </MenuProvider>
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
