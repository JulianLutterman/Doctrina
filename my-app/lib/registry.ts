import fs from 'fs';
import path from 'path';

const REGISTRY_PATH = path.join(process.cwd(), 'model_registry.json');

export interface ModelEntry {
  base_model: string;
  current_model_id: string; // The Tinker Model ID (e.g., tinker://...)
  sampling_path?: string; // Path to weights for sampling
  training_path?: string; // Path to weights for resuming training
}

export interface Registry {
  [alias: string]: ModelEntry;
}

export function getRegistry(): Registry {
  if (!fs.existsSync(REGISTRY_PATH)) {
    return {};
  }
  const data = fs.readFileSync(REGISTRY_PATH, 'utf-8');
  try {
    return JSON.parse(data);
  } catch (e) {
    console.error("Error parsing model registry:", e);
    return {};
  }
}

export function saveRegistry(registry: Registry) {
  fs.writeFileSync(REGISTRY_PATH, JSON.stringify(registry, null, 2));
}

export function getModel(alias: string): ModelEntry | null {
  const registry = getRegistry();
  return registry[alias] || null;
}

export function updateModel(alias: string, entry: ModelEntry) {
  const registry = getRegistry();
  registry[alias] = entry;
  saveRegistry(registry);
}

export function ensureModel(alias: string, baseModel: string): ModelEntry {
    const existing = getModel(alias);
    if (existing) {
        return existing;
    }
    // If it's a base model alias (no slash or known base), handled differently?
    // The prompt says: "Specific LLM: BaseName/SpecificTask".
    // "Check DB: Does Llama-3-8b/Finance-V1 exist? No: Map to Base LLM."

    // We create a new entry mapping to the base model initially.
    const newEntry: ModelEntry = {
        base_model: baseModel,
        current_model_id: baseModel, // Initially points to base model
        // No sampling/training path yet, implies using base model directly
    };
    updateModel(alias, newEntry);
    return newEntry;
}
