# Blockchain Consensus Visualization on Raspberry Pi

This project is a distributed simulation and visualization tool for blockchain consensus mechanisms, designed to run on a network of Raspberry Pi devices. It provides an orchestrator-node architecture where a central application configures the network and multiple Raspberry Pis act as mining nodes.

## Repository and Resources
- **Project Repository:** [Blockchain Consensus Visualization on Raspberry Pi](https://github.com/Franco0932/Blockchain-Consensus-Visualization-On-Raspberry-Pi-Proyecto.git)

---
## Project Structure
- `app.py`: The Main Orchestrator. Connects to all Raspberry Pis, retrieves their IP addresses, syncs the topology configurations, updates the locally hosted Web UI, and serves the control panel.
- `send_server.py`: A deployment utility script. It uses SCP over SSH to quickly deploy updated project files (like `server.py`, `start_visualization.py`, etc.) to all Raspberry Pis.
- `server.py`: The node application. This heavy script runs on each Raspberry Pi, simulating mining processes, blocks validation, and blockchain synchronization.
- `start_visualization.py`: The local UI visualizer for each node. It runs the visual representation of the blockchain and automatically opens the browser in fullscreen upon initialization.
- `network_struc.json`: The network topology configuration. Determines how Pi nodes can talk to each other (e.g., Circle, Grid, Star) and stores authentication credentials.
- `index_new.html`: The HTML user interface for the orchestrator, letting you set difficulty boundaries, throttling, and execute consensus actions.

---

## Setup & Deployment

### 1. Configure the Network Topology
Before deploying, define how your Raspberry Pis are interconnected.
1. Open the code folder in your preferred editor.
2. Edit `network_struc.json`. Map out `"connections_dict"` to dictate which node talks to which (Circle, Grid, or Star topology). Ensure `"hostnames"` includes all your node hostnames (e.g., `mypi1`, `mypi2`).

### 2. Deploy Project Files to Nodes
To avoid manually copying files to each Raspberry Pi, use the deployment script:
```bash
python send_server.py
```
This script will authenticate into each node configured in `network_struc.json` and automatically SCP all necessary operational files like `server.py` and `start_visualization.py` into them.

### 3. Initialize Nodes
On each Raspberry Pi device (you can SSH into them using `ssh raspberry-node@mypiX.local`), you need to run the Node server and the Node visualizer:
1. Run the consensus server simulation:
   ```bash
   python server.py
   ```
2. Run the visualizer (which automatically launches a Chromium fullscreen window):
   ```bash
   python start_visualization.py
   ```

### 4. Start the Central Orchestrator
Back on your main control computer, launch the web application orchestrator:
```bash
python app.py
```
**What happens in the background:**
- Connecting via SSH, `app.py` will retrieve the dynamically assigned IPs from your nodes.
- It injects them into the UI frontend.
- It uploads synchronization settings directly to the Pis.
- It will automatically launch your local web browser navigating to the control dashboard.

---

## Execution & Mining Process
1. On the launched Web Interface, you can control the entire blockchain environment.
2. Adjust system parameters like network delays, block throttling mechanisms, and mining difficulty levels.
3. Click **Start Everything** inside the UI.
4. Watch the Raspberry Pis visualize the block generation, consensus propagation, and eventual chain harmonization across the topology in real-time.
