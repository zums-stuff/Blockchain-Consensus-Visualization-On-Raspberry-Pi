import json, os, paramiko,re,time

def connect_to_pi(hostname, username, password):
    hostname_with_local = hostname
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname_with_local, username=username, password=password)
    return ssh_client

def execute_commands_on_pi(ssh_client, commands):
    results = []
    for command in commands:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        result = stdout.read().decode('utf-8').strip()
        results.append(result)
    return results

def get_ip_addresses(network_structure_file, username, password):
    script_dir = os.path.dirname(__file__)
    base_project_dir = os.path.dirname(script_dir)
    network_structure_file = os.path.join(base_project_dir, 'configs', 'network_struc.json')
    ip_adress_file = os.path.join(base_project_dir, 'configs', 'ip_address.json')
    try:
        # Read network structure from the JSON file
        with open(network_structure_file, 'r') as f:
            network_structure = json.load(f)
        # Extract hostnames
        hostnames = network_structure.get("hostnames", [])
        # Dictionary to store IP addresses
        ip_addresses = {}
        # SSH into each Raspberry Pi and get IP address
        commands = ['hostname -I']
        for hostname in hostnames:
            #hostname_with_local = f"{hostname}.local"
            hostname_with_local =hostname    
            try:
                # Connect to Raspberry Pi
                ssh_client = connect_to_pi(hostname, username, password)
                time.sleep(1)
                results = execute_commands_on_pi(ssh_client, commands)
                try:
                    results2=results[0].split(" ")
                except:
                    results2=results

                for ip_item in results2:
                    first_three_numbers_ip=int(ip_item[0:3])
                    if first_three_numbers_ip==192:
                        ip_address=ip_item
                        break
                    else:
                        ip_address = results[0] if results else 'N/A'
            
                # Extract the first IP address from the string using regular expressions
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', ip_address)
                first_ip = match.group(0)

                ip_addresses[hostname] = first_ip

            except Exception as e:
                print(f"Error connecting to {hostname_with_local}: {str(e)}")

            finally:
                ssh_client.close()

        # Save IP addresses to ip_address.json
        with open(ip_adress_file, 'w') as outfile:
            json.dump(ip_addresses, outfile)

        print("IP addresses saved to ip_address.json")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    network_structure_file = "network_struc.json"
    username = "raspberry-node"
    password = "mypi1"

    get_ip_addresses(network_structure_file, username, password)
