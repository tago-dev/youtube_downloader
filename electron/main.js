const { app, BrowserWindow, shell, dialog, ipcMain, Tray, Menu, nativeImage, Notification } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

let mainWindow;
let splashWindow;
let tray;
let pythonProcess;
const PORT = 54321;

const isDev = !app.isPackaged;

// ─── Paths ───────────────────────────────────────────────
function getBackendPath() {
  if (isDev) {
    return path.join(__dirname, '..');
  }
  return path.join(process.resourcesPath, 'backend');
}

function getDownloadsPath() {
  const backendPath = getBackendPath();
  const downloadsDir = path.join(backendPath, 'downloads');
  if (!fs.existsSync(downloadsDir)) {
    fs.mkdirSync(downloadsDir, { recursive: true });
  }
  return downloadsDir;
}

function getIconPath() {
  const iconName = process.platform === 'win32' ? 'icon.ico' : 'icon.png';
  const iconPath = path.join(__dirname, 'icons', iconName);
  if (fs.existsSync(iconPath)) return iconPath;
  return undefined;
}

function getPythonCommand() {
  if (process.platform === 'win32') {
    return 'python';
  }
  return 'python3';
}

// ─── Splash Screen ──────────────────────────────────────
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 400,
    height: 300,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    icon: getIconPath(),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  splashWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(getSplashHTML())}`);
  splashWindow.center();
}

function getSplashHTML() {
  return `<!DOCTYPE html>
<html>
<head>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    -webkit-app-region: drag;
    user-select: none;
  }
  .card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d1b69 100%);
    border-radius: 24px;
    padding: 48px 40px;
    text-align: center;
    box-shadow: 0 25px 60px rgba(0,0,0,0.4);
    width: 380px;
  }
  .icon { font-size: 48px; margin-bottom: 16px; }
  h1 { color: #fff; font-size: 22px; font-weight: 700; margin-bottom: 8px; }
  p { color: rgba(255,255,255,0.7); font-size: 13px; margin-bottom: 28px; }
  .loader-track {
    width: 100%;
    height: 4px;
    background: rgba(255,255,255,0.15);
    border-radius: 4px;
    overflow: hidden;
  }
  .loader-bar {
    height: 100%;
    width: 40%;
    background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    border-radius: 4px;
    animation: slide 1.2s ease-in-out infinite;
  }
  @keyframes slide {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(350%); }
  }
  .status { color: rgba(255,255,255,0.5); font-size: 11px; margin-top: 16px; }
</style>
</head>
<body>
  <div class="card">
    <div class="icon">⬇️</div>
    <h1>Playdown</h1>
    <p>YouTube • Instagram • Twitter/X</p>
    <div class="loader-track"><div class="loader-bar"></div></div>
    <div class="status">Iniciando servidor...</div>
  </div>
</body>
</html>`;
}

// ─── Main Window ─────────────────────────────────────────
function createMainWindow() {
  const iconPath = getIconPath();

  mainWindow = new BrowserWindow({
    width: 1100,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    show: false,
    title: 'Playdown',
    icon: iconPath,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    trafficLightPosition: { x: 16, y: 16 },
    backgroundColor: '#0f172a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      spellcheck: false
    },
    autoHideMenuBar: true
  });

  mainWindow.loadURL(`http://127.0.0.1:${PORT}`);

  // Abrir links externos no navegador padrão
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Interceptar navegação para links externos
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(`http://127.0.0.1:${PORT}`)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  mainWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.destroy();
      splashWindow = null;
    }
    mainWindow.show();
    mainWindow.focus();
  });

  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  mainWindow.on('close', (event) => {
    if (process.platform === 'darwin' && !app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ─── System Tray ─────────────────────────────────────────
function createTray() {
  const iconPath = getIconPath();
  let trayIcon;

  if (iconPath) {
    trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 18, height: 18 });
  } else {
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);
  tray.setToolTip('Playdown');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Abrir Playdown',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: 'Abrir Pasta de Downloads',
      click: () => {
        shell.openPath(getDownloadsPath());
      }
    },
    { type: 'separator' },
    {
      label: 'Sobre',
      click: () => {
        dialog.showMessageBox({
          type: 'info',
          title: 'Playdown',
          message: `Playdown v${app.getVersion()}`,
          detail: 'Baixe vídeos do YouTube, Instagram e Twitter/X.\nFeito com ❤️ por Tiago.'
        });
      }
    },
    { type: 'separator' },
    {
      label: 'Sair',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.focus();
      } else {
        mainWindow.show();
      }
    }
  });
}

// ─── Python Backend ──────────────────────────────────────
function startPythonBackend() {
  return new Promise((resolve, reject) => {
    const backendPath = getBackendPath();
    const pythonCmd = getPythonCommand();
    const appPath = path.join(backendPath, 'app.py');

    console.log(`[Backend] Path: ${appPath}`);
    console.log(`[Backend] Python: ${pythonCmd}`);
    console.log(`[Backend] CWD: ${backendPath}`);

    const env = {
      ...process.env,
      FLASK_APP: appPath,
      FLASK_ENV: isDev ? 'development' : 'production',
      PYTHONUNBUFFERED: '1',
      PORT: String(PORT)
    };

    pythonProcess = spawn(pythonCmd, [appPath], {
      cwd: backendPath,
      env,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    pythonProcess.stdout.on('data', (data) => {
      console.log(`[Python] ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      const msg = data.toString().trim();
      console.log(`[Python] ${msg}`);
    });

    pythonProcess.on('error', (error) => {
      console.error('[Backend] Erro ao iniciar Python:', error);
      reject(error);
    });

    pythonProcess.on('close', (code) => {
      console.log(`[Backend] Processo encerrado (código: ${code})`);
      pythonProcess = null;

      if (code !== 0 && code !== null && mainWindow && !app.isQuitting) {
        dialog.showErrorBox(
          'Servidor encerrado',
          'O servidor backend encerrou inesperadamente.\nO aplicativo será fechado.'
        );
        app.quit();
      }
    });

    waitForServer(resolve, reject);
  });
}

function waitForServer(resolve, reject, attempts = 0) {
  const maxAttempts = 60;

  if (attempts >= maxAttempts) {
    reject(new Error('Timeout: servidor Flask não iniciou em 30 segundos'));
    return;
  }

  if (!pythonProcess || pythonProcess.killed) {
    reject(new Error('Processo Python encerrou antes de ficar pronto'));
    return;
  }

  const req = http.request({
    hostname: '127.0.0.1',
    port: PORT,
    path: '/health',
    method: 'GET',
    timeout: 400
  }, (res) => {
    if (res.statusCode === 200) {
      console.log('[Backend] Servidor pronto!');
      resolve();
    } else {
      setTimeout(() => waitForServer(resolve, reject, attempts + 1), 500);
    }
  });

  req.on('error', () => {
    setTimeout(() => waitForServer(resolve, reject, attempts + 1), 500);
  });

  req.on('timeout', () => {
    req.destroy();
    setTimeout(() => waitForServer(resolve, reject, attempts + 1), 500);
  });

  req.end();
}

function stopPythonBackend() {
  if (pythonProcess) {
    console.log('[Backend] Encerrando processo Python...');
    pythonProcess.kill('SIGTERM');

    setTimeout(() => {
      if (pythonProcess && !pythonProcess.killed) {
        console.log('[Backend] Forçando encerramento (SIGKILL)');
        pythonProcess.kill('SIGKILL');
      }
    }, 3000);
  }
}

// ─── IPC Handlers ────────────────────────────────────────
function setupIPC() {
  ipcMain.handle('get-app-info', () => {
    return {
      version: app.getVersion(),
      platform: process.platform,
      arch: process.arch,
      isDev,
      downloadsPath: getDownloadsPath()
    };
  });

  ipcMain.on('open-downloads', () => {
    shell.openPath(getDownloadsPath());
  });

  ipcMain.on('open-external', (event, url) => {
    shell.openExternal(url);
  });

  ipcMain.handle('show-save-dialog', async (event, options) => {
    const result = await dialog.showSaveDialog(mainWindow, {
      title: 'Salvar vídeo',
      defaultPath: path.join(app.getPath('downloads'), options.filename || 'video.mp4'),
      filters: [
        { name: 'Vídeo', extensions: ['mp4', 'webm', 'mkv'] },
        { name: 'Áudio', extensions: ['mp3', 'webm', 'm4a', 'ogg'] },
        { name: 'Todos', extensions: ['*'] }
      ]
    });
    return result;
  });

  ipcMain.on('notify', (event, { title, body }) => {
    if (Notification.isSupported()) {
      new Notification({ title, body }).show();
    }
  });

  ipcMain.handle('get-downloads-path', () => {
    return getDownloadsPath();
  });

  ipcMain.on('show-item-in-folder', (event, filepath) => {
    shell.showItemInFolder(filepath);
  });
}

// ─── App Menu (macOS) ────────────────────────────────────
function buildAppMenu() {
  const isMac = process.platform === 'darwin';

  const template = [
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about', label: 'Sobre Playdown' },
        { type: 'separator' },
        { role: 'hide', label: 'Ocultar' },
        { role: 'hideOthers', label: 'Ocultar Outros' },
        { role: 'unhide', label: 'Mostrar Todos' },
        { type: 'separator' },
        { role: 'quit', label: 'Sair' }
      ]
    }] : []),
    {
      label: 'Editar',
      submenu: [
        { role: 'undo', label: 'Desfazer' },
        { role: 'redo', label: 'Refazer' },
        { type: 'separator' },
        { role: 'cut', label: 'Recortar' },
        { role: 'copy', label: 'Copiar' },
        { role: 'paste', label: 'Colar' },
        { role: 'selectAll', label: 'Selecionar Tudo' }
      ]
    },
    {
      label: 'Visualizar',
      submenu: [
        { role: 'reload', label: 'Recarregar' },
        { role: 'forceReload', label: 'Forçar Recarregar' },
        { type: 'separator' },
        { role: 'resetZoom', label: 'Tamanho Padrão' },
        { role: 'zoomIn', label: 'Aumentar Zoom' },
        { role: 'zoomOut', label: 'Diminuir Zoom' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: 'Tela Cheia' },
        ...(isDev ? [{ type: 'separator' }, { role: 'toggleDevTools', label: 'DevTools' }] : [])
      ]
    },
    {
      label: 'Janela',
      submenu: [
        { role: 'minimize', label: 'Minimizar' },
        { role: 'zoom', label: 'Zoom' },
        ...(isMac ? [
          { type: 'separator' },
          { role: 'front', label: 'Trazer Tudo pra Frente' }
        ] : [
          { role: 'close', label: 'Fechar' }
        ])
      ]
    }
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ─── App Lifecycle ───────────────────────────────────────
app.whenReady().then(async () => {
  app.isQuitting = false;

  buildAppMenu();
  setupIPC();
  createSplashWindow();

  try {
    console.log('[App] Iniciando backend Python...');
    await startPythonBackend();
    console.log('[App] Backend pronto, criando janela...');

    createTray();
    createMainWindow();
  } catch (error) {
    console.error('[App] Erro fatal:', error);

    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.destroy();
    }

    dialog.showErrorBox(
      'Erro ao iniciar',
      `Não foi possível iniciar o Playdown.\n\n` +
      `Verifique se o Python 3 está instalado e acessível no PATH.\n\n` +
      `Erro: ${error.message}`
    );
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  stopPythonBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null || mainWindow.isDestroyed()) {
    // Só recria se o backend já estiver rodando
    if (pythonProcess && !pythonProcess.killed) {
      createMainWindow();
    }
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
});

// Previne múltiplas instâncias
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// Tratamento de erros não capturados
process.on('uncaughtException', (error) => {
  console.error('[App] Erro não capturado:', error);
  stopPythonBackend();
});

process.on('unhandledRejection', (reason) => {
  console.error('[App] Promise não tratada:', reason);
});
