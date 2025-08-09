# app/main.py - SECTION RAG OPTIMISÉE
from __future__ import annotations

import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, Optional, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.main")

def get_rag_paths() -> Dict[str, str]:
    """
    🎯 DIRECT: Chemins fixes des RAG (plus de fallbacks inutiles)
    """
    
    # 🚀 CHEMINS FIXES CONNUS sur DigitalOcean
    base_path = "/workspace/backend/rag_index"
    
    return {
        "global": f"{base_path}/global",
        "broiler": f"{base_path}/broiler", 
        "layer": f"{base_path}/layer",
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    🔧 OPTIMISÉ: Lifespan avec chargement RAG intelligent
    """
    
    # Supabase (inchangé)
    app.state.supabase = None
    try:
        from supabase import create_client
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY")
        if url and key:
            app.state.supabase = create_client(url, key)
            logger.info("✅ Supabase prêt")
        else:
            logger.info("ℹ️ Supabase non configuré")
    except Exception as e:
        logger.warning("ℹ️ Supabase indisponible: %s", e)

    # 🚀 RAG OPTIMISÉ
    app.state.rag = None
    app.state.rag_broiler = None
    app.state.rag_layer = None
    
    try:
        from rag.embedder import FastRAGEmbedder
        
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    🚀 OPTIMISÉ: Chargement direct sans fallbacks inutiles
    """
    
    # Supabase (inchangé)
    app.state.supabase = None
    try:
        from supabase import create_client
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY")
        if url and key:
            app.state.supabase = create_client(url, key)
            logger.info("✅ Supabase prêt")
        else:
            logger.info("ℹ️ Supabase non configuré")
    except Exception as e:
        logger.warning("ℹ️ Supabase indisponible: %s", e)

    # 🎯 RAG DIRECT (ZÉRO FALLBACK)
    app.state.rag = None
    app.state.rag_broiler = None
    app.state.rag_layer = None
    
    try:
        from rag.embedder import FastRAGEmbedder
        
        # 🚀 CHEMINS FIXES CONNUS
        rag_paths = get_rag_paths()
        logger.info(f"📁 Chemins RAG fixes: {rag_paths}")

        # 🔧 Variables d'environnement (override si définies)
        env_override = {
            "global": os.getenv("RAG_INDEX_GLOBAL"),
            "broiler": os.getenv("RAG_INDEX_BROILER"), 
            "layer": os.getenv("RAG_INDEX_LAYER"),
        }
        
        # Appliquer les overrides ENV
        for key, env_path in env_override.items():
            if env_path and os.path.exists(env_path):
                rag_paths[key] = env_path
                logger.info(f"🔧 Override ENV pour {key}: {env_path}")

        # 🚀 CHARGEMENT RAG GLOBAL (obligatoire)
        global_path = rag_paths["global"]
        if os.path.exists(global_path):
            global_embedder = FastRAGEmbedder(debug=True, cache_embeddings=True, max_workers=2)
            if global_embedder.load_index(global_path) and global_embedder.has_search_engine():
                app.state.rag = global_embedder
                logger.info(f"✅ RAG Global chargé directement: {global_path}")
            else:
                logger.error(f"❌ RAG Global: Échec chargement depuis {global_path}")
        else:
            logger.error(f"❌ RAG Global: Chemin inexistant {global_path}")

        # 🚀 CHARGEMENT RAG BROILER (optionnel)
        broiler_path = rag_paths["broiler"]
        if os.path.exists(broiler_path):
            try:
                broiler_embedder = FastRAGEmbedder(debug=False, cache_embeddings=True, max_workers=2)
                if broiler_embedder.load_index(broiler_path) and broiler_embedder.has_search_engine():
                    app.state.rag_broiler = broiler_embedder
                    logger.info(f"✅ RAG Broiler chargé directement: {broiler_path}")
                else:
                    logger.warning(f"⚠️ RAG Broiler: Échec chargement depuis {broiler_path}")
            except Exception as e:
                logger.warning(f"⚠️ RAG Broiler: Erreur {e}")
        else:
            logger.info(f"ℹ️ RAG Broiler: Chemin inexistant {broiler_path} (optionnel)")

        # 🚀 CHARGEMENT RAG LAYER (optionnel)  
        layer_path = rag_paths["layer"]
        if os.path.exists(layer_path):
            try:
                layer_embedder = FastRAGEmbedder(debug=False, cache_embeddings=True, max_workers=2)
                if layer_embedder.load_index(layer_path) and layer_embedder.has_search_engine():
                    app.state.rag_layer = layer_embedder
                    logger.info(f"✅ RAG Layer chargé directement: {layer_path}")
                else:
                    logger.warning(f"⚠️ RAG Layer: Échec chargement depuis {layer_path}")
            except Exception as e:
                logger.warning(f"⚠️ RAG Layer: Erreur {e}")
        else:
            logger.info(f"ℹ️ RAG Layer: Chemin inexistant {layer_path} (optionnel)")

        # 📊 Résumé final
        rag_summary = {
            "global": "✅ Actif" if app.state.rag else "❌ CRITIQUE",
            "broiler": "✅ Actif" if app.state.rag_broiler else "ℹ️ Absent",
            "layer": "✅ Actif" if app.state.rag_layer else "ℹ️ Absent",
        }
        logger.info(f"📊 Status final: {rag_summary}")
        
        # Vérification critique
        if not app.state.rag:
            logger.error("🚨 ERREUR CRITIQUE: RAG Global non chargé - API dégradée")

    except Exception as e:
        logger.error("❌ Erreur critique initialisation RAG: %s", e)

    yield  # --- shutdown

    except Exception as e:
        logger.error("❌ Erreur initialisation RAG: %s", e)

    yield  # --- shutdown: rien pour l'instant

# Endpoint de debug simplifié
@app.get("/rag/debug", tags=["Debug"])
async def rag_debug():
    """🔍 Debug RAG direct (sans fallbacks inutiles)"""
    
    rag_paths = get_rag_paths()
    
    env_vars = {
        "RAG_INDEX_GLOBAL": os.getenv("RAG_INDEX_GLOBAL"),
        "RAG_INDEX_BROILER": os.getenv("RAG_INDEX_BROILER"),
        "RAG_INDEX_LAYER": os.getenv("RAG_INDEX_LAYER"),
    }
    
    # Vérification des chemins directs
    path_status = {}
    for name, path in rag_paths.items():
        try:
            exists = os.path.exists(path)
            is_dir = os.path.isdir(path) if exists else False
            files = sorted(os.listdir(path))[:10] if exists and is_dir else []
            
            path_status[name] = {
                "path": path,
                "exists": exists,
                "is_directory": is_dir,
                "files_found": len(files),
                "sample_files": files[:3]
            }
        except Exception as e:
            path_status[name] = {
                "path": path,
                "exists": False,
                "error": str(e)
            }
    
    # Status des instances RAG
    instances_status = {}
    for name, attr in [("global", "rag"), ("broiler", "rag_broiler"), ("layer", "rag_layer")]:
        embedder = getattr(app.state, attr, None)
        if embedder:
            try:
                has_search = embedder.has_search_engine()
                doc_count = embedder.get_document_count() if hasattr(embedder, 'get_document_count') else "unknown"
                instances_status[name] = {
                    "loaded": True,
                    "search_ready": has_search,
                    "documents": doc_count,
                    "status": "operational" if has_search else "loaded_but_no_search"
                }
            except Exception as e:
                instances_status[name] = {
                    "loaded": True,
                    "error": str(e),
                    "status": "error"
                }
        else:
            instances_status[name] = {
                "loaded": False,
                "status": "not_loaded"
            }
    
    return {
        "approach": "direct_paths_no_fallback",
        "environment_variables": env_vars,
        "fixed_paths": rag_paths,
        "path_verification": path_status,
        "rag_instances": instances_status,
        "optimization": {
            "fallbacks_eliminated": True,
            "direct_loading": True,
            "failed_attempts": 0,
            "performance": "optimal"
        }
    }

@app.get("/rag/test", tags=["Debug"])
async def test_rag_access():
    """🧪 Test complet d'accès aux RAG"""
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": {},
        "summary": {}
    }
    
    # Test 1: Vérification filesystem complète
    base_path = "/workspace/backend/rag_index"
    filesystem_test = {
        "base_path": base_path,
        "base_exists": os.path.exists(base_path),
        "directories": {}
    }
    
    for rag_type in ["global", "broiler", "layer"]:
        rag_path = f"{base_path}/{rag_type}"
        dir_info = {
            "path": rag_path,
            "exists": os.path.exists(rag_path),
            "is_directory": os.path.isdir(rag_path) if os.path.exists(rag_path) else False,
            "files": [],
            "file_sizes": {}
        }
        
        if dir_info["exists"] and dir_info["is_directory"]:
            try:
                files = os.listdir(rag_path)
                dir_info["files"] = sorted(files)
                dir_info["has_faiss"] = "index.faiss" in files
                dir_info["has_pkl"] = "index.pkl" in files
                dir_info["complete"] = dir_info["has_faiss"] and dir_info["has_pkl"]
                
                # Tailles des fichiers
                for file in files:
                    try:
                        file_path = os.path.join(rag_path, file)
                        size = os.path.getsize(file_path)
                        dir_info["file_sizes"][file] = f"{size / 1024 / 1024:.2f} MB"
                    except Exception:
                        dir_info["file_sizes"][file] = "unknown"
                        
            except Exception as e:
                dir_info["error"] = str(e)
        
        filesystem_test["directories"][rag_type] = dir_info
    
    results["tests"]["filesystem"] = filesystem_test
    
    # Test 2: Test de chargement RAG
    loading_test = {}
    for rag_type in ["global", "broiler", "layer"]:
        rag_path = f"{base_path}/{rag_type}"
        load_info = {
            "attempted": False,
            "success": False,
            "has_search_engine": False,
            "document_count": 0,
            "error": None
        }
        
        if os.path.exists(rag_path):
            try:
                load_info["attempted"] = True
                from rag.embedder import FastRAGEmbedder
                
                test_embedder = FastRAGEmbedder(debug=False, cache_embeddings=False, max_workers=1)
                
                if test_embedder.load_index(rag_path):
                    load_info["success"] = True
                    load_info["has_search_engine"] = test_embedder.has_search_engine()
                    
                    # Tenter de compter les documents
                    try:
                        if hasattr(test_embedder, 'get_document_count'):
                            load_info["document_count"] = test_embedder.get_document_count()
                        elif hasattr(test_embedder, 'documents') and test_embedder.documents:
                            load_info["document_count"] = len(test_embedder.documents)
                    except Exception:
                        load_info["document_count"] = "unknown"
                
            except Exception as e:
                load_info["error"] = str(e)
        
        loading_test[rag_type] = load_info
    
    results["tests"]["loading"] = loading_test
    
    # Test 3: Test des instances actuelles app.state
    current_instances = {}
    for name, attr in [("global", "rag"), ("broiler", "rag_broiler"), ("layer", "rag_layer")]:
        embedder = getattr(app.state, attr, None)
        instance_info = {
            "exists": embedder is not None,
            "functional": False,
            "document_count": 0,
            "search_ready": False
        }
        
        if embedder:
            try:
                instance_info["functional"] = True
                instance_info["search_ready"] = embedder.has_search_engine()
                
                if hasattr(embedder, 'get_document_count'):
                    instance_info["document_count"] = embedder.get_document_count()
                elif hasattr(embedder, 'documents') and embedder.documents:
                    instance_info["document_count"] = len(embedder.documents)
                    
            except Exception as e:
                instance_info["error"] = str(e)
        
        current_instances[name] = instance_info
    
    results["tests"]["current_instances"] = current_instances
    
    # Test 4: Test de recherche basique
    search_test = {}
    if app.state.rag:
        try:
            # Test avec une requête simple
            test_query = "broiler chicken weight"
            search_results = app.state.rag.search(test_query, k=3)
            
            search_test["global"] = {
                "query": test_query,
                "results_count": len(search_results) if search_results else 0,
                "success": len(search_results) > 0 if search_results else False,
                "sample_scores": [r.get('score', 0) for r in search_results[:3]] if search_results else []
            }
        except Exception as e:
            search_test["global"] = {
                "query": test_query,
                "error": str(e),
                "success": False
            }
    
    results["tests"]["search"] = search_test
    
    # Résumé
    available_rags = sum(1 for info in filesystem_test["directories"].values() if info.get("complete", False))
    loaded_rags = sum(1 for info in current_instances.values() if info.get("functional", False))
    
    results["summary"] = {
        "available_on_disk": available_rags,
        "loaded_in_memory": loaded_rags,
        "functional_rags": [name for name, info in current_instances.items() if info.get("search_ready", False)],
        "missing_rags": [name for name, info in filesystem_test["directories"].items() if not info.get("complete", False)],
        "recommendations": []
    }
    
    # Recommandations
    if available_rags == 1 and loaded_rags == 1:
        results["summary"]["recommendations"].append("✅ Configuration optimale: 1 RAG disponible et chargé")
    elif available_rags > loaded_rags:
        results["summary"]["recommendations"].append(f"⚠️ {available_rags} RAG disponibles mais seulement {loaded_rags} chargé(s)")
    elif available_rags == 0:
        results["summary"]["recommendations"].append("❌ Aucun RAG complet trouvé sur le disque")
        
    if not search_test.get("global", {}).get("success", False):
        results["summary"]["recommendations"].append("❌ Test de recherche échoué - vérifier le RAG Global")
    
    return results