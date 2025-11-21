import argparse
import asyncio
import json
import os
import sys
import tinker
from tinker import types
from tinker_cookbook import renderers, tokenizer_utils

# Set up argument parser
parser = argparse.ArgumentParser(description='Tinker Training Script')
parser.add_argument('--base_model', type=str, required=True, help='Base Model Name')
parser.add_argument('--resume_path', type=str, default=None, help='Path to resume training from (optional)')
parser.add_argument('--prompt', type=str, required=True, help='User prompt')
parser.add_argument('--completion', type=str, required=True, help='Completion to reinforce (Generated or Correct)')
parser.add_argument('--system_prompt', type=str, default="You are a helpful assistant.", help='System prompt')

# We are doing SFT on the provided pair (prompt, completion).
# If feedback was positive, completion = generated.
# If feedback was negative, completion = corrected.

async def main():
    args = parser.parse_args()

    try:
        service_client = tinker.ServiceClient()

        # Create Training Client
        # Always initialize with base_model.
        # Rank 32 is default/recommended in docs.
        training_client = service_client.create_lora_training_client(
            base_model=args.base_model,
            rank=32
        )

        # Resume if path provided
        if args.resume_path and args.resume_path != "null" and args.resume_path != "undefined":
            training_client.load_state(args.resume_path)

        # Prepare Data
        tokenizer = tokenizer_utils.get_tokenizer(args.base_model)

        renderer_name = "llama3"
        if "Qwen" in args.base_model:
            renderer_name = "qwen3"

        renderer = renderers.get_renderer(renderer_name, tokenizer)

        messages = [
            {'role': 'system', 'content': args.system_prompt},
            {'role': 'user', 'content': args.prompt},
            {'role': 'assistant', 'content': args.completion}
        ]

        # Build SFT example
        tokens, weights = renderer.build_supervised_example(messages)

        # Construct Datum
        # build_supervised_example returns full sequence.
        # Tinker expects next-token prediction, so target is shifted.
        # Actually, build_supervised_example usually returns tokens and weights for the full sequence.
        # We need to shift for input/target.

        input_tokens = tokens[:-1]
        target_tokens = tokens[1:]
        loss_weights = weights[1:]

        datum = types.Datum(
            model_input=types.ModelInput.from_ints(tokens=input_tokens),
            loss_fn_inputs=dict(
                weights=loss_weights,
                target_tokens=target_tokens
            )
        )

        # Train
        # 1 step SFT
        # Using cross_entropy

        fwdbwd_future = training_client.forward_backward([datum], "cross_entropy")
        optim_future = training_client.optim_step(types.AdamParams(learning_rate=1e-4)) # Use default LR for now

        fwdbwd_result = fwdbwd_future.result()
        optim_result = optim_future.result()

        # Save State (for resuming next time)
        # We use a timestamp or UUID for naming to ensure uniqueness if needed, or just "latest"
        # But we should probably keep a history or just overwrite?
        # Tinker paths are immutable usually? "This path is persistent".
        # So we create a new one.
        import uuid
        run_id = str(uuid.uuid4())[:8]

        save_state_future = training_client.save_state(name=f"ckpt-{run_id}")
        save_sampler_future = training_client.save_weights_for_sampler(name=f"sample-{run_id}")

        resume_path = save_state_future.result().path
        sampling_path = save_sampler_future.result().path

        print(json.dumps({
            "resume_path": resume_path,
            "sampling_path": sampling_path,
            "metrics": optim_result.metrics
        }))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
