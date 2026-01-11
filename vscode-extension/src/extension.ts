/**
 * VS Code Extension for Coding Agent
 */

import * as vscode from 'vscode';
import { AgentClient } from './agentClient';
import { ChatPanel } from './ui/chatPanel';
import { StatusBarManager } from './ui/statusBar';

let agentClient: AgentClient | undefined;
let chatPanel: ChatPanel | undefined;
let statusBar: StatusBarManager | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('Coding Agent extension is now active');

    // Initialize components
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }

    const config = vscode.workspace.getConfiguration('codingAgent');
    agentClient = new AgentClient(workspaceFolder.uri.fsPath, config);
    statusBar = new StatusBarManager();
    chatPanel = new ChatPanel(context.extensionUri, agentClient, statusBar);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('codingAgent.start', async () => {
            const task = await vscode.window.showInputBox({
                prompt: 'Enter task description',
                placeHolder: 'e.g., Add a login feature to the web app',
            });

            if (task) {
                await runTask(task);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codingAgent.stop', () => {
            agentClient?.stop();
            vscode.window.showInformationMessage('Agent stopped');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codingAgent.showChat', () => {
            chatPanel?.show();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codingAgent.indexWorkspace', async () => {
            await indexWorkspace();
        })
    );

    // Show chat panel on activation
    chatPanel.show();
}

async function runTask(task: string) {
    if (!agentClient || !statusBar) {
        return;
    }

    try {
        statusBar.setRunning();
        chatPanel?.addMessage('user', task);
        chatPanel?.addMessage('assistant', 'Starting agent...');

        const result = await agentClient.runTask(task);

        if (result.status === 'completed') {
            chatPanel?.addMessage('assistant', '✓ Task completed successfully!');
            vscode.window.showInformationMessage('Agent task completed');
        } else {
            chatPanel?.addMessage('assistant', `Task ended: ${result.status}`);
            vscode.window.showWarningMessage(`Agent task ended: ${result.status}`);
        }

        statusBar.setIdle();
    } catch (error: any) {
        chatPanel?.addMessage('assistant', `Error: ${error.message}`);
        vscode.window.showErrorMessage(`Agent error: ${error.message}`);
        statusBar.setIdle();
    }
}

async function indexWorkspace() {
    if (!agentClient) {
        return;
    }

    try {
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Indexing workspace...',
                cancellable: false,
            },
            async (progress) => {
                await agentClient!.indexWorkspace();
            }
        );

        vscode.window.showInformationMessage('Workspace indexed successfully');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Indexing failed: ${error.message}`);
    }
}

export function deactivate() {
    agentClient?.stop();
}

