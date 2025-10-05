# -*- coding: utf-8 -*-
"""
api/endpoints_chat/json_routes.py - JSON system endpoints
Version 5.0.1 - JSON validation, ingestion, search, and upload endpoints
"""

import time
import json
import logging
from utils.types import Any, List, Optional, Callable
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse

from config.config import BASE_PATH
from ..endpoints import safe_serialize_for_json
from ..chat_models import JSONValidationRequest, IngestionRequest

logger = logging.getLogger(__name__)


def create_json_routes(get_service: Callable[[str], Any]) -> APIRouter:
    """
    Crée les endpoints du système JSON avicole

    Args:
        get_service: Fonction pour récupérer un service par nom

    Returns:
        APIRouter configuré avec les endpoints JSON
    """
    router = APIRouter()

    def get_rag_engine():
        """Helper pour récupérer le RAG Engine"""
        health_monitor = get_service("health_monitor")
        if health_monitor:
            return health_monitor.get_service("rag_engine_enhanced")
        return None

    @router.post(f"{BASE_PATH}/json/validate")
    async def validate_json_document(request: JSONValidationRequest):
        """Valide un document JSON selon les schémas avicoles"""
        start_time = time.time()

        try:
            rag_engine = get_rag_engine()
            if not rag_engine:
                raise HTTPException(status_code=503, detail="RAG Engine non disponible")

            if not hasattr(rag_engine, "validate_json_document"):
                raise HTTPException(
                    status_code=501, detail="Validation JSON non disponible"
                )

            result = await rag_engine.validate_json_document(
                json_data=request.json_data, strict_mode=request.strict_mode
            )

            response = {
                **result,
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
                "version": "5.0.1_metrics_fixed",
            }

            return JSONResponse(content=safe_serialize_for_json(response))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur validation JSON: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "valid": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                },
            )

    @router.post(f"{BASE_PATH}/json/ingest")
    async def ingest_json_documents(request: IngestionRequest):
        """Ingère des documents JSON dans le système"""
        start_time = time.time()

        try:
            rag_engine = get_rag_engine()
            if not rag_engine:
                raise HTTPException(status_code=503, detail="RAG Engine non disponible")

            if not hasattr(rag_engine, "ingest_json_documents"):
                raise HTTPException(
                    status_code=501, detail="Ingestion JSON non disponible"
                )

            result = await rag_engine.ingest_json_documents(
                json_files=request.json_files, batch_size=request.batch_size
            )

            response = {
                **result,
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
                "batch_size_used": request.batch_size,
                "force_reprocess": request.force_reprocess,
            }

            return JSONResponse(content=safe_serialize_for_json(response))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur ingestion JSON: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                },
            )

    @router.post(f"{BASE_PATH}/json/search")
    async def search_json_enhanced(
        query: str = Form(...),
        genetic_line: Optional[str] = Form(None),
        performance_metrics: Optional[str] = Form(None),
        age_range: Optional[str] = Form(None),
    ):
        """Recherche avancée dans les documents JSON avec filtres avicoles"""
        start_time = time.time()

        try:
            rag_engine = get_rag_engine()
            if not rag_engine:
                raise HTTPException(status_code=503, detail="RAG Engine non disponible")

            if not hasattr(rag_engine, "search_json_enhanced"):
                raise HTTPException(
                    status_code=501, detail="Recherche JSON non disponible"
                )

            parsed_metrics = None
            if performance_metrics:
                try:
                    parsed_metrics = json.loads(performance_metrics)
                except json.JSONDecodeError:
                    parsed_metrics = [performance_metrics]

            parsed_age_range = None
            if age_range:
                try:
                    parsed_age_range = json.loads(age_range)
                except json.JSONDecodeError:
                    logger.warning(f"Âge range invalide: {age_range}")

            results = await rag_engine.search_json_enhanced(
                query=query,
                genetic_line=genetic_line,
                performance_metrics=parsed_metrics,
                age_range=parsed_age_range,
            )

            response = {
                "success": True,
                "results": results,
                "results_count": len(results),
                "query": query,
                "filters": {
                    "genetic_line": genetic_line,
                    "performance_metrics": parsed_metrics,
                    "age_range": parsed_age_range,
                },
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
            }

            return JSONResponse(content=safe_serialize_for_json(response))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur recherche JSON: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                },
            )

    @router.post(f"{BASE_PATH}/json/upload")
    async def upload_json_files(
        files: List[UploadFile] = File(...),
        batch_size: int = Form(5),
        auto_validate: bool = Form(True),
    ):
        """Upload et traitement de fichiers JSON avicoles"""
        start_time = time.time()

        try:
            if len(files) > 50:
                raise HTTPException(
                    status_code=413, detail="Maximum 50 fichiers par upload"
                )

            json_files = []
            errors = []

            for file in files:
                try:
                    if not file.filename.endswith(".json"):
                        errors.append(
                            f"{file.filename}: Format non supporté (JSON requis)"
                        )
                        continue

                    content = await file.read()
                    json_data = json.loads(content.decode("utf-8"))

                    json_files.append(
                        {
                            "filename": file.filename,
                            "data": json_data,
                            "size_bytes": len(content),
                        }
                    )

                except json.JSONDecodeError as e:
                    errors.append(f"{file.filename}: JSON invalide - {str(e)}")
                except Exception as e:
                    errors.append(f"{file.filename}: Erreur lecture - {str(e)}")

            if not json_files:
                raise HTTPException(
                    status_code=400, detail="Aucun fichier JSON valide trouvé"
                )

            validation_results = []
            if auto_validate:
                rag_engine = get_rag_engine()
                if rag_engine and hasattr(rag_engine, "validate_json_document"):
                    for json_file in json_files:
                        try:
                            validation = await rag_engine.validate_json_document(
                                json_data=json_file["data"], strict_mode=False
                            )
                            validation_results.append(
                                {
                                    "filename": json_file["filename"],
                                    "valid": validation.get("valid", False),
                                    "errors": validation.get("errors", []),
                                    "warnings": validation.get("warnings", []),
                                }
                            )
                        except Exception as e:
                            validation_results.append(
                                {
                                    "filename": json_file["filename"],
                                    "valid": False,
                                    "error": str(e),
                                }
                            )

            ingestion_result = None
            if auto_validate and validation_results:
                valid_files = [
                    jf
                    for jf, vr in zip(json_files, validation_results)
                    if vr.get("valid", False)
                ]

                if valid_files:
                    rag_engine = get_rag_engine()
                    if rag_engine and hasattr(rag_engine, "ingest_json_documents"):
                        try:
                            ingestion_result = await rag_engine.ingest_json_documents(
                                json_files=[f["data"] for f in valid_files],
                                batch_size=batch_size,
                            )
                        except Exception as e:
                            logger.error(f"Erreur ingestion: {e}")

            response = {
                "success": True,
                "files_uploaded": len(files),
                "files_parsed": len(json_files),
                "parsing_errors": errors,
                "validation_enabled": auto_validate,
                "validation_results": validation_results,
                "ingestion_result": ingestion_result,
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
            }

            return JSONResponse(content=safe_serialize_for_json(response))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur upload JSON: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                },
            )

    return router
