"""
Validateur de fichiers JSON avec gestion mémoire sécurisée
Module extrait du knowledge_extractor pour une meilleure modularité
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# Configuration sécurisée
MAX_FILE_SIZE_MB = 100
MAX_JSON_DEPTH = 10


class FileValidator:
    """Validateur de fichiers JSON avec gestion mémoire sécurisée"""

    def __init__(self, max_size_mb: int = MAX_FILE_SIZE_MB):
        self.max_size_mb = max_size_mb
        self.logger = logging.getLogger(f"{__name__}.FileValidator")

    def safe_json_load(self, file_path: str) -> Dict[str, Any]:
        """Charge un JSON avec vérification de taille et sécurité"""
        try:
            path = Path(file_path)

            # Vérification de la taille
            size_bytes = path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            if size_mb > self.max_size_mb:
                raise ValueError(
                    f"Fichier trop volumineux: {size_mb:.1f}MB (limite: {self.max_size_mb}MB)"
                )

            # Chargement sécurisé
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    # Tentative avec latin-1 en fallback
                    f.seek(0)
                    try:
                        content = f.read().encode("latin-1").decode("utf-8")
                        data = json.loads(content)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        raise json.JSONDecodeError(
                            f"Impossible de décoder le JSON: {e}", f.name, e.pos
                        )

                # Vérification de la profondeur (évite les JSON malveillants)
                self._check_json_depth(data, MAX_JSON_DEPTH)

                return data

        except Exception as e:
            self.logger.error(f"Erreur chargement {file_path}: {e}")
            raise

    def _check_json_depth(
        self, obj: Any, max_depth: int, current_depth: int = 0
    ) -> None:
        """Vérifie la profondeur du JSON pour éviter les attaques par déni de service"""
        if current_depth > max_depth:
            raise ValueError(f"JSON trop profond (> {max_depth} niveaux)")

        if isinstance(obj, dict):
            for value in obj.values():
                self._check_json_depth(value, max_depth, current_depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                self._check_json_depth(item, max_depth, current_depth + 1)

    def validate_json_file(self, file_path: str) -> Dict[str, Any]:
        """Valide un fichier JSON et diagnostique les problèmes"""
        result = {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "valid": False,
            "exists": False,
            "readable": False,
            "valid_json": False,
            "empty": False,
            "size_bytes": 0,
            "size_mb": 0.0,
            "issues": [],
            "content_preview": "",
            "structure": {},
            "chunks_count": 0,
            "debug_info": {},
        }

        try:
            # 1. Vérifier l'existence du fichier
            path = Path(file_path)
            if not path.exists():
                result["issues"].append("FILE_NOT_FOUND")
                return result

            result["exists"] = True
            result["size_bytes"] = path.stat().st_size
            result["size_mb"] = result["size_bytes"] / (1024 * 1024)

            # 2. Vérifier si le fichier est trop volumineux
            if result["size_mb"] > self.max_size_mb:
                result["issues"].append(
                    f"FILE_TOO_LARGE ({result['size_mb']:.1f}MB > {self.max_size_mb}MB)"
                )
                return result

            # 3. Vérifier si le fichier est vide
            if result["size_bytes"] == 0:
                result["empty"] = True
                result["issues"].append("EMPTY_FILE")
                return result

            # 4. Tenter de lire le fichier
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                result["readable"] = True
                result["content_preview"] = (
                    content[:200] + "..." if len(content) > 200 else content
                )

            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()
                    result["readable"] = True
                    result["issues"].append("ENCODING_ISSUE")
                    result["content_preview"] = (
                        content[:200] + "..." if len(content) > 200 else content
                    )
                except Exception as e:
                    result["issues"].append(f"READ_ERROR: {e}")
                    return result
            except Exception as e:
                result["issues"].append(f"READ_ERROR: {e}")
                return result

            # 5. Vérifier si le contenu est vide après nettoyage
            if not content.strip():
                result["empty"] = True
                result["issues"].append("EMPTY_CONTENT")
                return result

            # 6. Tenter de parser le JSON avec sécurité
            try:
                data = json.loads(content)
                result["valid_json"] = True

                # Analyser la structure
                result["debug_info"]["root_type"] = type(data).__name__

                if isinstance(data, dict):
                    result["structure"] = {
                        "type": "object",
                        "keys": list(data.keys())[:10],
                        "total_keys": len(data.keys()),
                    }
                    result["debug_info"]["all_keys"] = list(data.keys())

                    # Vérifier la présence de chunks
                    chunks_found = self._find_chunks_in_data(data)
                    if chunks_found is not None:
                        result["chunks_count"] = (
                            len(chunks_found) if isinstance(chunks_found, list) else 0
                        )
                        result["debug_info"]["chunks_found"] = True

                        if isinstance(chunks_found, list) and len(chunks_found) > 0:
                            valid_chunks = self._validate_chunk_samples(
                                chunks_found[:3]
                            )
                            result["debug_info"]["valid_chunks_found"] = valid_chunks

                            if valid_chunks == 0:
                                result["issues"].append("INVALID_CHUNKS")
                        elif len(chunks_found) == 0:
                            result["issues"].append("NO_CHUNKS")
                    else:
                        result["issues"].append("NO_CHUNKS_KEY")

                elif isinstance(data, list):
                    result["structure"] = {"type": "array", "length": len(data)}
                    result["chunks_count"] = len(data)
                    if len(data) > 0:
                        valid_chunks = self._validate_chunk_samples(data[:3])
                        result["debug_info"]["valid_chunks_found"] = valid_chunks
                else:
                    result["structure"] = {"type": type(data).__name__}
                    result["issues"].append("UNEXPECTED_ROOT_TYPE")

                # Déterminer si le fichier est valide
                critical_issues = [
                    "FILE_NOT_FOUND",
                    "EMPTY_FILE",
                    "READ_ERROR",
                    "EMPTY_CONTENT",
                    "NO_CHUNKS",
                    "INVALID_CHUNKS",
                    "FILE_TOO_LARGE",
                ]

                has_critical_issues = any(
                    any(critical in issue for critical in critical_issues)
                    for issue in result["issues"]
                )
                result["valid"] = not has_critical_issues

            except json.JSONDecodeError as e:
                result["issues"].append(f"INVALID_JSON: {e}")

        except Exception as e:
            result["issues"].append(f"VALIDATION_ERROR: {e}")

        return result

    def _find_chunks_in_data(self, data: Dict[str, Any]):
        """Trouve les chunks dans les données JSON"""
        chunk_keys = ["chunks", "segments", "content", "data", "extracts"]
        for key in chunk_keys:
            if key in data:
                return data[key]
        return None

    def _validate_chunk_samples(self, chunks_sample: List[Any]) -> int:
        """Valide un échantillon de chunks et retourne le nombre de chunks valides"""
        valid_count = 0

        for chunk in chunks_sample:
            if isinstance(chunk, dict):
                content_keys = [
                    "content",
                    "text",
                    "body",
                    "chunk_content",
                    "segment_content",
                    "data",
                ]
                for content_key in content_keys:
                    if content_key in chunk:
                        content_value = chunk[content_key]
                        if content_value and str(content_value).strip():
                            valid_count += 1
                            break
            elif isinstance(chunk, str) and chunk.strip():
                valid_count += 1

        return valid_count

    def validate_files_batch(self, file_paths: List[str]) -> Dict[str, Any]:
        """Valide un batch de fichiers et retourne un rapport consolidé"""
        results = {
            "total_files": len(file_paths),
            "valid_files": 0,
            "invalid_files": 0,
            "total_chunks": 0,
            "total_size_mb": 0.0,
            "problematic_files": [],
            "valid_files_list": [],
            "file_details": {},
        }

        self.logger.info(f"Validation de {len(file_paths)} fichiers...")

        for file_path in file_paths:
            validation = self.validate_json_file(file_path)
            file_name = Path(file_path).name

            results["file_details"][file_name] = validation
            results["total_size_mb"] += validation["size_mb"]

            if validation["valid"]:
                results["valid_files"] += 1
                results["valid_files_list"].append(file_path)
                results["total_chunks"] += validation["chunks_count"]
            else:
                results["invalid_files"] += 1
                results["problematic_files"].append(
                    {
                        "file": file_name,
                        "path": file_path,
                        "issues": validation["issues"],
                        "size_mb": validation["size_mb"],
                    }
                )

        return results
