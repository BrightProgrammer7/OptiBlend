const URL = "ws://localhost:9080";
const video = document.getElementById("videoElement");
const canvas = document.getElementById("canvasElement");
const context = canvas.getContext("2d");
const actionLabel = document.getElementById("actionLabel");
const confidenceIndicator = document.getElementById("confidenceIndicator");
const recipeSteps = document.getElementById("recipeSteps");
const timersContainer = document.getElementById("timersContainer");
const timers = document.getElementById("timers");
const culturalContext = document.getElementById("culturalContext");
const culturalText = document.getElementById("culturalText");
const chatLog = document.getElementById("chatLog");

let stream = null;
let webSocket = null;
let audioContext = null;
let workletNode = null;
let interval = null;
let activeTimers = [];
let currentRecipeId = "tajine_chicken";
let currentStep = -1;
let isListening = false;
let audioChunks = [];
let audioQueue = [];
let isPlayingAudio = false;
let lastSpeechTime = 0;
let silenceTimeout = null;
let audioChunkCount = 0;
let videoFrameCount = 0;

const MOROCCAN_COOKING_PROMPT = `
You are a Moroccan cooking assistant specialized in traditional Moroccan cuisine.
You speak primarily in Darija (Moroccan Arabic), with fallback to Arabic and French.

Your role:
- Guide users through traditional Moroccan recipes (tajine, couscous, rfissa, harira, etc.)
- Recognize kitchen actions from video (cutting, stirring, frying, seasoning, plating)
- Provide cultural context about ingredients, techniques, and history
- Give short, instructive voice responses in Darija
- Ask for clarification when detection is uncertain

Behavior:
- Keep responses concise (1-2 sentences)
- Use encouraging language
- Provide step-by-step guidance
- Explain traditional techniques when relevant
- Use function calls to retrieve recipe steps, timers, and cultural facts

When you detect a kitchen action, call the detect_kitchen_action function.
When the user completes a step, call get_next_recipe_step to guide them to the next step.
When the user asks about an ingredient, call explain_ingredient.
When starting a cooking phase that requires timing, call start_timer.
`;

const FUNCTION_DECLARATIONS = {
  "function_declarations": [
    {
      "name": "get_next_recipe_step",
      "description": "Get the next step in the current recipe",
      "parameters": {
        "type": "object",
        "properties": {
          "recipe_id": {
            "type": "string",
            "description": "The ID of the current recipe (e.g., 'tajine_chicken')"
          },
          "current_step": {
            "type": "integer",
            "description": "The current step number (0-indexed)"
          }
        },
        "required": ["recipe_id", "current_step"]
      }
    },
    {
      "name": "explain_ingredient",
      "description": "Get information about a Moroccan ingredient",
      "parameters": {
        "type": "object",
        "properties": {
          "ingredient_name": {
            "type": "string",
            "description": "The name of the ingredient in Darija, Arabic, French, or English"
          }
        },
        "required": ["ingredient_name"]
      }
    },
    {
      "name": "start_timer",
      "description": "Start a cooking timer",
      "parameters": {
        "type": "object",
        "properties": {
          "duration": {
            "type": "integer",
            "description": "Duration in seconds"
          },
          "label": {
            "type": "string",
            "description": "Label for the timer (e.g., 'Simmer tajine')"
          }
        },
        "required": ["duration", "label"]
      }
    },
    {
      "name": "get_cultural_context",
      "description": "Get cultural or historical context about a Moroccan dish or technique",
      "parameters": {
        "type": "object",
        "properties": {
          "topic": {
            "type": "string",
            "description": "The dish, ingredient, or technique to explain"
          }
        },
        "required": ["topic"]
      }
    },
    {
      "name": "detect_kitchen_action",
      "description": "Confirm the detected kitchen action from video",
      "parameters": {
        "type": "object",
        "properties": {
          "action": {
            "type": "string",
            "enum": ["cutting", "chopping", "stirring", "frying", "sauteing", "seasoning", "plating", "mixing", "kneading", "rolling", "idle"],
            "description": "The detected kitchen action"
          },
          "confidence": {
            "type": "number",
            "description": "Confidence level (0.0 to 1.0)"
          },
          "object": {
            "type": "string",
            "description": "The object being manipulated (e.g., 'onions', 'chicken', 'couscous')"
          }
        },
        "required": ["action", "confidence"]
      }
    }
  ]
};

// Action emoji mapping
const ACTION_EMOJIS = {
    "cutting": "🔪",
    "chopping": "🔪",
    "stirring": "🥄",
    "frying": "🍳",
    "sauteing": "🍳",
    "seasoning": "🧂",
    "plating": "🍽️",
    "mixing": "🥣",
    "kneading": "👐",
    "rolling": "🥖",
    "idle": "⏳"
};

async function startWebcam() {
    try {
        const constraints = {
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
            },
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
            },
        };
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;
        video.play();
        console.log("Webcam started");
    } catch (err) {
        console.error("Error accessing the webcam: ", err);
        addChatMessage("Error: Could not access webcam or microphone.", "system");
    }
}

function captureImage() {
    if (stream) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL("image/jpeg", 0.7).split(",")[1];
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
                
                // Check audio level to detect speech
                let hasSound = false;
                for (let i = 0; i < pcmData.length; i++) {
                    if (Math.abs(pcmData[i]) > 100) {
                        hasSound = true;
                        break;
                    }
                }
                
                if (hasSound) {
                    lastSpeechTime = Date.now();
                    // Clear any existing silence timeout
                    if (silenceTimeout) {
                        clearTimeout(silenceTimeout);
                        silenceTimeout = null;
                    }
                }
                
                if (webSocket && webSocket.readyState === WebSocket.OPEN) {
                    webSocket.send(JSON.stringify({
                        realtime_input: {
                            media_chunks: [
                                { mime_type: "audio/pcm", data: base64Pcm }
                            ]
                        }
                    }));
                    audioChunkCount++;
                    
                    // Auto-trigger after 2 seconds of silence
                    if (hasSound && !silenceTimeout && audioChunkCount > 20) {
                        silenceTimeout = setTimeout(() => {
                            if (Date.now() - lastSpeechTime >= 2000) {
                                console.log('Detected silence, auto-triggering assistant...');
                                triggerAssistant();
                            }
                        }, 2000);
                    }
                }
            };
            console.log("Audio processing started");
        } catch (err) {
            console.error("Error starting audio processing:", err);
        }
    }
}

function connectWebSocket() {
    webSocket = new WebSocket(URL);

    webSocket.onopen = () => {
        console.log("WebSocket connected");
        addChatMessage("Connected to cooking assistant!", "system");
        
        // Send setup configuration
        webSocket.send(JSON.stringify({
            setup: {
                model: "models/gemini-2.5-flash-native-audio-preview-09-2025",
                system_instruction: {
                    parts: [{ text: MOROCCAN_COOKING_PROMPT }]
                },
                tools: [FUNCTION_DECLARATIONS]
            }
        }));

        // Show welcome message
        setTimeout(() => {
            addChatMessage("السلام عليكم! Welcome to the Moroccan Cooking Assistant. Start speaking to begin!", "system");
        }, 500);

        // Start sending video frames
        interval = setInterval(() => {
            const frame = captureImage();
            if (frame && webSocket.readyState === WebSocket.OPEN) {
                webSocket.send(JSON.stringify({
                    realtime_input: {
                        media_chunks: [
                            { mime_type: "image/jpeg", data: frame }
                        ]
                    }
                }));
                videoFrameCount++;
                if (videoFrameCount % 5 === 0) {
                    console.log(`Sent ${audioChunkCount} audio chunks and ${videoFrameCount} video frames`);
                }
            }
        }, 1000); // Send frame every 1 second
    };

    webSocket.onmessage = (event) => {
        console.log("Received message from server:", event.data);
        const data = JSON.parse(event.data);
        
        if (data.text) {
            console.log("Received text:", data.text);
            addChatMessage(data.text, "assistant");
            
            // Check if text contains action detection
            if (data.text.includes("كتقطع") || data.text.includes("cutting") || data.text.includes("chopping")) {
                updateActionLabel("cutting", 0.9, "onions");
            }
        }
        
        if (data.audio) {
            playAudio(data.audio);
        }
    };

    webSocket.onclose = () => {
        console.log("WebSocket disconnected");
        clearInterval(interval);
        addChatMessage("Disconnected from cooking assistant.", "system");
    };

    webSocket.onerror = (error) => {
        console.error("WebSocket error:", error);
        addChatMessage("Connection error occurred.", "system");
    };
}

function updateActionLabel(action, confidence, object) {
    const emoji = ACTION_EMOJIS[action] || "👨‍🍳";
    const objectText = object ? ` ${object}` : "";
    actionLabel.textContent = `${emoji} ${action}${objectText}`;
    actionLabel.style.display = "block";
    
    // Update confidence indicator
    const confidencePercent = Math.round(confidence * 100);
    confidenceIndicator.textContent = `${confidencePercent}% confident`;
    confidenceIndicator.style.display = "block";
    
    // Hide after 5 seconds if confidence is high
    if (confidence > 0.7) {
        setTimeout(() => {
            actionLabel.style.display = "none";
            confidenceIndicator.style.display = "none";
        }, 5000);
    }
}

function addRecipeStep(stepNumber, instruction, tips, isActive = false) {
    const stepCard = document.createElement("div");
    stepCard.className = `step-card ${isActive ? "active" : ""}`;
    stepCard.id = `step-${stepNumber}`;
    
    stepCard.innerHTML = `
        <div>
            <span class="step-number">Step ${stepNumber + 1}</span>
            <div class="step-instruction">${instruction}</div>
            ${tips ? `<div class="step-tip">💡 ${tips}</div>` : ""}
        </div>
    `;
    
    recipeSteps.appendChild(stepCard);
}

function activateStep(stepNumber) {
    // Remove active class from all steps
    document.querySelectorAll(".step-card").forEach(card => {
        card.classList.remove("active");
    });
    
    // Add active class to current step
    const stepCard = document.getElementById(`step-${stepNumber}`);
    if (stepCard) {
        stepCard.classList.add("active");
        stepCard.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function addTimer(duration, label) {
    const timerId = Date.now();
    const endTime = Date.now() + (duration * 1000);
    
    const timerCard = document.createElement("div");
    timerCard.className = "timer-card";
    timerCard.id = `timer-${timerId}`;
    
    timerCard.innerHTML = `
        <div class="timer-label">${label}</div>
        <div class="timer-countdown" id="countdown-${timerId}">--:--</div>
    `;
    
    timers.appendChild(timerCard);
    timersContainer.style.display = "block";
    
    // Store timer info
    activeTimers.push({ id: timerId, endTime, label });
    
    // Start countdown
    updateTimerCountdown(timerId, endTime);
}

function updateTimerCountdown(timerId, endTime) {
    const countdownElement = document.getElementById(`countdown-${timerId}`);
    
    const updateInterval = setInterval(() => {
        const remaining = Math.max(0, endTime - Date.now());
        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        
        countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        if (remaining <= 0) {
            clearInterval(updateInterval);
            countdownElement.textContent = "Done!";
            countdownElement.style.color = "#4CAF50";
            
            // Play notification sound (optional)
            playNotificationSound();
            
            // Remove timer after 5 seconds
            setTimeout(() => {
                const timerCard = document.getElementById(`timer-${timerId}`);
                if (timerCard) {
                    timerCard.remove();
                }
                
                // Hide timers container if no more timers
                if (timers.children.length === 0) {
                    timersContainer.style.display = "none";
                }
            }, 5000);
        }
    }, 1000);
}

function showCulturalContext(text) {
    culturalText.textContent = text;
    culturalContext.style.display = "block";
}

function addChatMessage(text, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `chat-message ${sender}`;
    messageDiv.textContent = text;
    chatLog.appendChild(messageDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
}

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
        // Decode base64 to raw PCM data
        const binaryString = atob(base64Audio);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        
        // Create audio context if not exists
        if (!audioContext) {
            audioContext = new AudioContext({ sampleRate: 24000 });
        }
        
        // Convert PCM to AudioBuffer
        const audioBuffer = audioContext.createBuffer(1, bytes.length / 2, 24000);
        const channelData = audioBuffer.getChannelData(0);
        
        // Convert Int16 PCM to Float32 for Web Audio API
        const dataView = new DataView(bytes.buffer);
        for (let i = 0; i < channelData.length; i++) {
            channelData[i] = dataView.getInt16(i * 2, true) / 32768.0;
        }
        
        // Play the audio
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        
        // Play next chunk when this one ends
        source.onended = () => {
            playNextAudio();
        };
        
        source.start();
        console.log(`Playing audio chunk, duration: ${audioBuffer.duration}s`);
    } catch (err) {
        console.error("Error playing audio:", err);
        playNextAudio(); // Continue with next chunk even if this one failed
    }
}

function playNotificationSound() {
    // Simple beep sound using Web Audio API
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    
    oscillator.frequency.value = 800;
    oscillator.type = "sine";
    
    gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
    
    oscillator.start(audioCtx.currentTime);
    oscillator.stop(audioCtx.currentTime + 0.5);
}

function triggerAssistant() {
    // Send end of turn signal to trigger assistant response
    if (webSocket && webSocket.readyState === WebSocket.OPEN) {
        addChatMessage("Waiting for assistant response...", "system");
        
        // Resume audio context if suspended (browser autoplay policy)
        if (audioContext && audioContext.state === 'suspended') {
            audioContext.resume().then(() => {
                console.log('Audio context resumed');
            });
        }
        
        webSocket.send(JSON.stringify({
            client_content: {
                turn_complete: true
            }
        }));
    }
}

// Initialize on page load
window.onload = async () => {
    console.log("Initializing cooking assistant...");
    await startWebcam();
    await startAudioProcessing();
    connectWebSocket();
    
    // Add initial recipe steps (example)
    addRecipeStep(0, "قطع الدجاج لقطع متوسطة. قطع البصل شرائح رقيقة.", "خلي القطع متساوية باش تطيب مزيان.", true);
    addRecipeStep(1, "خلط الدجاج بالتوابل والثوم. خليه يرتاح 15 دقيقة.", "التتبيل كيخلي الدجاج يتشرب النكهة.");
    addRecipeStep(2, "حط زيت العود فالطبسيل. زيد البصل وقليه حتى يولي ذهبي.", "قلب البصل مزيان باش ما يحرقش.");
    
    currentStep = 0;
};
