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

async def list_models():
    if not TINKER_AVAILABLE:
        return {"error": "Tinker library not found"}
    try:
        service_client = tinker.ServiceClient()
        capabilities = await service_client.get_server_capabilities_async()
        return {"models": [m.model_name for m in capabilities.supported_models]}
    except Exception as e:
        return {"error": str(e)}

def handle_models(req_handler):
    if req_handler.command != "GET":
        req_handler.send_response(405)
        req_handler.end_headers()
        return

    result = asyncio.run(list_models())
    status = 500 if "error" in result and result["error"] != "Tinker library not found" else 200

    req_handler.send_response(status)
    req_handler.send_header('Content-Type', 'application/json')
    req_handler.end_headers()
    req_handler.wfile.write(json.dumps(result).encode())
