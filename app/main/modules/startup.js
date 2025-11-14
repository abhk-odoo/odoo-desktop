import path from 'path';
import { checkSession } from './session.js';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export async function loadInitialPage(mainWindow, store) {
    const domainList = store.get('domainHistory', null);
    const lastDomain = domainList?.url || null;

    if (!lastDomain) {
        return mainWindow.loadFile(
            path.join(__dirname, '../../renderer/startup/startup.html')
        );
    }

    const isLoggedIn = await checkSession(mainWindow, lastDomain);

    if (!isLoggedIn) {
        return mainWindow.loadFile(
            path.join(__dirname, '../../renderer/startup/startup.html')
        );
    }

    return;
}
