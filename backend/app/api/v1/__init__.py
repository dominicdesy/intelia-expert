"""
app/api/v1/__init__.py
Configuration des imports pour les modules API v1 d'Intelia Expert
STRUCTURE CORRIGÉE - Import des modules du même dossier
"""

# Import conditionnel de tous les modules disponibles dans v1/
try:
    from .expert import router as expert_router
    print("✅ Module expert v1 importé")
    EXPERT_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erreur import expert v1: {e}")
    expert_router = None
    EXPERT_AVAILABLE = False

try:
    from .auth import router as auth_router
    print("✅ Module auth v1 importé")
    AUTH_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erreur import auth v1: {e}")
    auth_router = None
    AUTH_AVAILABLE = False

try:
    from .admin import router as admin_router
    print("✅ Module admin v1 importé")
    ADMIN_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erreur import admin v1: {e}")
    admin_router = None
    ADMIN_AVAILABLE = False

try:
    from .health import router as health_router
    print("✅ Module health v1 importé")
    HEALTH_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erreur import health v1: {e}")
    health_router = None
    HEALTH_AVAILABLE = False

try:
    from .system import router as system_router
    print("✅ Module system v1 importé")
    SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erreur import system v1: {e}")
    system_router = None
    SYSTEM_AVAILABLE = False

try:
    from .logging import router as logging_router
    print("✅ Module logging v1 importé")
    LOGGING_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erreur import logging v1: {e}")
    logging_router = None
    LOGGING_AVAILABLE = False

# Export des routers disponibles
__all__ = []

if EXPERT_AVAILABLE:
    __all__.append('expert_router')
if AUTH_AVAILABLE:
    __all__.append('auth_router') 
if ADMIN_AVAILABLE:
    __all__.append('admin_router')
if HEALTH_AVAILABLE:
    __all__.append('health_router')
if SYSTEM_AVAILABLE:
    __all__.append('system_router')
if LOGGING_AVAILABLE:
    __all__.append('logging_router')

# Aussi exporter les modules pour compatibilité
if EXPERT_AVAILABLE:
    from . import expert
if AUTH_AVAILABLE:
    from . import auth
if ADMIN_AVAILABLE:
    from . import admin
if HEALTH_AVAILABLE:
    from . import health
if SYSTEM_AVAILABLE:
    from . import system
if LOGGING_AVAILABLE:
    from . import logging

print(f"📦 Modules API v1 disponibles: {__all__}")
print(f"🔧 Status: Expert={EXPERT_AVAILABLE}, Auth={AUTH_AVAILABLE}, Admin={ADMIN_AVAILABLE}")
print(f"🔧 Status: Health={HEALTH_AVAILABLE}, System={SYSTEM_AVAILABLE}, Logging={LOGGING_AVAILABLE}")