"""
Models Router
List available models (OpenAI-compatible)
"""

from fastapi import APIRouter
from app.models.schemas import ModelsResponse, ModelInfo
from app.config import settings
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """
    List available models (OpenAI-compatible)

    Returns information about the available LLM models.

    **Example response:**
    ```json
    {
      "object": "list",
      "data": [
        {
          "id": "intelia-llama-3.1-8b-aviculture",
          "object": "model",
          "created": 1234567890,
          "owned_by": "intelia"
        }
      ]
    }
    ```
    """
    logger.debug("Listing available models")

    # For now, return single model
    # In future, can add multiple fine-tuned models
    models = [
        ModelInfo(
            id="intelia-llama-3.1-8b-aviculture",
            created=int(time.time()),
            owned_by="intelia"
        )
    ]

    # If using base Llama (Phase 1), show that too
    if settings.llm_provider == "huggingface":
        models.append(
            ModelInfo(
                id=settings.huggingface_model,
                created=int(time.time()),
                owned_by="meta"
            )
        )

    return ModelsResponse(data=models)
