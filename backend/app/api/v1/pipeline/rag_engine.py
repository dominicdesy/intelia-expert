"""
RAGEngine - Version corrigée avec gestion robuste VectorStoreClient
CONSERVE: Structure originale + logique RAG
CORRIGE: 
- Retourne un dict au lieu d'une string pour compatibilité DialogueManager
- ✅ CORRECTION CRITIQUE: Gestion robuste résultats VectorStoreClient vides/erreurs
- ✅ AMÉLIORATION: Fallback gracieux si Pinecone indisponible
- ✅ AMÉLIORATION: Prompt RAG restructuré pour utiliser effectivement les documents
"""
import os
import logging
from app.api.v1.utils.integrations import VectorStoreClient
from app.api.v1.utils.openai_utils import safe_chat_completion

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Retrieval-Augmented Generation engine with fallback if no vector results.
    
    ✅ CORRECTION CRITIQUE: Gestion robuste des erreurs VectorStoreClient
    - Fix TypeError "list indices must be integers or slices, not str"
    - Fallback gracieux si Pinecone indisponible
    - Validation structure documents retournés
    """
    def __init__(self):
        try:
            self.vector_client = VectorStoreClient()
            self.vector_available = True
            logger.info("✅ RAGEngine: VectorStoreClient initialisé")
        except Exception as e:
            logger.error(f"❌ RAGEngine: Erreur init VectorStoreClient: {e}")
            self.vector_client = None
            self.vector_available = False

    def generate_answer(self, question, context):
        """
        ✅ CORRECTION CRITIQUE: Gestion robuste avec validation structure docs
        
        Format de retour: {
            "response": str,
            "source": str,
            "documents_used": int,
            "warning": str|None
        }
        """
        # ✅ Structure de retour standardisée
        result = {
            "response": "",
            "source": "",
            "documents_used": 0,
            "warning": None
        }
        
        # ✅ CORRECTION CRITIQUE: Gestion robuste recherche documentaire
        docs = []
        search_error = None
        
        if self.vector_available and self.vector_client:
            try:
                logger.debug(f"🔍 RAGEngine: Recherche docs pour: {question[:50]}...")
                docs = self.vector_client.query(question)
                
                # ✅ VALIDATION: Vérification structure docs retournés
                if not isinstance(docs, list):
                    logger.warning(f"⚠️ RAGEngine: docs n'est pas une liste: {type(docs)}")
                    docs = []
                elif docs and not all(isinstance(doc, dict) for doc in docs):
                    logger.warning(f"⚠️ RAGEngine: docs contient des non-dict")
                    # Filtrer uniquement les dicts valides
                    docs = [doc for doc in docs if isinstance(doc, dict)]
                
                logger.info(f"✅ RAGEngine: {len(docs)} documents trouvés")
                
            except Exception as e:
                logger.error(f"❌ RAGEngine: Erreur recherche docs: {type(e).__name__}: {e}")
                docs = []
                search_error = str(e)
        else:
            logger.warning("⚠️ RAGEngine: VectorStoreClient non disponible")
            search_error = "VectorStoreClient non disponible"
        
        # ✅ CORRECTION: Logique docs trouvés vs fallback
        if not docs:
            # ✅ FALLBACK: Pas de documents trouvés
            logger.info("🔄 RAGEngine: Fallback OpenAI (pas de docs)")
            fallback_prompt = self._build_fallback_prompt(question, context, search_error)
            
            try:
                resp = safe_chat_completion(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    messages=[{"role": "user", "content": fallback_prompt}],
                    temperature=0.0,
                    max_tokens=512
                )
                
                warning_msg = "Réponse basée sur les connaissances générales - aucun document spécifique trouvé"
                if search_error:
                    warning_msg += f" (Erreur recherche: {search_error})"
                
                result.update({
                    "response": resp.choices[0].message.content.strip(),
                    "source": "openai_fallback",
                    "documents_used": 0,
                    "warning": warning_msg
                })
                
            except Exception as e:
                logger.error(f"❌ RAGEngine: Erreur OpenAI fallback: {e}")
                result.update({
                    "response": "Je rencontre une difficulté technique pour répondre à votre question. Veuillez réessayer.",
                    "source": "error_fallback",
                    "documents_used": 0,
                    "warning": f"Erreur technique: {str(e)}"
                })
        
        else:
            # ✅ RAG: Documents trouvés
            logger.info(f"🎯 RAGEngine: Génération RAG avec {len(docs)} docs")
            rag_prompt = self._build_rag_prompt(question, context, docs)
            
            try:
                resp = safe_chat_completion(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    messages=[{"role": "user", "content": rag_prompt}],
                    temperature=0.0,
                    max_tokens=512
                )
                
                result.update({
                    "response": resp.choices[0].message.content.strip(),
                    "source": "rag_enhanced",
                    "documents_used": len(docs),
                    "warning": None  # Pas d'avertissement pour réponse RAG complète
                })
                
            except Exception as e:
                logger.error(f"❌ RAGEngine: Erreur OpenAI RAG: {e}")
                result.update({
                    "response": f"Documents trouvés ({len(docs)}) mais erreur de traitement. Consultez un expert.",
                    "source": "rag_error",
                    "documents_used": len(docs),
                    "warning": f"Erreur traitement RAG: {str(e)}"
                })
        
        logger.debug(f"📊 RAGEngine: Réponse générée - source: {result['source']}, docs: {result['documents_used']}")
        return result

    def _build_rag_prompt(self, question: str, context: dict, docs: list) -> str:
        """
        ✅ AMÉLIORATION: Construction prompt RAG avec validation docs
        """
        # ✅ VALIDATION: Extraction contenu docs robuste
        doc_contents = []
        for i, doc in enumerate(docs):
            try:
                if isinstance(doc, dict):
                    # Essayer différentes clés pour le contenu
                    content = (
                        doc.get('text') or 
                        doc.get('content') or 
                        doc.get('metadata', {}).get('text') or
                        str(doc)
                    )
                    doc_contents.append(f"Document {i+1}: {content}")
                else:
                    doc_contents.append(f"Document {i+1}: {str(doc)}")
            except Exception as e:
                logger.warning(f"⚠️ Erreur extraction doc {i}: {e}")
                doc_contents.append(f"Document {i+1}: [Erreur extraction]")
        
        doc_content = "\n".join(doc_contents)
        missing_info = self._identify_missing_context(context)
        
        prompt = f"""Vous êtes un expert vétérinaire spécialisé en aviculture et nutrition animale.

QUESTION: {question}

CONTEXTE DISPONIBLE: {context if context else "Aucun contexte spécifique fourni"}

DOCUMENTS SPÉCIALISÉS TROUVÉS:
{doc_content}

INSTRUCTIONS:
1. Utilisez PRIORITAIREMENT les informations des documents spécialisés ci-dessus
2. Donnez une réponse pratique et précise basée sur ces documents
3. Si les documents contiennent des informations pertinentes (même partielles), utilisez-les
4. Complétez avec vos connaissances générales si nécessaire
5. Mentionnez clairement les sources (documents vs connaissances générales)

{missing_info}

Répondez de manière professionnelle et pratique en utilisant les documents fournis."""

        return prompt

    def _build_fallback_prompt(self, question: str, context: dict, search_error: str = None) -> str:
        """
        ✅ AMÉLIORATION: Prompt fallback avec mention erreur optionnelle
        """
        missing_info = self._identify_missing_context(context)
        
        situation_msg = "Aucun document spécialisé trouvé dans la base de données."
        if search_error:
            situation_msg += f" (Erreur technique: {search_error})"
        
        prompt = f"""Vous êtes un expert vétérinaire spécialisé en aviculture et nutrition animale.

QUESTION: {question}

CONTEXTE DISPONIBLE: {context if context else "Aucun contexte spécifique fourni"}

SITUATION: {situation_msg}

INSTRUCTIONS:
1. Répondez en vous basant sur vos connaissances générales en aviculture
2. Donnez des informations pratiques et utiles
3. Restez professionnel et précis
4. Mentionnez que c'est une réponse générale

{missing_info}

Répondez de manière professionnelle en indiquant qu'il s'agit d'une réponse générale."""

        return prompt

    def _identify_missing_context(self, context: dict) -> str:
        """
        ✅ CONSERVATION: Méthode d'identification contexte manquant
        """
        if not context:
            context = {}
            
        missing_parts = []
        
        # Vérifier les informations clés pour les questions de nutrition/poids
        if not context.get("race") and not context.get("breed"):
            missing_parts.append("la race/lignée génétique (Ross, Cobb, Hubbard, etc.)")
        
        if not context.get("sexe") and not context.get("sex_category"):
            missing_parts.append("le sexe (mâle, femelle, mixte)")
        
        if not context.get("age_jours") and not context.get("age_phase"):
            missing_parts.append("l'âge précis")
        
        if missing_parts:
            missing_text = f"""
INFORMATIONS MANQUANTES POUR PLUS DE PRÉCISION:
Pour une réponse plus précise, il serait utile de connaître : {', '.join(missing_parts)}.

CONSIGNE SPÉCIALE:
- Donnez quand même une réponse générale utile
- Mentionnez que la réponse serait plus précise avec ces informations
- Expliquez pourquoi ces informations sont importantes (ex: les mâles grandissent plus vite que les femelles, les différentes lignées ont des courbes de croissance différentes)
"""
        else:
            missing_text = "CONTEXTE: Informations suffisantes pour une réponse précise."
        
        return missing_text

    def get_status(self) -> dict:
        """
        ✅ NOUVELLE MÉTHODE: Status RAG pour diagnostics
        """
        status = {
            "vector_client_available": self.vector_available,
            "vector_client_type": type(self.vector_client).__name__ if self.vector_client else None
        }
        
        if self.vector_available and hasattr(self.vector_client, 'test_connection'):
            try:
                status["connection_test"] = self.vector_client.test_connection()
            except Exception as e:
                status["connection_test"] = {"status": "error", "error": str(e)}
        
        return status