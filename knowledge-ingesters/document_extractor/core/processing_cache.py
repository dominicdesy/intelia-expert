"""
Gestionnaire de cache intelligent pour éviter les retraitements inutiles
Module extrait du knowledge_extractor pour une meilleure modularité
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class ProcessingCache:
    """Gestionnaire de cache pour éviter les retraitements inutiles"""

    def __init__(self, cache_dir: str = "processing_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "processing_cache.json"
        self.reports_dir = self.cache_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}.ProcessingCache")
        self.cache_data = self._load_cache()

    def _load_cache(self) -> Dict:
        """Charge le cache existant"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    self.logger.info(
                        f"Cache chargé: {len(cache_data.get('processed_files', {}))} fichiers"
                    )
                    return cache_data
            except Exception as e:
                self.logger.warning(f"Erreur chargement cache: {e}")
        else:
            self.logger.info("Nouveau cache créé")

        return {
            "processed_files": {},
            "last_update": datetime.now().isoformat(),
            "version": "1.0",
        }

    def _save_cache(self):
        """Sauvegarde le cache"""
        try:
            self.cache_data["last_update"] = datetime.now().isoformat()
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Cache sauvegardé: {self.cache_file}")
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde cache: {e}")

    def get_file_hash(self, file_path: str) -> str:
        """Calcule le hash d'un fichier pour détecter les modifications"""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""

    def should_process_file(
        self, file_path: str, min_conformity: float = 0.95, max_age_days: int = 30
    ) -> Dict[str, Any]:
        """Détermine si un fichier doit être traité"""
        file_key = str(Path(file_path).resolve())
        current_hash = self.get_file_hash(file_path)

        # Fichier jamais traité
        if file_key not in self.cache_data["processed_files"]:
            return {
                "should_process": True,
                "reason": "Fichier jamais traité",
                "status": "new",
            }

        file_info = self.cache_data["processed_files"][file_key]

        # Fichier modifié
        if file_info.get("file_hash") != current_hash:
            return {
                "should_process": True,
                "reason": "Fichier modifié",
                "status": "modified",
            }

        # Échec précédent
        if not file_info.get("success", False):
            return {
                "should_process": True,
                "reason": "Échec précédent",
                "status": "failed_retry",
            }

        # Conformité insuffisante
        conformity = file_info.get("final_conformity_score", 0.0)
        if conformity < min_conformity:
            return {
                "should_process": True,
                "reason": f"Conformité insuffisante: {conformity:.1%}",
                "status": "low_conformity",
            }

        # Traitement trop ancien
        last_processed = file_info.get("last_processed")
        if last_processed:
            try:
                last_date = datetime.fromisoformat(
                    last_processed.replace("Z", "+00:00")
                )
                age_days = (datetime.now() - last_date.replace(tzinfo=None)).days
                if age_days > max_age_days:
                    return {
                        "should_process": True,
                        "reason": f"Traitement ancien: {age_days} jours",
                        "status": "outdated",
                    }
            except Exception:
                pass

        return {
            "should_process": False,
            "reason": f"Fichier OK (conformité: {conformity:.1%})",
            "status": "up_to_date",
        }

    def record_processing_result(self, file_path: str, result: Dict[str, Any]):
        """Enregistre le résultat d'un traitement"""
        file_key = str(Path(file_path).resolve())
        file_hash = self.get_file_hash(file_path)

        processing_record = {
            "file_hash": file_hash,
            "last_processed": datetime.now().isoformat(),
            "success": result.get("injection_success", 0) > 0,
            "segments_created": result.get("segments_created", 0),
            "injection_success": result.get("injection_success", 0),
            "injection_errors": result.get("injection_errors", 0),
            "final_conformity_score": result.get("final_conformity_score", 0.0),
            "partial_success": result.get("partial_success", False),
            "report_path": result.get("report_path", ""),
            "error": result.get("error"),
        }

        self.cache_data["processed_files"][file_key] = processing_record
        self._save_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        processed = self.cache_data["processed_files"]
        if not processed:
            return {"total_files": 0}

        successful = sum(1 for info in processed.values() if info.get("success"))
        return {
            "total_files": len(processed),
            "successful": successful,
            "failed": len(processed) - successful,
            "success_rate": successful / len(processed) if processed else 0,
        }

    def cleanup_missing_files(self) -> int:
        """Nettoie le cache des fichiers qui n'existent plus"""
        cache_data = self.cache_data["processed_files"]
        files_to_remove = []
        existing_files = 0

        for file_path in cache_data.keys():
            if Path(file_path).exists():
                existing_files += 1
            else:
                files_to_remove.append(file_path)

        # Nettoyage des fichiers inexistants
        if files_to_remove:
            self.logger.warning(
                f"Nettoyage cache: {len(files_to_remove)} fichiers inexistants supprimés"
            )
            for file_path in files_to_remove:
                del cache_data[file_path]
            self._save_cache()

        # Détection d'incohérence majeure
        if existing_files < len(cache_data) * 0.5:
            self.logger.warning(
                f"Cache incohérent détecté: {existing_files}/{len(cache_data)} fichiers existent"
            )
            if existing_files == 0:
                self.logger.warning(
                    "Cache complètement obsolète - Considérer --force pour reconstruire"
                )

        return len(files_to_remove)
