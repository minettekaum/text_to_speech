<script lang="ts">
    let inputText = '';
    let referenceText = '';
    let audioUrl: string | null = null;
    let isProcessing = false;
    let selectedEffect = '';
    let error: string | null = null;
    let isRecording = false;
    let mediaRecorder: MediaRecorder | null = null;
    let audioChunks: BlobPart[] = [];
    let recordedAudioUrl: string | null = null;
    let uploadedAudioUrl: string | null = null;

    const soundEffects = [
        'laughs', 'clears throat', 'sighs', 'gasps', 'coughs',
        'singing', 'sings', 'mumbles', 'beep', 'groans',
        'sniffs', 'claps', 'screams', 'inhales', 'exhales',
        'applause', 'burps', 'humming', 'sneezes', 'chuckle',
        'whistles'
    ];

    function insertSoundEffect() {
        if (selectedEffect) {
            const effect = `(${selectedEffect})`;
            inputText = inputText + (inputText.endsWith(' ') ? '' : ' ') + effect + ' ';
            selectedEffect = '';
        }
    }

    async function handleGenerate() {
        isProcessing = true;
        error = null;
        
        try {
            // First, prepare the form data
            const formData = new FormData();
            formData.append('text', inputText);
            
            // Add reference text if available
            if (referenceText) {
                formData.append('reference_text', referenceText);
            }
            
            // Add audio file if available (either uploaded or recorded)
            if (uploadedAudioUrl) {
                const response = await fetch(uploadedAudioUrl);
                const blob = await response.blob();
                formData.append('audio', blob, 'reference.mp3');
            } else if (recordedAudioUrl) {
                const response = await fetch(recordedAudioUrl);
                const blob = await response.blob();
                formData.append('audio', blob, 'recorded.mp3');
            }

            const response = await fetch('http://localhost:8000/api/generate', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(errorData?.detail || 'Failed to generate audio');
            }

            const blob = await response.blob();
            if (blob.size === 0) {
                throw new Error('Generated audio is empty');
            }

            if (audioUrl) {
                URL.revokeObjectURL(audioUrl);
            }
            audioUrl = URL.createObjectURL(blob);

            const audioTest = new Audio(audioUrl);
            audioTest.onerror = () => {
                error = 'Error loading the generated audio';
                console.error('Audio loading error:', audioTest.error);
            };

        } catch (err) {
            console.error('Generation error:', err);
            error = err.message || 'Failed to generate audio. Please try again.';
            if (audioUrl) {
                URL.revokeObjectURL(audioUrl);
                audioUrl = null;
            }
        } finally {
            isProcessing = false;
        }
    }

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
                if (recordedAudioUrl) {
                    URL.revokeObjectURL(recordedAudioUrl);
                }
                recordedAudioUrl = URL.createObjectURL(audioBlob);
            };

            mediaRecorder.start();
            isRecording = true;
        } catch (err) {
            console.error('Recording error:', err);
            error = 'Failed to start recording. Please check your microphone permissions.';
        }
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            isRecording = false;
        }
    }

    function handleFileUpload(event: Event) {
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0];
        
        if (file) {
            if (file.type !== 'audio/mp3' && file.type !== 'audio/mpeg') {
                error = 'Please upload an MP3 file.';
                return;
            }

            if (uploadedAudioUrl) {
                URL.revokeObjectURL(uploadedAudioUrl);
            }
            uploadedAudioUrl = URL.createObjectURL(file);
            error = null;
        }
    }
</script>

<main class="container">
    <header>
        <h1>AI Text-to-Speech Generator</h1>
        <p class="subtitle">Transform your text to speech with Dia-1.6B model</p>
    </header>

    <section class="converter-section">
        <div class="main-input-container">
            <div class="text-input-section">
                <label for="text-input">Enter your text (required)</label>
                <textarea
                    id="text-input"
                    bind:value={inputText}
                    placeholder="Type or paste your text here..."
                    rows="6"
                ></textarea>

                <div class="sound-effects">
                    <label for="effect-select">Add Sound Effect</label>
                    <div class="effect-controls">
                        <select
                            id="effect-select"
                            bind:value={selectedEffect}
                            class="effect-select"
                        >
                            <option value="">Select a sound effect...</option>
                            {#each soundEffects as effect}
                                <option value={effect}>{effect}</option>
                            {/each}
                        </select>
                        <button
                            class="insert-button"
                            on:click={insertSoundEffect}
                            disabled={!selectedEffect}
                        >
                            Insert
                        </button>
                    </div>
                </div>
            </div>

            <div class="audio-input-section">
                <h3>Reference Audio (optional)</h3>
                <p class="helper-text">Upload or record a reference voice to influence the output style</p>
                
                <div class="reference-text">
                    <label for="reference-text">Reference Text (required if using reference audio)</label>
                    <textarea
                        id="reference-text"
                        bind:value={referenceText}
                        placeholder="Enter the exact transcript of your reference audio..."
                        rows="3"
                    ></textarea>
                </div>

                <div class="audio-upload">
                    <label for="audio-file">Upload MP3 File</label>
                    <input
                        type="file"
                        id="audio-file"
                        accept="audio/mp3,audio/mpeg"
                        on:change={handleFileUpload}
                    />
                    {#if uploadedAudioUrl}
                        <audio controls src={uploadedAudioUrl}>
                            Your browser does not support the audio element.
                        </audio>
                    {/if}
                </div>

                <div class="audio-record">
                    <label for="record-audio">Record Reference Audio</label>
                    <div class="record-controls">
                        {#if isRecording}
                            <button 
                                id="record-audio"
                                class="stop-button" 
                                on:click={stopRecording}
                            >
                                Stop Recording
                            </button>
                        {:else}
                            <button 
                                id="record-audio"
                                class="record-button" 
                                on:click={startRecording}
                            >
                                Start Recording
                            </button>
                        {/if}
                    </div>
                    {#if recordedAudioUrl}
                        <audio controls src={recordedAudioUrl}>
                            Your browser does not support the audio element.
                        </audio>
                    {/if}
                </div>
            </div>
        </div>

        <div class="controls">
            <button
                class="generate-button"
                on:click={handleGenerate}
                disabled={!inputText || isProcessing}
            >
                {#if isProcessing}
                    Generating...
                {:else}
                    Generate Audio
                {/if}
            </button>
        </div>

        <div class="output-container">
            <h2>Generated Audio</h2>
            <div class="output-audio">
                {#if error}
                    <p class="error-message">{error}</p>
                {:else if audioUrl}
                    <audio controls src={audioUrl}>
                        Your browser does not support the audio element.
                    </audio>
                {:else}
                    <p class="placeholder-text">Your generated audio will appear here</p>
                {/if}
            </div>
        </div>
    </section>
</main>

<style>
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
    }

    header {
        text-align: center;
        margin-bottom: 3rem;
    }

    h1 {
        font-size: 2.5rem;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }

    .subtitle {
        font-size: 1.2rem;
        color: #666;
    }

    .converter-section {
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 2rem;
    }

    .main-input-container {
        display: grid;
        grid-template-columns: 3fr 2fr;
        gap: 2rem;
        margin-bottom: 2rem;
    }

    .text-input-section {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .audio-input-section {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1.5rem;
        border: 2px dashed #e2e8f0;
    }

    .audio-input-section h3 {
        margin: 0;
        color: #2d3748;
        font-size: 1.2rem;
    }

    .helper-text {
        color: #718096;
        font-size: 0.9rem;
        margin: 0.5rem 0 1.5rem 0;
    }

    .audio-upload, .audio-record {
        background: white;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }

    label {
        display: block;
        font-size: 1.1rem;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }

    textarea {
        width: 100%;
        padding: 1rem;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        font-size: 1rem;
        resize: vertical;
        transition: border-color 0.2s;
    }

    textarea:focus {
        outline: none;
        border-color: #4299e1;
    }

    .controls {
        display: flex;
        justify-content: center;
        margin: 2rem 0;
    }

    .generate-button {
        background-color: #4299e1;
        color: white;
        padding: 0.8rem 2rem;
        border: none;
        border-radius: 8px;
        font-size: 1.1rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    .generate-button:hover:not(:disabled) {
        background-color: #3182ce;
    }

    .generate-button:disabled {
        background-color: #a0aec0;
        cursor: not-allowed;
    }

    .output-container {
        margin-top: 2rem;
        padding-top: 2rem;
        border-top: 2px solid #e2e8f0;
    }

    h2 {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-bottom: 1rem;
    }

    .output-audio {
        background: #f7fafc;
        border-radius: 8px;
        padding: 2rem;
        min-height: 100px;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    audio {
        width: 100%;
        max-width: 500px;
    }

    .error-message {
        color: #dc3545;
        font-weight: 500;
    }

    .placeholder-text {
        color: #718096;
        font-style: italic;
    }

    .sound-effects {
        margin-bottom: 2rem;
    }

    .effect-controls {
        display: flex;
        gap: 1rem;
        margin-top: 0.5rem;
    }

    .effect-select {
        flex: 1;
        padding: 0.8rem;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        font-size: 1rem;
        background-color: white;
        cursor: pointer;
        transition: border-color 0.2s;
    }

    .effect-select:focus {
        outline: none;
        border-color: #4299e1;
    }

    .insert-button {
        padding: 0.8rem 1.5rem;
        background-color: #48bb78;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 1rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    .insert-button:hover:not(:disabled) {
        background-color: #38a169;
    }

    .insert-button:disabled {
        background-color: #a0aec0;
        cursor: not-allowed;
    }

    .reference-text {
        margin-bottom: 1.5rem;
        background: white;
        border-radius: 8px;
        padding: 1.2rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }

    .reference-text textarea {
        width: 100%;
        padding: 0.8rem;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        font-size: 0.9rem;
        resize: vertical;
        transition: border-color 0.2s;
    }

    .reference-text textarea:focus {
        outline: none;
        border-color: #4299e1;
    }

    @media (max-width: 768px) {
        .container {
            padding: 1rem;
        }

        h1 {
            font-size: 2rem;
        }

        .converter-section {
            padding: 1rem;
        }

        .main-input-container {
            grid-template-columns: 1fr;
        }

        .audio-input-section {
            margin-top: 1rem;
        }
    }
</style> 