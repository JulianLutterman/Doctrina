# Refactored models handler to be a function, not a class
import json
import asyncio
try:
    from api import _tinker as tinker
    TINKER_AVAILABLE = True
except ImportError:
    try:
        import tinker
        TINKER_AVAILABLE = True
    except ImportError:
        TINKER_AVAILABLE = False

FALLBACK_MODELS = [
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "Qwen/Qwen3-30B-A3B",
    "Qwen/Qwen3-30B-A3B-Base",
    "Qwen/Qwen3-32B",
    "Qwen/Qwen3-8B",
    "Qwen/Qwen3-8B-Base",
    "Qwen/Qwen3-4B-Instruct-2507",
    "meta-llama/Llama-3.3-70B",
    "meta-llama/Llama-3.1-70B",
    "meta-llama/Llama-3.1-8B",
    "meta-llama/Llama-3.1-8B-Instruct",
    "meta-llama/Llama-3.2-3B",
    "meta-llama/Llama-3.2-1B"
]

async def list_models():
    # Always return fallback models if Tinker is not available or if request fails
    # This ensures the UI is usable even without a valid API key for Tinker
    models = []

    if TINKER_AVAILABLE:
        try:
            service_client = tinker.ServiceClient()
            # Attempt to fetch real models, but fallback if it fails (e.g. auth error)
            capabilities = await service_client.get_server_capabilities_async()
            models = [m.model_name for m in capabilities.supported_models]
        except Exception:
            # Fallback to hardcoded list
            pass

    if not models:
        models = FALLBACK_MODELS

    return {"models": models}


def handle_models(req_handler):
    if req_handler.command != "GET":
        req_handler.send_response(405)
        req_handler.end_headers()
        return

    result = asyncio.run(list_models())
    # Since we always return a list (fallback or real), status is 200
    status = 200

    req_handler.send_response(status)
    req_handler.send_header('Content-Type', 'application/json')
    req_handler.end_headers()
    req_handler.wfile.write(json.dumps(result).encode())
