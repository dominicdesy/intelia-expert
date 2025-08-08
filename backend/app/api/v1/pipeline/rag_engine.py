"""
RAGEngine - Version corrigée avec prompt amélioré pour utiliser effectivement les documents
CONSERVE: Structure originale + logique RAG
CORRIGE: 
- Retourne un dict au lieu d'une string pour compatibilité DialogueManager
- ✅ AMÉLIORATION MAJEURE: Prompt RAG restructuré pour utiliser les documents trouvés
- ✅ AMÉLIORATION: Mention des informations manquantes (race, sexe) pour précision
"""
import os
from app.api.v1.utils.integrations import VectorStoreClient
from app.api.v1.utils.openai_utils import safe_chat_completion

class RAGEngine:
    """
    Retrieval-Augmented Generation engine with fallback if no vector results.
    CORRIGÉ: Retourne maintenant un dict standardisé au lieu d'une string.
    ✅ AMÉLIORATION: Prompt RAG amélioré pour utiliser les documents et mentionner ce qui manque
    """
    def __init__(self):
        self.vector_client = VectorStoreClient()

    def generate_answer(self, question, context):
        """
        CORRIGÉ: Retourne un dict avec métadonnées au lieu d'une string simple
        ✅ AMÉLIORATION: Prompt restructuré pour utiliser les documents trouvés
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
            # ✅ AMÉLIORATION: Fallback GPT sans documents avec prompt plus intelligent
            fallback_prompt = self._build_fallback_prompt(question, context)
            
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
            # ✅ AMÉLIORATION MAJEURE: RAG avec documents - prompt restructuré
            rag_prompt = self._build_rag_prompt(question, context, docs)
            
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

    def _build_rag_prompt(self, question: str, context: dict, docs: list) -> str:
        """
        ✅ NOUVELLE MÉTHODE: Construction du prompt RAG amélioré
        """
        doc_content = "\n".join(str(d) for d in docs)
        
        # ✅ AMÉLIORATION: Analyser le contexte pour identifier ce qui manque
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

    def _build_fallback_prompt(self, question: str, context: dict) -> str:
        """
        ✅ NOUVELLE MÉTHODE: Construction du prompt fallback amélioré
        """
        missing_info = self._identify_missing_context(context)
        
        prompt = f"""Vous êtes un expert vétérinaire spécialisé en aviculture et nutrition animale.

QUESTION: {question}

CONTEXTE DISPONIBLE: {context if context else "Aucun contexte spécifique fourni"}

SITUATION: Aucun document spécialisé trouvé dans la base de données.

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
        ✅ NOUVELLE MÉTHODE: Identifie les informations manquantes importantes
        """
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