import { NextResponse } from 'next/server';
import { ensureModel } from '@/lib/registry';
import { spawn } from 'child_process';

// Force dynamic to prevent caching
export const dynamic = 'force-dynamic';

function runPythonScript(scriptPath: string, args: string[]): Promise<string> {
    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', [scriptPath, ...args], {
            env: { ...process.env }
        });

        let stdoutData = '';
        let stderrData = '';

        pythonProcess.stdout.on('data', (data) => {
            stdoutData += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            stderrData += data.toString();
        });

        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                console.error("Python Script Error:", stderrData);
                reject(new Error(`Script exited with code ${code}: ${stderrData}`));
            } else {
                resolve(stdoutData);
            }
        });

        pythonProcess.on('error', (err) => {
             reject(err);
        });
    });
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { model, messages, temperature, max_tokens } = body;

    if (!model || !messages || !Array.isArray(messages)) {
      return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
    }

    let baseModelName = "meta-llama/Llama-3.1-8B-Instruct";
    // Logic to determine base model / registry entry
    const { getModel, updateModel } = await import('@/lib/registry');
    let entry = getModel(model);

    if (!entry) {
        let effectiveBase = model;
        // Known prefixes logic
        if (model.startsWith("meta-llama/") || model.startsWith("Qwen/")) {
             const p = model.split('/');
             if (p.length > 2) {
                 effectiveBase = `${p[0]}/${p[1]}`;
             } else {
                 effectiveBase = model;
             }
        } else {
             effectiveBase = "meta-llama/Llama-3.1-8B-Instruct";
        }

        entry = {
            base_model: effectiveBase,
            current_model_id: effectiveBase
        };
        updateModel(model, entry);
    }

    const modelPath = entry.sampling_path || entry.base_model;

    const lastMessage = messages[messages.length - 1];
    if (lastMessage.role !== 'user') {
        return NextResponse.json({ error: "Last message must be from user" }, { status: 400 });
    }

    const prompt = lastMessage.content;
    const systemMsg = messages.find((m: any) => m.role === 'system');
    const systemPrompt = systemMsg ? systemMsg.content : "You are a helpful assistant.";

    // Use spawn instead of exec to avoid shell injection
    const scriptArgs = [
        '--model_path', modelPath,
        '--prompt', prompt,
        '--system_prompt', systemPrompt,
        '--max_tokens', String(max_tokens || 512),
        '--temperature', String(temperature || 0.7)
    ];

    try {
        const stdout = await runPythonScript('scripts/inference.py', scriptArgs);
        const result = JSON.parse(stdout);

        if (result.error) {
             return NextResponse.json({ error: result.error }, { status: 500 });
        }

        return NextResponse.json({
            id: "chatcmpl-" + Date.now(),
            object: "chat.completion",
            created: Math.floor(Date.now() / 1000),
            model: model,
            choices: [{
                index: 0,
                message: {
                    role: "assistant",
                    content: result.content
                },
                finish_reason: "stop"
            }]
        });
    } catch (e: any) {
        console.error("Error running inference:", e);
        return NextResponse.json({ error: "Internal Server Error: " + e.message }, { status: 500 });
    }

  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
