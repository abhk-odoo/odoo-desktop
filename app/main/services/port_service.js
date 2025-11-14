import net from 'net';

/**
 * Find an available port within the specified range
 * @param {number} start - Starting port number (default: 5050)
 * @param {number} end - Ending port number (default: 6000)
 * @returns {Promise<number>} - Promise that resolves to an available port
 */
export const findAvailablePort = (start = 5050, end = 6000) => {
    return new Promise((resolve, reject) => {
        const tryPort = (port) => {
            const server = net.createServer();

            server.once('error', (err) => {
                if (err.code === 'EADDRINUSE') {
                    if (port < end) {
                        tryPort(port + 1);
                    } else {
                        reject(new Error('No available port found'));
                    }
                } else {
                    reject(err);
                }
            });

            server.once('listening', () => {
                server.close(() => {
                    resolve(port);
                });
            });

            server.listen(port, '127.0.0.1');
        };

        tryPort(start);
    });
};
