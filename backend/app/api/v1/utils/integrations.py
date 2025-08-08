import os
from pinecone import Pinecone, ServerlessSpec
from typing import Any, Dict, List
from app.api.v1.utils.openai_utils import safe_embedding_create

class VectorStoreClient:
    """
    Client Pinecone pour la recherche vectorielle,
    avec création automatique de l'index si besoin.
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
        # 1. Génération de l'embedding
        resp = safe_embedding_create(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
            input=text
        )
        emb = resp["data"][0]["embedding"]

        # 2. Requête dans Pinecone
        results = self.index.query(
            vector=emb,
            top_k=top_k,
            include_metadata=True
        )

        # 3. Extraction des métadonnées retournées
        return [match["metadata"] for match in results["matches"]]