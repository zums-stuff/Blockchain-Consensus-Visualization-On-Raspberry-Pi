import json
import os
from web3 import Web3
from datetime import datetime

# --- CONFIGURACIÓN ---
# Esta ruta debe coincidir con la configuración de tu server.py
IPC_PATH = "/home/raspberry-node/.testchain44/geth.ipc"
OUTPUT_FILENAME = "mined_blocks_data.json"

def get_web3_connection():
    """Establece conexión IPC con el nodo Geth local"""
    if os.path.exists(IPC_PATH):
        try:
            w3 = Web3(Web3.IPCProvider(IPC_PATH))
            if w3.is_connected():
                return w3
        except Exception as e:
            print(f"Error conectando a Geth: {e}")
    return None

def fetch_and_save_blocks():
    w3 = get_web3_connection()
    
    if not w3:
        print("No se pudo conectar a Geth para guardar los datos.")
        return

    try:
        latest_block = w3.eth.block_number
        print(f"Extrayendo datos de {latest_block} bloques...")

        blockchain_data = []

        # Recorremos desde el bloque 0 hasta el último
        for i in range(latest_block + 1):
            block = w3.eth.get_block(i)
            
            # Calculamos el tiempo entre bloques (Time Diff)
            time_diff = 0
            if i > 0:
                prev_block = w3.eth.get_block(i - 1)
                time_diff = block.timestamp - prev_block.timestamp

            block_info = {
                "number": block.number,
                "hash": block.hash.hex(),
                "parentHash": block.parentHash.hex(),
                "miner": block.miner,
                "difficulty": block.difficulty,
                "size": block.size,
                "gasUsed": block.gasUsed,
                "timestamp": block.timestamp,
                "time_diff_seconds": time_diff,
                "date": datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            }
            blockchain_data.append(block_info)

        # Guardar en archivo JSON
        with open(OUTPUT_FILENAME, 'w') as f:
            json.dump(blockchain_data, f, indent=4)
            
        print(f"Datos guardados exitosamente en {OUTPUT_FILENAME}")
        print(f"Total bloques: {len(blockchain_data)}")

    except Exception as e:
        print(f"Error procesando los bloques: {e}")

if __name__ == "__main__":
    fetch_and_save_blocks()