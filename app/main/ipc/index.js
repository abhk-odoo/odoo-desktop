import printerIpc from './printer.ipc.js';
import domainIpc from './domain.ipc.js';

export default function registerIpc(context) {
    printerIpc(context);
    domainIpc(context);
}
