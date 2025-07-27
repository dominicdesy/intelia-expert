"""
app/api/__init__.py
Configuration des imports pour les modules API d'Intelia Expert
STRUCTURE CORRIGÉE - Import depuis v1/
"""

# Import conditionnel de tous les modules disponibles dans v1/
try:
    from .v1 import expert
    print("✅ Module expert importé depuis v1")
except ImportError as e:
    print(f"❌ Erreur import expert v1: {e}")
    expert = None

try:
    from .v1 import auth
    print("✅ Module auth importé depuis v1")
except ImportError as e:
    print(f"❌ Erreur import auth v1: {e}")
    auth = None

try:
    from .v1 import admin
    print("✅ Module admin importé depuis v1")
except ImportError as e:
    print(f"❌ Erreur import admin v1: {e}")
    admin = None

try:
    from .v1 import health
    print("✅ Module health importé depuis v1")
except ImportError as e:
    print(f"❌ Erreur import health v1: {e}")
    health = None

try:
    from .v1 import system
    print("✅ Module system importé depuis v1")  
except ImportError as e:
    print(f"❌ Erreur import system v1: {e}")
    system = None

try:
    from .v1 import logging
    print("✅ Module logging importé depuis v1")
except ImportError as e:
    print(f"❌ Erreur import logging v1: {e}")
    logging = None

# Export des modules disponibles
__all__ = []

if expert:
    __all__.append('expert')
if auth:
    __all__.append('auth') 
if admin:
    __all__.append('admin')
if health:
    __all__.append('health')
if system:
    __all__.append('system')
if logging:
    __all__.append('logging')

print(f"📦 Modules API disponibles depuis v1: {__all__}")
