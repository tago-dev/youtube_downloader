import webview
import sys
import threading
import time
import os
from app import app

# Garante que a pasta de downloads existe no local correto
if getattr(sys, 'frozen', False):
    # Se estiver rodando como executável
    base_dir = os.path.dirname(sys.executable)
else:
    # Se estiver rodando como script
    base_dir = os.path.dirname(os.path.abspath(__file__))

download_dir = os.path.join(base_dir, 'downloads')
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

def run_server():
    # Roda o Flask
    app.run(host='127.0.0.1', port=54321, debug=False, use_reloader=False)

def main():
    # Inicia o servidor Flask em uma thread separada
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()

    # Aguarda um pouco para o servidor subir
    time.sleep(1)

    # Cria a janela do aplicativo nativo apontando para o Flask local
    webview.create_window(
        'YouTube Downloader Pro', 
        'http://127.0.0.1:54321', 
        width=1000, 
        height=800,
        resizable=True
    )
    
    webview.start()

if __name__ == '__main__':
    main()
