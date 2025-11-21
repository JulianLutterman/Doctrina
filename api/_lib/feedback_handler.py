import json
import os
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from api._lib.model_utils import resolve_model_alias
from api._lib.registry import update_model_entry

try:
    from api import _tinker as tinker
    from api._tinker import types
    TINKER_AVAILABLE = True
except Exception:
    try:
        import tinker
        from tinker import types
        TINKER_AVAILABLE = True
    except Exception:
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

async def process_feedback_logic(data):
    if not TINKER_AVAILABLE:
        raise ImportError("Tinker library not available")

    model_alias = data.get("model_alias")
    prompt = data.get("prompt")
    feedback_type = data.get("feedback_type")
    correct_output = data.get("correct_output")
    logprobs = data.get("logprobs")
    tokens = data.get("tokens")

    if not model_alias:
            return {"error": "Model alias required"}

    base_model_name, current_model_id = await resolve_model_alias(model_alias)

    service_client = tinker.ServiceClient()
    target_text = ""

    if feedback_type == 'negative':
            if not correct_output:
                raise ValueError("Correct output required for negative feedback")

            client = service_client.create_sampling_client(base_model=base_model_name)
            tokenizer = get_tokenizer_wrapper(base_model_name)

            sys_prompt = "You are a helpful AI assistant."
            meta_prompt = (
            f"The user asked: {prompt}. The correct answer is: {correct_output}. "
            "Explain step-by-step, using Chain of Thought reasoning, how to arrive at this answer. "
            "Do not output the final answer, only the reasoning steps."
            )

            full_text = sys_prompt + "\n" + meta_prompt
            t_toks = tokenizer.encode(full_text).ids

            m_input = types.ModelInput.from_ints(tokens=t_toks)
            params = types.SamplingParams(max_tokens=1024, temperature=0.7)

            f = await client.sample_async(prompt=m_input, sampling_params=params, num_samples=1)
            if hasattr(f, 'result_async'):
                res = await f.result_async()
            else:
                res = f

            cot = tokenizer.decode(res.sequences[0].tokens, skip_special_tokens=True)
            target_text = f"{cot}\n\nAnswer: {correct_output}"

    examples = []

    if tokens and logprobs:
            examples.append({
                "prompt_text": prompt,
                "completion_tokens": tokens,
                "logprobs": logprobs,
                "advantage": 1.0 if feedback_type == 'positive' else -1.0
            })

    if feedback_type == 'negative':
            examples.append({
                "prompt_text": prompt,
                "completion_text": target_text,
                "advantage": 1.0
            })

    training_client = await service_client.create_lora_training_client_async(base_model=base_model_name, rank=32)

    if current_model_id.startswith("tinker://"):
        try:
            lf = await training_client.load_state_async(current_model_id)
            if hasattr(lf, 'result_async'): await lf.result_async()
        except:
            pass

    tokenizer = get_tokenizer_wrapper(base_model_name)
    data_batch = []

    for ex in examples:
        p_text = ex.get("prompt_text")
        c_text = ex.get("completion_text")
        c_toks = ex.get("completion_tokens")
        lp = ex.get("logprobs")
        adv = ex.get("advantage")

        p_toks = tokenizer.encode(p_text).ids

        if not c_toks:
            c_toks = tokenizer.encode(c_text).ids

        full = p_toks + c_toks
        inp_ids = full[:-1]
        tgt_ids = full[1:]

        adv_vec = [0.0] * len(inp_ids)
        lp_vec = [0.0] * len(inp_ids)
        start_idx = max(0, len(p_toks) - 1)

        for i in range(len(c_toks)):
            idx = start_idx + i
            if idx < len(adv_vec):
                adv_vec[idx] = float(adv)
                if lp and i < len(lp):
                    lp_vec[idx] = float(lp[i])

        lfn = "importance_sampling" if (lp is not None) else "cross_entropy"

        if lfn == "cross_entropy":
                w_vec = [0.0] * len(inp_ids)
                for i in range(len(c_toks)):
                    idx = start_idx + i
                    if idx < len(w_vec): w_vec[idx] = 1.0
                loss_in = {"target_tokens": tgt_ids, "weights": w_vec}
        else:
                loss_in = {"target_tokens": tgt_ids, "logprobs": lp_vec, "advantages": adv_vec}

        datum = types.Datum(model_input=types.ModelInput.from_ints(tokens=inp_ids), loss_fn_inputs=loss_in)
        data_batch.append((datum, lfn))

    new_id = current_model_id

    batches = {}
    for d, l in data_batch:
        if l not in batches: batches[l] = []
        batches[l].append(d)

    for l, b in batches.items():
            fb = await training_client.forward_backward_async(b, loss_fn=l)
            if hasattr(fb, 'result_async'): await fb.result_async()

            op = await training_client.optim_step_async(types.AdamParams(learning_rate=1e-5))
            if hasattr(op, 'result_async'): await op.result_async()

            sf = training_client.save_state(name=f"step_{os.urandom(4).hex()}")
            if hasattr(sf, 'result_async'):
                res = await sf.result_async()
            else:
                res = sf

            if hasattr(res, 'path'): new_id = res.path

    return base_model_name, new_id

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

def handle_feedback(req_handler):
    if req_handler.command != "POST":
        req_handler.send_response(405)
        req_handler.end_headers()
        return

    content_length = int(req_handler.headers['Content-Length'])
    body = req_handler.rfile.read(content_length).decode('utf-8')
    data = json.loads(body)

    try:
        base_model_name, new_model_id = run_async(process_feedback_logic(data))
        update_model_entry(data.get("model_alias"), base_model_name, new_model_id)

        req_handler.send_response(200)
        req_handler.send_header('Content-Type', 'application/json')
        req_handler.end_headers()
        req_handler.wfile.write(json.dumps({"success": True, "new_model_id": new_model_id}).encode())
    except Exception as e:
        req_handler.send_response(500)
        req_handler.end_headers()
        req_handler.wfile.write(json.dumps({"error": str(e), "traceback": traceback.format_exc()}).encode())
