import time
import subprocess
import json
import os
import socket
import threading
import hashlib
import webbrowser
from web3 import Web3
from flask import Flask, render_template_string, jsonify

# --- CONFIGURACIÓN ---
IPC_PATH = "/home/raspberry-node/.testchain44/geth.ipc"
CONFIG_FILE_PATH = "configuration_run.txt"
PORT = 8080

app = Flask(__name__)

# Estado global
state = {
    "blocks_by_number": {}, 
    "canonical_chain": [],
    "my_color": "#444444", 
    "hostname": socket.gethostname(),
    "peers": 0,
    "known_miners": {} 
}

# --- PLANTILLA HTML/CSS/JS ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Blockchain Visualization</title>
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        .sidebar { width: 220px; background: #181818; padding: 20px; flex-shrink: 0; border-right: 1px solid #333; display: flex; flex-direction: column; }
        .miner-item { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 0.8rem; word-break: break-all;}
        .miner-color { width: 15px; height: 15px; border-radius: 50%; border: 1px solid #fff; flex-shrink: 0;}
        
        .main-content { flex-grow: 1; display: flex; flex-direction: column; min-width: 0; }
        
        .header { background: #1e1e1e; padding: 0 30px; height: 70px; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; border-bottom: 1px solid #333; }
        .my-id { display: flex; align-items: center; gap: 15px; }
        .my-dot { width: 30px; height: 30px; border-radius: 50%; border: 2px solid #fff; display: grid; place-items: center; font-size: 0.7rem; color: #000; font-weight: bold; }

        .chain-view { flex-grow: 1; position: relative; overflow-x: auto; overflow-y: auto; background: #0f0f0f; display: flex; align-items: center; padding: 40px; }
        .chain-container { display: flex; gap: 40px; padding-right: 100px; align-items: flex-start; }
        
        .block-column { display: flex; flex-direction: column; gap: 20px; align-items: center; }
        
        .block {
            width: 170px; height: 240px; /* Ligeramente mas alto para que quepa la firma y las txs */
            background-color: #ccc; border-radius: 8px; color: #000;
            display: flex; flex-direction: column; justify-content: space-between;
            padding: 8px; border: 2px solid rgba(255,255,255,0.2);
            position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            transition: all 0.3s;
        }
        
        .block.orphan { opacity: 0.6; border: 2px dashed #ff4444; transform: scale(0.9); }
        .block.canonical { border: 2px solid #fff; box-shadow: 0 0 15px rgba(255,255,255,0.2); }

        .block-num { font-size: 1.8rem; font-weight: 800; text-align: center; opacity: 0.8; }
        .info-row { font-size: 0.65rem; margin-bottom: 3px; }
        .hash-val { font-family: monospace; background: rgba(255,255,255,0.5); padding: 2px; border-radius: 3px; }
        .miner-badge { background: rgba(0,0,0,0.15); padding: 4px; text-align: center; font-weight: bold; border-radius: 4px; font-size: 0.8rem; text-transform: uppercase; }

        
        /* Botón para forzar scroll al final */
        #goToEndBtn {
            display: none;
            position: absolute; bottom: 220px; right: 30px;
            background: #4caf50; color: white; border: none; padding: 10px 20px;
            border-radius: 20px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>Mineros en la Red</h3>
        <div id="minerList"></div>
    </div>

    <div class="main-content">
        <div class="header">
            <div class="my-id">
                <div class="my-dot" id="myColorDot">YO</div>
                <div>
                    <h2 style="margin:0" id="hostname">{{ hostname }}</h2>
                    <small id="myAddress" style="color:#888; font-family:monospace;">...</small>
                </div>
            </div>
            <div style="text-align:right;">
                <h3 style="margin:0">PEERS: <span id="peerCount">0</span></h3>
                <small>Bloque Actual: <span id="latestBlock">0</span></small>
            </div>
        </div>

        <div class="chain-view" id="scrollArea">
            <div class="chain-container" id="chainContainer">Cargando cadena...</div>
        </div>
        <button id="goToEndBtn" onclick="forceScrollRight()">Ir al Final ➔</button>

    </div>

    <script>
        let lastDataString = "";
        const scrollArea = document.getElementById('scrollArea');
        const goToEndBtn = document.getElementById('goToEndBtn');
        let userHasScrolled = false;

        //Detectar si el usuario hace scroll manual
        scrollArea.addEventListener('scroll', () => {
            const isAtEnd = scrollArea.scrollWidth - scrollArea.scrollLeft - scrollArea.clientWidth < 50;
            
            if (!isAtEnd) {
                userHasScrolled = true;
                goToEndBtn.style.display = 'block'; //Botón "Ir al final"
            } else {
                userHasScrolled = false;
                goToEndBtn.style.display = 'none'; //Ocultar botón si ya está al final
            }
        });

        function forceScrollRight() {
            scrollArea.scrollLeft = scrollArea.scrollWidth;
            userHasScrolled = false;
            goToEndBtn.style.display = 'none';
        }

        function update() {
            fetch('/data').then(r => r.json()).then(data => {
                document.getElementById('peerCount').innerText = data.peers;
                document.getElementById('myColorDot').style.backgroundColor = data.my_color;
                document.getElementById('myAddress').innerText = data.my_address;
                
                //Lista de mineros
                let minersHtml = '';
                for (const [addr, color] of Object.entries(data.known_miners)) {
                    minersHtml += `<div class="miner-item" style="${addr === data.my_address ? 'border:1px solid #fff; padding:5px;' : ''}">
                        <div class="miner-color" style="background:${color}"></div>
                        ${addr.substring(0,10)}... ${addr === data.my_address ? ' (YO)' : ''}
                    </div>`;
                }
                document.getElementById('minerList').innerHTML = minersHtml;

                const dataStr = JSON.stringify(data.blocks_by_number);
                
                if (dataStr !== lastDataString) {
                    lastDataString = dataStr;
                    const container = document.getElementById('chainContainer');
                    let html = '';
                    let maxBlock = 0;

                    const blockNums = Object.keys(data.blocks_by_number).sort((a,b) => a-b);
                    
                    if(blockNums.length > 0) {
                        maxBlock = blockNums[blockNums.length - 1];
                        document.getElementById('latestBlock').innerText = maxBlock;

                        blockNums.forEach(num => {
                            const blocksAtHeight = data.blocks_by_number[num];

                            html += `<div class="block-column">`;
                            blocksAtHeight.forEach(b => {
                                const isCanonical = data.canonical_chain.includes(b.hash);
                                const styleClass = isCanonical ? "canonical" : "orphan";
                                
                                let minerLabel = "NODO: " + b.miner.substring(0,10) + "..";
                                if(b.is_me) minerLabel = "ESTE NODO (YO)";

                                html += `
                                <div class="block ${styleClass}" style="background:${b.color}">
                                    <div class="block-num">${b.number}</div>
                                    <div class="info-row">
                                        <strong>PREV HASH</strong> <div class="hash-val">${b.parentHash.substring(0,16)}...</div>
                                    </div>
                                    <div class="info-row">
                                        <strong>ESTE BLOQUE</strong> <div class="hash-val">${b.hash.substring(0,16)}...</div>
                                    </div>
                                    <div class="info-row">
                                        <strong>FIRMADO POR</strong> <div class="hash-val" style="background:rgba(255,255,255,0.8); font-weight:bold; color:#000;">${b.miner.substring(0,12)}...</div>
                                    </div>
                                    <div class="info-row">
                                        <strong>TXs:</strong> <div class="hash-val" style="display:inline-block; font-weight:bold;">${b.tx_count}</div>
                                    </div>
                                    <div class="miner-badge">${minerLabel}</div>
                                    ${!isCanonical ? '<div style="background:red; color:white; font-size:0.6rem; text-align:center; margin-top:2px;">ORPHAN</div>' : ''}
                                </div>`;
                            });
                            html += `</div>`;
                            if (num < maxBlock) html += `<div style="font-size:2rem; color:#333; margin-top:80px;">→</div>`;
                        });
                        
                        container.innerHTML = html;
                        
                        //=== LÓGICA DE AUTO-SCROLL ===
                        if (!userHasScrolled) {
                            requestAnimationFrame(() => {
                                scrollArea.scrollLeft = scrollArea.scrollWidth;
                            });
                        }
                    }
                }
            }).catch(e => {});
        }

        setInterval(update, 1000);
    </script>
</body>
</html>
'''

# --- UTILS ---
def get_color_for_address(address):
    if not address: return "#333"
    hash_obj = hashlib.md5(address.encode())
    digest = hash_obj.digest()
    h = int(digest[0]) * 360 / 255
    return f"hsl({h:.0f}, 70%, 50%)"

def get_web3():
    try:
        w3 = Web3(Web3.IPCProvider(IPC_PATH))
        if w3.is_connected(): return w3
    except: pass
    return None

def get_local_address_from_file():
    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r') as f:
                for line in f:
                    if "eth_account" in line:
                        parts = line.split(':')
                        if len(parts) > 1: return parts[1].strip().lower()
    except: pass
    return None

def update_loop():
    global state
    memory_blocks = {} 
    known_miners_colors = {}

    while True:
        w3 = get_web3()
        if w3:
            try:
                try: my_address = w3.eth.coinbase.lower()
                except: my_address = ""

                latest = w3.eth.block_number
                start = max(0, latest - 50) 
                
                current_canonical_hashes = []
                
                for i in range(start, latest + 1):
                    try:
                        blk = w3.eth.get_block(i)
                        blk_hash = blk['hash'].hex()
                        current_canonical_hashes.append(blk_hash)
                        
                        if blk_hash not in memory_blocks:
                            miner_addr = blk['miner'].lower()
                            miner_name = miner_addr 
                            
                            if miner_name not in known_miners_colors:
                                known_miners_colors[miner_name] = get_color_for_address(miner_addr)

                            memory_blocks[blk_hash] = {
                                "number": i,
                                "hash": blk_hash,
                                "parentHash": blk['parentHash'].hex(),
                                "miner": miner_addr,
                                "miner_name": miner_name,
                                "tx_count": len(blk['transactions']), # Captura de transacciones agregada
                                "difficulty": blk['difficulty'],
                                "color": known_miners_colors[miner_name],
                                "is_me": (miner_addr == my_address)
                            }
                    except: pass
                
                blocks_by_number = {}
                for h, b in memory_blocks.items():
                    if b['number'] >= start and b['number'] <= latest:
                        num = b['number']
                        if num not in blocks_by_number: blocks_by_number[num] = []
                        blocks_by_number[num].append(b)

                state["blocks_by_number"] = blocks_by_number
                state["canonical_chain"] = current_canonical_hashes
                state["known_miners"] = known_miners_colors
                state["peers"] = w3.net.peer_count
                state["my_address"] = my_address if my_address else "Detectando..."

            except Exception as e:
                print(f"Viz Error: {e}")
        
        time.sleep(1)

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE, hostname=socket.gethostname())
@app.route('/data')
def data(): return jsonify(state)

def open_browser():
    time.sleep(2)  # wait for Flask to start
    hostname = socket.gethostname()
    url = f'http://{hostname}.local:{PORT}'
    env = dict(os.environ)
    if 'DISPLAY' not in env: env['DISPLAY'] = ':0'
    if 'WAYLAND_DISPLAY' not in env: env['WAYLAND_DISPLAY'] = 'wayland-1'

    try:
        subprocess.Popen(['chromium-browser', '--start-fullscreen', url], env=env)
    except Exception:
        webbrowser.open(url)

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    threading.Thread(target=update_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, debug=False)