# -*- coding: utf-8 -*-
"""
JSON endpoint handlers - Extracted from json_routes.py for better modularity
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
JSON endpoint handlers - Extracted from json_routes.py for better modularity
Handles JSON validation, ingestion, search, and upload functionality
"""

import time
import json
import logging
from utils.types import Any, List, Dict, Optional, Tuple
from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..endpoints import safe_serialize_for_json
from ..chat_models import JSONValidationRequest, IngestionRequest

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_rag_engine_from_service(get_service) -> Optional[Any]:
    """
    Get RAG Engine from health monitor service

    Args:
        get_service: Function to get service by name

    Returns:
        RAG Engine instance or None
    """
    health_monitor = get_service("health_monitor")
    if health_monitor:
        return health_monitor.get_service("rag_engine_enhanced")
    return None


def check_rag_engine_capability(rag_engine: Any, capability: str) -> None:
    """
    Check if RAG engine has required capability

    Args:
        rag_engine: RAG engine instance
        capability: Method name to check

    Raises:
        HTTPException: If engine is None or doesn't have capability
    """
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG Engine non disponible")

    if not hasattr(rag_engine, capability):
        raise HTTPException(status_code=501, detail=f"{capability} non disponible")


def parse_json_field(field_value: Optional[str], field_name: str) -> Optional[Any]:
    """
    Parse JSON string field safely

    Args:
        field_value: String value to parse
        field_name: Field name for logging

    Returns:
        Parsed JSON or None
    """
    if not field_value:
        return None

    try:
        return json.loads(field_value)
    except json.JSONDecodeError as e:
        logger.warning(f"{field_name} invalide: {field_value} - {e}")
        return None


def create_error_response(
    error: Exception, start_time: float, **extra_fields
) -> JSONResponse:
    """
    Create standardized error response

    Args:
        error: Exception that occurred
        start_time: Request start time
        **extra_fields: Additional fields to include

    Returns:
        JSONResponse with error details
    """
    response_data = {
        "success": False,
        "error": str(error),
        "processing_time": time.time() - start_time,
        **extra_fields,
    }
    return JSONResponse(status_code=500, content=response_data)


# ============================================================================
# ENDPOINT HANDLERS
# ============================================================================


async def handle_validate_json_document(
    get_service, request: JSONValidationRequest
) -> JSONResponse:
    """
    Handle JSON document validation endpoint

    Args:
        get_service: Function to get services
        request: Validation request with json_data and strict_mode

    Returns:
        JSONResponse with validation results
    """
    start_time = time.time()

    try:
        rag_engine = get_rag_engine_from_service(get_service)
        check_rag_engine_capability(rag_engine, "validate_json_document")

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
        return create_error_response(e, start_time, valid=False)


async def handle_ingest_json_documents(
    get_service, request: IngestionRequest
) -> JSONResponse:
    """
    Handle JSON documents ingestion endpoint

    Args:
        get_service: Function to get services
        request: Ingestion request with json_files, batch_size, force_reprocess

    Returns:
        JSONResponse with ingestion results
    """
    start_time = time.time()

    try:
        rag_engine = get_rag_engine_from_service(get_service)
        check_rag_engine_capability(rag_engine, "ingest_json_documents")

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
        return create_error_response(e, start_time)


async def handle_search_json_enhanced(
    get_service,
    query: str,
    genetic_line: Optional[str] = None,
    performance_metrics: Optional[str] = None,
    age_range: Optional[str] = None,
) -> JSONResponse:
    """
    Handle enhanced JSON search endpoint with filters

    Args:
        get_service: Function to get services
        query: Search query string
        genetic_line: Optional genetic line filter
        performance_metrics: Optional performance metrics filter (JSON string)
        age_range: Optional age range filter (JSON string)

    Returns:
        JSONResponse with search results
    """
    start_time = time.time()

    try:
        rag_engine = get_rag_engine_from_service(get_service)
        check_rag_engine_capability(rag_engine, "search_json_enhanced")

        # Parse JSON fields
        parsed_metrics = parse_json_field(performance_metrics, "performance_metrics")
        if parsed_metrics is None and performance_metrics:
            # Fallback to list with single value if parse failed
            parsed_metrics = [performance_metrics]

        parsed_age_range = parse_json_field(age_range, "age_range")

        # Execute search
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
        return create_error_response(e, start_time)


async def _parse_uploaded_files(
    files: List[UploadFile],
) -> Tuple[List[Dict], List[str]]:
    """
    Parse uploaded JSON files

    Args:
        files: List of uploaded files

    Returns:
        Tuple of (parsed_json_files, errors)
    """
    json_files = []
    errors = []

    for file in files:
        try:
            if not file.filename.endswith(".json"):
                errors.append(f"{file.filename}: Format non supporté (JSON requis)")
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

    return json_files, errors


async def _validate_json_files(rag_engine: Any, json_files: List[Dict]) -> List[Dict]:
    """
    Validate parsed JSON files

    Args:
        rag_engine: RAG engine instance
        json_files: List of parsed JSON files

    Returns:
        List of validation results
    """
    validation_results = []

    if not rag_engine or not hasattr(rag_engine, "validate_json_document"):
        return validation_results

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

    return validation_results


async def _ingest_valid_files(
    rag_engine: Any,
    json_files: List[Dict],
    validation_results: List[Dict],
    batch_size: int,
) -> Optional[Dict]:
    """
    Ingest files that passed validation

    Args:
        rag_engine: RAG engine instance
        json_files: List of parsed JSON files
        validation_results: Validation results
        batch_size: Batch size for ingestion

    Returns:
        Ingestion result or None
    """
    valid_files = [
        jf for jf, vr in zip(json_files, validation_results) if vr.get("valid", False)
    ]

    if not valid_files:
        return None

    if not rag_engine or not hasattr(rag_engine, "ingest_json_documents"):
        return None

    try:
        return await rag_engine.ingest_json_documents(
            json_files=[f["data"] for f in valid_files],
            batch_size=batch_size,
        )
    except Exception as e:
        logger.error(f"Erreur ingestion: {e}")
        return None


async def handle_upload_json_files(
    get_service,
    files: List[UploadFile],
    batch_size: int = 5,
    auto_validate: bool = True,
) -> JSONResponse:
    """
    Handle JSON files upload and processing endpoint

    Args:
        get_service: Function to get services
        files: List of uploaded files
        batch_size: Batch size for ingestion (default: 5)
        auto_validate: Enable automatic validation (default: True)

    Returns:
        JSONResponse with upload, validation, and ingestion results
    """
    start_time = time.time()

    try:
        # Validate file count
        if len(files) > 50:
            raise HTTPException(
                status_code=413, detail="Maximum 50 fichiers par upload"
            )

        # Parse uploaded files
        json_files, errors = await _parse_uploaded_files(files)

        if not json_files:
            raise HTTPException(
                status_code=400, detail="Aucun fichier JSON valide trouvé"
            )

        # Validate if requested
        validation_results = []
        if auto_validate:
            rag_engine = get_rag_engine_from_service(get_service)
            validation_results = await _validate_json_files(rag_engine, json_files)

        # Ingest valid files
        ingestion_result = None
        if auto_validate and validation_results:
            rag_engine = get_rag_engine_from_service(get_service)
            ingestion_result = await _ingest_valid_files(
                rag_engine, json_files, validation_results, batch_size
            )

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
        return create_error_response(e, start_time)
