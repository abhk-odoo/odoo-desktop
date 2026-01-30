import { exec } from "child_process";

/**
 * Kill a child process reliably (Windows + Unix)
 * @param {import("child_process").ChildProcess} child
 */
export const stopProcess = (child) => {
    return new Promise((resolve) => {
        if (!child || !child.pid) {
            return resolve();
        }

        const pid = child.pid;

        if (process.platform === "win32") {
            exec(`taskkill /PID ${pid} /T /F`, () => resolve());
            return;
        }

        try {
            process.kill(pid, "SIGTERM");
        } catch {
            return resolve();
        }

        // Force kill after timeout
        setTimeout(() => {
            try {
                process.kill(pid, "SIGKILL");
            } catch {}
            resolve();
        }, 3000);
    });
};
