import asyncio
import os
from api.lib.registry import get_model_entry, update_model_entry

try:
    from api import tinker
    TINKER_AVAILABLE = True
except ImportError:
    try:
        import tinker
        TINKER_AVAILABLE = True
    except ImportError:
        TINKER_AVAILABLE = False

_SUPPORTED_MODELS = []

async def get_supported_models():
    global _SUPPORTED_MODELS
    if _SUPPORTED_MODELS:
        return _SUPPORTED_MODELS

    if not TINKER_AVAILABLE:
        return []

    try:
        service_client = tinker.ServiceClient()
        capabilities = await service_client.get_server_capabilities_async()
        _SUPPORTED_MODELS = [m.model_name for m in capabilities.supported_models]
        return _SUPPORTED_MODELS
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []

async def resolve_model_alias(model_alias: str):
    entry = get_model_entry(model_alias)
    if entry:
        return entry["baseModel"], entry["currentModelId"]

    supported = await get_supported_models()
    if model_alias in supported:
        return model_alias, model_alias

    best_match = None
    for m in supported:
        if model_alias.startswith(m + "/"):
            if best_match is None or len(m) > len(best_match):
                best_match = m

    if best_match:
        update_model_entry(model_alias, best_match, best_match)
        return best_match, best_match

    return model_alias, model_alias
