import { ipcMain } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import * as utils from './utils.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default ({ store, mainWindow }) => {

    ipcMain.handle('get-domain-history', () => {
        return store.get('domainHistory', null);
    });

    ipcMain.handle('save-domain', (event, url) => {
        let cleanUrl = url;

        try {
            const u = new URL(url);
            cleanUrl = `${u.protocol}//${u.host}`;
        } catch (error) {
            throw error;
        }

        const entry = {
            url: cleanUrl,
            lastConnected: new Date().toISOString()
        };

        store.set('domainHistory', entry);

        return { success: true, domain: entry };
    });

    ipcMain.handle('load-domain', async (event, url) => {
        // Check URL reachability before loading
        const urlStatus = await utils.checkUrlReachable(url);
        if (!urlStatus.ok) {
            return false;
        }

        let result = null;

        function onNavigate() {
            result = true;
            mainWindow.webContents.removeListener("did-navigate", onNavigate);
        }

        mainWindow.webContents.once("did-navigate", onNavigate);

        try {
            await mainWindow.loadURL(url);
        } catch {
            result = false;
            mainWindow.webContents.removeListener("did-navigate", onNavigate);
        }

        return result;
    });
};
