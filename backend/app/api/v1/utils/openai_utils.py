import openai
import os

def safe_chat_completion(**kwargs):
    """
    Wrapper for OpenAI chat completions.
    Checks for API key and uses the modern API signature.
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured in environment variables.")
    openai.api_key = key
    try:
        return openai.chat.completions.create(**kwargs)
    except Exception as e:
        raise RuntimeError(f"OpenAI API call failed: {e}")
