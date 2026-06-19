import * as vscode from 'vscode';

let statusBarItem: vscode.StatusBarItem;
let outputChannel: vscode.OutputChannel;

interface IcaroSelection {
    startLine: number;
    startCharacter: number;
    endLine: number;
    endCharacter: number;
    text: string;
}

export function activate(context: vscode.ExtensionContext) {
    console.log('La extension "icaro-bridge" esta activa.');

    outputChannel = vscode.window.createOutputChannel('Icaro');
    context.subscriptions.push(outputChannel);

    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'icaro.sendContext';
    statusBarItem.text = '$(pulse) Icaro: Inicializando';
    statusBarItem.tooltip = 'Conexion con Icaro Core';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    async function sendContext(silent: boolean = true) {
        const editor = vscode.window.activeTextEditor;

        if (!editor) {
            if (!silent) {
                vscode.window.showErrorMessage('No hay archivo activo en el editor.');
            }

            statusBarItem.text = '$(circle-slash) Icaro: Sin archivo';
            statusBarItem.tooltip = 'Abre un archivo para sincronizarlo con Icaro Core';
            statusBarItem.backgroundColor = undefined;
            return;
        }

        const document = editor.document;
        const selection = editor.selection;

        let selectionData: IcaroSelection | null = null;
        if (!selection.isEmpty) {
            selectionData = {
                startLine: selection.start.line + 1,
                startCharacter: selection.start.character,
                endLine: selection.end.line + 1,
                endCharacter: selection.end.character,
                text: document.getText(selection)
            };
        }

        const payload = {
            fileName: document.fileName,
            language: document.languageId,
            code: document.getText(),
            selection: selectionData,
            timestamp: new Date().toISOString()
        };

        try {
            const config = vscode.workspace.getConfiguration('icaroBridge');
            const endpoint = config.get<string>('endpoint', 'http://localhost:8000/context');
            const timeoutMs = config.get<number>('timeoutMs', 2000);

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload),
                signal: AbortSignal.timeout(timeoutMs)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            statusBarItem.text = '$(check) Icaro: Conectado';
            statusBarItem.tooltip = `Icaro sincronizado: ${document.fileName}\n(Click para forzar envio)`;
            statusBarItem.backgroundColor = undefined;

            if (!silent) {
                vscode.window.showInformationMessage('Contexto enviado correctamente a Icaro Core.');
                outputChannel.show();
                outputChannel.appendLine(JSON.stringify(data, null, 2));
            }
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : String(error);

            statusBarItem.text = '$(warning) Icaro: Desconectado';
            statusBarItem.tooltip = `Error conectando con Icaro Core: ${message}`;
            statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');

            if (!silent) {
                vscode.window.showErrorMessage('No se pudo conectar con Icaro Core. Asegurate de que el asistente este corriendo.');
            }
        }
    }

    function debounce(fn: () => void, delay: number) {
        let timeoutId: NodeJS.Timeout | undefined;

        return () => {
            if (timeoutId) {
                clearTimeout(timeoutId);
            }

            timeoutId = setTimeout(fn, delay);
        };
    }

    const debouncedSendText = debounce(() => {
        void sendContext(true);
    }, 1200);
    const debouncedSendSelection = debounce(() => {
        void sendContext(true);
    }, 800);

    void sendContext(true);

    const changeEditorSub = vscode.window.onDidChangeActiveTextEditor(() => {
        void sendContext(true);
    });
    context.subscriptions.push(changeEditorSub);

    const changeDocSub = vscode.workspace.onDidChangeTextDocument((event) => {
        const editor = vscode.window.activeTextEditor;

        if (editor && event.document === editor.document) {
            debouncedSendText();
        }
    });
    context.subscriptions.push(changeDocSub);

    const changeSelSub = vscode.window.onDidChangeTextEditorSelection((event) => {
        if (event.textEditor === vscode.window.activeTextEditor) {
            debouncedSendSelection();
        }
    });
    context.subscriptions.push(changeSelSub);

    const disposable = vscode.commands.registerCommand('icaro.sendContext', async () => {
        statusBarItem.text = '$(pulse) Icaro: Enviando...';
        await sendContext(false);
    });
    context.subscriptions.push(disposable);
}

export function deactivate() {
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}
