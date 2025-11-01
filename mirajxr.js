const URL = "ws://localhost:9080";
const video = document.getElementById("videoElement");
const canvas = document.getElementById("canvasElement");
const context = canvas.getContext("2d");

// UI Elements
const startOverlay = document.getElementById("startOverlay");
const startButton = document.getElementById("startButton");
const actionLabel = document.getElementById("actionLabel");
const actionIcon = document.getElementById("actionIcon");
const actionText = document.getElementById("actionText");
const confidenceBadge = document.getElementById("confidenceBadge");
const stepOverlay = document.getElementById("stepOverlay");
const stepOverlayText = document.getElementById("stepOverlayText");
const recipeStepsContainer = document.getElementById("recipeStepsContainer");
const timersSection = document.getElementById("timersSection");
const timersContainer = document.getElementById("timersContainer");
const culturalSection = document.getElementById("culturalSection");
const culturalText = document.getElementById("culturalText");
const chatLog = document.getElementById("chatLog");

let stream = null;
let webSocket = null;
let audioContext = null;
let workletNode = null;
let interval = null;
let activeTimers = [];
let currentRecipeId = "tajine_chicken";
let currentStep = 0;
let audioQueue = [];
let isPlayingAudio = false;
let lastSpeechTime = 0;
let silenceTimeout = null;
let audioChunkCount = 0;
let videoFrameCount = 0;

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

// Moroccan Cooking Prompt with Cultural Heritage Focus
const MOROCCAN_COOKING_PROMPT = `
You are Miraj XR, an AI assistant dedicated to preserving Moroccan culinary heritage through interactive cooking guidance.

Your mission is to teach traditional Moroccan cooking while preserving cultural knowledge, techniques, and stories.

Language: Speak primarily in Darija (Moroccan Arabic), with fallback to Arabic and French.

Your role:
- Guide users through authentic Moroccan recipes (tajine, couscous, rfissa, harira, pastilla, etc.)
- Recognize kitchen actions and traditional tools (tajine pot, couscousière, mehraz/mortar)
- Share cultural context: ingredient origins, regional variations, cooking rituals, proverbs
- Validate cooking techniques and provide real-time corrections
- Preserve intangible culinary heritage through storytelling

Behavior:
- Keep responses concise (1-2 sentences)
- Use encouraging, warm language
- Share cultural wisdom when relevant
- Correct techniques gently
- Celebrate traditional methods

When you detect actions, call detect_kitchen_action.
When moving to next step, call get_next_recipe_step.
When user asks about ingredients or culture, call explain_ingredient or get_cultural_context.
When timing is critical, call start_timer.
`;

const FUNCTION_DECLARATIONS = {
  "function_declarations": [
    {
      "name": "get_next_recipe_step",
      "description": "Get the next step in the current traditional Moroccan recipe",
      "parameters": {
        "type": "object",
        "properties": {
          "recipe_id": {
            "type": "string",
            "description": "The ID of the current recipe"
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
      "description": "Get cultural and historical information about a Moroccan ingredient",
      "parameters": {
        "type": "object",
        "properties": {
          "ingredient_name": {
            "type": "string",
            "description": "The name of the ingredient"
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
            "description": "Label for the timer"
          }
        },
        "required": ["duration", "label"]
      }
    },
    {
      "name": "get_cultural_context",
      "description": "Get cultural or historical context about a Moroccan dish, technique, or tradition",
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
      "description": "Confirm detected kitchen action from video",
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
            "description": "The object being manipulated"
          }
        },
        "required": ["action", "confidence"]
      }
    }
  ]
};

// Start Button Handler
startButton.addEventListener("click", async () => {
    startOverlay.style.display = "none";
    await startWebcam();
    await startAudioProcessing();
    connectWebSocket();
    loadRecipeSteps();
});

async function startWebcam() {
    try {
        const constraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
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
        addChatMessage("Webcam and microphone activated. Ready to cook!", "system");
    } catch (err) {
        console.error("Error accessing media devices:", err);
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
        } catch (err) {
            console.error("Error starting audio processing:", err);
        }
    }
}

function connectWebSocket() {
    webSocket = new WebSocket(URL);

    webSocket.onopen = () => {
        console.log("WebSocket connected");
        addChatMessage("Connected to Miraj XR assistant!", "system");
        
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
            addChatMessage("السلام عليكم! Miraj XR is listening...", "system");
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
        }, 1000);
    };

    webSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.text) {
            console.log("Received text:", data.text);
            addChatMessage(data.text, "assistant");
        }
        
        if (data.audio) {
            playAudio(data.audio);
        }
    };

    webSocket.onclose = () => {
        console.log("WebSocket disconnected");
        clearInterval(interval);
        addChatMessage("Disconnected from Miraj XR assistant.", "system");
    };

    webSocket.onerror = (error) => {
        console.error("WebSocket error:", error);
        addChatMessage("Connection error occurred.", "system");
    };
}

function updateActionLabel(action, confidence, object = "") {
    const emoji = ACTION_EMOJIS[action] || "👨‍🍳";
    const objectText = object ? ` ${object}` : "";
    
    actionIcon.textContent = emoji;
    actionText.textContent = `${action}${objectText}`;
    actionLabel.style.display = "block";
    
    // Update confidence
    const confidencePercent = Math.round(confidence * 100);
    confidenceBadge.textContent = `${confidencePercent}% Confident`;
    confidenceBadge.style.display = "block";
    
    // Hide after 5 seconds if high confidence
    if (confidence > 0.7) {
        setTimeout(() => {
            actionLabel.style.display = "none";
            confidenceBadge.style.display = "none";
        }, 5000);
    }
}

function loadRecipeSteps() {
    // Example recipe steps for Chicken Tajine
    const steps = [
        {
            instruction: "قطع الدجاج لقطع متوسطة. قطع البصل شرائح رقيقة.",
            tip: "خلي القطع متساوية باش تطيب مزيان."
        },
        {
            instruction: "خلط الدجاج بالتوابل والثوم. خليه يرتاح 15 دقيقة.",
            tip: "التتبيل كيخلي الدجاج يتشرب النكهة."
        },
        {
            instruction: "حط زيت العود فالطبسيل. زيد البصل وقليه حتى يولي ذهبي.",
            tip: "قلب البصل مزيان باش ما يحرقش."
        },
        {
            instruction: "زيد الدجاج والتوابل. قلب مزيان.",
            tip: "خلي الدجاج يتحمر من كل الجهات."
        },
        {
            instruction: "زيد الماء والخضر. غطي الطاجين.",
            tip: "الماء خصو يغطي الدجاج بشوية."
        },
        {
            instruction: "خلي الطاجين يطيب على نار هادية 45 دقيقة.",
            tip: "ما تفتحش الطاجين بزاف باش ما يخرجش البخار."
        },
        {
            instruction: "زيد الزيتون والليمون المحفوظ. خلي 10 دقائق.",
            tip: "هادي اللمسة الأخيرة اللي كتعطي النكهة المغربية."
        },
        {
            instruction: "قدم الطاجين مع الخبز أو الكسكس.",
            tip: "بصحة وراحة!"
        }
    ];

    steps.forEach((step, index) => {
        addRecipeStep(index, step.instruction, step.tip, index === 0);
    });
}

function addRecipeStep(stepNumber, instruction, tip, isActive = false) {
    const stepCard = document.createElement("div");
    stepCard.className = `step-card ${isActive ? "active" : ""}`;
    stepCard.id = `step-${stepNumber}`;
    
    stepCard.innerHTML = `
        <div>
            <span class="step-number">${stepNumber + 1}</span>
            <span style="font-weight: 600;">${instruction}</span>
            ${tip ? `<div class="step-tip">💡 ${tip}</div>` : ""}
        </div>
    `;
    
    recipeStepsContainer.appendChild(stepCard);
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
        
        // Update step overlay
        const instruction = stepCard.querySelector("span:nth-child(2)").textContent;
        stepOverlayText.textContent = instruction;
        stepOverlay.style.display = "block";
        
        setTimeout(() => {
            stepOverlay.style.display = "none";
        }, 8000);
    }
    
    currentStep = stepNumber;
}

function completeStep(stepNumber) {
    const stepCard = document.getElementById(`step-${stepNumber}`);
    if (stepCard) {
        stepCard.classList.add("completed");
        stepCard.classList.remove("active");
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
    
    timersContainer.appendChild(timerCard);
    timersSection.style.display = "block";
    
    activeTimers.push({ id: timerId, endTime, label });
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
            playNotificationSound();
            
            setTimeout(() => {
                const timerCard = document.getElementById(`timer-${timerId}`);
                if (timerCard) timerCard.remove();
                
                if (timersContainer.children.length === 0) {
                    timersSection.style.display = "none";
                }
            }, 5000);
        }
    }, 1000);
}

function showCulturalContext(text) {
    culturalText.textContent = text;
    culturalSection.style.display = "block";
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
        
        source.onended = () => {
            playNextAudio();
        };
        
        source.start();
        console.log(`Playing audio chunk, duration: ${audioBuffer.duration}s`);
    } catch (err) {
        console.error("Error playing audio:", err);
        playNextAudio();
    }
}

function triggerAssistant() {
    if (webSocket && webSocket.readyState === WebSocket.OPEN) {
        addChatMessage("Waiting for assistant response...", "system");
        
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

function playNotificationSound() {
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
