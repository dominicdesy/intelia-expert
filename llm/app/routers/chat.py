"""
Chat Completions Router
OpenAI-compatible chat completion endpoint
"""

from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionMessage,
    UsageInfo,
    ErrorResponse,
)
from app.models.llm_client import LLMClient
from app.utils.metrics import track_tokens, track_inference
from app.dependencies import get_llm_client
import logging
import time
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@track_inference("intelia-llama")
async def create_chat_completion(
    request: ChatCompletionRequest, llm_client: LLMClient = Depends(get_llm_client)
):
    """
    Create a chat completion (OpenAI-compatible)

    This endpoint mimics OpenAI's /v1/chat/completions API for easy integration.

    **Example request:**
    ```json
    {
      "model": "intelia-llama-3.1-8b-aviculture",
      "messages": [
        {"role": "user", "content": "Comment réduire la mortalité des poulets?"}
      ],
      "temperature": 0.7,
      "max_tokens": 2000
    }
    ```

    **Example response:**
    ```json
    {
      "id": "chatcmpl-abc123",
      "object": "chat.completion",
      "created": 1234567890,
      "model": "intelia-llama-3.1-8b-aviculture",
      "choices": [{
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "Pour réduire la mortalité des poulets..."
        },
        "finish_reason": "stop"
      }],
      "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 320,
        "total_tokens": 470
      }
    }
    ```
    """
    try:
        logger.info(f"Chat completion request for model: {request.model}")
        logger.debug(f"Messages: {len(request.messages)} messages")

        # Validate messages
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages list cannot be empty")

        # Convert messages to dict format
        messages_dict = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        # Call LLM provider
        generated_text, prompt_tokens, completion_tokens = await llm_client.generate(
            messages=messages_dict,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stop=request.stop,
        )

        # Track token usage
        track_tokens(
            model=request.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        # Build response
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created_timestamp = int(time.time())

        response = ChatCompletionResponse(
            id=completion_id,
            created=created_timestamp,
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant", content=generated_text
                    ),
                    finish_reason="stop",
                )
            ],
            usage=UsageInfo(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

        logger.info(
            f"Completion successful. ID: {completion_id}, Tokens: {prompt_tokens}+{completion_tokens}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
