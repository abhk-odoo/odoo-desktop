import { BrowserWindow } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export async function createMainWindow() {
    const browserWindow = new BrowserWindow({
        autoHideMenuBar: true,
        icon: path.join(__dirname, "../../assets/icon.png"),
        webPreferences: {
            preload: path.join(__dirname, '../preload/preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
        },
    });

    browserWindow.webContents.setWindowOpenHandler(({ url }) => {
        return {
            action: "allow",
            overrideBrowserWindowOptions: {
                autoHideMenuBar: true,
            }
        };
    });

    browserWindow.maximize();
    return browserWindow;
}
