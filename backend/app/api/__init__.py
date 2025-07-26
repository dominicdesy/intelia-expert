"""
app/api/__init__.py
Configuration des imports pour les modules API d'Intelia Expert
"""

# Import conditionnel de tous les modules disponibles
try:
    from . import expert
    print("✅ Module expert importé")
except ImportError as e:
    print(f"❌ Erreur import expert: {e}")
    expert = None

try:
    from . import auth
    print("✅ Module auth importé")
except ImportError as e:
    print(f"❌ Erreur import auth: {e}")
    auth = None

try:
    from . import admin
    print("✅ Module admin importé")
except ImportError as e:
    print(f"❌ Erreur import admin: {e}")
    admin = None

try:
    from . import health
    print("✅ Module health importé")
except ImportError as e:
    print(f"❌ Erreur import health: {e}")
    health = None

try:
    from . import system
    print("✅ Module system importé")  
except ImportError as e:
    print(f"❌ Erreur import system: {e}")
    system = None

try:
    from . import logging
    print("✅ Module logging importé")
except ImportError as e:
    print(f"❌ Erreur import logging: {e}")
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

print(f"📦 Modules API disponibles: {__all__}")
