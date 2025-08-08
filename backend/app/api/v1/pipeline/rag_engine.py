"""
RAGEngine - Version corrigée avec format de retour standardisé
CONSERVE: Structure originale + logique RAG + prompts
CORRIGE: Retourne un dict au lieu d'une string pour compatibilité DialogueManager
"""
import os
from app.api.v1.utils.integrations import VectorStoreClient
from app.api.v1.utils.openai_utils import safe_chat_completion

class RAGEngine:
    """
    Retrieval-Augmented Generation engine with fallback if no vector results.
    CORRIGÉ: Retourne maintenant un dict standardisé au lieu d'une string.
    """
    def __init__(self):
        self.vector_client = VectorStoreClient()

    def generate_answer(self, question, context):
        """
        CORRIGÉ: Retourne un dict avec métadonnées au lieu d'une string simple
        Format de retour: {
            "response": str,
            "source": str,
            "documents_used": int,
            "warning": str|None
        }
        """
        # ✅ AJOUTÉ: Structure de retour standardisée
        result = {
            "response": "",
            "source": "",
            "documents_used": 0,
            "warning": None
        }
        
        # ✅ CONSERVATION: Logique de recherche documentaire identique
        docs = self.vector_client.query(question)
        
        if not docs:
            # ✅ CONSERVATION: Fallback GPT sans documents (prompt amélioré)
            fallback_prompt = (
                "Vous êtes un expert vétérinaire spécialisé en aviculture et nutrition animale. "
                "Bien que je n'aie pas trouvé de documentation spécifique, répondez de manière "
                "professionnelle et précise en vous basant sur vos connaissances générales.\n\n"
                f"Question: {question}\n"
                f"Contexte disponible: {context}\n\n"
                "Donnez une réponse pratique et utile, en mentionnant que c'est une réponse générale."
            )
            
            try:
                resp = safe_chat_completion(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    messages=[{"role": "user", "content": fallback_prompt}],
                    temperature=0.0,
                    max_tokens=512
                )
                
                # ✅ CORRIGÉ: Retour dict au lieu de string
                result.update({
                    "response": resp.choices[0].message.content.strip(),
                    "source": "openai_fallback",
                    "documents_used": 0,
                    "warning": "Réponse basée sur les connaissances générales - aucun document spécifique trouvé"
                })
                
            except Exception as e:
                # ✅ AJOUTÉ: Gestion d'erreur avec retour cohérent
                result.update({
                    "response": "Je rencontre une difficulté technique pour répondre à votre question. Veuillez réessayer.",
                    "source": "error_fallback",
                    "documents_used": 0,
                    "warning": f"Erreur technique: {str(e)}"
                })
        
        else:
            # ✅ CONSERVATION: RAG avec documents (prompt amélioré)
            doc_content = "\n".join(str(d) for d in docs)
            rag_prompt = (
                "Vous êtes un expert vétérinaire spécialisé en aviculture. "
                "Utilisez UNIQUEMENT les informations documentaires suivantes pour répondre "
                "de façon précise, factuelle et professionnelle. "
                "Ne vous basez que sur ces documents.\n\n"
                f"DOCUMENTS SPÉCIALISÉS:\n{doc_content}\n\n"
                f"QUESTION: {question}\n"
                f"CONTEXTE: {context}\n\n"
                "Réponse basée strictement sur la documentation:"
            )
            
            try:
                resp = safe_chat_completion(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    messages=[{"role": "user", "content": rag_prompt}],
                    temperature=0.0,
                    max_tokens=512
                )
                
                # ✅ CORRIGÉ: Retour dict avec métadonnées RAG
                result.update({
                    "response": resp.choices[0].message.content.strip(),
                    "source": "rag_enhanced",
                    "documents_used": len(docs),
                    "warning": None  # Pas d'avertissement pour réponse RAG complète
                })
                
            except Exception as e:
                # ✅ AJOUTÉ: Fallback en cas d'erreur OpenAI
                result.update({
                    "response": f"Documents trouvés ({len(docs)}) mais erreur de traitement. Consultez un expert.",
                    "source": "rag_error",
                    "documents_used": len(docs),
                    "warning": f"Erreur traitement RAG: {str(e)}"
                })
        
        return result