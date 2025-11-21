# Refactored models handler to be a function, not a class
import json
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor

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

def run_async(coro):
    """Runs an async coroutine in a way that works even if an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If we are in a running loop, we can't use asyncio.run().
        # We spawn a thread to run the coroutine in a new loop.
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)

def handle_models(req_handler):
    try:
        if req_handler.command != "GET":
            req_handler.send_response(405)
            req_handler.end_headers()
            return

        result = run_async(list_models())
        # Since we always return a list (fallback or real), status is 200
        status = 200

        req_handler.send_response(status)
        req_handler.send_header('Content-Type', 'application/json')
        req_handler.end_headers()
        req_handler.wfile.write(json.dumps(result).encode())
    except Exception as e:
        req_handler.send_response(500)
        req_handler.send_header('Content-Type', 'application/json')
        req_handler.end_headers()
        error_response = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        req_handler.wfile.write(json.dumps(error_response).encode())
