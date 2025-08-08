import os
import pinecone
from typing import Any, Dict, List
from app.api.v1.utils.openai_utils import safe_embedding_create

class VectorStoreClient:
    """
    Client Pinecone pour la recherche vectorielle,
    avec création automatique de l'index si besoin.
    """
    def __init__(self):
        api_key     = os.getenv("PINECONE_API_KEY")
        environment = os.getenv("PINECONE_ENVIRONMENT")       # ex. "aped-4627-b74a"
        index_name  = os.getenv("PINECONE_INDEX_NAME", "intelia-expert")

        # Initialisation Pinecone
        pinecone.init(api_key=api_key, environment=environment)

        # Création de l'index si absent
        if index_name not in pinecone.list_indexes():
            pinecone.create_index(
                name=index_name,
                dimension=1536,    # pour text-embedding-ada-002
                metric="cosine"
            )

        # Connexion à l'index
        self.index = pinecone.Index(index_name)

    def query(self, text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Génération de l'embedding
        resp = safe_embedding_create(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
            input=text
        )
        emb = resp["data"][0]["embedding"]

        # Requête dans Pinecone
        results = self.index.query(
            vector=emb,
            top_k=top_k,
            include_metadata=True
        )

        # Retour des métadonnées
        return [match["metadata"] for match in results["matches"]]
