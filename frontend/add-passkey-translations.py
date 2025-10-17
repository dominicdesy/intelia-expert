#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour ajouter les traductions WebAuthn/Passkey à tous les fichiers de langue
"""

import json
import os

os.chdir('public/locales')

# Traductions pour WebAuthn/Passkeys (EN comme référence)
passkey_translations = {
    "en": {
        "passkey.title": "Biometric Authentication",
        "passkey.description": "Sign in faster and more securely with Face ID, Touch ID, or fingerprint",
        "passkey.setup.title": "Set up Face ID / Touch ID",
        "passkey.setup.description": "Sign in instantly with your fingerprint or face recognition",
        "passkey.setup.button": "Enable biometric authentication",
        "passkey.setup.deviceName": "Device name (optional)",
        "passkey.setup.devicePlaceholder": "iPhone 15, MacBook Pro, etc.",
        "passkey.setup.success": "Biometric authentication enabled!",
        "passkey.setup.error": "Failed to set up biometric authentication",
        "passkey.setup.notSupported": "Your browser or device does not support biometric authentication",
        "passkey.setup.alreadySetup": "Biometric authentication is already enabled for this device",
        "passkey.login.title": "Sign in with Face ID / Touch ID",
        "passkey.login.button": "Sign in with biometrics",
        "passkey.login.description": "Use your fingerprint or face recognition to sign in instantly",
        "passkey.login.inProgress": "Waiting for biometric authentication...",
        "passkey.login.success": "Successfully signed in!",
        "passkey.login.error": "Biometric authentication failed",
        "passkey.login.canceled": "Authentication canceled",
        "passkey.manage.title": "Manage your devices",
        "passkey.manage.description": "View and manage devices authorized for biometric sign-in",
        "passkey.manage.noDevices": "No devices configured yet",
        "passkey.manage.deviceName": "Device",
        "passkey.manage.addedOn": "Added on",
        "passkey.manage.lastUsed": "Last used",
        "passkey.manage.never": "Never",
        "passkey.manage.delete": "Remove",
        "passkey.manage.confirmDelete": "Remove this device?",
        "passkey.manage.deleteSuccess": "Device removed successfully",
        "passkey.manage.deleteError": "Failed to remove device",
        "passkey.manage.synced": "Synced (iCloud / Google)",
        "passkey.manage.local": "This device only",
        "passkey.info.whatIs": "What is biometric authentication?",
        "passkey.info.description": "A secure and convenient way to sign in using your fingerprint, face, or device PIN instead of a password.",
        "passkey.info.benefits": "More secure than passwords and impossible to phish or steal.",
        "passkey.info.devices": "Works on iPhone, iPad, Android phones, and computers with biometric sensors.",
    },
    "fr": {
        "passkey.title": "Authentification biométrique",
        "passkey.description": "Connectez-vous plus rapidement et en toute sécurité avec Face ID, Touch ID ou empreinte digitale",
        "passkey.setup.title": "Configurer Face ID / Touch ID",
        "passkey.setup.description": "Connectez-vous instantanément avec votre empreinte digitale ou reconnaissance faciale",
        "passkey.setup.button": "Activer l'authentification biométrique",
        "passkey.setup.deviceName": "Nom de l'appareil (optionnel)",
        "passkey.setup.devicePlaceholder": "iPhone 15, MacBook Pro, etc.",
        "passkey.setup.success": "Authentification biométrique activée !",
        "passkey.setup.error": "Échec de la configuration de l'authentification biométrique",
        "passkey.setup.notSupported": "Votre navigateur ou appareil ne supporte pas l'authentification biométrique",
        "passkey.setup.alreadySetup": "L'authentification biométrique est déjà activée pour cet appareil",
        "passkey.login.title": "Se connecter avec Face ID / Touch ID",
        "passkey.login.button": "Se connecter avec biométrie",
        "passkey.login.description": "Utilisez votre empreinte digitale ou reconnaissance faciale pour vous connecter instantanément",
        "passkey.login.inProgress": "En attente de l'authentification biométrique...",
        "passkey.login.success": "Connexion réussie !",
        "passkey.login.error": "Échec de l'authentification biométrique",
        "passkey.login.canceled": "Authentification annulée",
        "passkey.manage.title": "Gérer vos appareils",
        "passkey.manage.description": "Consultez et gérez les appareils autorisés pour la connexion biométrique",
        "passkey.manage.noDevices": "Aucun appareil configuré pour l'instant",
        "passkey.manage.deviceName": "Appareil",
        "passkey.manage.addedOn": "Ajouté le",
        "passkey.manage.lastUsed": "Dernière utilisation",
        "passkey.manage.never": "Jamais",
        "passkey.manage.delete": "Supprimer",
        "passkey.manage.confirmDelete": "Supprimer cet appareil ?",
        "passkey.manage.deleteSuccess": "Appareil supprimé avec succès",
        "passkey.manage.deleteError": "Échec de la suppression de l'appareil",
        "passkey.manage.synced": "Synchronisé (iCloud / Google)",
        "passkey.manage.local": "Cet appareil uniquement",
        "passkey.info.whatIs": "Qu'est-ce que l'authentification biométrique ?",
        "passkey.info.description": "Un moyen sûr et pratique de se connecter en utilisant votre empreinte digitale, votre visage ou le code PIN de votre appareil au lieu d'un mot de passe.",
        "passkey.info.benefits": "Plus sécurisé que les mots de passe et impossible à voler ou hameçonner.",
        "passkey.info.devices": "Fonctionne sur iPhone, iPad, téléphones Android et ordinateurs avec capteurs biométriques.",
    },
    "es": {
        "passkey.title": "Autenticación biométrica",
        "passkey.description": "Inicie sesión más rápido y de forma segura con Face ID, Touch ID o huella dactilar",
        "passkey.setup.title": "Configurar Face ID / Touch ID",
        "passkey.setup.description": "Inicie sesión instantáneamente con su huella dactilar o reconocimiento facial",
        "passkey.setup.button": "Activar autenticación biométrica",
        "passkey.setup.deviceName": "Nombre del dispositivo (opcional)",
        "passkey.setup.devicePlaceholder": "iPhone 15, MacBook Pro, etc.",
        "passkey.setup.success": "¡Autenticación biométrica activada!",
        "passkey.setup.error": "Error al configurar la autenticación biométrica",
        "passkey.setup.notSupported": "Su navegador o dispositivo no admite autenticación biométrica",
        "passkey.setup.alreadySetup": "La autenticación biométrica ya está activada para este dispositivo",
        "passkey.login.title": "Iniciar sesión con Face ID / Touch ID",
        "passkey.login.button": "Iniciar sesión con biometría",
        "passkey.login.description": "Use su huella dactilar o reconocimiento facial para iniciar sesión instantáneamente",
        "passkey.login.inProgress": "Esperando autenticación biométrica...",
        "passkey.login.success": "¡Inicio de sesión exitoso!",
        "passkey.login.error": "Error de autenticación biométrica",
        "passkey.login.canceled": "Autenticación cancelada",
        "passkey.manage.title": "Administrar sus dispositivos",
        "passkey.manage.description": "Ver y administrar dispositivos autorizados para inicio de sesión biométrico",
        "passkey.manage.noDevices": "Aún no hay dispositivos configurados",
        "passkey.manage.deviceName": "Dispositivo",
        "passkey.manage.addedOn": "Agregado el",
        "passkey.manage.lastUsed": "Último uso",
        "passkey.manage.never": "Nunca",
        "passkey.manage.delete": "Eliminar",
        "passkey.manage.confirmDelete": "¿Eliminar este dispositivo?",
        "passkey.manage.deleteSuccess": "Dispositivo eliminado correctamente",
        "passkey.manage.deleteError": "Error al eliminar el dispositivo",
        "passkey.manage.synced": "Sincronizado (iCloud / Google)",
        "passkey.manage.local": "Solo este dispositivo",
        "passkey.info.whatIs": "¿Qué es la autenticación biométrica?",
        "passkey.info.description": "Una forma segura y conveniente de iniciar sesión usando su huella dactilar, rostro o PIN del dispositivo en lugar de una contraseña.",
        "passkey.info.benefits": "Más seguro que las contraseñas e imposible de robar o suplantar.",
        "passkey.info.devices": "Funciona en iPhone, iPad, teléfonos Android y computadoras con sensores biométricos.",
    }
}

# Autres langues: copier EN comme placeholder
other_languages = ['de', 'it', 'pt', 'nl', 'pl', 'ar', 'zh', 'ja', 'hi', 'id', 'th', 'tr', 'vi']

for lang in other_languages:
    passkey_translations[lang] = passkey_translations['en'].copy()

# Ajouter les traductions à chaque fichier
languages = ['en', 'fr', 'es', 'de', 'it', 'pt', 'nl', 'pl', 'ar', 'zh', 'ja', 'hi', 'id', 'th', 'tr', 'vi']

for lang in languages:
    filename = f'{lang}.json'
    print(f'\n=== Traitement de {filename} ===')

    # Charger le fichier existant
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Compter les clés ajoutées
    added_count = 0

    # Ajouter les nouvelles clés passkey
    for key, value in passkey_translations[lang].items():
        if key not in data:
            data[key] = value
            added_count += 1
            print(f'  + Ajout: {key}')

    # Sauvegarder dans l'ordre alphabétique
    ordered_data = dict(sorted(data.items()))

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(ordered_data, f, ensure_ascii=False, indent=2)

    print(f'  OK: {added_count} cles passkey ajoutees')

print('\n=== RESUME ===')
print(f'Traductions passkey ajoutees a {len(languages)} fichiers de langue')
print(f'Total de {len(passkey_translations["en"])} cles par langue')
print('\nNOTE: Les langues autres que EN, FR, ES utilisent les valeurs EN comme placeholder.')
print('Elles devront etre traduites manuellement plus tard.')
