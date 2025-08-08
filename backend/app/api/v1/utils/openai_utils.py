import openai
import os

def safe_chat_completion(**kwargs):
    """
    Wrapper sécurisé pour openai.chat.completions.create
    Vérifie la présence de la clé API et gère les erreurs.
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configurée dans les variables d'environnement.")
    openai.api_key = key
    try:
        return openai.chat.completions.create(**kwargs)
    except Exception as e:
        raise RuntimeError(f"Erreur lors de l'appel à OpenAI ChatCompletion: {e}")

def safe_embedding_create(input, model="text-embedding-ada-002", **kwargs):
    """
    Wrapper sécurisé pour openai.embeddings.create
    Vérifie la clé API et gère les erreurs. Retourne toujours une liste d'embeddings.
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configurée dans les variables d'environnement.")
    openai.api_key = key
    try:
        response = openai.embeddings.create(input=input, model=model, **kwargs)
        # openai.embeddings.create retourne un objet avec une clé .data (v1) ou ['data'] (v0.28)
        # Compatibilité: v1 = .data; v0.28 = ['data']
        data = getattr(response, 'data', None) or response.get('data', None)
        if not data:
            raise RuntimeError("La réponse OpenAI Embeddings ne contient pas de données.")
        return [item.embedding if hasattr(item, "embedding") else item["embedding"] for item in data]
    except Exception as e:
        raise RuntimeError(f"Erreur lors de l'appel à OpenAI Embedding: {e}")
