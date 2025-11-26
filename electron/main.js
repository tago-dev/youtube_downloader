const { app, BrowserWindow, shell, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let pythonProcess;
const PORT = 54321;

// Determina se está em modo desenvolvimento ou produção
const isDev = !app.isPackaged;

function getBackendPath() {
  if (isDev) {
    // Desenvolvimento: pasta pai do electron
    return path.join(__dirname, '..');
  } else {
    // Produção: pasta extraResources
    return path.join(process.resourcesPath, 'backend');
  }
}

function getPythonCommand() {
  // Tenta encontrar o Python no sistema
  const platform = process.platform;
  
  if (platform === 'win32') {
    return 'python';
  } else {
    // macOS e Linux
    return 'python3';
  }
}

function startPythonBackend() {
  return new Promise((resolve, reject) => {
    const backendPath = getBackendPath();
    const pythonCmd = getPythonCommand();
    const appPath = path.join(backendPath, 'app.py');

    console.log(`Iniciando backend Python em: ${appPath}`);
    console.log(`Usando comando: ${pythonCmd}`);

    // Define variáveis de ambiente
    const env = {
      ...process.env,
      FLASK_APP: appPath,
      FLASK_ENV: isDev ? 'development' : 'production',
      PYTHONUNBUFFERED: '1'
    };

    // Inicia o processo Python
    pythonProcess = spawn(pythonCmd, [appPath], {
      cwd: backendPath,
      env: env,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    pythonProcess.stdout.on('data', (data) => {
      console.log(`Python stdout: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      console.log(`Python stderr: ${data}`);
    });

    pythonProcess.on('error', (error) => {
      console.error('Erro ao iniciar Python:', error);
      dialog.showErrorBox(
        'Erro ao iniciar o servidor',
        `Não foi possível iniciar o backend Python.\n\nCertifique-se de que o Python 3 está instalado e acessível no PATH.\n\nErro: ${error.message}`
      );
      reject(error);
    });

    pythonProcess.on('close', (code) => {
      console.log(`Processo Python encerrado com código: ${code}`);
    });

    // Aguarda o servidor Flask estar pronto
    waitForServer(resolve, reject);
  });
}

function waitForServer(resolve, reject, attempts = 0) {
  const maxAttempts = 30; // 30 tentativas = 15 segundos
  
  if (attempts >= maxAttempts) {
    reject(new Error('Timeout aguardando servidor Flask iniciar'));
    return;
  }

  const options = {
    hostname: '127.0.0.1',
    port: PORT,
    path: '/',
    method: 'GET',
    timeout: 500
  };

  const req = http.request(options, (res) => {
    console.log(`Servidor Flask respondeu com status: ${res.statusCode}`);
    resolve();
  });

  req.on('error', () => {
    // Servidor ainda não está pronto, tenta novamente
    setTimeout(() => waitForServer(resolve, reject, attempts + 1), 500);
  });

  req.on('timeout', () => {
    req.destroy();
    setTimeout(() => waitForServer(resolve, reject, attempts + 1), 500);
  });

  req.end();
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'Video Downloader Pro',
    icon: path.join(__dirname, 'icons', 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    autoHideMenuBar: true,
    backgroundColor: '#1a1a2e'
  });

  // Carrega a URL do Flask
  mainWindow.loadURL(`http://127.0.0.1:${PORT}`);

  // Abre links externos no navegador padrão
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // DevTools apenas em desenvolvimento
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Quando o Electron está pronto
app.whenReady().then(async () => {
  try {
    // Mostra uma janela de loading ou splash aqui se quiser
    console.log('Iniciando backend Python...');
    await startPythonBackend();
    console.log('Backend iniciado com sucesso!');
    createWindow();
  } catch (error) {
    console.error('Erro fatal:', error);
    dialog.showErrorBox('Erro', `Não foi possível iniciar o aplicativo: ${error.message}`);
    app.quit();
  }
});

// Encerra o processo Python quando o app fecha
app.on('before-quit', () => {
  if (pythonProcess) {
    console.log('Encerrando processo Python...');
    pythonProcess.kill('SIGTERM');
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// Trata erros não capturados
process.on('uncaughtException', (error) => {
  console.error('Erro não capturado:', error);
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
  }
});
