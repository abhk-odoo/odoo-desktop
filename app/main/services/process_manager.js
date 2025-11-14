import { exec } from 'child_process';

/**
 * Stop a process gracefully with platform-specific handling
 * @param {ChildProcess} process - The process to stop
 * @returns {Promise<void>}
 */
export const stopProcess = (process) => {
    return new Promise((resolve) => {
        if (!process || process.killed) {
            resolve();
            return;
        }

        if (process.platform === 'win32') {
            exec(`taskkill /pid ${process.pid} /T /F`, (err, stdout, stderr) => {
                if (err) {
                    exec(`wmic process where processid=${process.pid} delete`, (wmicErr) => {
                        if (wmicErr) {
                            try {
                                process.kill(process.pid, 'SIGKILL');
                            } catch (killErr) {
                                console.error(`Failed to kill process ${process.pid}:`, killErr.message);
                            }
                        }
                        resolve();
                    });
                } else {
                    resolve();
                }
            });

            // Timeout fallback
            setTimeout(() => {
                if (!process.killed) {
                    try {
                        process.kill('SIGKILL');
                    } catch (err) {
                        console.error(`Force kill failed: ${err.message}`);
                    }
                }
                resolve();
            }, 5000);

        } else {
            // Unix-like systems (Linux, macOS)
            process.kill('SIGTERM');
            setTimeout(() => {
                if (!process.killed) {
                    process.kill('SIGKILL');
                }
                resolve();
            }, 3000);
        }

        process.killed = true;
    });
};
