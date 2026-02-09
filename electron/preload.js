const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // ─── Informações do App ─────────────────────────────
  getAppInfo: () => ipcRenderer.invoke('get-app-info'),
  platform: process.platform,

  // ─── Downloads ──────────────────────────────────────
  openDownloadsFolder: () => ipcRenderer.send('open-downloads'),
  getDownloadsPath: () => ipcRenderer.invoke('get-downloads-path'),
  showItemInFolder: (filepath) => ipcRenderer.send('show-item-in-folder', filepath),
  showSaveDialog: (options) => ipcRenderer.invoke('show-save-dialog', options),

  // ─── Links Externos ────────────────────────────────
  openExternal: (url) => ipcRenderer.send('open-external', url),

  // ─── Notificações ──────────────────────────────────
  notify: (title, body) => ipcRenderer.send('notify', { title, body }),

  // ─── Estado ────────────────────────────────────────
  isElectron: true
});

console.log('[Preload] Video Downloader Pro - APIs expostas com sucesso');
