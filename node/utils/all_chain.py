import json
import os
import time
from web3 import Web3
from hexbytes import HexBytes # Importante

IPC_PATH = "/home/raspberry-node/.testchain44/geth.ipc"
OUTPUT_FILENAME = "all_chain_data.json"

# Clase personalizada para convertir HexBytes a String en el JSON
class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)

def get_web3_connection():
    if os.path.exists(IPC_PATH):
        try:
            w3 = Web3(Web3.IPCProvider(IPC_PATH))
            if w3.is_connected():
                return w3
        except Exception:
            return None
    return None

def export_all_chain():
    w3 = get_web3_connection()
    if not w3:
        return

    try:
        latest = w3.eth.block_number
        chain_data = []

        for i in range(latest + 1):
            # Obtenemos bloque
            block = w3.eth.get_block(i, full_transactions=True)
            # Convertimos AttributeDict a dict normal para poder serializar
            block_dict = dict(block)
            chain_data.append(block_dict)

        # Guardamos usando el Encoder personalizado
        with open(OUTPUT_FILENAME, 'w') as f:
            json.dump(chain_data, f, indent=4, cls=HexJsonEncoder)
            
        print(f"Cadena exportada: {len(chain_data)} bloques.")

    except Exception as e:
        print(f"Error exportando cadena: {e}")

if __name__ == "__main__":
    export_all_chain()