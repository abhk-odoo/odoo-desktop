import { ipcMain } from 'electron';

export default ({ printService }) => {
    ipcMain.handle('get-print-port', () => {
        return printService ? printService.getPort() : null;
    });
};
