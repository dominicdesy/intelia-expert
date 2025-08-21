import { createPortal } from 'react-dom'
import { useEffect, useState } from 'react'
import { ModalProps } from '@/types'

// ==================== MODAL AVEC PORTAL - SOLUTION POUR LAYOUT MOBILE ====================
export const Modal = ({ isOpen, onClose, title, children }: ModalProps) => {
  const [mounted, setMounted] = useState(false)

  // S'assurer que le composant est monté côté client
  useEffect(() => {
    setMounted(true)
    return () => setMounted(false)
  }, [])

  // Empêcher le scroll du body quand la modal est ouverte
  useEffect(() => {
    if (isOpen && mounted) {
      // Sauvegarder les styles originaux
      const originalOverflow = document.body.style.overflow
      const originalPosition = document.body.style.position
      
      // Appliquer les styles pour la modal
      document.body.style.overflow = 'hidden'
      // Ne pas changer la position si elle est déjà fixed (mobile)
      if (originalPosition !== 'fixed') {
        document.body.style.position = 'relative'
      }
      
      return () => {
        // Restaurer les styles originaux
        document.body.style.overflow = originalOverflow
        if (originalPosition !== 'fixed') {
          document.body.style.position = originalPosition
        }
      }
    }
  }, [isOpen, mounted])

  // Ne pas rendre si pas encore monté ou pas ouvert
  if (!mounted || !isOpen) return null

  // Utiliser createPortal pour injecter la modal directement dans le body
  return createPortal(
    <div 
      // ✅ SOLUTION 1: Style inline avec !important pour forcer le positionnement
      style={{
        position: 'fixed !important' as any,
        top: '0 !important' as any,
        left: '0 !important' as any,
        right: '0 !important' as any,
        bottom: '0 !important' as any,
        zIndex: 99999, // Z-index très élevé
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px'
      }}
    >
      {/* ✅ SOLUTION 2: Overlay avec style inline */}
      <div 
        onClick={onClose}
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          zIndex: 1
        }}
      />
      
      {/* ✅ SOLUTION 3: Modal avec style inline et z-index élevé */}
      <div 
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          maxWidth: '32rem',
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          position: 'relative',
          zIndex: 2
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '24px',
          borderBottom: '1px solid #e5e7eb'
        }}>
          <h2 
            id="modal-title" 
            style={{
              fontSize: '1.25rem',
              fontWeight: '600',
              color: '#111827',
              margin: 0
            }}
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            aria-label="Fermer la modal"
            title="Fermer"
            style={{
              color: '#9ca3af',
              fontSize: '1.5rem',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
              lineHeight: 1,
              transition: 'color 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.color = '#4b5563'}
            onMouseOut={(e) => e.currentTarget.style.color = '#9ca3af'}
          >
            ×
          </button>
        </div>
        
        {/* Content */}
        <div style={{ padding: '24px' }}>
          {children}
        </div>
      </div>
    </div>,
    document.body // ✅ SOLUTION 4: Injecter directement dans le body
  )
}