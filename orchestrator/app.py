import json, paramiko,os, time,subprocess, threading,re, webbrowser
from scp import SCPClient


def read_network_structure(network_structure_file):
    with open(network_structure_file, 'r') as f:
        network_structure = json.load(f)
    
    hostnames_list = network_structure.get("hostnames", [])
    hostname_connection_dict = network_structure.get("connections_dict", {})
    universal_password = network_structure.get("universal_password", "")
    universal_username = network_structure.get("universal_username", "")
    
    return hostnames_list, hostname_connection_dict, universal_password, universal_username

def get_ip_from_hostname(hostname,ip_address_file):
    ip_address_file = os.path.join(script_dir, ip_address_file)

    with open(ip_address_file, 'r') as f:
        ip_addresses_dict = json.load(f)
    ip_address=ip_addresses_dict[hostname]
    return ip_address

def connect_to_pi(hostname, username, password, ip_address_file):
    # Append '.local' to the hostname
    #hostname_with_local = f"{hostname}.local"
    hostname_with_local = hostname
    ip_address=get_ip_from_hostname(hostname_with_local,ip_address_file)
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #print(hostname_with_local,username,password)
    time.sleep(2)
    ssh_client.connect(ip_address, username=username, password=password)
    return ssh_client

def execute_commands_on_pi(ssh_client, commands):
    results = []
    for command in commands:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        result = stdout.read().decode('utf-8').strip()
        results.append(result)
    return results

def get_ip_dict(hostnames_list, username, password):
    ip_dict = {}
    try:
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configs')
        with open(os.path.join(config_dir, 'ip_address.json'), 'r') as f:
            saved_ips = json.load(f)

        for hostname in hostnames_list:
            ip_dict[hostname] = saved_ips.get(hostname, 'N/A')
    except Exception as e:
        print(f"Error reading IPs: {e}")
        for hostname in hostnames_list:
            ip_dict[hostname] = 'N/A'
    return ip_dict


#Funciones Legacy
def set_static_ip_for_pi(hostnames_list, username, password):
    for hostname in hostnames_list:
        last_digit = hostname.lstrip("mypi")  # Get the last part of the hostname
        if int(last_digit) < 10:
            static_ip = f'192.168.1.10{last_digit}'  # Create a static IP
        else:
            static_ip = f'192.168.1.1{last_digit}'  # Create a static IP

        #print("STATIC IP: ", static_ip)
        commands = [
            f'sudo sed -i "s/^static ip_address=.*$/static ip_address={static_ip}\/24/" /etc/dhcpcd.conf',
            'sudo dhclient -r',  # Release the current IP
            'sudo dhclient'  # Renew the IP with the new static IP
        ]
        ssh_client = connect_to_pi(hostname, username, password,"ip_address.json")
        execute_commands_on_pi(ssh_client, commands)
        ssh_client.close()
        print("Static IP set for", hostname)
    #print("Static IP change completed.")





def update_ip_addresses_in_html(html_file, ip_dict):
    # Read the HTML content
    with open(html_file, 'r') as f:
        html_content = f.read()

    # Find the line with "const ipAdresses = {"
    start_idx = html_content.find("const ipAdresses = {")
    if start_idx == -1:
        raise ValueError('The line "const ipAdresses = {" was not found in the HTML content.')

    # Extract the part of the HTML file after "const ipAdresses = {"
    ipAdresses_start = html_content[start_idx:]
    
    # Find the closing curly brace '}' of the "const ipAdresses" dictionary
    end_idx = ipAdresses_start.find("}")
    if end_idx == -1:
        raise ValueError('The closing curly brace "}" for "const ipAdresses" was not found.')

    # Split the HTML content into two parts: before "const ipAdresses" and after the dictionary
    before_ipAdresses = html_content[:start_idx]
    after_ipAdresses = ipAdresses_start[end_idx + 1:]

    # Generate the updated JavaScript code for the IP addresses
    updated_ip_addresses = "\n".join([f'    {hostname}: \'{ip}\',' for hostname, ip in ip_dict.items()])
    updated_ip_addresses = f'const ipAdresses = {{\n{updated_ip_addresses}\n}};'

    # Combine the parts to create the updated HTML content
    updated_html_content = f'{before_ipAdresses}{updated_ip_addresses}{after_ipAdresses}'

    # Write the updated HTML content back to the file
    with open(html_file, 'w') as f:
        f.write(updated_html_content)


def copy_file_to_raspberry_pis(hostnames, password, local_file_path, remote_file_path):
    ip_dict = {}
    try:
        with open(os.path.join(os.path.dirname(__file__), 'ip_address.json'), 'r') as f:
            ip_dict = json.load(f)
    except:
        pass
    try:
        for hostname in hostnames:
            target_ip = ip_dict.get(hostname, hostname)
            #Create an SSH client
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            #Connect to the Raspberry Pi using SSH
            ssh_client.connect(target_ip, username="raspberry-node", password=password)
            time.sleep(1)

            #Use SCP to copy the file to the Pis
            with SCPClient(ssh_client.get_transport()) as scp:
                scp.put(local_file_path, remote_file_path)
                
            # Close the SSH session
            ssh_client.close()

            print(f"File copied to {hostname} ({target_ip}) successfully.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    script_dir = os.path.dirname(__file__)
    # Task 1: Read network_struc.json to get Network Structure and username, pi password, list of pis in network
    base_project_dir = os.path.dirname(script_dir)
    network_structure_file = os.path.join(base_project_dir, 'configs', 'network_struc.json')
    ip_address_file = os.path.join(base_project_dir, 'configs', 'ip_address.json')

    hostnames_list, _, universal_password, universal_username = read_network_structure(network_structure_file)
    #print("Results: ", hostnames_list, universal_password, universal_username)
    # Task 2: Set static IP addresses
    #set_static_ip_for_pi(hostnames_list, universal_username, universal_password)

    #Revertir esto en caso de que no funcione
    # Task 4: Get IP Adresses, save them into ip_aderss.json
    # current_directory = os.path.dirname(os.path.abspath(__file__))
    # script_relative_path = "get_ip_adresses.py"
    # script_path = os.path.join(current_directory, script_relative_path)
    # subprocess.run(["python", script_path])


    # Task 3: Get IP addresses
    ip_dict = get_ip_dict(hostnames_list, universal_username, universal_password)
    #print("IP dict: ", ip_dict)


    # Task 5: Update index_new.html
    index_html_file = os.path.join(script_dir, 'webui', 'index_new.html')

    update_ip_addresses_in_html(index_html_file,ip_dict)
    #update_ip_addresses_in_html(index_html_file,ip_dict)

# Task 6: Execute Copying Function
    copy_file_to_raspberry_pis(hostnames=hostnames_list, password=universal_password, local_file_path=network_structure_file , remote_file_path="network_struc.json" )
    time.sleep(3)
    copy_file_to_raspberry_pis(hostnames=hostnames_list, password=universal_password, local_file_path=ip_address_file , remote_file_path="ip_address.json" )

    # Task 7: Start HTTP server and open index_new.html in browser
    import http.server
    import socketserver
    import threading
    
    PORT = 8000
    Handler = http.server.SimpleHTTPRequestHandler
    
    def start_server():
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving at http://localhost:{PORT}")
            httpd.serve_forever()
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(2)
    
    # Open browser
    webbrowser.open(f'http://localhost:{PORT}/index_new.html')
    
    # Keep the script running
    print("Server is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
