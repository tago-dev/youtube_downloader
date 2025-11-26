// Preload script para Electron
// Expõe APIs seguras para o renderer process se necessário

const { contextBridge, ipcRenderer } = require('electron');

// Expõe funções seguras para o frontend (se necessário no futuro)
contextBridge.exposeInMainWorld('electronAPI', {
  // Exemplo: abrir pasta de downloads
  openDownloadsFolder: () => ipcRenderer.send('open-downloads'),
  
  // Versão do app
  getVersion: () => process.env.npm_package_version || '1.0.0',
  
  // Plataforma
  platform: process.platform
});

console.log('Preload script carregado - Video Downloader Pro');
