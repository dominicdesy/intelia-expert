#!/usr/bin/env python3
"""Script pour remplacer les emojis par du texte professionnel dans les logs"""

import re
from pathlib import Path

# Mapping des emojis vers du texte professionnel
EMOJI_REPLACEMENTS = {
    "🔥": "",
    "✅": "[OK]",
    "⚠️": "[WARNING]",
    "❌": "[ERROR]",
    "🚀": "",
    "📚": "",
    "🗂️": "",
    "🔗": "",
    "🧠": "[LangSmith]",
    "⚡": "[RRF]",
    "🌐": "",
    "📊": "",
    "🎯": "[Mode]",
    "🎉": "",
    "🔧": "",
    "📶": "[Mode]",
    "🛡️": "",
}

# Remplacements de messages complets
MESSAGE_REPLACEMENTS = {
    "🔥🔥🔥 DÉMARRAGE VERSION FINALE - ARCHITECTURE CENTRALISÉE 🔥🔥🔥": "Application startup - centralized architecture",
    "🔥🔥🔥 TIMESTAMP LIFESPAN: %s 🔥🔥🔥": "Lifespan timestamp: %s",
    "🔥🔥🔥 LIFESPAN DÉMARRÉ - VERSION FINALE 🔥🔥🔥": "APPLICATION LIFESPAN STARTED",
    "🔧 INJECTION DES SERVICES - ARCHITECTURE CENTRALISÉE 🔧": "Service injection - centralized architecture",
    "✅ ROUTER CENTRALISÉ MIS À JOUR AVEC SERVICES INJECTÉS ✅": "Router updated with injected services",
    "✅ Router mis à jour avec services injectés": "Router updated with injected services",
    "🎉 APPLICATION VERSION FINALE PRÊTE - ARCHITECTURE CENTRALISÉE 🎉": "Application ready - all services initialized",
    "🎉 APPLICATION VERSION FINALE PRÊTE 🎉": "APPLICATION READY",
    "🔥 SHUTDOWN VERSION FINALE 🔥": "Application shutdown initiated",
    "✅ Cache Core opérationnel": "Cache Core operational",
    "⚠️ Cache Core présent mais non opérationnel": "Warning: Cache Core present but not operational",
    "⚠️ Cache Core non initialisé - mode sans cache": "Warning: Cache Core not initialized - cache disabled",
    "⚠️ Cache Core non disponible - mode sans cache": "Warning: Cache Core not available - cache disabled",
    "✅ RAG Engine opérationnel": "RAG Engine operational",
    "⚠️ RAG Engine non disponible": "Warning: RAG Engine not available",
    "✅ Service de traduction opérationnel": "Translation service operational",
    "⚠️ Service de traduction non disponible": "Warning: Translation service not available",
    "🧠 LangSmith actif - Projet:": "LangSmith active - Project:",
    "⚡ RRF Intelligent actif - Learning:": "RRF Intelligent active - Learning:",
    "🌐 API disponible sur": "API available at",
    "📊 Services initialisés:": "Initialized services:",
    "🎯 Mode: COMPLET (tous services opérationnels)": "Mode: FULL (all services operational)",
    "📶 Mode: DÉGRADÉ (services essentiels seulement)": "Mode: DEGRADED (essential services only)",
    "📶 Mode: MINIMAL (fonctionnalités de base)": "Mode: MINIMAL (basic features only)",
    "🚀 Démarrage Intelia Expert Backend - Architecture Modulaire": "Starting Intelia Expert Backend - Modular Architecture",
    "🚀 Démarrage serveur sur": "Starting server on",
    "🚀 DÉMARRAGE SERVEUR VERSION FINALE SUR": "Starting server on",
    "🛡️ Mode dégradé supporté pour cache/Redis": "Degraded mode supported for cache/Redis",
    "🌐 Service de traduction initialisé au démarrage": "Translation service initialized at startup",
    "🔥 VERSION FINALE: 4.0.4-translation-service-fixed 🔥": "Version: 4.0.4-translation-service-fixed",
    "⚠️ Langues non chargées:": "Warning: Languages not loaded:",
    "📚 Domaines disponibles:": "Available domains:",
    "⚠️ Service de traduction retourné None": "Warning: Translation service returned None",
    "❌ Import error service traduction:": "Error: Translation service import failed:",
    "❌ Erreur initialisation service traduction:": "Error: Translation service initialization failed:",
    "⚠️ Erreurs de services externes uniquement - Continuons": "Warning: External service errors only - continuing",
    "⚠️ Application démarrée en mode dégradé": "Warning: Application started in degraded mode",
    "✅ Application démarrée avec succès": "Application started successfully",
    "✅ Health monitor minimal créé": "Minimal health monitor created",
    "✅ Cache Core nettoyé": "Cache Core cleaned up",
    "✅ RAG Engine nettoyé": "RAG Engine cleaned up",
    "✅ Agent RAG nettoyé": "RAG Agent cleaned up",
    "✅ Application arrêtée proprement": "Application stopped cleanly",
    "✅ Rate limiting avec Redis activé": "Rate limiting with Redis enabled",
    "⚠️ Rate limiting en mémoire (Redis indisponible)": "Warning: In-memory rate limiting (Redis unavailable)",
    "⚠️ Redis non disponible pour rate limiting:": "Warning: Redis unavailable for rate limiting:",
    "⚠️ Rate limiting en mémoire activé (fallback)": "Warning: In-memory rate limiting enabled (fallback)",
    "✅ Rate limiting middleware activé (10 req/min/user)": "Rate limiting middleware enabled (10 req/min/user)",
    "⚠️ Application démarrée sans rate limiting": "Warning: Application started without rate limiting",
    "✅ Cache Core initialisé avec succès": "Cache Core initialized successfully",
    "⚠️ Timeout initialisation Cache Core": "Warning: Cache Core initialization timeout",
    "⚠️ Erreur initialisation Cache Core:": "Warning: Cache Core initialization error:",
    "✅ RAG Engine Enhanced initialisé": "RAG Engine Enhanced initialized successfully",
    "⚠️ RAG Engine en mode dégradé": "Warning: RAG Engine in degraded mode",
    "✅ Agent RAG disponible": "RAG Agent available",
}


def remove_emojis_from_file(file_path: Path):
    """Remove emojis from a single file"""
    print(f"Processing {file_path}")

    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # Replace complete messages first
    for old_msg, new_msg in MESSAGE_REPLACEMENTS.items():
        content = content.replace(old_msg, new_msg)

    # Then replace individual emojis
    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        content = content.replace(emoji, replacement)

    # Clean up double spaces
    content = re.sub(r"  +", " ", content)
    content = re.sub(
        r'logger\.(info|warning|error|critical)\("  ', r'logger.\1("', content
    )
    content = re.sub(
        r'logger\.(info|warning|error|critical)\(" ', r'logger.\1("', content
    )

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        print(f"  ✓ Updated {file_path}")
        return True
    else:
        print("  - No changes needed")
        return False


def main():
    """Main function"""
    base_dir = Path(__file__).parent.parent

    files_to_process = [
        base_dir / "main.py",
        base_dir / "utils" / "monitoring.py",
    ]

    updated_count = 0
    for file_path in files_to_process:
        if file_path.exists():
            if remove_emojis_from_file(file_path):
                updated_count += 1
        else:
            print(f"Warning: {file_path} not found")

    print(f"\nProcessed {len(files_to_process)} files, updated {updated_count} files")


if __name__ == "__main__":
    main()
