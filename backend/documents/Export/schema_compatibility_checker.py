#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour vérifier la compatibilité du schéma Weaviate
avec le pipeline d'ingestion
"""

import os
import weaviate
import weaviate.classes as wvc
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
COLLECTION_NAME = "InteliaKnowledge"

def connect_weaviate():
    """Connexion à Weaviate"""
    try:
        auth = wvc.init.Auth.api_key(WEAVIATE_API_KEY)
        headers = {"X-OpenAI-Api-Key": OPENAI_API_KEY}
        
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=auth,
            headers=headers
        )
        
        if client.is_ready():
            print("✅ Connexion Weaviate réussie")
            return client
        else:
            print("❌ Weaviate non prêt")
            return None
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return None

def get_current_schema(client):
    """Récupère le schéma actuel de la collection"""
    try:
        if not client.collections.exists(COLLECTION_NAME):
            print(f"❌ Collection '{COLLECTION_NAME}' n'existe pas")
            return None
        
        collection = client.collections.get(COLLECTION_NAME)
        schema = collection.config.get()
        
        print(f"✅ Schéma récupéré pour '{COLLECTION_NAME}'")
        return schema
    except Exception as e:
        print(f"❌ Erreur récupération schéma: {e}")
        return None

def analyze_schema_properties(schema):
    """Analyse les propriétés du schéma actuel"""
    if not schema or not hasattr(schema, 'properties'):
        print("❌ Impossible d'analyser les propriétés")
        return {}
    
    current_properties = {}
    
    print("\n📋 PROPRIÉTÉS ACTUELLES DU SCHÉMA:")
    print("-" * 50)
    
    for prop in schema.properties:
        prop_name = prop.name
        prop_type = prop.data_type
        current_properties[prop_name] = str(prop_type)
        print(f"  • {prop_name:<20} : {prop_type}")
    
    return current_properties

def get_pipeline_requirements():
    """Définit les propriétés requises par le pipeline"""
    return {
        # Propriétés de base
        "content": "TEXT",
        "title": "TEXT", 
        "source": "TEXT",
        "category": "TEXT",
        "language": "TEXT",
        
        # Propriétés métier (ATTENTION: différences possibles)
        "geneticLine": "TEXT",      # Pipeline utilise: geneticLine
        "birdType": "TEXT",         # Pipeline utilise: birdType  
        "siteType": "TEXT",         # Pipeline utilise: siteType
        "phase": "TEXT",
        
        # Propriétés techniques
        "originalFile": "TEXT",
        "fileHash": "TEXT",
        "syncTimestamp": "NUMBER",
        "chunkIndex": "NUMBER", 
        "totalChunks": "NUMBER",
        "isComplete": "BOOL",
        
        # Propriétés de classification
        "classificationConfidence": "NUMBER",
        "detectedMetrics": "TEXT[]",  # Liste de strings
        "entitiesCount": "NUMBER",
        "qualityScore": "NUMBER",
        "sourceMetadata": "OBJECT"    # Objet complexe
    }

def check_compatibility(current_props, required_props):
    """Vérifie la compatibilité entre schéma actuel et requis"""
    print("\n🔍 ANALYSE DE COMPATIBILITÉ:")
    print("-" * 50)
    
    missing_props = []
    type_mismatches = []
    compatible_props = []
    
    for prop_name, required_type in required_props.items():
        if prop_name not in current_props:
            missing_props.append(prop_name)
            print(f"❌ MANQUANT: {prop_name} ({required_type})")
        else:
            current_type = current_props[prop_name]
            if required_type in current_type or current_type in required_type:
                compatible_props.append(prop_name)
                print(f"✅ COMPATIBLE: {prop_name} ({current_type})")
            else:
                type_mismatches.append((prop_name, current_type, required_type))
                print(f"⚠️  TYPE DIFFÉRENT: {prop_name} (actuel: {current_type}, requis: {required_type})")
    
    # Propriétés supplémentaires dans le schéma actuel
    extra_props = [p for p in current_props if p not in required_props]
    if extra_props:
        print(f"\nℹ️  PROPRIÉTÉS SUPPLÉMENTAIRES (non utilisées par le pipeline):")
        for prop in extra_props:
            print(f"  • {prop} ({current_props[prop]})")
    
    return {
        "missing": missing_props,
        "type_mismatches": type_mismatches, 
        "compatible": compatible_props,
        "extra": extra_props
    }

def generate_recommendations(analysis):
    """Génère des recommandations basées sur l'analyse"""
    print("\n💡 RECOMMANDATIONS:")
    print("-" * 50)
    
    if not analysis["missing"] and not analysis["type_mismatches"]:
        print("✅ PARFAIT: Le schéma est entièrement compatible avec le pipeline!")
        return "compatible"
    
    if analysis["missing"]:
        print("🔧 PROPRIÉTÉS MANQUANTES à ajouter:")
        for prop in analysis["missing"]:
            print(f"  • {prop}")
        print("   → Solution: Exécuter une migration de schéma")
    
    if analysis["type_mismatches"]:
        print("⚠️  INCOMPATIBILITÉS DE TYPE:")
        for prop, current, required in analysis["type_mismatches"]:
            print(f"  • {prop}: {current} → {required}")
        print("   → Solution: Adapter le code du pipeline ou migrer le schéma")
    
    # Vérification critique pour les champs métier
    critical_mismatches = [
        (prop, current, required) for prop, current, required in analysis["type_mismatches"]
        if prop in ["geneticLine", "birdType", "siteType", "species"]
    ]
    
    if critical_mismatches:
        print("\n🚨 ATTENTION - INCOMPATIBILITÉS CRITIQUES:")
        for prop, current, required in critical_mismatches:
            print(f"   {prop}: pipeline attend {required}, schéma a {current}")
        return "critical_issues"
    
    return "minor_issues"

def suggest_code_fixes(analysis):
    """Suggère des corrections de code si nécessaire"""
    if "species" in [prop for prop, _, _ in analysis["type_mismatches"]]:
        print("\n🔧 CORRECTION CODE SUGGÉRÉE:")
        print("-" * 50)
        print("Dans votre pipeline, modifiez la construction du document Weaviate:")
        print("")
        print("# AVANT (dans _process_and_upload_document):")
        print('weaviate_doc = {')
        print('    "geneticLine": classification.genetic_line if classification.genetic_line else "general",')
        print('    "birdType": classification.bird_type if classification.bird_type else "general",')
        print('    "siteType": classification.site_type if classification.site_type else "general",')
        print('    # ...')
        print('}')
        print("")
        print("# APRÈS (adapté au schéma existant):")
        print('weaviate_doc = {')
        print('    "geneticLine": classification.genetic_line if classification.genetic_line else "general",')
        print('    "species": classification.bird_type if classification.bird_type else "general",  # Utilise species au lieu de birdType')
        print('    "siteType": classification.site_type if classification.site_type else "general",')
        print('    # ...')
        print('}')

def main():
    print("🔍 DIAGNOSTIC DE COMPATIBILITÉ SCHÉMA WEAVIATE")
    print("=" * 60)
    
    # Vérifications préliminaires
    if not all([WEAVIATE_URL, WEAVIATE_API_KEY, OPENAI_API_KEY]):
        print("❌ Variables d'environnement manquantes")
        print("Vérifiez: WEAVIATE_URL, WEAVIATE_API_KEY, OPENAI_API_KEY")
        return
    
    # Connexion
    client = connect_weaviate()
    if not client:
        return
    
    try:
        # Récupération du schéma actuel
        schema = get_current_schema(client)
        if not schema:
            return
        
        # Analyse des propriétés
        current_props = analyze_schema_properties(schema)
        required_props = get_pipeline_requirements()
        
        # Vérification de compatibilité
        analysis = check_compatibility(current_props, required_props)
        
        # Recommandations
        status = generate_recommendations(analysis)
        
        # Corrections de code si nécessaire
        if status == "critical_issues":
            suggest_code_fixes(analysis)
        
        # Résumé final
        print(f"\n📊 RÉSUMÉ:")
        print("-" * 20)
        print(f"✅ Compatible: {len(analysis['compatible'])}")
        print(f"❌ Manquant: {len(analysis['missing'])}")
        print(f"⚠️  Type différent: {len(analysis['type_mismatches'])}")
        print(f"ℹ️  Extra: {len(analysis['extra'])}")
        
        if status == "compatible":
            print("\n🎉 Votre pipeline peut s'exécuter sans modification!")
        elif status == "minor_issues":
            print("\n⚠️  Problèmes mineurs - quelques ajustements nécessaires")
        else:
            print("\n🚨 Problèmes critiques - modifications requises avant exécution")
    
    finally:
        client.close()

if __name__ == "__main__":
    main()
