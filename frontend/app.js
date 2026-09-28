/**
 * AI + IoT Dynamic Ambulance Corridor Dashboard Controller
 */

// Node layout positions on the 600x420 canvas
const NODE_POSITIONS = {
  "A": { x: 90,  y: 80,  label: "A (Incident)", type: "START" },
  "B": { x: 300, y: 80,  label: "B (J01)",      type: "JUNCTION", juncId: "J01" },
  "C": { x: 510, y: 80,  label: "C (J02)",      type: "JUNCTION", juncId: "J02" },
  "D": { x: 90,  y: 200, label: "D (SouthWest)",type: "JUNCTION" },
  "E": { x: 300, y: 200, label: "E (J04)",      type: "JUNCTION", juncId: "J04" },
  "F": { x: 510, y: 200, label: "F (East)",     type: "JUNCTION" },
  "G": { x: 300, y: 310, label: "G (J03)",      type: "JUNCTION", juncId: "J03" },
  "HOSPITAL": { x: 300, y: 390, label: "HOSPITAL (Apex)", type: "HOSPITAL" }
};

const EDGES = [
  ["A", "B"], ["B", "C"],
  ["A", "D"], ["D", "E"], ["B", "E"],
  ["C", "F"], ["E", "F"],
  ["E", "G"], ["G", "HOSPITAL"]
];

// App State
let currentRoute = ["A", "B", "E", "G", "HOSPITAL"];
let activePriorityJunction = "J01";
let ambulanceNode = "A";
let ambulanceStatus = "IDLE";
let ambulanceSpeed = 0;
let emergencyState = "IDLE";
let fallStatus = "NORMAL";
let fallConfidence = 0.0;
let recoveryElapsed = 0.0;
let recoveryTimeout = 10.0;
let simulationInterval = null;
let animationFrameId = null;

// Video Canvas Simulation State
let videoState = {
  personPosture: "STANDING", // STANDING, FALLEN
  personY: 180,
  isSimulating: false,
  timerRunning: false,
  timerStart: 0
};

// DOM Elements
const videoCanvas = document.getElementById("videoCanvas");
const vCtx = videoCanvas.getContext("2d");
const roadCanvas = document.getElementById("roadNetworkCanvas");
const rCtx = roadCanvas.getContext("2d");

const timerDigits = document.getElementById("timer-digits");
const timerDesc = document.getElementById("timer-desc");
const timerProgressFill = document.getElementById("timer-progress-fill");
const hudFallState = document.getElementById("hud-fall-state");
const hudFallConf = document.getElementById("hud-fall-conf");
const hudPosture = document.getElementById("hud-posture");
const hudAlert = document.getElementById("hud-emergency-alert");

const ambIdEl = document.getElementById("amb-id");
const ambStatusEl = document.getElementById("amb-status");
const ambPosEl = document.getElementById("amb-pos");
const ambUpcomingEl = document.getElementById("amb-upcoming");
const ambSpeedEl = document.getElementById("amb-speed");
const junctionsListEl = document.getElementById("junctions-list");
const eventLogsEl = document.getElementById("event-logs");

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  startClock();
  renderJunctionCards();
  startCanvasRenderLoop();
  fetchLatestState();
  setInterval(fetchLatestState, 1000);
});

function startClock() {
  setInterval(() => {
    const now = new Date();
    document.getElementById("live-clock").textContent = now.toLocaleTimeString();
  }, 1000);
}

function setupEventListeners() {
  document.getElementById("btn-trigger-emergency").addEventListener("click", triggerFullEmergencySimulation);
  document.getElementById("btn-trigger-recovery").addEventListener("click", triggerRecoverySimulation);
  document.getElementById("btn-run-video-inference").addEventListener("click", runVideoInferenceApi);
  document.getElementById("btn-reset-all").addEventListener("click", resetAllState);
  document.getElementById("btn-auto-simulate").addEventListener("click", autoRunCorridorSimulation);
  document.getElementById("btn-step-simulate").addEventListener("click", stepCorridorSimulation);
  document.getElementById("btn-reset-signals").addEventListener("click", resetSignals);
  
  // File Upload Handlers
  const fileInput = document.getElementById("videoFileInput");
  const fileNameDisplay = document.getElementById("selectedFileName");
  const uploadBtn = document.getElementById("btn-upload-analyze");

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      fileNameDisplay.textContent = e.target.files[0].name;
    } else {
      fileNameDisplay.textContent = "No file selected";
    }
  });

  uploadBtn.addEventListener("click", uploadAndAnalyzeVideo);

  document.getElementById("btn-clear-logs").addEventListener("click", () => {
    eventLogsEl.innerHTML = "";
    addLog("System", "Event logs cleared.");
  });
}

async function uploadAndAnalyzeVideo() {
  const fileInput = document.getElementById("videoFileInput");
  if (!fileInput.files || fileInput.files.length === 0) {
    alert("Please select a recorded video file (.mp4, .avi, .mov) first!");
    return;
  }

  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);

  const uploadBtn = document.getElementById("btn-upload-analyze");
  uploadBtn.disabled = true;
  uploadBtn.innerHTML = `<span class="btn-icon">⏳</span> Processing...`;

  addLog("Upload", `Uploading and analyzing recorded video: '${file.name}' (${(file.size / (1024*1024)).toFixed(1)} MB)...`);
  timerDesc.textContent = `Running YOLOv8 inference and 10s recovery analysis on '${file.name}'...`;

  try {
    const res = await fetch("/api/video/upload", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Video upload failed");
    }

    const data = await res.json();
    addLog("AI", `Video Analysis Complete: ${data.total_frames_processed} frames in ${data.processing_time_seconds}s.`);
    addLog("AI", `Fall Confirmed: ${data.fall_confirmed} | Recovery Outcome: ${data.recovery_state}`);

    // Switch visualizer from canvas to output video player
    const player = document.getElementById("uploadedVideoPlayer");
    const canvas = document.getElementById("videoCanvas");
    const hud = document.getElementById("hud-overlay");

    canvas.style.display = "none";
    player.style.display = "block";
    player.src = data.output_video_url;
    player.play();

    if (data.emergency_triggered) {
      hudAlert.style.display = "block";
      addLog("Emergency", "10-Second Non-Recovery condition detected! SUSPECTED SERIOUS MEDICAL EMERGENCY triggered.");
      triggerEmergencyEscalation();
    } else if (data.recovery_state === "FALL_RECOVERED") {
      hudFallState.textContent = "RECOVERED";
      timerDesc.textContent = "Video Analysis: Person recovered before 10 seconds. Status: FALL_RECOVERED.";
    } else {
      timerDesc.textContent = `Video Analysis complete. Final state: ${data.recovery_state}.`;
    }

  } catch (error) {
    addLog("Error", `Failed to process video: ${error.message}`);
    alert(`Error processing video: ${error.message}`);
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.innerHTML = `<span class="btn-icon">⚡</span> Upload & Run AI`;
  }
}

function addLog(type, message) {
  const time = new Date().toLocaleTimeString();
  const entry = document.createElement("div");
  entry.className = `log-entry log-${type.toLowerCase()}`;
  entry.innerHTML = `<span class="log-time">[${time}] [${type}]</span><span class="log-msg">${message}</span>`;
  eventLogsEl.appendChild(entry);
  eventLogsEl.scrollTop = eventLogsEl.scrollHeight;
}

// --- Fetch Backend State ---
async function fetchLatestState() {
  try {
    const [statusRes, juncRes] = await Promise.all([
      fetch("/api/ambulance/status").catch(() => null),
      fetch("/api/junctions").catch(() => null)
    ]);

    if (statusRes && statusRes.ok) {
      const ambData = await statusRes.json();
      ambulanceStatus = ambData.status;
      ambulanceNode = ambData.current_node || "A";
      ambulanceSpeed = ambData.speed || 0;
      updateTelemetryUI();
    }

    if (juncRes && juncRes.ok) {
      const juncs = await juncRes.json();
      updateJunctionsUI(juncs);
    }
  } catch (err) {
    // offline or backend restarting
  }
}

// --- Video Canvas Drawing ---
function drawVideoCanvas() {
  vCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
  
  // Background Room
  vCtx.fillStyle = "#0c111e";
  vCtx.fillRect(0, 0, videoCanvas.width, videoCanvas.height);

  // Grid Lines
  vCtx.strokeStyle = "rgba(255, 255, 255, 0.04)";
  vCtx.lineWidth = 1;
  for (let x = 0; x < videoCanvas.width; x += 40) {
    vCtx.beginPath(); vCtx.moveTo(x, 0); vCtx.lineTo(x, videoCanvas.height); vCtx.stroke();
  }
  for (let y = 0; y < videoCanvas.height; y += 40) {
    vCtx.beginPath(); vCtx.moveTo(0, y); vCtx.lineTo(videoCanvas.width, y); vCtx.stroke();
  }

  // Floor Line
  vCtx.strokeStyle = "rgba(0, 153, 255, 0.3)";
  vCtx.lineWidth = 3;
  vCtx.beginPath();
  vCtx.moveTo(0, 310);
  vCtx.lineTo(videoCanvas.width, 310);
  vCtx.stroke();

  // Person Drawing
  if (videoState.personPosture === "STANDING") {
    // Upright bounding box
    const bx = 270, by = 130, bw = 100, bh = 180;
    vCtx.strokeStyle = "#00e699";
    vCtx.lineWidth = 2;
    vCtx.strokeRect(bx, by, bw, bh);

    // Label
    vCtx.fillStyle = "#00e699";
    vCtx.font = "bold 12px 'JetBrains Mono'";
    vCtx.fillText(`person (0.92) [STANDING]`, bx, by - 8);

    // Silhouette
    vCtx.fillStyle = "rgba(0, 230, 153, 0.25)";
    vCtx.fillRect(bx, by, bw, bh);
    
    // Head & Body
    vCtx.fillStyle = "#ffffff";
    vCtx.beginPath(); vCtx.arc(320, 160, 20, 0, Math.PI * 2); vCtx.fill();
    vCtx.fillRect(305, 185, 30, 80);
    vCtx.fillRect(300, 265, 15, 45);
    vCtx.fillRect(325, 265, 15, 45);
  } else {
    // Fallen posture (horizontal bounding box on floor)
    const bx = 180, by = 250, bw = 280, bh = 60;
    vCtx.strokeStyle = "#ff3366";
    vCtx.lineWidth = 2;
    vCtx.strokeRect(bx, by, bw, bh);

    // Label
    vCtx.fillStyle = "#ff3366";
    vCtx.font = "bold 12px 'JetBrains Mono'";
    vCtx.fillText(`person (0.95) [FALLEN/LYING_DOWN]`, bx, by - 8);

    // Silhouette
    vCtx.fillStyle = "rgba(255, 51, 102, 0.3)";
    vCtx.fillRect(bx, by, bw, bh);

    // Fallen Human Body
    vCtx.fillStyle = "#ffffff";
    vCtx.beginPath(); vCtx.arc(210, 280, 18, 0, Math.PI * 2); vCtx.fill();
    vCtx.fillRect(230, 270, 90, 22);
    vCtx.fillRect(320, 272, 80, 16);
  }
}

// --- Road Network Graph Canvas Drawing ---
function drawRoadNetworkCanvas() {
  rCtx.clearRect(0, 0, roadCanvas.width, roadCanvas.height);

  // Draw Edges / Roads
  EDGES.forEach(([u, v]) => {
    const p1 = NODE_POSITIONS[u];
    const p2 = NODE_POSITIONS[v];
    const isCorridorEdge = isEdgeInActiveRoute(u, v);

    // Road Base
    rCtx.strokeStyle = isCorridorEdge ? "rgba(0, 230, 153, 0.4)" : "rgba(255, 255, 255, 0.12)";
    rCtx.lineWidth = isCorridorEdge ? 8 : 4;
    rCtx.beginPath();
    rCtx.moveTo(p1.x, p1.y);
    rCtx.lineTo(p2.x, p2.y);
    rCtx.stroke();

    if (isCorridorEdge) {
      // Glowing green wave road center
      rCtx.strokeStyle = "#00e699";
      rCtx.lineWidth = 2;
      rCtx.setLineDash([8, 6]);
      rCtx.beginPath();
      rCtx.moveTo(p1.x, p1.y);
      rCtx.lineTo(p2.x, p2.y);
      rCtx.stroke();
      rCtx.setLineDash([]);
    }
  });

  // Draw Nodes
  Object.keys(NODE_POSITIONS).forEach(nodeKey => {
    const node = NODE_POSITIONS[nodeKey];
    const isAmbHere = ambulanceNode === nodeKey;
    const isPriorityJunc = node.juncId === activePriorityJunction;

    // Node Outer Ring / Glow
    if (isPriorityJunc) {
      rCtx.fillStyle = "rgba(0, 230, 153, 0.25)";
      rCtx.beginPath();
      rCtx.arc(node.x, node.y, 22, 0, Math.PI * 2);
      rCtx.fill();
    }

    // Node Circle
    rCtx.fillStyle = getNodeColor(node);
    rCtx.beginPath();
    rCtx.arc(node.x, node.y, node.type === "HOSPITAL" ? 14 : 10, 0, Math.PI * 2);
    rCtx.fill();
    rCtx.strokeStyle = "#ffffff";
    rCtx.lineWidth = 2;
    rCtx.stroke();

    // Node Label
    rCtx.fillStyle = "#e2e8f0";
    rCtx.font = "600 11px 'Outfit'";
    rCtx.textAlign = "center";
    rCtx.fillText(node.label, node.x, node.y - 16);

    // Ambulance Marker on current node
    if (isAmbHere) {
      // Siren pulse ring
      rCtx.strokeStyle = "#ff3366";
      rCtx.lineWidth = 2;
      rCtx.beginPath();
      rCtx.arc(node.x, node.y, 20 + Math.sin(Date.now() / 150) * 4, 0, Math.PI * 2);
      rCtx.stroke();

      // Ambulance Icon
      rCtx.fillStyle = "#ff3366";
      rCtx.font = "bold 16px sans-serif";
      rCtx.fillText("🚑", node.x, node.y + 6);
    }
  });
}

function getNodeColor(node) {
  if (node.type === "START") return "#ff3366";
  if (node.type === "HOSPITAL") return "#ffb800";
  if (node.juncId === activePriorityJunction) return "#00e699";
  return "#0099ff";
}

function isEdgeInActiveRoute(u, v) {
  if (!currentRoute || currentRoute.length < 2) return false;
  for (let i = 0; i < currentRoute.length - 1; i++) {
    if ((currentRoute[i] === u && currentRoute[i+1] === v) ||
        (currentRoute[i] === v && currentRoute[i+1] === u)) {
      return true;
    }
  }
  return false;
}

function startCanvasRenderLoop() {
  function render() {
    drawVideoCanvas();
    drawRoadNetworkCanvas();
    animationFrameId = requestAnimationFrame(render);
  }
  render();
}

// --- Simulations ---
function triggerFullEmergencySimulation() {
  resetAllState();
  addLog("AI", "Video Inference: Fall detected. Initializing 5-frame consecutive validation...");
  videoState.personPosture = "FALLEN";
  fallStatus = "FALL_CONFIRMED";
  fallConfidence = 0.94;
  
  hudFallState.textContent = "CONFIRMED";
  hudFallConf.textContent = "0.94";
  hudPosture.textContent = "LYING_DOWN";
  
  document.getElementById("step-detect").classList.add("active");
  document.getElementById("step-validate").classList.add("active");
  document.getElementById("step-monitor").classList.add("active");

  addLog("Validator", "5 consecutive fall frames validated. Starting 10-second non-recovery window.");
  timerDesc.textContent = "Monitoring person posture for 10-second recovery timeout...";

  let startTime = Date.now();
  let durationMs = 10000;

  if (simulationInterval) clearInterval(simulationInterval);
  
  simulationInterval = setInterval(() => {
    let elapsedMs = Date.now() - startTime;
    let elapsedSec = Math.min(10.0, elapsedMs / 1000.0);
    let progressPct = (elapsedSec / 10.0) * 100;

    timerDigits.textContent = `${elapsedSec.toFixed(1)}s / 10.0s`;
    timerProgressFill.style.width = `${progressPct}%`;

    if (elapsedSec >= 10.0) {
      clearInterval(simulationInterval);
      triggerEmergencyEscalation();
    }
  }, 100);
}

function triggerRecoverySimulation() {
  resetAllState();
  addLog("AI", "Fall detected. Monitoring 10-second recovery window...");
  videoState.personPosture = "FALLEN";
  fallStatus = "FALL_CONFIRMED";
  
  hudFallState.textContent = "MONITORING";
  hudPosture.textContent = "LYING_DOWN";

  let startTime = Date.now();
  let durationMs = 4000;

  if (simulationInterval) clearInterval(simulationInterval);
  
  simulationInterval = setInterval(() => {
    let elapsedMs = Date.now() - startTime;
    let elapsedSec = Math.min(4.0, elapsedMs / 1000.0);
    let progressPct = (elapsedSec / 10.0) * 100;

    timerDigits.textContent = `${elapsedSec.toFixed(1)}s / 10.0s`;
    timerProgressFill.style.width = `${progressPct}%`;

    if (elapsedSec >= 3.5) {
      clearInterval(simulationInterval);
      videoState.personPosture = "STANDING";
      fallStatus = "FALL_RECOVERED";
      hudFallState.textContent = "RECOVERED";
      hudPosture.textContent = "STANDING";
      timerDesc.textContent = "Person recovered and stood back up within 3.5s. Status: FALL_RECOVERED.";
      addLog("Recovery", "Person stood back up at t=3.5s! Event classified as FALL_RECOVERED (No ambulance required).");
    }
  }, 100);
}

async function triggerEmergencyEscalation() {
  hudAlert.style.display = "block";
  document.getElementById("step-trigger").classList.add("emergency");
  timerDesc.textContent = "10s elapsed with no recovery! SUSPECTED SERIOUS MEDICAL EMERGENCY triggered.";
  
  addLog("Emergency", "10 SECONDS COMPLETED WITHOUT RECOVERY. Triggering SUSPECTED SERIOUS MEDICAL EMERGENCY.");

  // Call FastAPI backend
  try {
    const res = await fetch("/api/emergency", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_source: "videos/emergency.mp4",
        confidence: 0.94,
        frame_number: 300,
        trigger: "fall_with_10_second_non_recovery",
        location_node: "A"
      })
    });

    if (res.ok) {
      const data = await res.json();
      addLog("FastAPI", `Emergency Event Registered (ID: ${data.event_id.slice(0, 8)}...). Dispatching AMB_01.`);
    }
  } catch (e) {
    addLog("FastAPI", "Dispatched local in-memory emergency response for AMB_01.");
  }

  // Calculate shortest path
  ambulanceStatus = "DISPATCHED";
  ambulanceNode = "A";
  activePriorityJunction = "J01";
  updateTelemetryUI();

  addLog("Router", "Calculated Optimal Route (A*): A -> B (J01) -> E (J04) -> G (J03) -> HOSPITAL");
  addLog("MQTT", "Published PRIORITY command to upcoming junction J01 (Green Wave Corridor).");

  setTimeout(() => {
    autoRunCorridorSimulation();
  }, 1200);
}

function autoRunCorridorSimulation() {
  if (ambulanceStatus === "IDLE") {
    ambulanceStatus = "DISPATCHED";
    ambulanceNode = "A";
    activePriorityJunction = "J01";
  }

  const routeSequence = [
    { node: "A", nextJunc: "J01", speed: 40 },
    { node: "B", nextJunc: "J04", speed: 52 },
    { node: "E", nextJunc: "J03", speed: 55 },
    { node: "G", nextJunc: null,  speed: 48 },
    { node: "HOSPITAL", nextJunc: null, speed: 0 }
  ];

  let stepIdx = 0;
  if (simulationInterval) clearInterval(simulationInterval);

  simulationInterval = setInterval(() => {
    if (stepIdx >= routeSequence.length) {
      clearInterval(simulationInterval);
      return;
    }

    const currentStep = routeSequence[stepIdx];
    ambulanceNode = currentStep.node;
    ambulanceSpeed = currentStep.speed;
    ambulanceStatus = currentStep.node === "HOSPITAL" ? "ARRIVED" : "EN_ROUTE";
    activePriorityJunction = currentStep.nextJunc;

    updateTelemetryUI();

    if (currentStep.node === "HOSPITAL") {
      addLog("Ambulance", "AMB_01 ARRIVED AT APEX HOSPITAL! Patient handed over to emergency triage.");
      addLog("Corridor", "All traffic junctions returned to NORMAL signal cycle.");
      resetSignals();
    } else {
      addLog("GPS", `AMB_01 reached node '${currentStep.node}' @ ${currentStep.speed} km/h. Next priority junction: ${currentStep.nextJunc || "Destination"}`);
      if (currentStep.nextJunc) {
        addLog("IoT", `Dynamic Green Wave: Granted GREEN PRIORITY to ${currentStep.nextJunc}`);
      }
    }

    stepIdx++;
  }, 1600);
}

function stepCorridorSimulation() {
  const steps = ["A", "B", "E", "G", "HOSPITAL"];
  let currIdx = steps.indexOf(ambulanceNode);
  if (currIdx === -1 || currIdx >= steps.length - 1) {
    currIdx = 0;
  } else {
    currIdx++;
  }

  ambulanceNode = steps[currIdx];
  ambulanceStatus = ambulanceNode === "HOSPITAL" ? "ARRIVED" : "EN_ROUTE";
  ambulanceSpeed = ambulanceNode === "HOSPITAL" ? 0 : 50;

  const juncMap = { "A": "J01", "B": "J04", "E": "J03", "G": null, "HOSPITAL": null };
  activePriorityJunction = juncMap[ambulanceNode];

  updateTelemetryUI();
  addLog("Manual", `Ambulance moved to ${ambulanceNode}. Upcoming priority: ${activePriorityJunction || "HOSPITAL"}`);
}

async function runVideoInferenceApi() {
  addLog("System", "Running YOLO inference on recorded video 'videos/test_emergency.mp4'...");
  triggerFullEmergencySimulation();
}

function resetAllState() {
  if (simulationInterval) clearInterval(simulationInterval);
  ambulanceNode = "A";
  ambulanceStatus = "IDLE";
  ambulanceSpeed = 0;
  activePriorityJunction = "J01";
  videoState.personPosture = "STANDING";
  
  hudAlert.style.display = "none";
  hudFallState.textContent = "NORMAL";
  hudFallConf.textContent = "0.00";
  hudPosture.textContent = "UPRIGHT";
  timerDigits.textContent = "0.0s / 10.0s";
  timerProgressFill.style.width = "0%";
  timerDesc.textContent = "Waiting for confirmed fall event...";

  document.querySelectorAll(".step-badge").forEach(b => b.classList.remove("active", "emergency"));
  document.getElementById("step-detect").classList.add("active");

  updateTelemetryUI();
  resetSignals();
  addLog("System", "System reset to clean in-memory state.");
}

function resetSignals() {
  fetch("/api/junctions/reset", { method: "POST" }).catch(() => {});
  activePriorityJunction = null;
  renderJunctionCards();
}

function updateTelemetryUI() {
  ambIdEl.textContent = "AMB_01";
  ambStatusEl.textContent = ambulanceStatus;
  ambPosEl.textContent = `Node ${ambulanceNode}`;
  ambUpcomingEl.textContent = activePriorityJunction ? `${activePriorityJunction} (Priority)` : "None (Hospital Approach)";
  ambSpeedEl.textContent = `${ambulanceSpeed} km/h • ${ambulanceStatus === 'ARRIVED' ? '0s' : '45s'}`;
  renderJunctionCards();
}

function renderJunctionCards() {
  const junctions = [
    { id: "J01", name: "Central Crossing", lat: "21.1465" },
    { id: "J02", name: "Main Highway",    lat: "21.1470" },
    { id: "J04", name: "Central Hub",     lat: "21.1425" },
    { id: "J03", name: "Hospital Ring",   lat: "21.1390" }
  ];

  junctionsListEl.innerHTML = junctions.map(j => {
    const isPriority = activePriorityJunction === j.id;
    return `
      <div class="junction-card ${isPriority ? 'priority-active' : ''}">
        <div class="junc-header">
          <span class="junc-id">${j.id} - ${j.name}</span>
          <span class="junc-status-tag ${isPriority ? 'priority' : ''}">${isPriority ? 'PRIORITY (GREEN WAVE)' : 'NORMAL'}</span>
        </div>
        <div class="traffic-lights-row">
          <div class="light-group">
            <span class="light-group-label">Corridor (NS)</span>
            <div class="signal-housing">
              <span class="signal-bulb red ${!isPriority ? 'on' : ''}"></span>
              <span class="signal-bulb yellow"></span>
              <span class="signal-bulb green ${isPriority ? 'on' : ''}"></span>
            </div>
          </div>
          <div class="light-group">
            <span class="light-group-label">Cross Traffic (EW)</span>
            <div class="signal-housing">
              <span class="signal-bulb red ${isPriority ? 'on' : ''}"></span>
              <span class="signal-bulb yellow"></span>
              <span class="signal-bulb green ${!isPriority ? 'on' : ''}"></span>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function updateJunctionsUI(backendJunctions) {
  // Can synchronize live with backend list
}
