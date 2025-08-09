import os
from pinecone import Pinecone, ServerlessSpec
from typing import Any, Dict, List
import logging
from app.api.v1.utils.openai_utils import safe_embedding_create

logger = logging.getLogger(__name__)

class VectorStoreClient:
    """
    Client Pinecone pour la recherche vectorielle,
    avec création automatique de l'index si besoin.
    
    ✅ CORRECTION CRITIQUE: Fix TypeError "list indices must be integers or slices, not str"
    Le problème venait de l'accès incorrect aux résultats Pinecone
    """
    def __init__(self):
        api_key     = os.getenv("PINECONE_API_KEY")
        environment = os.getenv("PINECONE_ENVIRONMENT")
        index_name  = os.getenv("PINECONE_INDEX_NAME", "intelia-expert")

        # ✅ CORRIGÉ: Initialisation Pinecone v3.x
        self.pc = Pinecone(api_key=api_key)

        # ✅ CORRIGÉ: Création de l'index si absent (nouvelle API)
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        if index_name not in existing_indexes:
            self.pc.create_index(
                name=index_name,
                dimension=1536,    # dimension pour text-embedding-ada-002
                metric="cosine",
                spec=ServerlessSpec(
                    cloud='aws',
                    region=environment or 'us-east-1'
                )
            )

        # ✅ CORRIGÉ: Connexion à l'index (nouvelle API)
        self.index = self.pc.Index(index_name)

    def query(self, text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        ✅ CORRECTION CRITIQUE: Gestion robuste des résultats Pinecone
        """
        try:
            # 1. Génération de l'embedding avec gestion d'erreurs
            logger.debug(f"🔍 Génération embedding pour: {text[:50]}...")
            
            resp = safe_embedding_create(
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
                input=text
            )
            
            # ✅ CORRECTION: Vérification structure réponse OpenAI
            if not resp or "data" not in resp or not resp["data"]:
                logger.error("❌ Réponse OpenAI embedding vide ou malformée")
                return []
            
            emb = resp["data"][0]["embedding"]
            logger.debug(f"✅ Embedding généré: dimension {len(emb)}")

            # 2. Requête dans Pinecone avec gestion d'erreurs
            logger.debug(f"🔍 Requête Pinecone avec top_k={top_k}")
            
            results = self.index.query(
                vector=emb,
                top_k=top_k,
                include_metadata=True
            )
            
            # ✅ CORRECTION CRITIQUE: Debugging structure résultats
            logger.debug(f"🔍 Type résultats Pinecone: {type(results)}")
            logger.debug(f"🔍 Clés résultats: {list(results.keys()) if hasattr(results, 'keys') else 'Pas un dict'}")
            
            # ✅ CORRECTION CRITIQUE: Gestion robuste structure résultats
            if hasattr(results, 'matches') and results.matches:
                # Structure objet avec attribut matches
                matches = results.matches
                logger.debug(f"✅ Trouvé {len(matches)} matches via attribut")
                
            elif isinstance(results, dict) and "matches" in results:
                # Structure dictionnaire avec clé matches
                matches = results["matches"]
                logger.debug(f"✅ Trouvé {len(matches)} matches via dict")
                
            elif isinstance(results, list):
                # ✅ NOUVEAU: Cas où results est directement une liste
                matches = results
                logger.debug(f"✅ Résultats directement en liste: {len(matches)} items")
                
            else:
                # Aucun résultat trouvé
                logger.warning(f"⚠️ Structure résultats Pinecone inattendue: {type(results)}")
                return []

            # 3. ✅ CORRECTION CRITIQUE: Extraction métadonnées robuste
            extracted_metadata = []
            
            for i, match in enumerate(matches):
                try:
                    # ✅ GESTION: Différents formats de match
                    if hasattr(match, 'metadata') and match.metadata:
                        # Format objet avec attribut metadata
                        metadata = match.metadata
                        
                    elif isinstance(match, dict) and "metadata" in match:
                        # Format dictionnaire avec clé metadata
                        metadata = match["metadata"]
                        
                    elif isinstance(match, dict):
                        # ✅ NOUVEAU: Match est directement la metadata
                        metadata = match
                        
                    else:
                        # ✅ FALLBACK: Conversion string si nécessaire
                        logger.warning(f"⚠️ Match {i} format inattendu: {type(match)}")
                        metadata = {"text": str(match)}
                    
                    extracted_metadata.append(metadata)
                    
                except Exception as e:
                    logger.error(f"❌ Erreur extraction metadata match {i}: {e}")
                    # Fallback sécurisé
                    extracted_metadata.append({"text": str(match), "error": str(e)})
            
            logger.info(f"✅ Pinecone: {len(extracted_metadata)} métadonnées extraites")
            return extracted_metadata
            
        except Exception as e:
            logger.error(f"❌ Erreur critique Pinecone query: {type(e).__name__}: {e}")
            logger.error(f"🔍 Détails erreur: {str(e)}")
            
            # ✅ FALLBACK: Retourner liste vide au lieu de crasher
            return []

    def test_connection(self) -> Dict[str, Any]:
        """
        ✅ NOUVELLE MÉTHODE: Test de connexion Pinecone pour diagnostics
        """
        try:
            # Test simple avec embedding factice
            test_vector = [0.1] * 1536  # Dimension text-embedding-ada-002
            
            results = self.index.query(
                vector=test_vector,
                top_k=1,
                include_metadata=True
            )
            
            return {
                "status": "success",
                "message": "Connexion Pinecone fonctionnelle",
                "result_type": str(type(results)),
                "has_matches": hasattr(results, 'matches') or (isinstance(results, dict) and "matches" in results)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Erreur connexion Pinecone: {e}",
                "error_type": type(e).__name__
            }