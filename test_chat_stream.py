"""
Test de l'endpoint /api/v1/chat/stream avec streaming LLM real-time
"""

import asyncio
import httpx
import json
import time


async def test_chat_stream():
    """
    Test l'endpoint /api/v1/chat/stream avec streaming SSE
    """
    url = "http://localhost:8000/chat/stream"

    query = "What is FCR in poultry farming?"

    print(f"[TEST] Testing /api/v1/chat/stream endpoint")
    print(f"[QUERY] {query}\n")

    request_data = {
        "message": query,
        "tenant_id": "test_stream_user"
    }

    start_time = time.time()
    chunk_count = 0
    full_response = ""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                json=request_data,
                headers={"Accept": "text/event-stream"}
            ) as response:

                if response.status_code != 200:
                    print(f"[ERROR] HTTP {response.status_code}")
                    print(await response.aread())
                    return

                print(f"[OK] Connected to streaming endpoint\n")

                current_event = None
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue

                    # Parse SSE format
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()

                    elif line.startswith("data:"):
                        data_str = line.split(":", 1)[1].strip()

                        try:
                            data = json.loads(data_str)

                            if current_event == "start":
                                print(f"[START] Provider: {data.get('provider', 'unknown')}")
                                print(f"        Model: {data.get('model', 'unknown')}")
                                print(f"        Max tokens: {data.get('max_tokens', 'unknown')}\n")

                            elif current_event == "chunk":
                                chunk_count += 1
                                content = data.get("content", "")
                                full_response += content

                                # Print first 10 chunks
                                if chunk_count <= 10:
                                    print(f"[CHUNK {chunk_count}] {repr(content)}")
                                elif chunk_count == 11:
                                    print(f"[...] (streaming continues...)")

                            elif current_event == "end":
                                duration = time.time() - start_time
                                print(f"\n[END] Streaming complete!")
                                print(f"      Total chunks: {chunk_count}")
                                print(f"      Total tokens: {data.get('total_tokens', 'unknown')}")
                                print(f"      Duration: {duration:.2f}s")
                                print(f"\n[RESPONSE]\n{full_response[:500]}...")
                                break

                            elif current_event == "error":
                                print(f"\n[ERROR] {data.get('error', 'Unknown error')}")
                                break

                        except json.JSONDecodeError as e:
                            print(f"[WARNING] Invalid JSON: {data_str[:100]}")
                            continue

        print(f"\n[SUCCESS] Streaming test completed!")
        print(f"[STATS] Chunks: {chunk_count}, Duration: {time.time() - start_time:.2f}s")

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_chat_stream())
