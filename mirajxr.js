const URL = "ws://localhost:9080";
const video = document.getElementById("videoElement");
const canvas = document.getElementById("canvasElement");
const context = canvas.getContext("2d");

// UI Elements
const startOverlay = document.getElementById("startOverlay");
const startButton = document.getElementById("startButton");
const chatLog = document.getElementById("chatLog");
const mixTableBody = document.getElementById("mixTableBody");
const targetPciVal = document.getElementById("targetPciVal");
const projectedPciVal = document.getElementById("projectedPciVal");
const sulfurVal = document.getElementById("sulfurVal");
const chlorideVal = document.getElementById("chlorideVal");

let stream = null;
let webSocket = null;
let audioContext = null;
let workletNode = null;
let interval = null;
let audioQueue = [];
let isPlayingAudio = false;

// Industrial System Prompt (Client sends this to Server to configure Gemini)
const STARTUP_CONFIG = {
    setup: {
        model: "models/gemini-2.5-flash-native-audio-preview-09-2025",
        // Valid tools and prompts are injected by the Python backend now 
    }
};

startButton.addEventListener("click", async () => {
    startOverlay.style.display = "none";
    await startWebcam();
    await startAudioProcessing();
    connectWebSocket();
});

async function startWebcam() {
    try {
        const constraints = {
            video: { width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true }
        };
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;
        video.play();
        addLog("Vision System Activated - Monitoring Conveyor", "system");
    } catch (err) {
        console.error("Error accessing media devices:", err);
        addLog("CRITICAL: Camera/Mic Access Failed", "system");
    }
}

function captureImage() {
    if (stream) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
    }
    return null;
}

async function startAudioProcessing() {
    if (stream) {
        try {
            audioContext = new AudioContext({ sampleRate: 16000 });
            await audioContext.audioWorklet.addModule('pcm-processor.js');
            const source = audioContext.createMediaStreamSource(stream);
            workletNode = new AudioWorkletNode(audioContext, 'pcm-processor');
            source.connect(workletNode);
            workletNode.connect(audioContext.destination);

            workletNode.port.onmessage = (event) => {
                const pcmData = event.data;
                const base64Pcm = btoa(String.fromCharCode.apply(null, new Uint8Array(pcmData.buffer)));

                if (webSocket && webSocket.readyState === WebSocket.OPEN) {
                    webSocket.send(JSON.stringify({
                        realtime_input: {
                            media_chunks: [{ mime_type: "audio/pcm", data: base64Pcm }]
                        }
                    }));
                }
            };
        } catch (err) {
            console.error("Error starting audio processing:", err);
        }
    }
}

function connectWebSocket() {
    webSocket = new WebSocket(URL);

    webSocket.onopen = () => {
        console.log("WebSocket connected");
        addLog("Connected to Holcim AI Server", "system");

        // Send initial setup
        webSocket.send(JSON.stringify(STARTUP_CONFIG));

        // Start sending video frames
        interval = setInterval(() => {
            const frame = captureImage();
            if (frame && webSocket.readyState === WebSocket.OPEN) {
                webSocket.send(JSON.stringify({
                    realtime_input: {
                        media_chunks: [{ mime_type: "image/jpeg", data: frame }]
                    }
                }));
            }
        }, 1000); // 1 FPS analysis
    };

    webSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.text) {
            addLog(data.text, "assistant");
        }

        if (data.audio) {
            playAudio(data.audio);
        }

        // Handle SCADA Data Updates
        if (data.type === "scada_update") {
            updateScadaPanel(data.data);
        }
    };

    webSocket.onclose = () => {
        console.log("WebSocket disconnected");
        clearInterval(interval);
        addLog("Connection Lost - Reconnecting...", "system");
    };

    webSocket.onerror = (error) => {
        console.error("WebSocket error:", error);
    };
}

function updateScadaPanel(data) {
    // 1. Update Mix Table
    if (data.mix_ton_per_hour) {
        mixTableBody.innerHTML = "";
        for (const [fuel, amount] of Object.entries(data.mix_ton_per_hour)) {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${fuel}</td>
                <td class="fuel-amount">${amount.toFixed(2)} t/h</td>
            `;
            mixTableBody.appendChild(row);
        }
        addLog(`New Mix Optimized. Total: ${data.total_feed_rate} t/h`, "scada");
    }

    // 2. Update KPIs
    if (data.avg_pci) projectedPciVal.textContent = Math.round(data.avg_pci);
    if (data.avg_sulfur_percent) sulfurVal.textContent = data.avg_sulfur_percent.toFixed(2) + "%";
    if (data.avg_chloride_percent) chlorideVal.textContent = data.avg_chloride_percent.toFixed(2) + "%";

    // 3. Update Params if returned
    if (data.new_params) {
        targetPciVal.textContent = data.new_params["Target PCI"];
        addLog("Operational Parameters Updated via Voice", "scada");
    }
}

function addLog(text, type) {
    const entry = document.createElement("div");
    entry.className = `log-entry ${type}`;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    entry.textContent = `[${time}] ${text}`;
    chatLog.appendChild(entry);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// Audio Playback Logic
async function playAudio(base64Audio) {
    audioQueue.push(base64Audio);
    if (!isPlayingAudio) {
        playNextAudio();
    }
}

async function playNextAudio() {
    if (audioQueue.length === 0) {
        isPlayingAudio = false;
        return;
    }

    isPlayingAudio = true;
    const base64Audio = audioQueue.shift();

    try {
        const binaryString = atob(base64Audio);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        if (!audioContext) {
            audioContext = new AudioContext({ sampleRate: 24000 });
        }

        const audioBuffer = audioContext.createBuffer(1, bytes.length / 2, 24000);
        const channelData = audioBuffer.getChannelData(0);

        const dataView = new DataView(bytes.buffer);
        for (let i = 0; i < channelData.length; i++) {
            channelData[i] = dataView.getInt16(i * 2, true) / 32768.0;
        }

        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.onended = () => playNextAudio();
        source.start();
    } catch (err) {
        console.error("Error playing audio:", err);
        playNextAudio();
    }
}
