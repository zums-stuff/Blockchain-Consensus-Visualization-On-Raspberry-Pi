from flask import Flask, request, jsonify
from flask_cors import CORS
from web3 import Web3
import paramiko,os, subprocess, json, socket,random,time,re,signal
import http.server
import os
import shutil
import socket
import concurrent.futures
import math

app = Flask(__name__)
CORS(app)

def write_to_file(name, value, filename):
    with open(filename, 'a') as file:
        file.write(f"{name}: {value}\n")


def write_to_json(name, value, filename):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    data[name] = value
    with open(filename, 'w') as file:
        json.dump(data, file, indent=2)

#HELPER FUNCTIONS P1
#1) Get Hostname of Raspberry PI
def get_hostname():
    try:
        # Get the hostname of the current Raspberry Pi
        hostname = socket.gethostname()
        return hostname
    except Exception as e:
        print(f"Error getting hostname: {str(e)}")
        return None
#2) Function to get Username
def get_username():
    return os.getlogin()

#GLOBAL VALUES
base_enode_url_path="/home/raspberry-node/enode_url.txt"
base_ip_path="/home/raspberry-node/ip_adress.txt"
base_ip_filename="ip_adress.txt"
base_chainid=5000
base_ipc_path = "/home/raspberry-node/.testchain44/geth.ipc"
base_genesis_block_configuration_file_path = "/home/raspberry-node/Documents/testchain_final.json"
base_pi_home_path="/home/raspberry-node/"

base_pi_password="mypi1"
base_password_file_path = "/tmp/account_password.txt"
base_hostname=get_hostname()
base_account_name="testchain44"

base_pi_username=get_username()

base_port = 4242
base_networkid = 42

w3 = Web3(Web3.IPCProvider(base_ipc_path))


#HELPER FUNCTIONS P2

def get_ip_from_hostname(hostname):
    script_dir = os.path.dirname(__file__)
    ip_address_file = os.path.join(script_dir, 'ip_address.json')

    with open(ip_address_file, 'r') as f:
        ip_addresses_dict = json.load(f)
    ip_address=ip_addresses_dict[hostname]
    return ip_address

#1) Run Command Function
def run_command(command):
    process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process.stdout.strip(), process.stderr.strip()

#1) Function to Copy Files between Raspberry PIs
def scp_copy_from_raspberry_pi(hostname, username, password, remote_file_path, local_file_path):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ip_address=get_ip_from_hostname(hostname)
        ssh_client.connect(ip_address, username=username, password=password)
        scp = ssh_client.open_sftp()
        scp.get(remote_file_path, local_file_path)
        scp.close()
        ssh_client.close()
        print(f"File '{remote_file_path}' copied to '{local_file_path}' successfully.")
    except Exception as e:
        print(f"Failed to copy file: {str(e)}")

#2) Function to Create temp Password for Creating Blockchain Directory
def create_temp_password_file(account_password):
    with open(base_password_file_path, 'w') as f:
        f.write(account_password)
    return base_password_file_path



#4) Function to get the Directory where the Ethereum Network data is stored by Geth (Geth Etehreum client)
def get_datadir(account_name):
    return f"/home/{get_username()}/.{account_name}"

#5) Function to Create JSON Response
def create_response(status, message):
    return jsonify({'status': status, 'message': message})

#6) Function to Read or Write:
def read_write(read_or_write,file_name_with_ending,write_value):
    if read_or_write=="write":
        with open(base_pi_home_path+file_name_with_ending, 'w') as file:
            file.write(write_value)
        return
    elif read_or_write=="read":
        with open(base_pi_home_path+file_name_with_ending, 'r') as file:
            read_value=file.read().strip()
        return read_value

#7) Save IP Adress to File
def save_ip_adress_to_file(filename):
    try:
        ip_address = subprocess.check_output(['hostname', '-I']).decode('utf-8')
        # Extract the first IP address from the string using regular expressions
        match = re.search(r'(\d+\.\d+\.\d+\.\d+)', ip_address)
        first_ip = match.group(0)
        read_write("write",filename,first_ip)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False




#9 Function to save chain_id to file
def save_chain_ids_to_file(chain_id_info):
    # Save the hostname: chain_id pairs to a JSON file
    with open("current_chain_ids.json", 'w') as json_file:
        json.dump(chain_id_info, json_file, indent=4)

#10) Function to get largest chain_id
def get_largest_chain_id():
    try:
        with open("current_chain_ids.json", 'r') as json_file:
            data = json.load(json_file)

        # Extract chain_ids from the loaded data
        chain_ids = [int(chain_id) for chain_id in data.values() if isinstance(chain_id, int)]

        if chain_ids:
            # Return the largest chain_id
            return str(max(chain_ids))
        else:
            print("No valid chain_ids found in the file.")
            return None

    except Exception as e:
        print(f"Failed to get the largest chain_id: {str(e)}")
        return None

#11) Function to save chain_ids in file and return largest one
def get_right_chain_id():
    res = read_network_config("network_struc.json")
    network_type, connections_dict, hostnames = res["network_type"], res["connections_dict"], res["hostnames"]

    chain_id_info = {}  # To store hostname: chain_id pairs

    try:
        for hostname in hostnames:
            connection_info = connections_dict.get(hostname, {})
            pi_username = base_pi_username
            pi_password = base_pi_password

            try:
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                #full_hostname = hostname + '.local'
                full_hostname = hostname
                ip_address=get_ip_from_hostname(full_hostname)

                ssh_client.connect(ip_address, username=pi_username, password=pi_password)

                # Read chain_id from the Raspberry Pi
                chain_id = read_chain_id(ssh_client, base_genesis_block_configuration_file_path)

                if chain_id is not None:
                    chain_id_info[full_hostname] = chain_id

            finally:
                ssh_client.close()

    except Exception as e:
        print(f"Error getting chain_id from Pis: {str(e)}")
        return None, {}

    # Save the hostname: chain_id pairs to a JSON file
    save_chain_ids_to_file(chain_id_info)

    # Determine the maximum chain_id
    max_chain_id = max(chain_id_info.values(), default=None)

    if max_chain_id is not None:
        # Calculate the new chain_id as maximum value + 1
        new_chain_id = max_chain_id + 1
        print(f"The new chain_id will be: {new_chain_id}")
    else:
        print("Failed to retrieve the maximum chain_id.")
        new_chain_id = None

    return new_chain_id, chain_id_info


#12) Increase ChainId by one (unique identifier of Ethereum Network)
def update_chain_id_on_pis(pi_hostnames, pi_username, pi_password, file_path):
    chain_id_info = {}

    try:
        for hostname in pi_hostnames:
            try:
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                #full_hostname = hostname + '.local'
                full_hostname = hostname
                ip_address=get_ip_from_hostname(full_hostname)
                ssh_client.connect(ip_address, username=pi_username, password=pi_password)

                # Read chain_id from the Raspberry Pi
                chain_id = read_chain_id(ssh_client, file_path)

                if chain_id is not None:
                    chain_id_info[full_hostname] = chain_id

            finally:
                ssh_client.close()

    except Exception as e:
        print(f"Error getting chain_id from Pis: {str(e)}")
        return False

    # Determine the maximum chain_id
    max_chain_id = max(chain_id_info.values(), default=None)


    if max_chain_id is not None:
        # Calculate the new chain_id as maximum value + 1
        new_chain_id = max_chain_id + 1
        print(f"The new chain_id will be: {new_chain_id}")
        hostname=get_hostname()

        # Write the new chain_id to all Pis
        try:
            for hostname in pi_hostnames:
                try:
                    ssh_client = paramiko.SSHClient()
                    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    #full_hostname = hostname + '.local'
                    full_hostname = hostname
                    print(f"Connecting to {full_hostname} with {pi_username}/{pi_password}")
                    ip_adress=get_ip_from_hostname(full_hostname)
                    ssh_client.connect(ip_adress, username=pi_username, password=pi_password)
                    # Update chain_id on the Raspberry Pi
                    update_chain_id(ssh_client, file_path, new_chain_id)

                finally:
                    ssh_client.close()

            print("Successfully updated chain_id on all Pis.")
            return True

        except Exception as e:
            print(f"Error updating chain_id on Pis: {str(e)}")
            return False

    else:
        print("Failed to retrieve the maximum chain_id.")
        return False
#13) Function to read chain_id
def read_chain_id(ssh_client, file_path):
    try:
        # Read chain_id from the file on the Raspberry Pi
        _, stdout, _ = ssh_client.exec_command(f"cat {file_path}")
        data = json.loads(stdout.read().decode())
        return data.get('config', {}).get('chainId')
    except Exception as e:
        print(f"Error reading chain_id from file: {str(e)}")
        return None

def update_chain_id(ssh_client, file_path, new_chain_id):
    try:
        # Read existing data
        _, stdout, _ = ssh_client.exec_command(f"cat {file_path}")
        data = json.loads(stdout.read().decode())

        # Update chain_id in the data
        data['config']['chainId'] = new_chain_id

        # Write the updated data back to the file on the Raspberry Pi
        _, stdout, _ = ssh_client.exec_command(f"echo '{json.dumps(data, indent=4)}' > {file_path}")
        #print(f"Updated chain_id on {file_path} to {new_chain_id}")

    except Exception as e:
        print(f"Error updating chain_id in file: {str(e)}")


#9) Create Random ETH Account Identifier to send miner rewards to (each node should get a unique)
def generate_random_ethereum_addresses(num_addresses):
    addresses = set()  # Use a set to ensure uniqueness

    while len(addresses) < num_addresses:
        # Generate a random 20-byte (160-bit) Ethereum address
        address = "0x" + "".join(random.choice("0123456789abcdef") for _ in range(40))
        addresses.add(address)
    return list(addresses)

#10) Initialize Web3 instance
def initialize_web3(ipc_path):
    global w3
    w3 = Web3(Web3.IPCProvider(ipc_path))
    return w3

#11) Read Network Configuration
def read_network_config(filename):
    with open(filename, 'r') as json_file:
        data = json.load(json_file)
    number_of_blocks_per_run,network_type,hostnames,connections_dict=data["number_of_blocks_per_run"],data["network_type"],data["hostnames"],data["connections_dict"]
    return {"network_type":network_type,"connections_dict":connections_dict,"hostnames":hostnames,"number_of_blocks_per_run":number_of_blocks_per_run}


#12) Open file on Pi
def open_file_on_pi(hostname, password, file_path):
    # Create an SSH client instance
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        #Connect to the Raspberry Pi using SSH
        ip_address=get_ip_from_hostname(hostname)
        ssh_client.connect(ip_address, username='raspberry-node', password=password)
        #Open the file
        stdin, stdout, stderr = ssh_client.exec_command(f'cat {file_path}')
        #Read the contents of the file
        file_contents = stdout.read().decode('utf-8')
        return file_contents

    except paramiko.AuthenticationException:
        print("Authentication failed. Please check the password.")
    except paramiko.SSHException as e:
        print(f"SSH error: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        ssh_client.close()

#13) Read Enode Url from Pi
def read_enode_url_from_pi(hostname, password, enode_url_file_path):
        enode_url=open_file_on_pi(hostname,password,enode_url_file_path)
        return enode_url

#14) Get IP corrected Enode Url
def get_ip_corrected_enode_url(enode_url,ip_adress):
    start=enode_url.find('@')
    end=enode_url.find('?')
    updated_enode_url = enode_url.replace(enode_url[start+1:end+1], ip_adress+":4242?")
    return updated_enode_url

#15) Get IP of hostname
def get_ip_of_hostname(hostname,password,ip_adress_file_path):
        ip_adress_of_hostname=open_file_on_pi(hostname,password,ip_adress_file_path)
        return ip_adress_of_hostname

#16) Get Correct Enode Urls given hostnames
def get_correct_enode_urls(origin_hostnames):
    try:
        enode_url_dict_wrong_ip={}
        enode_url_dict_correct_ip={}
        #1) Get Enode Urls of hostnames, get ip adresses of hostnames, correct enode urls with right ip adresses
        for hostname in origin_hostnames:
            #hostname_long = hostname+(".local")
            hostname_long = hostname
            enode_url_dict_wrong_ip[hostname]=read_enode_url_from_pi(hostname_long,base_pi_password,base_enode_url_path)
            ip_adress=get_ip_from_hostname(hostname_long)
            corrected_enode_url=get_ip_corrected_enode_url(enode_url_dict_wrong_ip[hostname],ip_adress)
            enode_url_dict_correct_ip[hostname]=corrected_enode_url
        #2) Add Peers
        return enode_url_dict_correct_ip
    except Exception as e:
        return str(e), 500

#17) Get Enode Urls for a given hostname
def get_enode_urls_for_hostname(hostnames,connections_dict,correct_enode_url_dict):
    list_enode=[]
    line_network_correct_enode_list_for_hostname_dict={}
    for hostname in hostnames:
        for add_hostname in connections_dict[hostname]:
            list_enode.append(correct_enode_url_dict[add_hostname])
        line_network_correct_enode_list_for_hostname_dict[hostname]=list_enode
        list_enode=[]
    return line_network_correct_enode_list_for_hostname_dict

#17) Write hostname_port dict json file
def write_hostname_port_dict(hostname_port_dict):
    try:
        with open("hostname_port_dict.json", 'w') as json_file:
            json.dump(hostname_port_dict, json_file, indent=4)
        print("Successfully wrote to hostname_port_dict.json")
    except Exception as e:
        print(f"Failed to write to hostname_port_dict.json: {str(e)}")

#17) Read ports for hostname from json file
def read_ports_for_hostname(hostname):
    try:
        with open("hostname_port_dict.json", 'r') as json_file:
            data = json.load(json_file)

        ports = data.get(hostname, [])
        if ports:
            return ports
        else:
            return None
    except FileNotFoundError:
        print("hostname_port_dict.json not found.")
        return None
    except Exception as e:
        print(f"Failed to read from hostname_port_dict.json: {str(e)}")
        return None

#18) Add Peer Function
#18) Add Peer Function (VERSIÓN CON REINTENTOS)
def add_peer(my_hostname, connections_dict, hostnames):
    correct_enode_url_dict = get_correct_enode_urls(hostnames)
    line_network_correct_enode_list_for_hostname_dict = get_enode_urls_for_hostname(hostnames, connections_dict, correct_enode_url_dict)
    my_hostname_enode_list = line_network_correct_enode_list_for_hostname_dict[my_hostname]

    if my_hostname_enode_list:
        for enode_url in my_hostname_enode_list:
            # Reintentar hasta 5 veces si falla
            max_retries = 5
            retry_count = 0
            peer_added = False

            while retry_count < max_retries and not peer_added:
                try:
                    # Intentar añadir el peer
                    w3.geth.admin.add_peer(enode_url)
                    time.sleep(3)  # Aumentado a 3 segundos

                    # Verificar si se añadió
                    peers = w3.geth.admin.peers()
                    mypi_port_list = []
                    ip_port_dict = {}
                    mypi_ip = "unknown"

                    if peers:
                        for peer in peers:
                            if 'network' in peer and 'localAddress' in peer['network']:
                                local_addr = peer['network']['localAddress']
                                if ':' in local_addr:
                                    mypi_ip = local_addr.split(':')[0]
                                    mypi_port_list.append(local_addr.split(':')[1])

                            remote_addr = peer.get('network', {}).get('remoteAddress', '')
                            target_ip = enode_url.split('@')[1].split(':')[0]

                            if remote_addr.split(':')[0] == target_ip:
                                peer_added = True

                    if peer_added:
                        print(f"Peer {enode_url.split('@')[1].split(':')[0]} added successfully on attempt {retry_count + 1}")

                        if mypi_ip != "unknown":
                            ip_port_dict[mypi_ip] = mypi_port_list
                            hostname_port_dict = {}
                            hostname_port_dict[get_hostname()] = ip_port_dict[mypi_ip]
                            write_hostname_port_dict(hostname_port_dict)
                        break
                    else:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"Peer not added yet, retrying ({retry_count}/{max_retries})...")
                            time.sleep(5)  # Esperar 5 segundos antes de reintentar

                except Exception as e:
                    print(f"Error adding peer (attempt {retry_count + 1}): {str(e)}")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(5)

            if not peer_added:
                print(f"Failed to add peer {enode_url.split('@')[1].split(':')[0]} after {max_retries} attempts")

    return None



#MAIN FUNCTIONS
#1) Create Directory where Ethereum Network Data is stored
def create_directory():
    try:
        account_name = base_account_name
        datadir = get_datadir(account_name)
        #remove directory if it exists else create it
        os.system(f'rm -rf {datadir}' if os.path.exists(datadir) else '')
        password_file = create_temp_password_file(base_pi_password)
        command = f"geth --datadir {datadir} account new --password {password_file}"
        stdout = run_command(command)
        return create_response("success", f"Directory '{account_name}' created.") if "Your new key was generated" in stdout else create_response("error", "Failed to create the directory.")

    except Exception as e:
        return create_response("error", str(e))

#2) Initialize Blockchain
def init_blockchain():
    datadir=get_datadir(base_account_name)
    init_command = f"geth --datadir {datadir} init "+base_genesis_block_configuration_file_path

    # CAMBIO AQUI: Capturamos y mostramos el resultado
    stdout, stderr = run_command(init_command)
    print("\n--- DEBUG INIT ---")
    print("Comando:", init_command)
    print("Salida:", stdout)
    print("Error:", stderr)
    print("------------------\n")

#3) Get Enode Url and save in File
def get_and_save_enode_url_to_file(enode_url_file_name):
    try:
        time.sleep(1)
        enode_url=w3.geth.admin.node_info()["enode"]
        time.sleep(1)
        read_write("write",enode_url_file_name,enode_url)
        return
    except:
        return

#4) Start Node Function
def start_node():
    eth_account=generate_random_ethereum_addresses(1)[0]
    if eth_account:
        write_to_file("eth_account",eth_account,"configuration_run.txt")
    try:
        datadir = f"/home/raspberry-node/.{base_account_name}"
        command = f"geth --datadir {datadir} --syncmode full --snapshot=false --port {base_port} --networkid {base_networkid} console --nodiscover --miner.etherbase={eth_account} 2>&1 | tee mining_output.log"

        time.sleep(2)
        subprocess.Popen(command, shell=True)
        return jsonify({"status": "success", "message": "Node started successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


#5) Function to start the miner, stop miner after certain block number is reached and save log data and move it to right folder
#(VERSION RPC)
def start_miner(mining_option):
    print("=== START MINER ===")
    res = read_network_config("network_struc.json")
    number_of_blocks_per_run = res["number_of_blocks_per_run"]
    print(f"Target blocks: {number_of_blocks_per_run}")

    try:
        # Iniciar visualización
        process = subprocess.Popen(["python3", "start_visualization.py"])
        print("Visualization started")
        time.sleep(10)

        # Iniciar minero - FIX: USAR RPC DIRECTO
        print(f"Starting miner with {mining_option} threads...")
        try:
            # Método 1: Llamada RPC directa (Funciona en cualquier versión de Web3)
            w3.provider.make_request('miner_start', [mining_option])
            print("Miner started via RPC miner_start")
        except Exception as e:
            print(f"RPC miner_start failed: {e}")
            try:
                # Método 2: Intento legacy
                w3.geth.miner.start(mining_option)
            except:
                print("Could not start miner via python wrapper")

        # Loop hasta alcanzar bloques objetivo
        while True:
            try:
                current_block = w3.eth.block_number
            except:
                current_block = 0

            if current_block % 1 == 0:
                print(f"Mining progress: {current_block}/{number_of_blocks_per_run} blocks")

            if current_block >= number_of_blocks_per_run:
                print(f"Target reached! Block {current_block} >= {number_of_blocks_per_run}")
                break

            time.sleep(5)

        # Detener minero - FIX: USAR RPC DIRECTO
        print("Stopping miner...")
        try:
            w3.provider.make_request('miner_stop', [])
            print("Miner stopped via RPC")
        except:
            try:
                w3.geth.miner.stop()
            except:
                pass

        # Detener visualización
        print("Stopping visualization...")
        process.terminate()
        print("Visualization stopped")

        # Guardar datos
        print("Saving block data...")
        save_block_data()
        print("Data saved")

        print("=== MINER COMPLETED SUCCESSFULLY ===")
        return "Miner executed successfully"

    except Exception as e:
        print(f"ERROR in start_miner: {e}")
        return str(e)













import hashlib

def calculate_checksums(file_paths):
    checksums_dict = {}

    for file_path in file_paths:
        md5 = hashlib.md5()

        try:
            with open(file_path, 'rb') as file:
                # Read the file in chunks to handle large files
                for chunk in iter(lambda: file.read(4096), b''):
                    md5.update(chunk)
        except FileNotFoundError:
            # If a file is not found, set checksums to None for that file
            checksums_dict[file_path] = None
            continue
        except Exception as e:
            # If an exception occurs, set checksums to the error message for that file
            checksums_dict[file_path] = str(e)
            continue

        # Add checksums to the dictionary
        checksums_dict[file_path] = {
            'md5_checksum': md5.hexdigest()
        }

    return checksums_dict

def write_checksums_to_json(checksums_dict, output_file='checksums.json'):
    with open(output_file, 'w') as json_file:
        json.dump(checksums_dict, json_file, indent=2)

#7 Function to save log data into folder
def organize_files(chain_id):
    # Get the hostname of the machine
    pi_hostname = socket.gethostname()

    # Define the base directory and paths for the files to be copied
    base_directory = "MAP"
    pi_directory = os.path.join(base_directory, pi_hostname)
    chain_directory = os.path.join(pi_directory, str(chain_id))

    # Create the base directory if it doesn't exist
    if not os.path.exists(base_directory):
        os.makedirs(base_directory)

    # Create the pi_hostname directory if it doesn't exist
    if not os.path.exists(pi_directory):
        os.makedirs(pi_directory)

    # Create the chain_id directory if it doesn't exist
    if not os.path.exists(chain_directory):
        os.makedirs(chain_directory)

    # List of files to be copied
    hostname=get_hostname()

    try:
        if chain_id:
            write_to_file("chainid", chain_id, "configuration_run.txt")
    except:
        pass

    file_path_chain_id=base_genesis_block_configuration_file_path
    with open(file_path_chain_id, 'r') as json_file:
            data = json.load(json_file)
            chain_id = data.get('config', {}).get('chainId')


    file_paths = [
    '/home/raspberry-node/MAP/{hostname}}/{chain_id}/all_block_data.json',
    '/home/raspberry-node/MAP/{hostname}}/{chain_id}/block_data.log',
    '/home/raspberry-node/MAP/{hostname}}/{chain_id}/chain_output.json',
    '/home/raspberry-node/MAP/{hostname}}/{chain_id}/mining_output.log',
    '/home/raspberry-node/MAP/{hostname}}/{chain_id}//output_mining.json',
    '/home/raspberry-node/MAP/{hostname}}/{chain_id}//configuration_run.txt',
    # Add other file paths as needed
]

    files_to_copy = ["checksums.json","block_data.log", "mining_output.log", "output.json","chain_output.json", "output_mining.json","all_block_data.json","configuration_run.txt"]

    chesums_dict=calculate_checksums(file_paths)
    write_checksums_to_json(chesums_dict)
    # Copy each file to the chain_id directory
    for file_name in files_to_copy:
        source_path = os.path.join(".", file_name)  # Assuming the files are in the current directory
        destination_path = os.path.join(chain_directory, file_name)
        shutil.copy2(source_path, destination_path)
        #hostname_long = pi_hostname+(".local")
        hostname_long = pi_hostname
        ip_adress=get_ip_from_hostname(hostname_long)


    print(f"Files copied successfully to {ip_adress}\\SharedFolder\\MAP\\{pi_hostname}\\{chain_id}")
    return "Organize File Function worrked perfecly"

#8 Function to generate topology connections
def generate_topology_connections(topo_type, hostnames):
    # 1. Ordenamos la lista para que todos los nodos tengan el mismo mapa mental
    hosts = sorted(hostnames)
    n = len(hosts)
    conns = {h: [] for h in hosts}

    print(f"Generando topología: {topo_type} para {n} nodos")

    if topo_type == "circle":
        for i in range(n):
            conns[hosts[i]].append(hosts[(i + 1) % n])

    elif topo_type == "star":
        center = hosts[0]
        conns[center] = hosts[1:] # El centro ve a todos
        for i in range(1, n):
            conns[hosts[i]].append(center) # Todos ven al centro

    elif topo_type == "grid":
        if n > 0:
            cols = math.ceil(math.sqrt(n))

            for i in range(n):
                # Conexión Derecha: Si no es borde derecho Y existe vecino
                if (i + 1) % cols != 0 and (i + 1) < n:
                    conns[hosts[i]].append(hosts[i+1])     # Ida
                    conns[hosts[i+1]].append(hosts[i])     # Vuelta

                # Conexión Abajo: Si existe vecino abajo
                if (i + cols) < n:
                    conns[hosts[i]].append(hosts[i+cols])  # Ida
                    conns[hosts[i+cols]].append(hosts[i])  # Vuelta

    return conns

###########ENDPOINTS################################################

#1) Endpoint to change difficulty in genesis block config file
@app.route('/change_difficulty', methods=['POST'])
def change_difficulty():
    try:
        new_difficulty = request.args.get('difficulty')
        hostname=get_hostname()
        try:
            if new_difficulty:
                write_to_file("mining difficulty",new_difficulty,"configuration_run.txt")
        except:
            pass

        if new_difficulty is None:
            return "Difficulty parameter is missing", 400
        # Read the existing genesis block configuration
        with open(base_genesis_block_configuration_file_path, 'r') as json_file:
            data = json.load(json_file)
            data['difficulty'] = hex(int(new_difficulty)) #Aseguramos que lea la dificultad en hexadecimal

        # Write the updated configuration back to the genesis block file
        with open(base_genesis_block_configuration_file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)

        return jsonify({"status": "success", "message": "Difficulty parameter updated successfully."})
    except Exception as e:
        return f"Error: {str(e)}", 500


#2)Start Node Endpoint
@app.route('/start_node', methods=['GET'])
def start_node2():
    try:
        #1) Create Directory
        create_directory()
        #2) Save IP Adress into File
        save_ip_adress_to_file(base_ip_filename)

        # --- SOLO MYPI1 DEBE CAMBIAR EL CHAIN ID ---
        if get_hostname() == "mypi1":
            print("Soy mypi1: Actualizando Chain ID para la red...")
            res=read_network_config("network_struc.json")
            network_type, connections_dict, pi_hostnames=res["network_type"], res["connections_dict"],res["hostnames"]
            update_chain_id_on_pis(pi_hostnames, base_pi_username, base_pi_password, base_genesis_block_configuration_file_path)
        else:
            print("No soy mypi1: Esperando configuración de Chain ID...")
            time.sleep(5)
        # ------------------------------------------------

        # IMPORTANTE: NO llamar a change_difficulty() aquí
        # porque ya se configuró desde el HTML antes de start_everything

        #6) Initialize ETH Blockchain
        init_blockchain()
        #7) Initialize Web3
        initialize_web3(base_ipc_path)
        #8)Start Node
        start_node()
        #9) Save Enode Url in File
        get_and_save_enode_url_to_file('enode_url.txt')
        return ""

    except Exception as e:
        print(f"ERROR EN START_NODE: {str(e)}")
        return str(e), 500


#3) Add Peers Endpoint
@app.route('/addpeers', methods=['POST'])
def add_peers_endpoint():
    print("REACHED addpeers endpoint")
    try:
        #1)Read and save network_struct
        res=read_network_config("network_struc.json")
        print(1)
        network_type, connections_dict, hostnames=res["network_type"], res["connections_dict"],res["hostnames"]
        #2)Add Peers
        add_peer(base_hostname,connections_dict, hostnames)
        return jsonify({"status": "success", "message": "Peers added successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



def introduce_delay(delay_ms, port):
    try:
        subprocess.run(['sudo', 'tc', 'qdisc', 'add', 'dev', 'eth0', 'root', 'handle', '1:', 'prio', 'priomap', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'])
        subprocess.run(['sudo', 'tc', 'qdisc', 'add', 'dev', 'eth0', 'parent', '1:2', 'handle', '20:', 'netem', f'delay', f'{delay_ms}ms'])
        subprocess.run(['sudo', 'tc', 'filter', 'add', 'dev', 'eth0', 'parent', '1:0', 'protocol', 'ip', 'u32', 'match', 'ip', 'dport', str(port), '0xffff', 'flowid', '1:2'])
        print(f"Delay of {delay_ms} milliseconds added for port {port}.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return False

#4) Delay Endpoint
@app.route('/delay', methods=['POST'])
def delay():
    delay = request.args.get("delay")
    read_write("write","delay.txt",str(delay))
    try:
        hostname=get_hostname()
        if delay:
            write_to_file("delay in miliseconds", delay, "configuration_run.txt")
    except:
        pass
    return jsonify({"status": "ok", "delay": delay}), 200




def delay2():
    delay=read_write("read","delay.txt","")
    try:
        hostname=get_hostname()
    except:
        pass

    if delay:
        try:
            ports=read_ports_for_hostname(get_hostname())
            for port in ports:
                introduce_delay(delay,port)
                print("Delayed port: ",port,"for: ",delay," milliseconds")
            return "Delayed ports succesfully"
        except Exception as e:
            return str(e), 500
    else:
        return"No ports delayed"


def start_visualization():
    subprocess.run(["python3", "start_visualization.py"], check=True)

#6) Start Mining and Visualization Endpoint
@app.route('/start_mining_visualization', methods=['GET'])
def start_mining_visualization():
    print(">>> Reached start_mining_visualization endpoint")
    mining_option = int(request.args.get("mining_option", 1))
    print(f">>> Mining option: {mining_option}")

    print(">>> Calling start_miner()...")
    result = start_miner(mining_option)
    print(f">>> start_miner() returned: {result}")

    return jsonify({"status": "success", "result": result})


#7) Stop Mining Endpoint
@app.route('/stop_mining', methods=['POST'])
def stop_mining():
    try:
        #stop mniing
        w3.geth.miner.stop()

        return "Succeeded to stop mining", 200

    except Exception as e:
        return str(e), 500


#8) Endpoint to save/convert log data and move them to a folder
@app.route('/save_block_data', methods=['POST'])
def save_block_data():
    try:
        # Execute the commands to save block data
        subprocess.run(['python', 'block_json.py'], check=True)
        subprocess.run(['python', 'mining_json.py'], check=True)
        subprocess.run(['python', 'all_chain.py'], check=True)
        #subprocess.run(['python', 'chain_json.py'], check=True)

        # chain_json.py executed periodically during visualization not called here

        hostname=get_hostname()
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        hostname = hostname
        #hostname = hostname + '.local'
        ip_address=get_ip_from_hostname(hostname)
        ssh_client.connect(ip_address, username=base_pi_username, password=base_pi_password)
        chain_id = read_chain_id(ssh_client, base_genesis_block_configuration_file_path)

        organize_files(chain_id)
        return "ALL DATA saved all succesfully"
    except Exception as e:
        error_message = f"Error running scripts: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500


#9) Endpoint to Stop Server
@app.route('/stop_server', methods=['POST'])
def stop_function():
    func = request.environ.get('werkzeug.server.shutdown')
    func()
    os.kill(os.getpid(), signal.SIGINT)
    return 'Server stopped!'



# Global variable to store the number of test runs
number_of_testruns = 1  # Default value

@app.route('/number_of_testruns', methods=['POST'])
def set_number_of_testruns():
    global number_of_testruns
    try:
        # Get the number from the request
        number_tr=request.args.get('number_of_testruns')
        # Set the global variable
        number_of_testruns = number_tr
        read_write("write","number_of_testruns.txt",number_of_testruns)
        hostname=get_hostname()
        try:
            if number_of_testruns:
                write_to_file("number of testruns", number_of_testruns, "configuration_run.txt")
        except:
            pass

        return number_of_testruns
    except ValueError:
        return 1


def send_sigint_to_geth():
    try:
        # Run the 'pidof geth' command to get the PID, and use it to send SIGINT signal
        subprocess.run(["kill -INT `pidof geth`"], shell=True, check=True)
        print("SIGINT signal sent to Geth successfully.")
        time.sleep(5)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

# Call the function
#10) Combined Add Peers, Start Mining and Start Visualization Endpoint
@app.route('/start_everything', methods=['POST'])
def start_everything():
    try:
        with open('/home/raspberry-node/number_of_testruns.txt', 'r') as f:
            content = f.read().strip()
            number_of_testruns = int(content) if content else 1
    except Exception as e:
        print(f"Warning reading testruns: {e}")
        number_of_testruns = 1

    print("Total Number of Testruns: ", number_of_testruns)

    try:
        for i in range(number_of_testruns):
            print(f"=== TEST RUN {i+1}/{number_of_testruns} ===")

            # IMPORTANTE: Primero leer la dificultad del archivo y aplicarla
            # antes de inicializar el nodo
            print("Reading difficulty configuration...")
            try:
                with open(base_genesis_block_configuration_file_path, 'r') as f:
                    genesis_config = json.load(f)
                    current_difficulty = int(genesis_config.get('difficulty', '0x1'), 16)
                    print(f"Current difficulty from genesis file: {current_difficulty}")
            except Exception as e:
                print(f"Error reading difficulty: {e}")

            # 1) Setup node (esto ya incluye change_difficulty internamente)
            start_node2()

            # ESPERA SINCRONIZADA: Todos los nodos deben esperar el mismo tiempo
            # independientemente de su dificultad
            print("Waiting for ALL nodes to initialize (synchronized wait)...")
            time.sleep(20)  # <- AUMENTADO a 20 segundos para dar tiempo a todos

            hostname = get_hostname()
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ip_address = get_ip_from_hostname(hostname)
            ssh_client.connect(ip_address, username=base_pi_username, password=base_pi_password)

            res = read_network_config("network_struc.json")
            network_type, connections_dict, hostnames = res["network_type"], res["connections_dict"], res["hostnames"]

            # 2) Add Peers (con reintentos mejorados)
            print("Adding peers...")
            add_peer(base_hostname, connections_dict, hostnames)

            # VERIFICAR PEERS REALMENTE CONECTADOS
            print("Verifying peer connections...")
            time.sleep(3)
            peers = w3.geth.admin.peers()
            print(f"Current peers connected: {len(peers)}")
            expected_peers = len(connections_dict.get(hostname, []))
            print(f"Expected peers for {hostname}: {expected_peers}")

            if len(peers) < expected_peers:
                print(f"WARNING: Only {len(peers)}/{expected_peers} peers connected!")
                print("Attempting additional connection attempts...")
                # Segundo intento para peers faltantes
                time.sleep(5)
                add_peer(base_hostname, connections_dict, hostnames)
                peers = w3.geth.admin.peers()
                print(f"After retry: {len(peers)} peers connected")

            print("Peers added")

            # 3) Start Mining
            print("Starting mining and visualization...")
            start_mining_visualization()
            print("Mining completed")

            # 4) Stop geth
            print("Stopping geth...")
            send_sigint_to_geth()
            print("Geth stopped")

            # 5) Wait before next test run
            if i < number_of_testruns - 1:
                print(f"Waiting before next test run...")
                time.sleep(10)

        return jsonify({"status": "success", "message": f"Completed {number_of_testruns} test runs"})

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Endpoint to change network topology
@app.route('/change_topology', methods=['POST'])
def change_topology():
    try:
        new_topology = request.args.get('topology')

        if new_topology is None:
            return jsonify({"status": "error", "message": "Topology parameter is missing"}), 400

        # Valid topologies
        valid_topologies = ['circle', 'grid', 'star']
        if new_topology.lower() not in valid_topologies:
            return jsonify({"status": "error", "message": f"Invalid topology. Must be one of: {valid_topologies}"}), 400

        # Read current network structure
        with open('network_struc.json', 'r') as json_file:
            data = json.load(json_file)

        hostnames = data.get('hostnames', [])

        # Update topology type
        data['network_type'] = new_topology.lower()

        connections_dict = generate_topology_connections(new_topology.lower(), hostnames)

        # Update connections
        data['connections_dict'] = connections_dict

        # Write updated configuration back to file
        with open('network_struc.json', 'w') as json_file:
            json.dump(data, json_file, indent=4)

        try:
            hostname = get_hostname()
            if new_topology:
                write_to_file("network topology", new_topology, "configuration_run.txt")
        except:
            pass

        return jsonify({
            "status": "success",
            "message": f"Network topology changed to {new_topology}",
            "connections": connections_dict
        })

    except Exception as e:
        print(f"ERROR changing topology: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)