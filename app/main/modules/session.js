import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
let isLoggingOut = false;

export async function checkSession(mainWindow, domain) {
    return new Promise((resolve) => {
        const loginCheckUrl = `${domain}/web/login?redirect=%2Fodoo%3F`;

        const listener = () => {
            const url = mainWindow.webContents.getURL();

            if (url.includes("/web/login")) {
                resolve(false);
            } else if (url.includes("/odoo")) {
                resolve(true);
            };

            cleanup();
        };

        const onFailLoad = () => {
            cleanup();
            resolve(false);
        };

        function cleanup() {
            mainWindow.webContents.removeListener("did-navigate", listener);
            mainWindow.webContents.removeListener("did-fail-load", onFailLoad);
        }

        mainWindow.webContents.on("did-navigate", listener);
        mainWindow.webContents.on("did-fail-load", onFailLoad);
        mainWindow.loadURL(loginCheckUrl);
    });
}

export function logoutInterceptor(mainWindow) {

    // Detect logout request
    mainWindow.webContents.session.webRequest.onBeforeRequest(
        { urls: ["*://*/web/session/logout*"] },
        (details, callback) => {
            isLoggingOut = true;
            callback({});
        }
    );

    // Detect redirect to login after logout
    mainWindow.webContents.on("did-navigate", (event, url) => {
        if (isLoggingOut && url.includes("/web/login")) {
            isLoggingOut = false;

            mainWindow.loadFile(
                path.join(__dirname, "../../renderer/startup/startup.html")
            );
        }
    });
}
