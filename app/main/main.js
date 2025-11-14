import { app } from 'electron';
import PrintService from './services/print_service.js';
import Store from 'electron-store';
import registerIpc from './ipc/index.js';
import { createMainWindow } from './modules/window.js';
import { loadInitialPage } from './modules/startup.js';
import { logoutInterceptor } from './modules/session.js';

/**
 * @type {import('electron').BrowserWindow | null}
 */
let mainWindow = null;

/**
 * @type {import('./services/print_service.js').default | null}
 */
let printService = null;

const store = new Store();

async function initializePrintService() {
    printService = new PrintService();
    try {
        await printService.start();
    } catch (err) {
        console.error('Print service failed:', err.message);
    }
}

async function startApp() {
    try {
        await initializePrintService();

        mainWindow = await createMainWindow();
        registerIpc({ mainWindow, store, printService });

        logoutInterceptor(mainWindow);

        await loadInitialPage(mainWindow, store);
    } catch (error) {
        console.error('Application initialization failed:', error);
    }
}

app.whenReady().then(startApp);

// Handle quit
let isQuitting = false;
app.on('before-quit', async (event) => {
    if (isQuitting) {
        return
    };
    event.preventDefault();
    isQuitting = true;

    if (printService) {
        await printService.stop()
    };

    process.exit(0);
});

app.on('window-all-closed', async () => {
    if (printService) {
        await printService.stop()
    };
    if (process.platform !== 'darwin') {
        app.quit()
    };
});

// Handle system signals
['SIGINT', 'SIGTERM'].forEach(signal => {
    process.on(signal, async () => {
        if (printService) await printService.stop();
        process.exit(0);
    });
});
