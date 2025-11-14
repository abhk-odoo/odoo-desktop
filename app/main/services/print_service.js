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
        const binaryName = process.platform === 'win32' ? 'main.exe' : 'main';
        
        // Determine the platform-specific build path
        const platformDir = process.platform === 'win32' ? 'win-x64' : 'linux-x64';
        
        let buildOutputPath;
        if (isDev) {
            // Development mode - look in project build directory
            buildOutputPath = path.join(__dirname, '../../../build', platformDir);
        } else {
            // Production mode - electron-builder extraResources path
            buildOutputPath = path.join(process.resourcesPath, 'build', platformDir);
        }

        const serverExePath = path.join(buildOutputPath, binaryName);
        
        
        // Check if the executable exists
        if (!fs.existsSync(serverExePath)) {
            console.error(`ERROR: Print service executable not found at: ${serverExePath}`);
            console.error(`Make sure you have built the ${platformDir} executable.`);
            
            throw new Error('Print service executable not found');
        }
        
        const port = await findAvailablePort(5050, 6000);
        this.port = port;

        this.serverProcess = spawn(serverExePath, [`--port=${port}`], {
            detached: false,
            stdio: ['pipe', 'pipe', 'pipe'],
            windowsHide: false,
        });

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
        
        return port;
    }

    /**
     * Stop the print service
     * @returns {Promise<void>}
     */
    async stop() {
        if (this.serverProcess) {
            await stopProcess(this.serverProcess);
            this.serverProcess = null;
            this.port = null;
        }
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
