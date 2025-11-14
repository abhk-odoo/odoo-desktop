import { net } from 'electron';

export async function checkUrlReachable(url, timeout = 5000) {
    return new Promise((resolve) => {
        let timedOut = false;
        const req = net.request({
            method: 'GET',
            url,
        });

        const timer = setTimeout(() => {
            timedOut = true;
            req.abort();
            resolve({ ok: false, error: 'timeout' });
        }, timeout);

        req.on('response', (res) => {
            clearTimeout(timer);
            // treat 2xx and 3xx as reachable
            const ok = res.statusCode >= 200 && res.statusCode < 400;
            resolve({ ok, statusCode: res.statusCode });
            // consume body to free sockets
            res.on('data', () => {});
            res.on('end', () => {});
        });

        req.on('error', (error) => {
            if (!timedOut) {
                clearTimeout(timer);
                resolve({ ok: false, error: error.message });
            }
        });

        req.end();
    });
}
