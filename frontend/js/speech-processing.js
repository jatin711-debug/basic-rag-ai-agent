// speech-processing.js

class SpeechProcessor {
    constructor(apiEndpoint) {
        this.apiEndpoint = apiEndpoint || '/api/query';
    }

    async processAudio(audioBase64) {
        try {
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    audio: audioBase64
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error processing audio:', error);
            throw error;
        }
    }

    async processText(text) {
        try {
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: text
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error processing text query:', error);
            throw error;
        }
    }

    playAudioResponse(base64Audio) {
        return new Promise((resolve, reject) => {
            try {
                // Convert base64 to blob
                const byteCharacters = atob(base64Audio);
                const byteNumbers = new Array(byteCharacters.length);

                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }

                const byteArray = new Uint8Array(byteNumbers);
                const audioBlob = new Blob([byteArray], { type: 'audio/mp3' });

                // Create audio element and play
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);

                audio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                    resolve();
                };

                audio.onerror = (error) => {
                    URL.revokeObjectURL(audioUrl);
                    reject(error);
                };

                audio.play();
            } catch (error) {
                console.error('Error playing audio response:', error);
                reject(error);
            }
        });
    }
}

// Export the processor
window.SpeechProcessor = SpeechProcessor;