import { NextResponse } from 'next/server';
import { getModel, updateModel } from '@/lib/registry';
import { spawn } from 'child_process';

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
    const { model_alias, prompt, generated_output, feedback_type, correct_output } = body;

    if (!model_alias || !prompt || !feedback_type) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const entry = getModel(model_alias);
    if (!entry) {
        return NextResponse.json({ error: 'Model alias not found' }, { status: 404 });
    }

    let completionToReinforce = "";
    if (feedback_type === 'positive') {
        completionToReinforce = generated_output;
    } else if (feedback_type === 'negative') {
        if (!correct_output) {
             return NextResponse.json({ error: 'correct_output required for negative feedback' }, { status: 400 });
        }
        completionToReinforce = correct_output;
    } else {
        return NextResponse.json({ error: 'Invalid feedback_type' }, { status: 400 });
    }

    const resumePath = entry.training_path || "";

    const scriptArgs = [
        '--base_model', entry.base_model,
        '--resume_path', resumePath,
        '--prompt', prompt,
        '--completion', completionToReinforce
    ];

    console.log("Running training script...");

    try {
        const stdout = await runPythonScript('scripts/train.py', scriptArgs);
        const result = JSON.parse(stdout);

        if (result.error) {
            return NextResponse.json({ error: result.error }, { status: 500 });
        }

        entry.training_path = result.resume_path;
        entry.sampling_path = result.sampling_path;
        entry.current_model_id = result.sampling_path;

        updateModel(model_alias, entry);

        return NextResponse.json({ success: true, new_model_id: entry.current_model_id, metrics: result.metrics });

    } catch (e: any) {
        console.error("Error running training:", e);
        return NextResponse.json({ error: "Training failed: " + e.message }, { status: 500 });
    }

  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
