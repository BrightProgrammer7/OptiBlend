class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        
        if (input && input.length > 0) {
            const inputChannel = input[0];
            
            if (inputChannel && inputChannel.length > 0) {
                // Convert Float32 to Int16 PCM
                const pcmData = new Int16Array(inputChannel.length);
                for (let i = 0; i < inputChannel.length; i++) {
                    // Clamp and convert to 16-bit PCM
                    const s = Math.max(-1, Math.min(1, inputChannel[i]));
                    pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }
                
                // Send PCM data to main thread
                this.port.postMessage(pcmData);
            }
        }
        
        return true;
    }
}

registerProcessor('pcm-processor', PCMProcessor);