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
    # Cargar archivo de IPs
    ip_dict = {}
    try:
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configs')
        with open(os.path.join(config_dir, 'ip_address.json'), 'r') as f:
            ip_dict = json.load(f)

    except Exception as e:
        print(f"Advertencia: No se pudo leer ip_address.json ({e})")

    for hostname in hostnames:
        # Usar la IP si existe en el JSON, sino intentar usar el hostname original
        target_ip = ip_dict.get(hostname, hostname)
        
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Conectar a la Raspberry Pi usando la IP
            ssh_client.connect(target_ip, username="raspberry-node", password=password, timeout=5)
            
            # Usar SCP para copiar el archivo
            with SCPClient(ssh_client.get_transport()) as scp:
                scp.put(local_file_path, remote_file_path)
                
            print(f"Archivo '{os.path.basename(local_file_path)}' copiado a {hostname} ({target_ip}) exitosamente.")
            
        except Exception as e:
            print(f"Error copiando a {hostname} ({target_ip}): {e}")
        
        finally:
            ssh_client.close()

if __name__ == "__main__":
    script_dir = os.path.dirname(__file__)
    
    # 1. Leer configuración de la red
    base_project_dir = os.path.dirname(script_dir)
    network_structure_file = os.path.join(base_project_dir, 'configs', 'network_struc.json')

    if not os.path.exists(network_structure_file):
        print(f"Error: No se encontró el archivo {network_structure_file}")
        exit(1)

    hostnames_list, _, universal_password, universal_username = read_network_structure(network_structure_file)
    print(f"--- Iniciando despliegue a: {hostnames_list} ---")

    # Mapeo exacto: (Ruta local en tu laptop, Nombre con el que se guarda en la Raspberry Pi)
    files_to_send = [
        (os.path.join(base_project_dir, "node", "server.py"), "server.py"),
        (os.path.join(base_project_dir, "node", "start_visualization.py"), "start_visualization.py"),
        (os.path.join(base_project_dir, "node", "tx_generator.py"), "tx_generator.py"),
        (os.path.join(base_project_dir, "node", "utils", "plot_emissions.py"), "plot_emissions.py"),
        (os.path.join(base_project_dir, "node", "utils", "analyze_metrics.py"), "analyze_metrics.py"),
        (os.path.join(base_project_dir, "node", "utils", "block_json.py"), "block_json.py"),
        (os.path.join(base_project_dir, "node", "utils", "mining_json.py"), "mining_json.py"),
        (os.path.join(base_project_dir, "node", "utils", "all_chain.py"), "all_chain.py"),
        (os.path.join(base_project_dir, "configs", "testchain_final.json"), "testchain_final.json")
    ]

    for local_path, remote_filename in files_to_send:
        if os.path.exists(local_path):
            print(f"\nProcesando: {remote_filename}...")
            copy_file_to_raspberry_pis(
                hostnames=hostnames_list,
                password=universal_password,
                local_file_path=local_path,
                remote_file_path=remote_filename
            )
        else:
            print(f"ADVERTENCIA: No se encontró '{local_path}'. Se omitirá.")

    print("\n--- ¡Despliegue finalizado! ---")
