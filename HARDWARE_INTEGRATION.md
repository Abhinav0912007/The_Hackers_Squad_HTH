# Hardware Integration Guide — AI + IoT Dynamic Ambulance Corridor

This document explains the physical hardware architecture, wiring schematics, network setup, and step-by-step firmware flashing procedure to connect ESP32 microcontrollers, traffic lights, and GPS modules to the AI system.

---

## 1. System Communication & Hardware Topology

```
                  ┌─────────────────────────────────────────┐
                  │          CENTRAL COMPUTER / AI          │
                  │   FastAPI + YOLO + Dynamic Route Engine │
                  │           IP: 192.168.1.100             │
                  └────────────────────┬────────────────────┘
                                       │
                              [ Local Wi-Fi Router ]
                                       │0
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
         ┌─────────────────────────┐       ┌─────────────────────────┐
         │     ESP32 Node (J01)    │       │     ESP32 Node (J02)    │
         │   Central Crossing      │       │   Main Highway          │
         │   Subscribes:           │       │   Subscribes:           │
         │   junction/J01/command  │       │   junction/J02/command  │
         └────────────┬────────────┘       └────────────┬────────────┘
                      ▼                                 ▼
         ┌─────────────────────────┐       ┌─────────────────────────┐
         │   6 Traffic Light LEDs  │       │   6 Traffic Light LEDs  │
         │ (NS: R/Y/G, EW: R/Y/G)  │       │ (NS: R/Y/G, EW: R/Y/G)  │
         └─────────────────────────┘       └─────────────────────────┘
```

---

## 2. Hardware Bill of Materials (Per Junction)

| Component | Model / Spec | Quantity | Purpose |
|---|---|---|---|
| **Microcontroller** | ESP32 DevKit V1 (30-pin or 38-pin) | 1 per Junction | Wi-Fi client, MQTT subscriber & GPIO driver |
| **Traffic Light Module** | 3-Color LED Module (5V/3.3V) or 6x Discrete LEDs | 2 modules (or 6 LEDs) | 1 set for Corridor (NS), 1 set for Cross (EW) |
| **Current Resistors** | $220\ \Omega$ (if using discrete LEDs) | 6 | Protect LEDs from over-current |
| **Breadboard / PCB** | Standard 400/830-point breadboard | 1 | Circuit assembly |
| **Jumper Wires** | Male-to-Female / Male-to-Male | 10-12 | Connecting ESP32 pins to LEDs |
| **Power Supply** | Micro-USB Cable (5V 1A) or 5V Power Adapter | 1 | Powering the ESP32 |

---

## 3. Circuit Wiring Schematic & Pin Mapping

### Complete ESP32 Pin Connections:

```
                          ESP32 DevKit V1
                     ┌───────────────────────┐
                     │ 3V3               GND ├───► (Common Ground Rail)
                     │ EN                D23 ├───► 🔴 Corridor RED LED
                     │ VP                D22 ├───► 🟡 Corridor YELLOW LED
                     │ VN                D21 ├───► 🟢 Corridor GREEN LED (Priority)
                     │ D34               D19 ├───► 🔴 Cross RED LED (Priority)
                     │ D35               D18 ├───► 🟡 Cross YELLOW LED
                     │ D32                D5 ├───► 🟢 Cross GREEN LED
                     │ ...               ... │
                     └───────────────────────┘
```

### Detailed Wiring Table:

| Signal Direction | Color | ESP32 GPIO Pin | Normal Mode Behavior | Priority Mode (Ambulance Approaching) |
|---|---|---|---|---|
| **Corridor (North-South)** | 🔴 **RED** | **GPIO 23** | ON when Cross is Green | **OFF** |
| **Corridor (North-South)** | 🟡 **YELLOW** | **GPIO 22** | Transition (1s) | **OFF** |
| **Corridor (North-South)** | 🟢 **GREEN** | **GPIO 21** | Standard cycle (4s) | **FORCED ON (GREEN WAVE)** |
| **Cross Traffic (East-West)** | 🔴 **RED** | **GPIO 19** | Standard cycle (4s) | **FORCED ON (STOP CROSS TRAFFIC)** |
| **Cross Traffic (East-West)** | 🟡 **YELLOW** | **GPIO 18** | Transition (1s) | **OFF** |
| **Cross Traffic (East-West)** | 🟢 **GREEN** | **GPIO 5** | ON when Corridor is Red | **OFF** |
| **Ground** | **GND** | **GND Pin** | Connects to LED cathode (-) / GND pins |

---

## 4. Step-by-Step Hardware Setup & Flashing

### Step 1: Install MQTT Broker on Your Computer
The central AI sends priority commands via MQTT.
1. Download & install **Eclipse Mosquitto** from [mosquitto.org](https://mosquitto.org/download/).
2. Start the broker (runs on port `1883`).
3. Find your PC's IP address on the local Wi-Fi:
   - Open PowerShell: `ipconfig`
   - Note the **IPv4 Address** (e.g. `192.168.1.100`).

---

### Step 2: Configure `.env` in the Project
Update [.env](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/.env) on your computer:
```env
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
```

---

### Step 3: Flash the Firmware to the ESP32

The firmware is located in:
👉 [hardware/esp32/esp32_corridor_controller.ino](file:///c:/Users/Dell/OneDrive/Desktop/Ambulance_IOT/hardware/esp32/esp32_corridor_controller.ino)

1. Open **Arduino IDE**.
2. Install the following libraries (*Sketch $\rightarrow$ Include Library $\rightarrow$ Manage Libraries*):
   - **`PubSubClient`** (by Nick O'Leary)
   - **`ArduinoJson`** (by Benoit Blanchon)
3. Open `hardware/esp32/esp32_corridor_controller.ino`.
4. Modify lines 31–37 with your Wi-Fi name, password, and PC IP:
   ```cpp
   // --- WiFi Credentials ---
   const char* WIFI_SSID     = "YOUR_WIFI_SSID";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

   // --- Central PC / MQTT Broker IP ---
   const char* MQTT_BROKER   = "192.168.1.100";  // Put your PC IP here
   const int   MQTT_PORT     = 1883;

   // --- Junction ID ---
   const char* JUNCTION_ID   = "J01";            // Use J02, J03 for other nodes
   ```
5. Connect your ESP32 via USB cable, select **Tools $\rightarrow$ Board $\rightarrow$ ESP32 Dev Module**, select the COM port, and click **Upload**.

---

## 5. Testing & Hardware Verification Checklist

1. **Power On ESP32**:
   - Open Arduino IDE Serial Monitor at `115200` baud.
   - Verify output:
     ```text
     [ESP32] Dynamic Ambulance Corridor Controller Initializing...
     [WiFi] Connected! IP: 192.168.1.45
     [MQTT] Attempting connection... Connected!
     ```
   - Verify LEDs start cycling in **NORMAL mode** (Corridor Green $\rightarrow$ Yellow $\rightarrow$ Red $\rightarrow$ Cross Green).

2. **Start the Central Web System**:
   ```bash
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Trigger Green Corridor Priority**:
   - Open the web dashboard: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - Click **"Simulate Fall + 10s Non-Recovery"** or **"Step Next Junction"**.
   - **Physical Result**:
     - The ESP32 receives `{"command": "PRIORITY", "duration": 20}`.
     - **Corridor Green LED (GPIO 21)** turns **ON**.
     - **Cross Red LED (GPIO 19)** turns **ON**.
   - When the ambulance moves past the junction or reaches the hospital, the ESP32 receives `{"command": "NORMAL"}` and instantly restores the standard light cycle.

---

## 6. Real Ambulance GPS Tracker Integration (Optional)

If adding physical GPS hardware inside the ambulance vehicle:
- **Module**: NEO-6M / NEO-8M GPS.
- **Connections**:
  - `VCC -> 3.3V` / `5V`
  - `GND -> GND`
  - `TX -> ESP32 GPIO 16 (RX2)`
  - `RX -> ESP32 GPIO 17 (TX2)`
- The ambulance ESP32 reads GPS NMEA sentences using `TinyGPS++` and publishes to MQTT topic `ambulance/AMB_01/location`:
  ```json
  {
    "ambulance_id": "AMB_01",
    "latitude": 21.1465,
    "longitude": 79.0910,
    "speed": 55.0
  }
  ```
The central system consumes this feed, calculates the upcoming junction in real-time, and shifts the green wave forward automatically.
