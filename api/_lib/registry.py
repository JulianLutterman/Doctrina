import os
import json

# Simple Registry using /tmp for MVP (Ephemeral on Serverless)
# In production, use Vercel KV

REGISTRY_FILE = "/tmp/model_registry.json"

def get_registry():
    if not os.path.exists(REGISTRY_FILE):
        return {}
    try:
        with open(REGISTRY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_registry(registry):
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f)

def get_model_entry(alias):
    reg = get_registry()
    return reg.get(alias)

def update_model_entry(alias, base_model, current_model_id):
    reg = get_registry()
    reg[alias] = {
        "baseModel": base_model,
        "currentModelId": current_model_id
    }
    save_registry(reg)
