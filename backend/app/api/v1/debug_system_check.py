#!/usr/bin/env python3
"""
local_diagnostic.py - DIAGNOSTIC LOCAL DEPUIS app/api/v1

🚨 SCRIPT DE DIAGNOSTIC DEPUIS LE DOSSIER COURANT
Vérifie les fichiers présents et leur contenu.
"""

import os
import sys

def check_files_present():
    """Vérifie quels fichiers sont présents"""
    
    print("📁 === VÉRIFICATION FICHIERS PRÉSENTS ===")
    
    files_to_check = [
        "conversation_memory.py",
        "conversation_memory_enhanced.py", 
        "expert_services.py",
        "expert_integrations.py",
        "expert_utils.py"
    ]
    
    files_status = {}
    
    for filename in files_to_check:
        exists = os.path.exists(filename)
        if exists:
            size = os.path.getsize(filename)
            print(f"✅ {filename} - {size} bytes")
            files_status[filename] = {"exists": True, "size": size}
        else:
            print(f"❌ {filename} - MANQUANT")
            files_status[filename] = {"exists": False, "size": 0}
    
    return files_status

def check_memory_file_content():
    """Vérifie le contenu du fichier de mémoire"""
    
    print("\n🧠 === VÉRIFICATION CONTENU FICHIER MÉMOIRE ===")
    
    # Vérifier conversation_memory.py
    if os.path.exists("conversation_memory.py"):
        print("📄 Analyse conversation_memory.py...")
        
        with open("conversation_memory.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Vérifier les fonctions critiques
        critical_functions = [
            "find_original_question",
            "mark_question_for_clarification", 
            "IntelligentEntities",
            "get_conversation_memory_stats",
            "original_question_recovery"
        ]
        
        missing_functions = []
        for func in critical_functions:
            if func not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ Fonctions manquantes dans conversation_memory.py: {missing_functions}")
            print("🚨 PROBLÈME: Vous utilisez l'ANCIEN système de mémoire")
            return False
        else:
            print("✅ Toutes les fonctions critiques présentes dans conversation_memory.py")
            return True
    
    # Vérifier conversation_memory_enhanced.py
    elif os.path.exists("conversation_memory_enhanced.py"):
        print("📄 conversation_memory_enhanced.py existe mais conversation_memory.py manque")
        print("🔧 SOLUTION: Renommer conversation_memory_enhanced.py → conversation_memory.py")
        return False
    
    else:
        print("❌ Aucun fichier de mémoire trouvé")
        return False

def check_expert_services_content():
    """Vérifie le contenu d'expert_services.py"""
    
    print("\n⚙️ === VÉRIFICATION CONTENU EXPERT SERVICES ===")
    
    if not os.path.exists("expert_services.py"):
        print("❌ expert_services.py manquant")
        return False
    
    with open("expert_services.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Vérifier les méthodes critiques ajoutées
    critical_methods = [
        "_extract_age_from_original_question",
        "_build_complete_enriched_question",
        "_process_clarification_response_corrected",
        "age_info = self._extract_age_from_original_question"
    ]
    
    missing_methods = []
    for method in critical_methods:
        if method not in content:
            missing_methods.append(method)
    
    if missing_methods:
        print(f"❌ Méthodes manquantes dans expert_services.py: {missing_methods}")
        print("🚨 PROBLÈME: expert_services.py pas mis à jour avec les corrections")
        return False
    else:
        print("✅ Toutes les méthodes critiques présentes dans expert_services.py")
        return True

def check_integrations_imports():
    """Vérifie les imports dans expert_integrations.py"""
    
    print("\n🔗 === VÉRIFICATION IMPORTS INTÉGRATIONS ===")
    
    if not os.path.exists("expert_integrations.py"):
        print("❌ expert_integrations.py manquant")
        return False
    
    with open("expert_integrations.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Vérifier l'import de mémoire
    if "from app.api.v1.conversation_memory_enhanced import" in content:
        print("⚠️ Import pointe vers conversation_memory_enhanced")
        if os.path.exists("conversation_memory_enhanced.py") and not os.path.exists("conversation_memory.py"):
            print("🔧 SOLUTION: Renommer conversation_memory_enhanced.py → conversation_memory.py")
            print("🔧 OU: Changer l'import vers conversation_memory")
            return False
    elif "from app.api.v1.conversation_memory import" in content:
        print("✅ Import pointe vers conversation_memory (correct)")
        return True
    else:
        print("❌ Import de mémoire non trouvé ou incorrect")
        return False

def provide_solutions(files_status, memory_ok, services_ok, integrations_ok):
    """Fournit les solutions basées sur le diagnostic"""
    
    print("\n🔧 === SOLUTIONS RECOMMANDÉES ===")
    
    if not memory_ok:
        if files_status.get("conversation_memory_enhanced.py", {}).get("exists", False):
            print("\n💡 SOLUTION MÉMOIRE:")
            print("   Exécutez cette commande:")
            print("   mv conversation_memory_enhanced.py conversation_memory.py")
            print("   (Cela renomme le fichier enhanced vers le nom standard)")
        else:
            print("\n❌ PROBLÈME CRITIQUE: conversation_memory_enhanced.py manquant")
            print("   Vous devez créer ce fichier avec le contenu de l'artifact")
    
    if not services_ok:
        print("\n💡 SOLUTION SERVICES:")
        print("   Remplacer expert_services.py par le contenu de l'artifact 'expert_services_fixed'")
    
    if not integrations_ok:
        print("\n💡 SOLUTION INTÉGRATIONS:")
        print("   Vérifier que l'import dans expert_integrations.py pointe vers le bon fichier")

def main():
    """Fonction principale"""
    
    print("🔍 === DIAGNOSTIC LOCAL SYSTÈME CLARIFICATION ===")
    print(f"📍 Dossier courant: {os.getcwd()}")
    
    # Vérifications
    files_status = check_files_present()
    memory_ok = check_memory_file_content() 
    services_ok = check_expert_services_content()
    integrations_ok = check_integrations_imports()
    
    print(f"\n📋 === RÉSUMÉ DIAGNOSTIC ===")
    print(f"{'✅' if memory_ok else '❌'} Système de Mémoire: {'OK' if memory_ok else 'PROBLÈME'}")
    print(f"{'✅' if services_ok else '❌'} Services Expert: {'OK' if services_ok else 'PROBLÈME'}")
    print(f"{'✅' if integrations_ok else '❌'} Intégrations: {'OK' if integrations_ok else 'PROBLÈME'}")
    
    if memory_ok and services_ok and integrations_ok:
        print("\n🎉 TOUS LES COMPOSANTS SONT CORRECTS")
        print("🤔 Si le problème persiste, il pourrait être dans la logique de flux")
    else:
        provide_solutions(files_status, memory_ok, services_ok, integrations_ok)

if __name__ == "__main__":
    main()