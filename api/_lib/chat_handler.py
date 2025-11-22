# Refactored chat handler
import json
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from api._lib.model_utils import resolve_model_alias

try:
    from api import _tinker as tinker
    from api._tinker import types
    TINKER_AVAILABLE = True
except Exception as e:
    try:
        import tinker
        from tinker import types
        TINKER_AVAILABLE = True
    except Exception as e2:
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
        try:
            return Tokenizer.from_pretrained(fallback)
        except:
            return Tokenizer.from_pretrained("gpt2")

async def process_chat(data):
    if not TINKER_AVAILABLE:
        return {"error": "Tinker library not available"}

    model_alias = data.get("model")
    messages = data.get("messages")

    if not model_alias or not messages:
         return {"error": "Missing model or messages"}

    base_model_name, model_to_use = await resolve_model_alias(model_alias)

    service_client = tinker.ServiceClient()

    if model_to_use.startswith("tinker://"):
        client = service_client.create_sampling_client(model_path=model_to_use)
    else:
        client = service_client.create_sampling_client(base_model=model_to_use)

    tokenizer = get_tokenizer_wrapper(base_model_name)

    full_text = ""
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            full_text += f"{content}\n"
        elif role == "user":
            full_text += f"User: {content}\nAssistant: "
        elif role == "assistant":
            full_text += f"{content}\n"

    # encoding
    encoding = tokenizer.encode(full_text)
    tokens = encoding.ids

    model_input = types.ModelInput.from_ints(tokens=tokens)
    params = types.SamplingParams(max_tokens=512, temperature=0.7)

    try:
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
    except tinker.APIStatusError as e:
        return {"error": str(e), "status_code": e.status_code}
    except Exception as e:
        print(f"Error processing chat: {e}")
        traceback.print_exc()
        return {"error": str(e)}

def run_async(coro):
    """Runs an async coroutine in a way that works even if an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)

def handle_chat(req_handler):
    if req_handler.command != "POST":
        req_handler.send_response(405)
        req_handler.end_headers()
        return

    content_length = int(req_handler.headers['Content-Length'])
    body = req_handler.rfile.read(content_length).decode('utf-8')
    data = json.loads(body)

    try:
        result = run_async(process_chat(data))

        status = 200
        if "error" in result:
             if "status_code" in result:
                 status = result["status_code"]
             elif result["error"] != "Tinker library not available":
                 status = 500

        req_handler.send_response(status)
        req_handler.send_header('Content-Type', 'application/json')
        req_handler.end_headers()
        req_handler.wfile.write(json.dumps(result).encode())
    except Exception as e:
        print(f"Error in handle_chat: {e}")
        traceback.print_exc()
        req_handler.send_response(500)
        req_handler.end_headers()
        req_handler.wfile.write(json.dumps({"error": "Internal Server Error"}).encode())
