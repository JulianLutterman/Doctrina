from http.server import BaseHTTPRequestHandler
import json
import os
import asyncio
from api.lib.model_utils import resolve_model_alias

try:
    import tinker
    from tinker import types
    TINKER_AVAILABLE = True
except ImportError:
    TINKER_AVAILABLE = False

def get_tokenizer_wrapper(model_name: str):
    from tokenizers import Tokenizer
    if "Qwen3" in model_name:
        fallback = "Qwen/Qwen2.5-1.5B-Instruct"
    elif "Llama-3" in model_name:
        fallback = "gpt2"
    else:
        fallback = model_name

    try:
        return Tokenizer.from_pretrained(model_name)
    except:
        print(f"Warning: Failed to load tokenizer for {model_name}, falling back to {fallback}")
        try:
            return Tokenizer.from_pretrained(fallback)
        except:
            # Ultimate fallback if even fallback fails (e.g. gated)
            return Tokenizer.from_pretrained("gpt2")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body)

        model_alias = data.get("model")
        messages = data.get("messages")

        if not model_alias or not messages:
             self.send_response(400)
             self.end_headers()
             self.wfile.write(json.dumps({"error": "Missing model or messages"}).encode())
             return

        async def handle_async():
            base_model_name, model_to_use = await resolve_model_alias(model_alias)

            last_message = messages[-1]
            prompt_text = last_message["content"]

            sys_msg = next((m for m in messages if m["role"] == "system"), None)
            sys_prompt = sys_msg["content"] if sys_msg else None

            service_client = tinker.ServiceClient()

            if model_to_use.startswith("tinker://"):
                client = service_client.create_sampling_client(model_path=model_to_use)
            else:
                client = service_client.create_sampling_client(base_model=model_to_use)

            tokenizer = get_tokenizer_wrapper(base_model_name)

            # Simple concatenation (tokenizers doesn't have apply_chat_template)
            full_text = (sys_prompt + "\n" if sys_prompt else "") + prompt_text

            # tokenizers encode returns Encoding object
            encoding = tokenizer.encode(full_text)
            tokens = encoding.ids

            model_input = types.ModelInput.from_ints(tokens=tokens)
            params = types.SamplingParams(max_tokens=512, temperature=0.7)

            future = await client.sample_async(prompt=model_input, sampling_params=params, num_samples=1)
            if hasattr(future, 'result_async'):
                 result = await future.result_async()
            else:
                 result = future

            seq = result.sequences[0]
            output_text = tokenizer.decode(seq.tokens, skip_special_tokens=True)

            return {
                "output": output_text,
                "logprobs": seq.logprobs,
                "tokens": seq.tokens
            }

        try:
            result = asyncio.run(handle_async())
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
