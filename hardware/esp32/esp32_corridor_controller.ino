/*
  =============================================================================
  4 TRAFFIC SIGNALS - ESP32 with Dashboard MQTT Sync
  =============================================================================
  Features:
    - 4 Traffic Signals (R1..G4) with 10s GREEN, 3s YELLOW non-blocking cycle.
    - MQTT & Serial JSON state reporting to sync with Web Dashboard in real time.
    - Priority Corridor override support via MQTT commands.
  =============================================================================
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// --- WiFi Credentials ---
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// --- MQTT Broker Configuration ---
const char* MQTT_BROKER   = "192.168.1.100";  // Central Server / Dashboard Broker IP
const int   MQTT_PORT     = 1883;
const char* MQTT_USER     = "";
const char* MQTT_PASS     = "";

const char* JUNCTION_ID   = "J01";
const char* TOPIC_COMMAND = "junction/J01/command";
const char* TOPIC_STATUS  = "junction/J01/status";
const char* TOPIC_LOCATION = "ambulance/AMB_01/location";

// --- GPIO Pin Definitions for 4 Signals ---
// SIGNAL 1
#define R1 13
#define Y1 12
#define G1 14

// SIGNAL 2
#define R2 27
#define Y2 26
#define G2 25

// SIGNAL 3
#define R3 33
#define Y3 32
#define G3 23

// SIGNAL 4
#define R4 19
#define Y4 18
#define G4 5

// --- Global State Variables ---
WiFiClient espClient;
PubSubClient mqttClient(espClient);

enum SignalMode { MODE_NORMAL, MODE_PRIORITY };
SignalMode currentMode = MODE_NORMAL;

int activeSignal = 1;        // Active signal (1, 2, 3, or 4)
String activeColor = "GREEN"; // "GREEN", "YELLOW"

unsigned long lastPhaseChange = 0;
const unsigned long GREEN_DURATION  = 10000; // 10s GREEN
const unsigned long YELLOW_DURATION = 3000;  // 3s YELLOW

enum PhaseState { STATE_GREEN, STATE_YELLOW };
PhaseState currentPhaseState = STATE_GREEN;

unsigned long priorityStartTime = 0;
unsigned long priorityDurationMs = 20000; // default 20s

// Function Declarations
void setupWiFi();
void reconnectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void setHardwareSignals(int activeSig, String color);
void allRed();
void publishStatus();
void handleNormalTrafficCycle();

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[ESP32] 4 Traffic Signals Controller Initializing...");

  // Configure Pins
  pinMode(R1, OUTPUT); pinMode(Y1, OUTPUT); pinMode(G1, OUTPUT);
  pinMode(R2, OUTPUT); pinMode(Y2, OUTPUT); pinMode(G2, OUTPUT);
  pinMode(R3, OUTPUT); pinMode(Y3, OUTPUT); pinMode(G3, OUTPUT);
  pinMode(R4, OUTPUT); pinMode(Y4, OUTPUT); pinMode(G4, OUTPUT);

  allRed();

  setupWiFi();
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  // Initial State: Signal 1 GREEN
  activeSignal = 1;
  activeColor = "GREEN";
  currentPhaseState = STATE_GREEN;
  setHardwareSignals(activeSignal, activeColor);
  lastPhaseChange = millis();
  publishStatus();
}

void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  unsigned long currentMillis = millis();

  if (currentMode == MODE_PRIORITY) {
    if (currentMillis - priorityStartTime >= priorityDurationMs) {
      Serial.println("[ESP32] Priority duration elapsed. Returning to NORMAL cycle.");
      currentMode = MODE_NORMAL;
      activeSignal = 1;
      activeColor = "GREEN";
      currentPhaseState = STATE_GREEN;
      lastPhaseChange = currentMillis;
      setHardwareSignals(activeSignal, activeColor);
      publishStatus();
    }
  } else {
    handleNormalTrafficCycle();
  }
}

void setupWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n[WiFi] Connection timeout. Operating in standalone hardware mode.");
  }
}

void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;

  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Connecting...");
    String clientId = "ESP32_Junction_" + String(JUNCTION_ID);
    if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
      Serial.println(" Connected!");
      mqttClient.subscribe(TOPIC_COMMAND);
      mqttClient.subscribe(TOPIC_LOCATION);
      publishStatus();
    } else {
      Serial.print(" Failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Retrying in 3 seconds...");
      delay(3000);
      break;
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.printf("[MQTT RX] Topic: %s | Message: %s\n", topic, message.c_str());

  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);
  if (error) return;

  const char* command = doc["command"];
  if (command && strcmp(command, "PRIORITY") == 0) {
    int durationSec = doc["duration"] | 20;
    int targetSignal = doc["signal"] | 1;
    priorityDurationMs = durationSec * 1000UL;
    priorityStartTime = millis();
    currentMode = MODE_PRIORITY;

    activeSignal = targetSignal;
    activeColor = "GREEN";
    setHardwareSignals(activeSignal, activeColor);
    publishStatus();
  } else if (command && strcmp(command, "NORMAL") == 0) {
    currentMode = MODE_NORMAL;
    activeSignal = 1;
    activeColor = "GREEN";
    currentPhaseState = STATE_GREEN;
    lastPhaseChange = millis();
    setHardwareSignals(activeSignal, activeColor);
    publishStatus();
  }
}

void allRed() {
  digitalWrite(R1, HIGH); digitalWrite(Y1, LOW); digitalWrite(G1, LOW);
  digitalWrite(R2, HIGH); digitalWrite(Y2, LOW); digitalWrite(G2, LOW);
  digitalWrite(R3, HIGH); digitalWrite(Y3, LOW); digitalWrite(G3, LOW);
  digitalWrite(R4, HIGH); digitalWrite(Y4, LOW); digitalWrite(G4, LOW);
}

void setHardwareSignals(int activeSig, String color) {
  allRed();

  if (activeSig == 1) {
    if (color == "GREEN")  { digitalWrite(R1, LOW); digitalWrite(G1, HIGH); }
    if (color == "YELLOW") { digitalWrite(R1, LOW); digitalWrite(Y1, HIGH); }
  } else if (activeSig == 2) {
    if (color == "GREEN")  { digitalWrite(R2, LOW); digitalWrite(G2, HIGH); }
    if (color == "YELLOW") { digitalWrite(R2, LOW); digitalWrite(Y2, HIGH); }
  } else if (activeSig == 3) {
    if (color == "GREEN")  { digitalWrite(R3, LOW); digitalWrite(G3, HIGH); }
    if (color == "YELLOW") { digitalWrite(R3, LOW); digitalWrite(Y3, HIGH); }
  } else if (activeSig == 4) {
    if (color == "GREEN")  { digitalWrite(R4, LOW); digitalWrite(G4, HIGH); }
    if (color == "YELLOW") { digitalWrite(R4, LOW); digitalWrite(Y4, HIGH); }
  }
}

void publishStatus() {
  StaticJsonDocument<256> doc;
  doc["junction_id"] = JUNCTION_ID;
  doc["mode"] = (currentMode == MODE_PRIORITY) ? "PRIORITY" : "NORMAL";
  doc["active_signal"] = activeSignal;
  doc["phase"] = activeColor;
  doc["s1"] = (activeSignal == 1) ? activeColor : "RED";
  doc["s2"] = (activeSignal == 2) ? activeColor : "RED";
  doc["s3"] = (activeSignal == 3) ? activeColor : "RED";
  doc["s4"] = (activeSignal == 4) ? activeColor : "RED";
  doc["timestamp"] = millis();

  char buffer[256];
  serializeJson(doc, buffer);
  Serial.printf("[STATUS] %s\n", buffer);

  if (mqttClient.connected()) {
    mqttClient.publish(TOPIC_STATUS, buffer);
  }
}

void handleNormalTrafficCycle() {
  unsigned long now = millis();

  if (currentPhaseState == STATE_GREEN) {
    if (now - lastPhaseChange >= GREEN_DURATION) {
      currentPhaseState = STATE_YELLOW;
      activeColor = "YELLOW";
      setHardwareSignals(activeSignal, activeColor);
      lastPhaseChange = now;
      publishStatus();
    }
  } else if (currentPhaseState == STATE_YELLOW) {
    if (now - lastPhaseChange >= YELLOW_DURATION) {
      activeSignal = (activeSignal % 4) + 1; // Cycle 1 -> 2 -> 3 -> 4 -> 1
      currentPhaseState = STATE_GREEN;
      activeColor = "GREEN";
      setHardwareSignals(activeSignal, activeColor);
      lastPhaseChange = now;
      publishStatus();
    }
  }
}
