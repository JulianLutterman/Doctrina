# Tinker Self-Improving API & Dashboard

A robust "Self-Improving API" and Frontend Dashboard built with Next.js and the Tinker Fine-Tuning Platform.

## Features

*   **OpenAI-Compatible API**: `/api/chat/completions` endpoint mimicking OpenAI's signature.
*   **Self-Improving Loop**: `/api/feedback` endpoint implementing Reinforcement Fine-Tuning (RFT).
*   **Model Registry**: Maps user-defined aliases (e.g., `Llama-3-8b/Finance-V1`) to Tinker Model IDs.
*   **Frontend Dashboard**: Clean UI for chatting and providing feedback (Thumbs Up/Down).
*   **Secure Execution**: Uses secure subprocess spawning for Python integration.

## Deployment on Vercel

### Prerequisites

This application requires a **Python runtime** to execute the Tinker scripts.

**Important**: Standard Vercel Node.js deployments do not include a Python runtime accessible via `child_process`. To deploy this successfully on Vercel, you have two main options:

1.  **Hybrid Deployment (Recommended)**: Deploy the Python scripts (`scripts/`) as Vercel Python Serverless Functions (requires restructuring `scripts/` into `api/` python functions) or use a separate Python backend service.
2.  **Docker/Container**: Deploy using a Docker container (e.g., via Vercel's container support or another provider like Railway/Fly.io) that installs both Node.js and Python.

For this repository, the structure is designed as a Next.js monolith. To run it "out of the box" locally or on a VPS:

### Local Setup

1.  **Install Dependencies**:
    ```bash
    npm install
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```
    TINKER_API_KEY=your_tinker_api_key_here
    ```

3.  **Run Development Server**:
    ```bash
    npm run dev
    ```

4.  **Access**:
    *   Frontend: `http://localhost:3000`
    *   API: `http://localhost:3000/api/chat/completions`

### Vercel Persistence Note

The Model Registry uses a local JSON file (`model_registry.json`). On serverless platforms like Vercel, the filesystem is ephemeral. Changes to the registry (updates from fine-tuning) will **not persist** across redeployments or function cold starts.

**For Production Persistence**:
1.  Use **Vercel KV (Redis)**.
2.  Update `lib/registry.ts` to read/write from Vercel KV instead of the local file.

## Usage

1.  **Chat**: Enter a model alias (e.g., `Llama-3-8b/MyTask`) and start chatting.
2.  **Feedback**:
    *   **Thumbs Up**: Triggers a positive reinforcement training run on the generated response.
    *   **Thumbs Down**: Prompts for the *correct* response, then triggers a training run reinforcing the correction.
3.  **Improvement**: Subsequent requests to the same alias will use the newly trained model checkpoint.
