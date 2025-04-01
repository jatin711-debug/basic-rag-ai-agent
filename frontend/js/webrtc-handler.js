// webrtc-handler.js

class WebRTCHandler {
    constructor() {
        this.stream = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;

        // Callbacks
        this.onRecordingStart = null;
        this.onRecordingStop = null;
        this.onAudioData = null;
    }

    async setupMicrophone() {
        try {
            // Get user media permissions
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            return true;
        } catch (error) {
            console.error('Error accessing microphone:', error);
            return false;
        }
    }

    startRecording() {
        if (!this.stream) {
            console.error('No microphone access granted');
            return false;
        }

        this.audioChunks = [];
        this.mediaRecorder = new MediaRecorder(this.stream);

        this.mediaRecorder.addEventListener('dataavailable', event => {
            if (event.data.size > 0) {
                this.audioChunks.push(event.data);
            }
        });

        this.mediaRecorder.addEventListener('start', () => {
            this.isRecording = true;
            if (this.onRecordingStart) this.onRecordingStart();
        });

        this.mediaRecorder.addEventListener('stop', async () => {
            this.isRecording = false;
            
            // Create audio blob and convert to base64
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
            
            // Convert to base64
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = () => {
                const base64data = reader.result.split(',')[1]; // Remove the data URL prefix
                
                if (this.onAudioData) {
                    this.onAudioData(base64data);
                }
            };
            
            if (this.onRecordingStop) this.onRecordingStop();
        });

        // Start recording
        this.mediaRecorder.start();
        return true;
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            return true;
        }
        return false;
    }

    cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }
}

// Export the handler
window.WebRTCHandler = WebRTCHandler;