const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('printer', {
  printReceipt: async (content) => {
    try {
      const port = await ipcRenderer.invoke('get-print-port');
      const response = await fetch(`http://localhost:${port}/print`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(content)
      });
      return await response.json();
    } catch (error) {
      return {
        status: false,
        printer: null,
        message: error.message,
        error_code: 'CONNECTION_FAILED'
      };
    }
  },
  getDefaultPrinter: async () => {
    try {
      const port = await ipcRenderer.invoke('get-print-port');
      const response = await fetch(`http://localhost:${port}/printer`);

      return await response.json();
    } catch (error) {
      return {
        status: false,
        printer: null,
        message: error.message,
        error_code: 'CONNECTION_FAILED'
      };
    }
  }
});

// API for startup screen
contextBridge.exposeInMainWorld('domain', {
  load_domain: (url) => ipcRenderer.invoke('load-domain', url),
  get_domain_history: () => ipcRenderer.invoke('get-domain-history'),
  save_domain: (url) => ipcRenderer.invoke('save-domain', url)
});

// Common API
contextBridge.exposeInMainWorld("isNativeApp", true);

const patchPushManagerOnly = `
(function() {
    if (!navigator.serviceWorker) {
        return;
    }

    const getRegistration = navigator.serviceWorker.getRegistration.bind(navigator.serviceWorker);

    navigator.serviceWorker.getRegistration = async function() {
        const reg = await getRegistration();

        if (!reg) {
            return reg;
        }

        // Patch pushManager ONLY if not already patched
        if (!reg._pushPatched) {
            Object.defineProperty(reg, "pushManager", {
                value: null,
                writable: false,
                configurable: false,
            });

            reg._pushPatched = true;
        }

        return reg;
    };
})();`;

window.addEventListener("DOMContentLoaded", () => {
    const script = document.createElement("script");
    script.textContent = patchPushManagerOnly;
    document.documentElement.appendChild(script);
});
