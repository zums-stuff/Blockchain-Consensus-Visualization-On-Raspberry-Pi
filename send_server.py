import json
import paramiko
import os
import time
from scp import SCPClient

def read_network_structure(network_structure_file):
    with open(network_structure_file, 'r') as f:
        network_structure = json.load(f)
    
    hostnames_list = network_structure.get("hostnames", [])
    hostname_connection_dict = network_structure.get("connections_dict", {})
    universal_password = network_structure.get("universal_password", "")
    universal_username = network_structure.get("universal_username", "")
    
    return hostnames_list, hostname_connection_dict, universal_password, universal_username


def copy_file_to_raspberry_pis(hostnames, password, local_file_path, remote_file_path):
    for hostname in hostnames:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Conectar a la Raspberry Pi
            ssh_client.connect(hostname, username="raspberry-node", password=password, timeout=5)
            
            # Usar SCP para copiar el archivo
            with SCPClient(ssh_client.get_transport()) as scp:
                scp.put(local_file_path, remote_file_path)
                
            print(f"Archivo '{os.path.basename(local_file_path)}' copiado a {hostname} exitosamente.")
            
        except Exception as e:
            print(f"Error copiando a {hostname}: {e}")
        
        finally:
            ssh_client.close()

if __name__ == "__main__":
    script_dir = os.path.dirname(__file__)
    
    # 1. Leer configuración de la red
    network_structure_file = os.path.join(script_dir, 'network_struc.json')
    
    if not os.path.exists(network_structure_file):
        print(f"Error: No se encontró el archivo {network_structure_file}")
        exit(1)

    hostnames_list, _, universal_password, universal_username = read_network_structure(network_structure_file)

    print(f"--- Iniciando despliegue a: {hostnames_list} ---")

    # 2. LISTA DE ARCHIVOS A ENVIAR
    files_to_send = [
        #"repuesto_de_server.py",
        #"network_struc.json",
        #"ip_address.json",
        #"block_json.py",
        #"mining_json.py",
        #"all_chain.py",
        "start_visualization.py" 
        #"app.py",
        #"get_ip_adresses.py",
        #"reset_nodo.sh",
        #"testchain_final.json"
        
    ]

    # 3. Bucle para enviar cada archivo
    for filename in files_to_send:
        local_path = os.path.join(script_dir, filename)
        
        # Verificamos que el archivo exista en TU pc antes de intentar enviarlo
        if os.path.exists(local_path):
            print(f"\nProcesando: {filename}...")
            
            remote_filename = filename

            if filename == "repuesto_de_server.py":
                remote_filename = "server.py"
                print(f"   -> Se renombrará a '{remote_filename}' en el destino.")

            copy_file_to_raspberry_pis(
                hostnames=hostnames_list, 
                password=universal_password, 
                local_file_path=local_path, 
                remote_file_path=remote_filename
            )
        else:
            print(f"ADVERTENCIA: No se encontró '{filename}' en la carpeta actual. Se omitirá.")

    print("\n--- ¡Despliegue finalizado! ---")