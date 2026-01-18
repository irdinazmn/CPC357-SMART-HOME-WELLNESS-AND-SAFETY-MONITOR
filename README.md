# 🏠 Smart Home Wellness & Safety Monitoring System

## 📋 Project Overview
An IoT-based home monitoring system that tracks environmental conditions (air quality, motion, light, leaks) and provides real-time insights through a secure cloud dashboard. The system demonstrates end-to-end IoT architecture from sensor simulation to cloud processing and visualization.

## 🚀 Quick Start

### Prerequisites
- Google Cloud Platform (GCP) account
- Firebase project
- Python 3.8+
- MQTT broker (Mosquitto)

### System Architecture
Wokwi Simulation → MQTT → GCP VM (Mosquitto) → Python Bridge → Firebase → Streamlit Dashboard

## 🛠️ Setup & Installation

### 1. GCP VM Setup
```bash
# Create VM instance
gcloud compute instances create iot-monitor \
  --machine-type=e2-micro \
  --zone=asia-southeast1-a \
  --tags=mqtt,streamlit

# SSH into VM
gcloud compute ssh iot-monitor
```
### 2. Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Mosquitto MQTT broker
sudo apt install mosquitto mosquitto-clients -y

# Install Python
sudo apt install python3 python3-pip python3-venv -y
```

### 3. Project Setup
```bash
# Clone/Create project directory
mkdir ~/iot-bridge && cd ~/iot-bridge

# Create virtual environment
python3 -m venv dashboard-env
source dashboard-env/bin/activate

# Install Python packages
pip install paho-mqtt firebase-admin streamlit plotly pandas numpy \
            streamlit-option-menu pyjwt python-dotenv
```

### 4. Configure Services
MQTT Broker Configuration
```bash
# Create MQTT user
sudo mosquitto_passwd -c /etc/mosquitto/passwd sensor_node
# Password: sensorpwd

# Configure Mosquitto
sudo nano /etc/mosquitto/mosquitto.conf
```

Add to config:
```
conf
listener 1883 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
```

## Firebase Setup
1. Download firebase-key.json from Firebase Console:
- Go to Project Settings → Service accounts
- Click "Generate new private key"
2. Place in project directory: ~/iot-bridge/firebase-key.json

## 🚀 Running the System
Step-by-Step Execution
### 1. Start MQTT Services
```bash
# Restart MQTT broker
sudo systemctl restart mosquitto

# Verify status
sudo systemctl status mosquitto
# Should show: active (running)
``` 
### 2. Start MQTT-Firebase Bridge
```bash
# Restart bridge service
sudo systemctl restart mqtt-firebase

# Verify status
sudo systemctl status mqtt-firebase
# Should show: active (running)
```

### 3. Start Dashboard
```bash
# Navigate to project folder
cd ~/iot-bridge

# Activate Python environment
source dashboard-env/bin/activate

# Launch dashboard (replace IP with your VM's external IP)
streamlit run streamlit_app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --browser.serverAddress YOUR_VM_EXTERNAL_IP

# Example with IP:
# streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --browser.serverAddress 35.247.154.240
```

### 4. Start Wokwi Simulation
1. Open browser to: https://wokwi.com/projects/new/esp32
Upload project files:
- diagram.json
- arduino.cpp
- secrets.h
2. Click "Start Simulation"
3. Monitor Serial output for connection status

## Alternative: Using System Services
```bash
# Stop dashboard if running via systemd
sudo systemctl stop streamlit-dashboard

# Start all services
sudo systemctl restart mosquitto
sudo systemctl restart mqtt-firebase
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```
