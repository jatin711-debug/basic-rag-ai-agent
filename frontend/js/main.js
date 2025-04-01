// main.js

document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const startStopButton = document.getElementById('startStopButton');
    const statusElement = document.getElementById('status');
    const chatDisplay = document.getElementById('chatDisplay');
    const textQueryInput = document.getElementById('textQuery');
    const sendButton = document.getElementById('sendButton');

    // Initialize WebRTC handler and speech processor
    const webrtcHandler = new WebRTCHandler();
    const speechProcessor = new SpeechProcessor('/api/query');

    // Setup initial microphone access
    let microphoneReady = false;

    async function setupMicrophone() {
        microphoneReady = await webrtcHandler.setupMicrophone();
        if (!microphoneReady) {
            statusElement.textContent = 'Microphone access denied';
            startStopButton.disabled = true;
        }
    }

    // Initialize microphone
    setupMicrophone();

    // Handle recording events
    webrtcHandler.onRecordingStart = () => {
        startStopButton.classList.add('recording');
        startStopButton.querySelector('.text').textContent = 'Stop Recording';
        statusElement.textContent = 'Recording...';
    };

    webrtcHandler.onRecordingStop = () => {
        startStopButton.classList.remove('recording');
        startStopButton.querySelector('.text').textContent = 'Start Recording';
        statusElement.textContent = 'Processing...';
    };

    webrtcHandler.onAudioData = async (audioData) => {
        try {
            addMessageToChat('Sending audio...', 'user');

            // Process the audio
            const response = await speechProcessor.processAudio(audioData);

            // Display the query and response
            addMessageToChat(response.query, 'user');
            addMessageToChat(response.text_response, 'assistant');

            // Play the audio response
            statusElement.textContent = 'Playing response...';
            await speechProcessor.playAudioResponse(response.audio_response);
            statusElement.textContent = 'Ready';
        } catch (error) {
            console.error('Error processing speech:', error);
            statusElement.textContent = 'Error processing speech';
            addMessageToChat('Sorry, there was an error processing your request.', 'assistant');
        }
    };

    // Recording button event
    startStopButton.addEventListener('click', () => {
        if (!microphoneReady) {
            setupMicrophone();
            return;
        }

        if (webrtcHandler.isRecording) {
            webrtcHandler.stopRecording();
        } else {
            webrtcHandler.startRecording();
        }
    });

    // Text input event
    sendButton.addEventListener('click', async () => {
        sendTextQuery();
    });

    textQueryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendTextQuery();
        }
    });

    async function sendTextQuery() {
        const query = textQueryInput.value.trim();
        if (!query) return;

        try {
            addMessageToChat(query, 'user');
            textQueryInput.value = '';
            statusElement.textContent = 'Processing...';

            // Process the text query
            const response = await speechProcessor.processText(query);

            // Display the response
            addMessageToChat(response.text_response, 'assistant');

            // Play the audio response
            statusElement.textContent = 'Playing response...';
            await speechProcessor.playAudioResponse(response.audio_response);
            statusElement.textContent = 'Ready';
        } catch (error) {
            console.error('Error processing text query:', error);
            statusElement.textContent = 'Error processing query';
            addMessageToChat('Sorry, there was an error processing your request.', 'assistant');
        }
    }

    // Helper to add messages to the chat display
    function addMessageToChat(message, sender) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message');
        messageElement.classList.add(`${sender}-message`);
        messageElement.textContent = message;

        chatDisplay.appendChild(messageElement);
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
    }
});