import json
import os
import time
from web3 import Web3

# --- CONFIGURACIÓN ---
IPC_PATH = "/home/raspberry-node/.testchain44/geth.ipc"
OUTPUT_FILENAME = "mining_node_data.json"

def get_web3_connection():
    if os.path.exists(IPC_PATH):
        try:
            w3 = Web3(Web3.IPCProvider(IPC_PATH))
            if w3.is_connected():
                return w3
        except Exception:
            return None
    return None

def save_mining_data():
    w3 = get_web3_connection()
    
    data = {
        "timestamp": time.time(),
        "status": "finished",
        "node_info": "Geth connection failed"
    }

    if w3:
        try:
            # Obtener información del nodo y red
            node_info = w3.geth.admin.node_info()
            peer_count = w3.net.peer_count
            is_mining = w3.eth.mining
            hashrate = w3.eth.hashrate
            gas_price = w3.eth.gas_price

            data = {
                "timestamp": time.time(),
                "node_id": node_info.get('id', 'unknown'),
                "enode": node_info.get('enode', 'unknown'),
                "ip": node_info.get('ip', 'unknown'),
                "peer_count": peer_count,
                "is_mining_at_stop": is_mining,
                "hashrate": hashrate,
                "gas_price": gas_price,
                "protocols": list(node_info.get('protocols', {}).keys())
            }
        except Exception as e:
            data["error"] = str(e)

    # Guardar en archivo JSON
    try:
        with open(OUTPUT_FILENAME, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Datos de nodo guardados en {OUTPUT_FILENAME}")
    except Exception as e:
        print(f"Error guardando JSON: {e}")

if __name__ == "__main__":
    save_mining_data()