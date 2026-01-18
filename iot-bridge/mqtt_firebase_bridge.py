# nano mqtt_firebase_bridge.py in GCP VM

# mqtt_firebase_bridge.py
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import logging

# Firebase Configuration
CRED_PATH = "firebase-key.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Firebase
try:
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("✅ Firebase initialized successfully")
except Exception as e:
    logger.error(f"❌ Firebase initialization failed: {e}")
    exit(1)

# MQTT Configuration
MQTT_BROKER = "35.247.154.240"  # GCP Compute Engine
MQTT_PORT = 8883  # SSL/TLS port
MQTT_USER = "sensor_node"
MQTT_PASSWORD = "sensorpwd"
MQTT_TLS = True  # Use SSL/TLS

# Topics to subscribe
TOPICS = [
    "home/sensors/data",
    "home/sensors/alerts",
    "home/heartbeat"
]

# Collections in Firestore
COLLECTIONS = {
    "home/sensors/data": "sensor_readings",
    "home/sensors/alerts": "alerts",
    "home/heartbeat": "device_heartbeats"
}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("✅ Connected to MQTT broker")
        # Subscribe to all topics
        for topic in TOPICS:
            client.subscribe(topic)
            logger.info(f"   Subscribed to: {topic}")
    else:
        logger.error(f"❌ Connection failed with code: {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        logger.info(f"📨 Received message on [{topic}]")
        
        # Add timestamp
        data['received_at'] = datetime.now().isoformat()
        data['topic'] = topic
        
        # Store in appropriate Firestore collection
        collection_name = COLLECTIONS.get(topic, "unknown_messages")
        
        # For sensor data, use device_id + timestamp as document ID
        if topic == "home/sensors/data":
            device_id = data.get('device_id', 'unknown')
            timestamp = data.get('timestamp', str(datetime.now().timestamp()))
            doc_id = f"{device_id}_{timestamp}"
            
            # Store in sensor_readings collection
            db.collection(collection_name).document(doc_id).set(data)
            
            # Also update latest reading for this device
            db.collection('devices_latest').document(device_id).set({
                'last_reading': data,
                'last_updated': data['received_at']
            })
            
            logger.info(f"💾 Saved sensor data from {device_id}")
        
        # For alerts, store with auto-generated ID
        elif topic == "home/sensors/alerts":
            # Add alert status
            data['alert_status'] = 'active'
            data['acknowledged'] = False
            
            doc_ref = db.collection(collection_name).add(data)
            logger.info(f"🚨 Saved alert: {data.get('alert_type', 'unknown')}")
            
        # For heartbeats
        elif topic == "home/heartbeat":
            device_id = data.get('device_id', 'unknown')
            db.collection(collection_name).document(device_id).set(data)
            logger.info(f"❤️  Updated heartbeat for {device_id}")
        
        else:
            # Store unknown messages
            db.collection(collection_name).add(data)
            logger.warning(f"⚠️  Unknown topic, saved to {collection_name}")
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")

def main():
    # Create MQTT client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # Enable TLS if configured
        if MQTT_TLS:
            client.tls_set(ca_certs=None, certfile=None, keyfile=None, 
                          cert_reqs=mqtt.ssl.CERT_REQUIRED, tls_version=mqtt.ssl.PROTOCOL_TLSv1_2)
            client.tls_insecure_set(True)  # For development/testing
        
        # Connect to MQTT broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        logger.info(f"🔗 Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT} (TLS: {MQTT_TLS})")
        
        # Start loop
        client.loop_forever()
        
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
        client.disconnect()
    except Exception as e:
        logger.error(f"❌ MQTT connection error: {e}")

if __name__ == "__main__":
    main()