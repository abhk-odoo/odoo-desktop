const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('printer', {
  printReceipt: async (content) => {
    const port = await ipcRenderer.invoke('get-print-port');
    try {
      const response = await fetch(`http://localhost:${port}/print`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(content)
      });
      const respJson = await response.json();
      return respJson;
    } catch (err) {
      return {
        success: false,
        message: err.message
      }
    }
  },
  getDefaultPrinter: async () => {
    const port = await ipcRenderer.invoke('get-print-port');
    try {
      const res = await fetch(`http://localhost:${port}/printer`);
      return await res.json();
    } catch (error) {
      return { success: false, message: error.message};
    }
  }
});

// API for startup screen
contextBridge.exposeInMainWorld('domain', {
  load_domain: (url) => ipcRenderer.invoke('load-domain', url),
  get_domain_history: () => ipcRenderer.invoke('get-domain-history'),
  save_domain: (url) => ipcRenderer.invoke('save-domain', url)
});

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
