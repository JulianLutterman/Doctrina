import argparse
import asyncio
import json
import os
import sys
import tinker
from tinker import types
from tinker_cookbook import renderers, tokenizer_utils

# Set up argument parser
parser = argparse.ArgumentParser(description='Tinker Inference Script')
parser.add_argument('--model_path', type=str, required=True, help='Path to the model (Tinker ID or Base Model Name)')
parser.add_argument('--prompt', type=str, required=True, help='User prompt')
parser.add_argument('--system_prompt', type=str, default="You are a helpful assistant.", help='System prompt')
parser.add_argument('--max_tokens', type=int, default=512, help='Max tokens to generate')
parser.add_argument('--temperature', type=float, default=0.7, help='Temperature')

async def main():
    args = parser.parse_args()

    # Initialize Service Client
    service_client = tinker.ServiceClient()

    # Check if model_path is a Tinker URI or a base model name
    # If it starts with "tinker://", it's a trained model path.
    # Otherwise, it's a base model name (e.g. "meta-llama/Llama-3.1-8B-Instruct")

    try:
        if args.model_path.startswith("tinker://"):
            sampling_client = service_client.create_sampling_client(model_path=args.model_path)
            # For tokenizer, we might need the base model name.
            # However, we don't easily know the base model from the tinker path here without metadata.
            # For now, let's assume a default or try to infer/pass it.
            # HACK: We should pass base_model if known. But Tinker paths usually contain metadata?
            # The docs say: `create_sampling_client` takes `model_path` OR `base_model`.
            # If we pass `model_path`, Tinker should know what to do.
            # But `tokenizer_utils.get_tokenizer` needs a model name.
            # Let's assume Llama 3.1 8B Instruct for tokenizer if not specified.
            # Ideally, the caller passes the base model name too.
            # Let's use a reasonable default for tokenizer if we can't guess.
            tokenizer_name = "meta-llama/Llama-3.1-8B-Instruct"
        else:
            sampling_client = service_client.create_sampling_client(base_model=args.model_path)
            tokenizer_name = args.model_path

        tokenizer = tokenizer_utils.get_tokenizer(tokenizer_name)

        # Try to guess renderer. The docs say "llama3" is a renderer name.
        renderer_name = "llama3" # Default
        if "Qwen" in tokenizer_name:
            renderer_name = "qwen3"

        renderer = renderers.get_renderer(renderer_name, tokenizer)

        messages = [
            {'role': 'system', 'content': args.system_prompt},
            {'role': 'user', 'content': args.prompt}
        ]

        model_input = renderer.build_generation_prompt(messages)

        sampling_params = types.SamplingParams(
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            stop=renderer.get_stop_sequences()
        )

        # Sample
        future = sampling_client.sample(prompt=model_input, sampling_params=sampling_params, num_samples=1)
        result = future.result()

        # Parse
        tokens = result.sequences[0].tokens
        response_message, _ = renderer.parse_response(tokens)

        print(json.dumps({"content": response_message["content"]}))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
