import { spawn } from 'child_process';
import { app } from 'electron';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { findAvailablePort } from './port_service.js';
import { stopProcess } from './process_manager.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default class PrintService {
    constructor() {
        this.serverProcess = null;
        this.port = null;
    }

    /**
     * Start the print service
     * @returns {Promise<number>} - The port number the service is running on
     */
    async start() {
        const isDev = !app.isPackaged;
        
        if (isDev) {
            // Development mode - run Python directly
            return await this.startPythonDirect();
        } else {
            // Production mode - use built executable
            return await this.startExecutable();
        }
    }

    /**
     * Start the Python server directly in development mode
     * @returns {Promise<number>}
     */
    async startPythonDirect() {
        const port = await findAvailablePort(5050, 6000);
        this.port = port;

        // Find the Python server file
        const serverPyPath = path.join(__dirname, '../../../server/main.py');
        
        // Check if the Python file exists
        if (!fs.existsSync(serverPyPath)) {
            throw new Error(`Python server file not found at: ${serverPyPath}`);
        }

        console.log(`[PrintService] Starting Python server directly: ${serverPyPath}`);

        // Use python3 on non-Windows, python on Windows
        const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';
        
        this.serverProcess = spawn(pythonCommand, [serverPyPath, `--port=${port}`], {
            detached: false,
            stdio: ['pipe', 'pipe', 'pipe'],
            windowsHide: false,
            cwd: path.dirname(serverPyPath) // Set working directory to the Python file's location
        });

        this.setupProcessHandlers();
        return port;
    }

    /**
     * Start the built executable (production mode)
     * @returns {Promise<number>}
     */
    async startExecutable() {
        const binaryName = process.platform === 'win32' ? 'main.exe' : 'main';
        const platformDir = process.platform === 'win32' ? 'win-x64' : 'linux-x64';
        
        // Production mode - electron-builder extraResources path
        const buildOutputPath = path.join(process.resourcesPath, 'build', platformDir);
        const serverExePath = path.join(buildOutputPath, binaryName);
        
        // Check if the executable exists
        if (!fs.existsSync(serverExePath)) {
            throw new Error(`Print service executable not found at: ${serverExePath}`);
        }
        
        const port = await findAvailablePort(5050, 6000);
        this.port = port;

        this.serverProcess = spawn(serverExePath, [`--port=${port}`], {
            detached: false,
            stdio: ['pipe', 'pipe', 'pipe'],
            windowsHide: false,
        });

        this.setupProcessHandlers();
        return port;
    }

    /**
     * Setup common process event handlers
     */
    setupProcessHandlers() {
        this.serverProcess.stdout.on("data", (data) => {
            console.log("[PrintService] SERVER STDOUT:", data.toString());
        });

        this.serverProcess.stderr.on("data", (data) => {
            console.log("[PrintService] SERVER STDERR:", data.toString());
        });
        
        this.serverProcess.on('exit', (code, signal) => {
            if (code !== 0) {
                console.error(`Print service exited with code ${code}, signal ${signal}`);
            }
            this.serverProcess = null;
            this.port = null;
        });

        this.serverProcess.on('error', (error) => {
            console.error('[PrintService] Failed to start process:', error);
            this.serverProcess = null;
            this.port = null;
        });
    }

    /**
     * Stop the print service
     * @returns {Promise<void>}
     */
    async stop() {
        if (!this.serverProcess) return;

        const proc = this.serverProcess;
        this.serverProcess = null;
        this.port = null;

        await stopProcess(proc);
    }

    /**
     * Get the current port the service is running on
     * @returns {number|null}
     */
    getPort() {
        return this.port;
    }

    /**
     * Check if the service is running
     * @returns {boolean}
     */
    isRunning() {
        return this.serverProcess && !this.serverProcess.killed;
    }
}