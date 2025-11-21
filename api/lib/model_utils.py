import asyncio
import os
from api.lib.registry import get_model_entry, update_model_entry

try:
    import tinker
    TINKER_AVAILABLE = True
except ImportError:
    TINKER_AVAILABLE = False

# Global cache for supported models
_SUPPORTED_MODELS = []
_SUPPORTED_MODELS_TIMESTAMP = 0

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
    # 1. Check Registry
    entry = get_model_entry(model_alias)
    if entry:
        return entry["baseModel"], entry["currentModelId"]

    # 2. Check if it is a supported base model
    supported = await get_supported_models()
    if model_alias in supported:
        # It's a base model. Register it as such?
        # Or just use it.
        # Prompt says "Route to BaseModel and save mapping" if Base/Specific called.
        # If just Base called, effectively Base/Base?
        return model_alias, model_alias

    # 3. Try to parse as Base/Specific
    # Find longest prefix that is a supported model
    best_match = None
    for m in supported:
        if model_alias.startswith(m + "/"):
            if best_match is None or len(m) > len(best_match):
                best_match = m

    if best_match:
        # First time calling Base/Specific
        # Register it
        update_model_entry(model_alias, best_match, best_match)
        return best_match, best_match

    # 4. Fallback (maybe list hasn't updated or network error)
    # Assume everything before last slash is base?
    # Or split by first slash?
    # Safe fallback: Assume the alias IS the base model ID (user might know better)
    return model_alias, model_alias
