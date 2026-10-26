const servos = ["base", "shoulder", "elbow", "wristtilt", "wristyaw", "claw"];

let isRecording = false;
let recording = [];
let previousTime = null;
let isReplaying = false;

const recordButton = document.getElementById("recordButton");
const stopButton = document.getElementById("stopButton");
const replayButton = document.getElementById("replayButton");
const recordingStatus = document.getElementById("recordingStatus");
const clearButton = document.getElementById("clearButton");
const stopReplayButton = document.getElementById("stopReplayButton");
let scene, camera, renderer, armTipSphere, controls;
let armLine;

const visionFeed = document.getElementById("vision-feed");
const visionFrame = document.getElementById("vision-frame");
const visionSelection = document.getElementById("vision-selection");
const visionStatus = document.getElementById("vision-status");
const visionModeButton = document.getElementById("vision-mode-button");
const gameStatus = document.getElementById("game-status");
const gameStartButton = document.getElementById("game-start-button");
const gameContinueButton = document.getElementById("game-continue-button");
const gameDiceRollButton = document.getElementById("game-dice-roll-button");
const gameResetButton = document.getElementById("game-reset-button");
const gameColourButtons = document.querySelectorAll("[data-game-color]");

let calibrationColor = null;
let calibrationStart = null;
let calibrationMode = false;

const jointSpheres = [];

function sendData() {

    const servoAngles = {};
    const durationInput = document.getElementById("duration-ms");
    const durationMs = Number(durationInput.value);
    if (!Number.isInteger(durationMs) || durationMs < 300 || durationMs > 30000) {
        durationInput.setCustomValidity("Enter a duration from 300 to 30000 ms.");
        durationInput.reportValidity();
        return;
    }
    durationInput.setCustomValidity("");

    for (let servo of servos) {
        const servoAngle = document.getElementById(servo).value;

        servoAngles[servo] = Number(servoAngle);

        const labelName = servo + "Val";
        document.getElementById(labelName).innerText = servoAngle;
    }
    servoAngles.duration_ms = durationMs;

    if (isRecording) {
        const currentTime = performance.now();
        const delay = currentTime - previousTime;

        recording.push({
            base: servoAngles.base,
            shoulder: servoAngles.shoulder,
            elbow: servoAngles.elbow,
            wristtilt: servoAngles.wristtilt,
            wristyaw: servoAngles.wristyaw,
            claw: servoAngles.claw,
            delay: delay
        });

        previousTime = currentTime;
    }

    fetch("http://127.0.0.1:5001/control", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(servoAngles)
    })
    .then(response => response.json())
    .then(data => {
        if (armTipSphere) {

            document.getElementById('val-x').innerText = Math.round(data.x);
            document.getElementById('val-y').innerText = Math.round(data.y);
            document.getElementById('val-z').innerText = Math.round(data.z);
            
            armTipSphere.position.set(data.x, data.z, data.y);

            if (data.joints && armLine) {
                const points = data.joints.map((pt, index) => {
                    const x = pt.x;
                    const y = pt.z;
                    const z = pt.y;

                    if (jointSpheres[index]) {
                        jointSpheres[index].position.set(x, y, z);
                    }
                    return new THREE.Vector3(x, y, z);
                });

                armLine.geometry.dispose();
                armLine.geometry = new THREE.BufferGeometry().setFromPoints(points);
            }
        }
    })
    .catch(error => console.error("Error updating coordinates:", error));
}

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function replayRecording() {

    if (recording.length === 0) {
        recordingStatus.innerText = "Nothing to Replay";
        return;
    }

    if (isReplaying) {
        return;
    }

    isRecording = false;
    isReplaying = true;
    recordingStatus.innerText = "Replaying...";

    for (let move of recording) {

        if (!isReplaying) {
            break;
        }

        await wait(move.delay);

        if (!isReplaying) {
            break;
        }

        document.getElementById("base").value = move.base;
        document.getElementById("shoulder").value = move.shoulder;
        document.getElementById("elbow").value = move.elbow;
        document.getElementById("wristtilt").value = move.wristtilt;
        document.getElementById("wristyaw").value = move.wristyaw;
        document.getElementById("claw").value = move.claw;

        sendData();
    }

    isReplaying = false;

    if (recordingStatus.innerText === "Replaying...") {
        recordingStatus.innerText = "Replay finished";
    }
}

function openClaw() {
    document.getElementById("claw").value = 80;
    sendData();
}

function closeClaw() {
    document.getElementById("claw").value = 30;
    sendData();
}

function goHome() {
    document.getElementById("base").value = 90;
    document.getElementById("shoulder").value = 180;
    document.getElementById("elbow").value = 175;
    document.getElementById("wristtilt").value = 90;
    document.getElementById("wristyaw").value = 90;
    document.getElementById("claw").value = 80;

    sendData();
}

async function moveToCoordinates() {
    const targetX = parseFloat(document.getElementById("target-input-x").value);
    const targetY = parseFloat(document.getElementById("target-input-y").value);
    const targetZ = parseFloat(document.getElementById("target-input-z").value);
    const targetPitch = parseFloat(document.getElementById("target-input-pitch").value);
    const statusEl = document.getElementById("ik-status");
    const previewEl = document.getElementById("ik-angle-preview");

    statusEl.innerText = "Status: Calculating...";
    statusEl.style.color = "#ffaa00";

    try {
        const response = await fetch("/solve_ik", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                x: targetX,
                y: targetY,
                z: targetZ,
                pitch: targetPitch
            })
        });

        const result = await response.json();

        if (result.reachable) {
            statusEl.innerText = "Status: Solved (Manual Verification)";
            statusEl.style.color = "#00ffcc";

            document.getElementById("prev-base").innerText = result.base;
            document.getElementById("prev-shoulder").innerText = result.shoulder;
            document.getElementById("prev-elbow").innerText = result.elbow;
            document.getElementById("prev-wrist").innerText = result.wristtilt;

            previewEl.style.display = "block";

        } else {
            statusEl.innerText = `Status: Out of Reach (${result.error || "Geometry limit"})`;
            statusEl.style.color = "#ff4444";
            previewEl.style.display = "none";
        }
    } catch (err) {
        statusEl.innerText = "Status: Error communicating with server";
        statusEl.style.color = "#ff4444";
        previewEl.style.display = "none";
        console.error("IK error", err);
    }
}


document.getElementById("btn-move-ik").onclick = moveToCoordinates;

document.getElementById("homeButton").onclick = goHome;
document.getElementById("openClawButton").onclick = openClaw;
document.getElementById("closeClawButton").onclick = closeClaw;

recordButton.onclick = function() {

    if (isReplaying) {
        return;
    }

    isRecording = true;
    recording = [];
    previousTime = performance.now();

    recordingStatus.innerText = "Recording...";
    console.log("Recording Started");
};

stopButton.onclick = function() {
    isRecording = false;

    recordingStatus.innerText = "Not Recording";
    console.log("Recording Stopped");
    console.log(recording);
};

replayButton.onclick = function() {
    replayRecording();
};

stopReplayButton.onclick = function() {
    isReplaying = false;
    recordingStatus.innerText = "Replay stopped";
};

clearButton.onclick = function() {

    isRecording = false;
    isReplaying = false;

    recording = [];
    previousTime = null;

    recordingStatus.innerText = "Recording cleared"

    console.log("Recording Cleared");
    console.log(recording);
};

let dataChanged = false;

for (let servo of servos) {

    document.getElementById(servo).oninput = function() {

        const servoAngle = this.value;
        document.getElementById(servo + "Val").innerText = servoAngle;

        dataChanged = true;
    };
}

setInterval(function() {

    if (dataChanged) {
        sendData();
        dataChanged = false;
    }

}, 50);

function init3DViewer() {
    const container = document.getElementById('arm-3d-canvas');

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(400, 400, 500);
    camera.lookAt(0, 0, 150);

    renderer = new THREE.WebGLRenderer({antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    const gridHelper = new THREE.GridHelper(1000, 30);
    scene.add(gridHelper);

    const axesHelper = new THREE.AxesHelper(300);
    scene.add(axesHelper);

    const geometry = new THREE.SphereGeometry(8, 32, 32);
    const material = new THREE.MeshStandardMaterial({
        color: 0x00ffcc,
        roughness: 0.4,
        metalness: 0.2
    });

    armTipSphere = new THREE.Mesh(geometry, material);
    scene.add(armTipSphere);

    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x00ffff, linewidth: 3});
    const lineGeometry = new THREE.BufferGeometry();

    const positions = new Float32Array(6 * 3);
    lineGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    armLine = new THREE.Line(lineGeometry, lineMaterial);
    scene.add(armLine)

    const jointGeo = new THREE.SphereGeometry(6, 16, 16);
    const jointMat = new THREE.MeshBasicMaterial({ color: 0xffaa00 });
    for (let i = 0; i < 6; i++) {
        const sphere = new THREE.Mesh(jointGeo, jointMat);
        scene.add(sphere);
        jointSpheres.push(sphere);

    }

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(200,400,300);
    scene.add(directionalLight);

    animate();
    sendData();
}

function animate() {
    requestAnimationFrame(animate);
    if (controls) {
        controls.update();
    }
    
    renderer.render(scene, camera);
}

window.onload = init3DViewer;

async function sendGameAction(action) {
    const endpoints = {
        start: "/game_start",
        continue: "/game_continue",
        diceRoll: "/game_dice_roll",
        reset: "/game_reset"
    };

    try {
        const response = await fetch(endpoints[action], { method: "POST" });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || `Game request failed (HTTP ${response.status})`);
        }

        renderGameState(result);
    } catch (error) {
        gameStatus.innerText = error.message;
        console.error("Game request error:", error);
    }
}

async function selectGameColour(colour) {
    try {
        const response = await fetch("/game_select_colour", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ colour })
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || `Colour selection failed (HTTP ${response.status})`);
        }
        renderGameState(result);
    } catch (error) {
        gameStatus.innerText = error.message;
        console.error("Manual colour selection error:", error);
    }
}

function renderGameState(state) {
    gameStatus.innerText = state.current_stage
        ? `${state.message} Current stage: ${state.current_stage.replaceAll("_", " ")}.`
        : state.message;
    gameStartButton.disabled = state.status !== "waiting_for_colour";
    gameContinueButton.hidden = state.status !== "awaiting_block_removal";
    gameContinueButton.disabled = state.status !== "awaiting_block_removal";
    const diceSequenceAllowedStatuses = [
        "waiting_for_colour",
        "awaiting_block_removal",
        "round_complete",
        "dice_only_complete",
        "error"
    ];
    gameDiceRollButton.disabled = !diceSequenceAllowedStatuses.includes(state.status);
    gameResetButton.disabled = [
        "homing",
        "running_block",
        "running_dice",
        "running_dice_only"
    ].includes(state.status);
    gameColourButtons.forEach((button) => {
        button.disabled = state.status !== "waiting_for_colour";
        button.setAttribute(
            "aria-pressed",
            String(button.dataset.gameColor === state.selected_colour)
        );
    });
}

async function refreshGameState() {
    try {
        const response = await fetch("/game_status");
        if (!response.ok) {
            throw new Error(`Could not refresh game status (HTTP ${response.status})`);
        }
        renderGameState(await response.json());
    } catch (error) {
        console.error("Game status refresh error:", error);
    }
}

gameStartButton.addEventListener("click", () => sendGameAction("start"));
gameContinueButton.addEventListener("click", () => sendGameAction("continue"));
gameDiceRollButton.addEventListener("click", () => sendGameAction("diceRoll"));
gameResetButton.addEventListener("click", () => sendGameAction("reset"));
gameColourButtons.forEach((button) => {
    button.addEventListener("click", () => selectGameColour(button.dataset.gameColor));
});
refreshGameState();
window.setInterval(refreshGameState, 1000);

document.querySelectorAll("[data-vision-color]").forEach((button) => {
    button.addEventListener("click", () => {
        calibrationColor = button.dataset.visionColor;
        visionStatus.innerText =
            `Drag a box around the ${calibrationColor} card in the camera image.`;
    });
});

visionModeButton.addEventListener("click", async () => {
    const nextMode = !calibrationMode;

    try {
        const response = await fetch("/vision_mode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: nextMode })
        });

        const contentType = response.headers.get("content-type") || "";
        const result = contentType.includes("application/json")
            ? await response.json()
            : {};

        if (!response.ok) {
            throw new Error(
                result.error || `Could not change vision mode (HTTP ${response.status})`
            );
        }

        if (!contentType.includes("application/json")) {
            throw new Error("Server returned an unexpected response for vision mode");
        }

        calibrationMode = result.enabled;
        visionModeButton.innerText = calibrationMode
            ? "Hide detection boxes"
            : "Show detection boxes";
        visionStatus.innerText = calibrationMode
            ? "Detection boxes are visible."
            : "Detection boxes are hidden.";
    } catch (error) {
        visionStatus.innerText = error.message;
        console.error("Vision mode error:", error);
    }
});

function getImagePosition(event) {
    const bounds = visionFeed.getBoundingClientRect();

    return {
        x: Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width)),
        y: Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height))
    };
}

visionFrame.addEventListener("pointerdown", (event) => {
    if (!calibrationColor) {
        return;
    }

    event.preventDefault();
    visionFrame.setPointerCapture(event.pointerId);
    calibrationStart = getImagePosition(event);

    visionSelection.style.display = "block";
    visionSelection.style.left = `${calibrationStart.x * 100}%`;
    visionSelection.style.top = `${calibrationStart.y * 100}%`;
    visionSelection.style.width = "0";
    visionSelection.style.height = "0";
});

visionFrame.addEventListener("pointermove", (event) => {
    if (!calibrationStart) {
        return;
    }

    const current = getImagePosition(event);
    const left = Math.min(calibrationStart.x, current.x);
    const top = Math.min(calibrationStart.y, current.y);
    const width = Math.abs(current.x - calibrationStart.x);
    const height = Math.abs(current.y - calibrationStart.y);

    visionSelection.style.left = `${left * 100}%`;
    visionSelection.style.top = `${top * 100}%`;
    visionSelection.style.width = `${width * 100}%`;
    visionSelection.style.height = `${height * 100}%`;
});

visionFrame.addEventListener("pointerup", async (event) => {
    if (!calibrationStart || !calibrationColor) {
        return;
    }

    const current = getImagePosition(event);
    const selection = {
        color: calibrationColor,
        x: Math.min(calibrationStart.x, current.x),
        y: Math.min(calibrationStart.y, current.y),
        width: Math.abs(current.x - calibrationStart.x),
        height: Math.abs(current.y - calibrationStart.y)
    };

    calibrationStart = null;
    visionSelection.style.display = "none";

    if (selection.width < 0.01 || selection.height < 0.01) {
        visionStatus.innerText = "The selected area is too small. Try again.";
        return;
    }

    visionStatus.innerText = `Calibrating ${selection.color}...`;

    try {
        const response = await fetch("/vision_calibrate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(selection)
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "Calibration failed");
        }

        visionStatus.innerText = `Calibrated ${result.color}.`;
        calibrationColor = null;
    } catch (error) {
        visionStatus.innerText = error.message;
        console.error("Vision calibration error:", error);
    }
});

visionFeed.addEventListener("error", () => {
    visionStatus.innerText =
        "Could not load camera feed. Check that the camera is connected and restart Flask.";
});