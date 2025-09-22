#!/usr/bin/env python3
"""
Weaviate Collection Cleanup Tool
Supprime toutes les collections d'une instance Weaviate pour un redémarrage propre.

ATTENTION: Ce script supprime DÉFINITIVEMENT toutes les données.
Utilisez uniquement sur des instances de développement/test.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
try:
    from dotenv import load_dotenv

    # Cherche le .env dans le répertoire courant et parents
    env_paths = [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Variables d'environnement chargées depuis: {env_path}")
            break
except ImportError:
    logger.warning(
        "python-dotenv non installé - utilisez les variables d'environnement système"
    )


class WeaviateCleanupTool:
    """Outil de nettoyage complet pour Weaviate"""

    def __init__(self, weaviate_url: str = None, api_key: str = None):
        self.weaviate_url = weaviate_url or os.getenv("WEAVIATE_URL")
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY")
        self.client = None

        if not self.weaviate_url:
            raise ValueError("WEAVIATE_URL manquante dans .env ou paramètres")
        if not self.api_key:
            raise ValueError("WEAVIATE_API_KEY manquante dans .env ou paramètres")

        self._setup_client()

    def _setup_client(self):
        """Configure le client Weaviate"""
        try:
            import weaviate

            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.weaviate_url,
                auth_credentials=weaviate.auth.AuthApiKey(self.api_key),
            )

            if not self.client.is_ready():
                raise ConnectionError("Impossible de se connecter à Weaviate")

            logger.info(f"✅ Connexion réussie à: {self.weaviate_url}")

        except ImportError:
            raise ImportError("pip install weaviate-client requis")
        except Exception as e:
            logger.error(f"❌ Erreur de connexion Weaviate: {e}")
            raise

    def list_collections(self) -> List[str]:
        """Liste toutes les collections existantes"""
        try:
            collections = []

            # Méthode 1: API v4
            if hasattr(self.client, "collections"):
                try:
                    collection_names = self.client.collections.list_all()
                    if isinstance(collection_names, dict):
                        collections = list(collection_names.keys())
                    elif hasattr(collection_names, "__iter__"):
                        collections = list(collection_names)
                    else:
                        collections = [str(collection_names)]

                    logger.info(f"📋 Collections trouvées (v4): {collections}")
                    return collections
                except Exception as v4_error:
                    logger.debug(f"Méthode v4 échouée: {v4_error}")

            # Méthode 2: API GraphQL (fallback)
            try:
                schema = self.client.schema.get()
                if "classes" in schema:
                    collections = [cls["class"] for cls in schema["classes"]]
                    logger.info(f"📋 Collections trouvées (GraphQL): {collections}")
                    return collections
            except Exception as graphql_error:
                logger.debug(f"Méthode GraphQL échouée: {graphql_error}")

            # Méthode 3: HTTP direct (fallback ultime)
            try:
                import requests

                response = requests.get(
                    f"{self.weaviate_url}/v1/schema",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if response.status_code == 200:
                    schema = response.json()
                    if "classes" in schema:
                        collections = [cls["class"] for cls in schema["classes"]]
                        logger.info(f"📋 Collections trouvées (HTTP): {collections}")
                        return collections
            except Exception as http_error:
                logger.debug(f"Méthode HTTP échouée: {http_error}")

            logger.warning("⚠️ Aucune méthode de listage n'a fonctionné")
            return []

        except Exception as e:
            logger.error(f"❌ Erreur lors du listage: {e}")
            return []

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Récupère les statistiques d'une collection"""
        try:
            if hasattr(self.client, "collections"):
                collection = self.client.collections.get(collection_name)

                # Tente de récupérer le nombre d'objets
                try:
                    result = collection.aggregate.over_all(total_count=True)
                    count = result.total_count if hasattr(result, "total_count") else 0
                except Exception:
                    # Fallback - essaie fetch_objects avec limit
                    try:
                        objects = collection.query.fetch_objects(limit=1)
                        count = (
                            len(objects.objects) if hasattr(objects, "objects") else 0
                        )
                        if count > 0:
                            count = "1+"  # Au moins 1 objet
                    except Exception:
                        count = "Inconnu"

                return {"name": collection_name, "object_count": count, "exists": True}
            else:
                return {
                    "name": collection_name,
                    "object_count": "Inconnu",
                    "exists": True,
                }

        except Exception as e:
            logger.debug(f"Erreur stats pour {collection_name}: {e}")
            return {"name": collection_name, "object_count": 0, "exists": False}

    def delete_collection(self, collection_name: str) -> bool:
        """Supprime une collection spécifique"""
        try:
            logger.info(f"🗑️ Suppression de la collection: {collection_name}")

            # Méthode 1: API v4
            if hasattr(self.client, "collections"):
                try:
                    self.client.collections.delete(collection_name)
                    logger.info(f"✅ Collection {collection_name} supprimée (v4)")
                    return True
                except Exception as v4_error:
                    logger.debug(
                        f"Suppression v4 échouée pour {collection_name}: {v4_error}"
                    )

            # Méthode 2: Schema API (fallback)
            try:
                self.client.schema.delete_class(collection_name)
                logger.info(f"✅ Collection {collection_name} supprimée (schema)")
                return True
            except Exception as schema_error:
                logger.debug(
                    f"Suppression schema échouée pour {collection_name}: {schema_error}"
                )

            # Méthode 3: HTTP direct (fallback ultime)
            try:
                import requests

                response = requests.delete(
                    f"{self.weaviate_url}/v1/schema/{collection_name}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if response.status_code in [200, 404]:  # 404 = déjà supprimée
                    logger.info(f"✅ Collection {collection_name} supprimée (HTTP)")
                    return True
                else:
                    logger.error(
                        f"❌ Erreur HTTP {response.status_code} pour {collection_name}"
                    )
                    return False
            except Exception as http_error:
                logger.error(
                    f"❌ Suppression HTTP échouée pour {collection_name}: {http_error}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Erreur suppression {collection_name}: {e}")
            return False

    def cleanup_all_collections(self, confirm: bool = False) -> Dict[str, Any]:
        """Supprime toutes les collections"""

        if not confirm:
            logger.error("❌ Nettoyage annulé - paramètre confirm=True requis")
            return {"success": False, "error": "Confirmation requise"}

        logger.warning(
            "🚨 DÉBUT DU NETTOYAGE COMPLET - SUPPRESSION DE TOUTES LES COLLECTIONS"
        )

        # 1. Liste les collections existantes
        collections = self.list_collections()

        if not collections:
            logger.info("✅ Aucune collection à supprimer")
            return {"success": True, "deleted_collections": [], "total_deleted": 0}

        # 2. Récupère les statistiques avant suppression
        stats_before = []
        for collection_name in collections:
            stats = self.get_collection_stats(collection_name)
            stats_before.append(stats)
            logger.info(f"📊 {collection_name}: {stats['object_count']} objets")

        # 3. Suppression de chaque collection
        deleted_collections = []
        failed_collections = []

        for collection_name in collections:
            try:
                if self.delete_collection(collection_name):
                    deleted_collections.append(collection_name)
                else:
                    failed_collections.append(collection_name)
            except Exception as e:
                logger.error(f"❌ Erreur suppression {collection_name}: {e}")
                failed_collections.append(collection_name)

        # 4. Vérification post-suppression
        remaining_collections = self.list_collections()

        # 5. Rapport final
        result = {
            "success": len(failed_collections) == 0,
            "deleted_collections": deleted_collections,
            "failed_collections": failed_collections,
            "remaining_collections": remaining_collections,
            "total_deleted": len(deleted_collections),
            "total_failed": len(failed_collections),
            "stats_before": stats_before,
            "cleanup_timestamp": datetime.now().isoformat(),
        }

        # Logs finaux
        if result["success"]:
            logger.info("🎉 NETTOYAGE TERMINÉ AVEC SUCCÈS")
            logger.info(f"✅ Collections supprimées: {len(deleted_collections)}")
        else:
            logger.warning("⚠️ NETTOYAGE PARTIELLEMENT RÉUSSI")
            logger.warning(f"✅ Supprimées: {len(deleted_collections)}")
            logger.warning(f"❌ Échouées: {len(failed_collections)}")
            logger.warning(f"🔄 Collections restantes: {remaining_collections}")

        return result

    def close(self):
        """Ferme la connexion Weaviate"""
        if self.client:
            self.client.close()
            logger.info("🔒 Connexion Weaviate fermée")


def main():
    """Interface en ligne de commande"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Outil de nettoyage complet Weaviate",
        epilog="ATTENTION: Supprime DÉFINITIVEMENT toutes les collections!",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirme la suppression (REQUIS pour éviter les suppressions accidentelles)",
    )
    parser.add_argument("--url", help="URL Weaviate (ou WEAVIATE_URL dans .env)")
    parser.add_argument(
        "--api-key", help="Clé API Weaviate (ou WEAVIATE_API_KEY dans .env)"
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Liste seulement les collections sans supprimer",
    )

    args = parser.parse_args()

    try:
        # Initialisation
        cleanup_tool = WeaviateCleanupTool(weaviate_url=args.url, api_key=args.api_key)

        # Mode liste seulement
        if args.list_only:
            print("\n📋 COLLECTIONS EXISTANTES:")
            collections = cleanup_tool.list_collections()

            if not collections:
                print("   Aucune collection trouvée")
            else:
                for collection_name in collections:
                    stats = cleanup_tool.get_collection_stats(collection_name)
                    print(f"   • {collection_name}: {stats['object_count']} objets")

            cleanup_tool.close()
            return 0

        # Vérification de confirmation
        if not args.confirm:
            print("\n❌ ERREUR: Le paramètre --confirm est requis pour la suppression")
            print("💡 Utilisez --list-only pour voir les collections sans supprimer")
            print("⚠️  Exemple: python weaviate_cleanup.py --confirm")
            return 1

        # Confirmation interactive supplémentaire
        print("\n🚨 ATTENTION: Vous allez supprimer TOUTES les collections Weaviate")
        print(f"🎯 Instance cible: {cleanup_tool.weaviate_url}")

        # Liste les collections qui seront supprimées
        collections = cleanup_tool.list_collections()
        if collections:
            print(f"\n📋 Collections qui seront supprimées ({len(collections)}):")
            for collection_name in collections:
                stats = cleanup_tool.get_collection_stats(collection_name)
                print(f"   • {collection_name}: {stats['object_count']} objets")
        else:
            print("\n✅ Aucune collection à supprimer")
            cleanup_tool.close()
            return 0

        # Confirmation finale
        response = input(
            f"\n❓ Confirmer la suppression de {len(collections)} collection(s)? (tapez 'OUI' pour confirmer): "
        )

        if response != "OUI":
            print("❌ Suppression annulée par l'utilisateur")
            cleanup_tool.close()
            return 1

        # Exécution du nettoyage
        result = cleanup_tool.cleanup_all_collections(confirm=True)

        # Rapport final
        print("\n📊 RAPPORT DE NETTOYAGE:")
        print(f"   ✅ Collections supprimées: {result['total_deleted']}")
        print(f"   ❌ Échecs: {result['total_failed']}")
        print(f"   🔄 Collections restantes: {len(result['remaining_collections'])}")

        if result["failed_collections"]:
            print("\n⚠️ Collections non supprimées:")
            for failed in result["failed_collections"]:
                print(f"   • {failed}")

        cleanup_tool.close()
        return 0 if result["success"] else 1

    except KeyboardInterrupt:
        print("\n\n⏹️ Interruption utilisateur - Nettoyage annulé")
        return 1
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return 1


# Fonction utilitaire pour usage programmatique
def quick_cleanup(
    weaviate_url: str = None, api_key: str = None, confirm: bool = False
) -> bool:
    """Nettoyage rapide programmatique"""
    try:
        cleanup_tool = WeaviateCleanupTool(weaviate_url, api_key)
        result = cleanup_tool.cleanup_all_collections(confirm=confirm)
        cleanup_tool.close()
        return result["success"]
    except Exception as e:
        logger.error(f"Erreur nettoyage rapide: {e}")
        return False


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
