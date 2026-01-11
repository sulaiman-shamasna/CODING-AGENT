/**
 * Client for communicating with Python agent
 */

import * as child_process from 'child_process';
import * as path from 'path';

export interface AgentResult {
    status: string;
    iterations?: number;
    completion_reason?: string;
    verification_result?: any;
    error?: string;
}

export class AgentClient {
    private workspacePath: string;
    private pythonPath: string;
    private currentProcess?: child_process.ChildProcess;

    constructor(workspacePath: string, config: any) {
        this.workspacePath = workspacePath;
        this.pythonPath = config.get('pythonPath', 'python');
    }

    async runTask(task: string): Promise<AgentResult> {
        return new Promise((resolve, reject) => {
            // Build command
            const args = ['run', task, '--workspace', this.workspacePath];

            // Start agent process
            this.currentProcess = child_process.spawn('coding-agent', args, {
                cwd: this.workspacePath,
            });

            let stdout = '';
            let stderr = '';

            this.currentProcess.stdout?.on('data', (data) => {
                stdout += data.toString();
                console.log('[Agent]', data.toString());
            });

            this.currentProcess.stderr?.on('data', (data) => {
                stderr += data.toString();
                console.error('[Agent Error]', data.toString());
            });

            this.currentProcess.on('close', (code) => {
                if (code === 0) {
                    // Try to parse result from stdout
                    resolve({
                        status: 'completed',
                        iterations: 1,
                    });
                } else {
                    reject(new Error(stderr || 'Agent process failed'));
                }
            });

            this.currentProcess.on('error', (error) => {
                reject(error);
            });
        });
    }

    async indexWorkspace(): Promise<void> {
        return new Promise((resolve, reject) => {
            const args = ['index', '--workspace', this.workspacePath];

            const process = child_process.spawn('coding-agent', args, {
                cwd: this.workspacePath,
            });

            process.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error('Indexing failed'));
                }
            });

            process.on('error', (error) => {
                reject(error);
            });
        });
    }

    stop(): void {
        if (this.currentProcess) {
            this.currentProcess.kill();
            this.currentProcess = undefined;
        }
    }
}

