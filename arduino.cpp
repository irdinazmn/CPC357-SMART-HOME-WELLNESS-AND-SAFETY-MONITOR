#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "secrets.h"

// SSL/TLS Root Certificate
const char* ca_cert = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDdzCCAl+gAwIBAgIEAgAAuTANBgkqhkiG9w0BAQsFADBaMQswCQYDVQQGEwJJ
RTESMBAGA1UECAgMQ0NvIiwgQ291bnR5MRAwDgYDVQQKDAdQcml2YXRlMQswCQYD
VQQLDAJDQTEYMBYGA1UEAwwPUm9vdCBBdXRob3JpdHkwHhcNMjEwMzIzMDcxODIw
WhcNMjQwNzAxMDcxODIwWjBaMQswCQYDVQQGEwJJRTESMBAGA1UECAgMQ0NvIiwg
Q291bnR5MRAwDgYDVQQKDAdQcml2YXRlMQswCQYDVQQLDAJDQTEYMBYGA1UEAwwP
Um9vdCBBdXRob3JpdHkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDC
vjN8agPwIJG6OBcf4x5GXrEt4oLlqx0+HWe4Z0XMrGvWGFJGmNFxOpJd4fqDgX5Q
wExHBmQjK8SIeEL1CTKL4YvIZGSGP9QjU3kGiKxd9JnLr5Xl3i3G6QKcjH3gAy0H
cWPqXaLKm2iGBPi3tLo8hVkWPq8nRWZJf1oMSyWHIJjgKsP6bRJHLLJPFiLCPLqS
rI8pPjuZKmVvDYzJJvJJ7eZJPXEjAx/Yp1U/rN1vZCKZwZEQNQW8fHyVd4pJUBwm
jLUhG7e9gCXWP9cJXUL8V0MKbCKCU0oAkkN1Zc4bLEJBZGRQQY+KHzZHGKLvI7Lm
zXfqnJQAEkVBAgMBAAGjMDAuMAwGA1UdEwQFMAMBAf8wHgYDVR0RBBcwFYITbW9z
cXVpdHRvLnB1YmxpYy5mcjANBgkqhkiG9w0BAQsFAAOCAQEAqIZeN/qJ8fWJGHMo
3bQ0lBRyE+1U2W3F3sPfZjCN8N3w+E0QXMUg/EcHDL1B5rMDVVGZmCr6YJCPzqp0
s5j+Hc7a7VqL1jIWPB+8UpqAIl2nqQYkGVNdMfZvGQGD0tLuVLRVGOI3e9wB7YTi
JCf3J5oDxVfZI0k2Q8Z3g8nQDXGSdSvZQ+j6LcQVNLGZvZfL1P8S7JaQXhGxCu2p
vVq0P2V2jK7KXqO4rDCLVaRdZJhfJJEqYFJvNqJhVUVQT1Q2Y0VNsZlNLxqEsJLR
qhLDhzNhvZcQwKPlNmvGPdJvs1TiPHHIQQRzEoLQjJqqLUAqMqGpbCzMDqxkH0Ue
Fw==
-----END CERTIFICATE-----
)EOF";

// Pin Definitions (same as before)
#define MQ2_PIN 3          // MQ2 analog output
#define RAIN_BUTTON_PIN 5  // Pushbutton for rain simulation
#define LDR_PIN 7        // ADC1_CH6

// Digital I/O
#define PIR_PIN 9        // Input
#define BUZZER_PIN 11    // Output
#define STATUS_LED 15    // Built-in LED on most S2 Mini boards

// Global Variables
WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);

unsigned long lastSensorRead = 0;
unsigned long lastPublish = 0;
unsigned long lastHeartbeat = 0;
unsigned long lastMotionTime = 0;
bool motionAlertSent = false;
bool mqttConnected = false;

// Sensor Values Structure
struct SensorData {
  int airQuality;
  bool isRaining;
  bool motionDetected;
  int lightLevel;
  float temperature;
  float humidity;
  float batteryLevel;  // Simulated for demo
} sensorData;

// System Status
struct SystemStatus {
  bool wifiConnected;
  bool mqttConnected;
  int uptimeMinutes;
  int publishCount;
  int errorCount;
} systemStatus;

// Function Prototypes
void setupWiFi();
void connectMQTT();
void simulateSensors();
void readSensors();
void publishSensorData();
void publishAlert(String alertType, String message, String severity);
void publishHeartbeat();
void triggerLocalAlert(String alertType);
void checkAlerts();
void checkMotionTimeout(unsigned long currentTime);
void mqttCallback(char* topic, byte* payload, unsigned int length);
void reconnectMQTT();

void setup() {
  Serial.begin(115200);
  
  // Initialize pins
  pinMode(STATUS_LED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  pinMode(RAIN_BUTTON_PIN, INPUT_PULLUP);  // Button with pull-up
  
  // Startup sequence
  for (int i = 0; i < 3; i++) {
    digitalWrite(STATUS_LED, HIGH);
    delay(200);
    digitalWrite(STATUS_LED, LOW);
    delay(200);
  }
  
  Serial.println("\n========================================");
  Serial.println("   Smart Home Wellness Monitor (VM)");
  Serial.println("   GCP Compute Engine + MQTT Broker");
  Serial.println("========================================");
  
  // Initialize system status
  systemStatus.wifiConnected = false;
  systemStatus.mqttConnected = false;
  systemStatus.uptimeMinutes = 0;
  systemStatus.publishCount = 0;
  systemStatus.errorCount = 0;
  
  setupWiFi();
  
  // Configure MQTT client with SSL/TLS
  espClient.setCACert(ca_cert);  // Set root certificate for SSL verification
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  
  Serial.println("\nSetup complete. Starting monitoring...");
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Handle MQTT connection
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
  
  // Update uptime
  systemStatus.uptimeMinutes = currentMillis / 60000;
  
  // Read sensors periodically
  if (currentMillis - lastSensorRead >= SENSOR_READ_INTERVAL) {
    simulateSensors();  // Wokwi simulation
    checkAlerts();
    lastSensorRead = currentMillis;
  }
  
  // Publish sensor data periodically
  if (currentMillis - lastPublish >= MQTT_PUBLISH_INTERVAL) {
    if (mqttClient.connected()) {
      publishSensorData();
      lastPublish = currentMillis;
      systemStatus.publishCount++;
      digitalWrite(STATUS_LED, HIGH);
      delay(50);
      digitalWrite(STATUS_LED, LOW);
    }
  }
  
  // Publish heartbeat
  if (currentMillis - lastHeartbeat >= HEARTBEAT_INTERVAL) {
    if (mqttClient.connected()) {
      publishHeartbeat();
      lastHeartbeat = currentMillis;
    }
  }
  
  // Check for motion timeout
  checkMotionTimeout(currentMillis);
  
  // Small delay to prevent watchdog issues in Wokwi
  delay(10);
}

void setupWiFi() {
  Serial.print("\n📶 Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    digitalWrite(STATUS_LED, !digitalRead(STATUS_LED));
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    systemStatus.wifiConnected = true;
    Serial.println("\n✅ WiFi Connected!");
    Serial.print("   IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("   Signal Strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    systemStatus.wifiConnected = false;
    Serial.println("\n❌ WiFi Connection Failed!");
    systemStatus.errorCount++;
  }
}

void connectMQTT() {
  Serial.print("\n🔗 Connecting to MQTT Broker (SSL/TLS): ");
  Serial.print(MQTT_SERVER);
  Serial.print(":");
  Serial.println(MQTT_PORT);
  
  // For testing: skip certificate verification if needed
  // Uncomment the next line if you get certificate verification errors
  espClient.setInsecure();
  
  String clientId = "esp32_monitor_01_" + String(random(10000, 99999));
  
  if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
    systemStatus.mqttConnected = true;
    Serial.println("✅ MQTT Connected (SSL/TLS)!");
    
    // Subscribe to control topics
    mqttClient.subscribe(TOPIC_CONTROL);
    mqttClient.subscribe(TOPIC_STATUS);
    
    Serial.println("   Subscribed to topics:");
    Serial.print("     ");
    Serial.println(TOPIC_CONTROL);
    Serial.print("     ");
    Serial.println(TOPIC_STATUS);
    
    // Publish connection announcement
    publishAlert("SYSTEM", "Device connected to MQTT broker (SSL)", "INFO");
    
  } else {
    systemStatus.mqttConnected = false;
    Serial.print("❌ MQTT Connection Failed, rc=");
    Serial.println(mqttClient.state());
    systemStatus.errorCount++;
    Serial.println("   Note: If certificate error, try uncommenting espClient.setInsecure();");
  }
}

void reconnectMQTT() {
  static unsigned long lastReconnectAttempt = 0;
  unsigned long currentMillis = millis();
  
  // Try to reconnect every 10 seconds
  if (currentMillis - lastReconnectAttempt >= 10000) {
    lastReconnectAttempt = currentMillis;
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("🔄 Attempting MQTT reconnection...");
      connectMQTT();
    } else {
      Serial.println("⚠️  WiFi not connected, reconnecting WiFi first...");
      setupWiFi();
    }
  }
}

// In simulateSensors() function - REPLACE with:
void simulateSensors() {
  // 1. Air Quality from MQ2 (actual reading in Wokwi)
  sensorData.airQuality = analogRead(MQ2_PIN);  // 0-4095 on ESP32
  
  // MQ2 in Wokwi gives values ~0-1000 normally
  // Scale to PPM for realism
  int mq2_raw = sensorData.airQuality;
  sensorData.airQuality = map(mq2_raw, 0, 1000, 50, 500);
  
  // 2. Rain/Leak detection from button
  sensorData.isRaining = (digitalRead(RAIN_BUTTON_PIN) == LOW);
  
  // 3. Motion from PIR
  sensorData.motionDetected = (digitalRead(PIR_PIN) == HIGH);
  if (sensorData.motionDetected) {
    lastMotionTime = millis();
    motionAlertSent = false;
  }
  
  // 4. Light from LDR
  sensorData.lightLevel = analogRead(LDR_PIN);
  
  // 5. Temperature & Humidity (simulated)
  sensorData.temperature = 25.0 + 3.0 * sin(millis() / 600000.0);
  sensorData.humidity = 60.0 + 10.0 * sin(millis() / 900000.0);
  
  // 6. Battery simulation
  sensorData.batteryLevel = 85.0 + 10.0 * sin(millis() / 1800000.0);
  
  // Debug output
  if (DEBUG_MODE) {
    Serial.println("\n=== Sensor Readings ===");
    Serial.printf("MQ2 Raw: %d, Air Quality: %d PPM\n", mq2_raw, sensorData.airQuality);
    Serial.printf("Rain/Leak: %s (Button: %s)\n", 
                  sensorData.isRaining ? "YES" : "NO",
                  digitalRead(RAIN_BUTTON_PIN) == LOW ? "PRESSED" : "NOT PRESSED");
    Serial.printf("Motion: %s\n", sensorData.motionDetected ? "DETECTED" : "NONE");
    Serial.printf("Light Level: %d\n", sensorData.lightLevel);
    Serial.printf("Temperature: %.1f°C\n", sensorData.temperature);
    Serial.printf("Humidity: %.1f%%\n", sensorData.humidity);
    Serial.printf("Battery: %.1f%%\n", sensorData.batteryLevel);
  }
}

void checkAlerts() {
  // Air Quality Alert
  if (sensorData.airQuality > AIR_QUALITY_ALERT_THRESHOLD) {
    String msg = "Air quality critical: " + String(sensorData.airQuality) + " PPM";
    publishAlert("AIR_QUALITY", msg, "HIGH");
    triggerLocalAlert("AIR_QUALITY");
  }
  
  // Water Leak Alert
  if (sensorData.isRaining) {
    publishAlert("WATER_LEAK", "Water leak detected!", "HIGH");
    triggerLocalAlert("WATER_LEAK");
  }
  
  // Temperature Alerts
  if (sensorData.temperature > TEMP_HIGH_THRESHOLD) {
    String msg = "High temperature: " + String(sensorData.temperature) + "°C";
    publishAlert("TEMPERATURE", msg, "MEDIUM");
  } else if (sensorData.temperature < TEMP_LOW_THRESHOLD) {
    String msg = "Low temperature: " + String(sensorData.temperature) + "°C";
    publishAlert("TEMPERATURE", msg, "MEDIUM");
  }
  
  // Humidity Alerts
  if (sensorData.humidity > HUMIDITY_HIGH_THRESHOLD) {
    String msg = "High humidity: " + String(sensorData.humidity) + "%";
    publishAlert("HUMIDITY", msg, "LOW");
  } else if (sensorData.humidity < HUMIDITY_LOW_THRESHOLD) {
    String msg = "Low humidity: " + String(sensorData.humidity) + "%";
    publishAlert("HUMIDITY", msg, "LOW");
  }
  
  // Darkness Alert
  if (sensorData.lightLevel < LIGHT_DARK_THRESHOLD) {
    publishAlert("LIGHT", "Room is dark", "INFO");
  }
}

void checkMotionTimeout(unsigned long currentTime) {
  if (!motionAlertSent && 
      (currentTime - lastMotionTime > MOTION_TIMEOUT) && 
      lastMotionTime != 0) {
    
    String msg = "No motion detected for " + String(MOTION_TIMEOUT/60000) + " minutes";
    publishAlert("MOTION_TIMEOUT", msg, "MEDIUM");
    motionAlertSent = true;
  }
}

void publishSensorData() {
  if (!mqttClient.connected()) return;
  
  StaticJsonDocument<512> jsonDoc;
  
  // Device info
  jsonDoc["device_id"] = DEVICE_ID;
  jsonDoc["device_type"] = DEVICE_TYPE;
  jsonDoc["location"] = DEVICE_LOCATION;
  jsonDoc["timestamp"] = millis();
  jsonDoc["uptime_seconds"] = millis() / 1000;
  
  // Sensor readings
  JsonObject sensors = jsonDoc.createNestedObject("sensors");
  sensors["air_quality_ppm"] = sensorData.airQuality;
  sensors["water_leak"] = sensorData.isRaining;
  sensors["motion"] = sensorData.motionDetected;
  sensors["light_level"] = sensorData.lightLevel;
  sensors["temperature_c"] = sensorData.temperature;
  sensors["humidity_percent"] = sensorData.humidity;
  sensors["battery_percent"] = sensorData.batteryLevel;
  
  // System status
  JsonObject status = jsonDoc.createNestedObject("system");
  status["wifi_connected"] = systemStatus.wifiConnected;
  status["mqtt_connected"] = systemStatus.mqttConnected;
  status["rssi"] = WiFi.RSSI();
  status["publish_count"] = systemStatus.publishCount;
  status["error_count"] = systemStatus.errorCount;
  
  String payload;
  serializeJson(jsonDoc, payload);
  
  if (mqttClient.publish(TOPIC_SENSOR_DATA, payload.c_str())) {
    if (DEBUG_MODE) {
      Serial.println("\n📤 Published Sensor Data:");
      Serial.println(payload);
    }
  } else {
    Serial.println("❌ Failed to publish sensor data");
    systemStatus.errorCount++;
  }
}

void publishAlert(String alertType, String message, String severity) {
  if (!mqttClient.connected()) return;
  
  StaticJsonDocument<256> alertDoc;
  alertDoc["device_id"] = DEVICE_ID;
  alertDoc["timestamp"] = millis();
  alertDoc["alert_type"] = alertType;
  alertDoc["severity"] = severity;
  alertDoc["message"] = message;
  
  // Add relevant sensor data to alert
  if (alertType == "AIR_QUALITY") {
    alertDoc["value"] = sensorData.airQuality;
    alertDoc["threshold"] = AIR_QUALITY_ALERT_THRESHOLD;
  } else if (alertType == "WATER_LEAK") {
    alertDoc["value"] = sensorData.isRaining;
  } else if (alertType == "TEMPERATURE") {
    alertDoc["value"] = sensorData.temperature;
  }
  
  String payload;
  serializeJson(alertDoc, payload);
  
  if (mqttClient.publish(TOPIC_ALERTS, payload.c_str())) {
    Serial.printf("\n🚨 Alert Published: %s - %s\n", alertType.c_str(), message.c_str());
  }
}

void publishHeartbeat() {
  if (!mqttClient.connected()) return;
  
  StaticJsonDocument<256> heartbeat;
  heartbeat["device_id"] = DEVICE_ID;
  heartbeat["timestamp"] = millis();
  heartbeat["uptime_minutes"] = systemStatus.uptimeMinutes;
  heartbeat["free_heap"] = ESP.getFreeHeap();
  heartbeat["wifi_rssi"] = WiFi.RSSI();
  heartbeat["publish_count"] = systemStatus.publishCount;
  
  String payload;
  serializeJson(heartbeat, payload);
  
  mqttClient.publish("home/heartbeat", payload.c_str());
  
  if (DEBUG_MODE) {
    Serial.println("\n❤️  Heartbeat published");
  }
}

void triggerLocalAlert(String alertType) {
  // Visual and audible alert
  for (int i = 0; i < 3; i++) {
    digitalWrite(STATUS_LED, HIGH);
    if (alertType == "AIR_QUALITY" || alertType == "WATER_LEAK") {
      digitalWrite(BUZZER_PIN, HIGH);  // Buzzer only for critical alerts
    }
    delay(200);
    digitalWrite(STATUS_LED, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    delay(200);
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.printf("\n📨 MQTT Message [%s]: ", topic);
  
  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);
  
  // Parse JSON
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.print("JSON Parse Error: ");
    Serial.println(error.c_str());
    return;
  }
  
  String topicStr = String(topic);
  
  // Handle control messages
  if (topicStr == TOPIC_CONTROL) {
    if (doc.containsKey("command")) {
      String command = doc["command"].as<String>();
      
      Serial.print("Received command: ");
      Serial.println(command);
      
      if (command == "buzzer_test") {
        Serial.println("Testing buzzer...");
        triggerLocalAlert("TEST");
        
        // Send response
        publishAlert("SYSTEM", "Buzzer test completed", "INFO");
        
      } else if (command == "get_status") {
        Serial.println("Sending status...");
        publishSensorData();
        
      } else if (command == "reboot") {
        Serial.println("Rebooting device...");
        publishAlert("SYSTEM", "Device rebooting", "INFO");
        delay(1000);
        ESP.restart();
        
      } else if (command == "led_on") {
        digitalWrite(STATUS_LED, HIGH);
        publishAlert("SYSTEM", "LED turned ON", "INFO");
        
      } else if (command == "led_off") {
        digitalWrite(STATUS_LED, LOW);
        publishAlert("SYSTEM", "LED turned OFF", "INFO");
        
      } else if (command == "set_interval") {
        if (doc.containsKey("interval_ms")) {
          // int newInterval = doc["interval_ms"];
          // MQTT_PUBLISH_INTERVAL = newInterval;
          Serial.println("Publish interval updated");
        }
      }
    }
  }
}