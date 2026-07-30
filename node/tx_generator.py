import time
import csv
import sys
import threading
from web3 import Web3
import traceback

# Redirigir stdout y stderr a un archivo para depuración (sin buffer para escribir inmediato)
sys.stdout = open('tx_generator_log.txt', 'w', buffering=1)
sys.stderr = sys.stdout

# Configuracion
IPC_PATH = "/home/raspberry-node/.testchain44/geth.ipc"
PASSWORD = "mypi1"
TX_INTERVAL = 1  # Enviar una transacción cada 3 segundos
OUTPUT_CSV = "tx_metrics.csv"

tx_records = {}
csv_lock = threading.Lock()

def init_csv():
    with open(OUTPUT_CSV, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["tx_hash", "time_sent", "time_mined", "completion_time_sec", "block_number"])

def write_tx_to_csv(tx_hash, time_sent, time_mined, completion_time, block_number):
    with csv_lock:
        with open(OUTPUT_CSV, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([tx_hash, time_sent, time_mined, completion_time, block_number])

def check_receipts(w3):
    while True:
        try:
            # Iterar sobre una copia de las llaves para evitar RuntimeError
            pending_txs = list(tx_records.keys())
            for tx_hash in pending_txs:
                if tx_records[tx_hash]['mined'] == False:
                    try:
                        receipt = w3.eth.get_transaction_receipt(tx_hash)
                        if receipt is not None:
                            time_mined = time.time()
                            time_sent = tx_records[tx_hash]['time_sent']
                            completion_time = time_mined - time_sent
                            block_number = receipt['blockNumber']
                            
                            tx_records[tx_hash]['mined'] = True
                            tx_records[tx_hash]['completion_time'] = completion_time
                            
                            print(f"Tx {tx_hash.hex()[:8]}... minada en bloque {block_number}. Terminación: {completion_time:.3f} seg")
                            write_tx_to_csv(tx_hash.hex(), time_sent, time_mined, round(completion_time, 3), block_number)
                            
                            # Limpiar memoria
                            del tx_records[tx_hash]
                    except Exception:
                        pass # Aún no minada
        except Exception as e:
            print(f"Error verificando receipts: {e}\n{traceback.format_exc()}")
        time.sleep(1)

def start_generating():
    print("Inicializando Web3...")
    w3 = Web3(Web3.IPCProvider(IPC_PATH))
    
    # Intentar inyectar POA middleware (si aplica)
    try:
        from web3.middleware import geth_poa_middleware
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        print("POA middleware inyectado.")
    except Exception as e:
        print(f"Nota: No se inyectó POA middleware: {e}")

    # Esperar hasta conectar
    while not w3.is_connected():
        print("Esperando conexion a Geth...")
        time.sleep(2)
        
    print("Conectado a Geth exitosamente!")

    # Desbloquear cuenta coinbase
    sender = None
    while sender is None:
        try:
            # Usar llamada RPC directa porque w3.eth.coinbase fue removido en Web3 v6
            response = w3.provider.make_request('eth_coinbase', [])
            coinbase_addr = response.get('result')
            if coinbase_addr:
                sender_acc = w3.to_checksum_address(coinbase_addr)
                # Llamada directa RPC para desbloquear
                w3.provider.make_request('personal_unlockAccount', [sender_acc, PASSWORD, 0])
                sender = sender_acc
                print(f"Cuenta coinbase {sender} desbloqueada exitosamente.")
            else:
                print("No se encontró coinbase en geth. Reintentando en 2s...")
                time.sleep(2)
        except Exception as e:
            print(f"Error desbloqueando cuenta: {e}\n{traceback.format_exc()}")
            sender = None
            time.sleep(2)

    init_csv()
    
    # Iniciar hilo que verifica recibos
    receipt_thread = threading.Thread(target=check_receipts, args=(w3,), daemon=True)
    receipt_thread.start()
    
    # Esperar a que se genere el DAG y comience a minar bloques reales
    print("Esperando a que termine la generación del DAG (el nodo minará su primer bloque nuevo)...")
    initial_block = w3.eth.block_number
    while w3.eth.block_number == initial_block:
        time.sleep(2)
    print("¡DAG terminado y minería iniciada! Comenzando a enviar transacciones...")

    print(f"Iniciando generador de tráfico (1 Tx cada {TX_INTERVAL}s)...")
    tx_count = 0
    try:
        while True:
            # Enviar transacción a sí mismo (0 ETH de valor)
            try:
                time_sent = time.time()
                tx_hash = w3.eth.send_transaction({
                    'from': sender,
                    'to': sender,
                    'value': 0
                })
                
                tx_records[tx_hash] = {
                    'time_sent': time_sent,
                    'mined': False
                }
                tx_count += 1
                print(f"Tx #{tx_count} enviada. Esperando confirmación...")
            except Exception as e:
                print(f"Error enviando transacción: {e}")
            
            time.sleep(TX_INTERVAL)
    except KeyboardInterrupt:
        print("Generador detenido manualmente.")
    except Exception as e:
        print(f"Error en generador: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    start_generating()
