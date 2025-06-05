<script lang="ts">
    interface Message {
        speaker: string;
        text: string;
    }

    let messages: Message[] = [];
    let currentInput = '';
    let availableSpeakers: string[] = ['[S1]'];
    let selectedSpeaker = '[S1]';
    let maxSpeakerNumber = 1;  // Track the highest speaker number seen
    let inputText = '';
    let audioUrl: string | null = null;
    let isProcessing = false;
    let selectedEffect = '';
    let error: string | null = null;
    let isRecording = false;
    let mediaRecorder: MediaRecorder | null = null;
    let audioChunks: BlobPart[] = [];
    let recordedAudioUrl: string | null = null;
    let uploadedAudioUrl: string | null = null;

    // Generation parameters with correct ranges
    let maxNewTokens = 1024;  // Default middle value
    let cfgScale = 3.0;       // Default middle value
    let temperature = 1.2;    // Default middle value
    let topP = 0.9;          // Default middle value
    let cfgFilterTopK = 32;   // Default middle value
    let speedFactor = 0.9;    // Default middle value
    let showAdvancedSettings = false;

    let generationProgress = 0;
    let progressInterval: number;

    const soundEffects = [
        'applause',
        'beep',
        'burps',
        'chuckle',
        'claps',
        'clears throat',
        'coughs',
        'exhales',
        'gasps',
        'groans',
        'humming',
        'inhales',
        'laughs',
        'mumbles',
        'screams',
        'sighs',
        'sings',
        'singing',
        'sneezes',
        'sniffs',
        'whistles'
    ];

    function updateAvailableSpeakers() {
        if (messages.length === 0) {
            // First message
            availableSpeakers = ['[S1]'];
            selectedSpeaker = '[S1]';
            maxSpeakerNumber = 1;
            return;
        }

        const lastMessage = messages[messages.length - 1];
        const lastSpeaker = lastMessage.speaker;

        if (messages.length === 1 && lastSpeaker === '[S1]') {
            // After first S1 message
            availableSpeakers = ['[S1]', '[S2]'];
            maxSpeakerNumber = 2;
            selectedSpeaker = availableSpeakers[0];
            return;
        }

        if (messages.length === 2 && messages[0].speaker === '[S1]') {
            if (lastSpeaker === '[S1]') {
                // S1 -> S1 pattern
                availableSpeakers = ['[S1]', '[S2]'];
                maxSpeakerNumber = 2;
            } else if (lastSpeaker === '[S2]') {
                // S1 -> S2 pattern
                availableSpeakers = ['[S1]', '[S2]', '[S3]'];
                maxSpeakerNumber = 3;
            }
            selectedSpeaker = availableSpeakers[0];
            return;
        }

        // For all subsequent messages, maintain the highest speaker number seen
        const lastSpeakerNum = parseInt(lastSpeaker.match(/\d+/)[0]);
        
        if (lastSpeaker === '[S2]' && maxSpeakerNumber < 3) {
            maxSpeakerNumber = 3;  // Introduce S3
        } else if (lastSpeaker === '[S3]' && maxSpeakerNumber < 4) {
            maxSpeakerNumber = 4;  // Introduce S4
        }

        // Create array of all speakers up to maxSpeakerNumber
        availableSpeakers = Array.from(
            { length: maxSpeakerNumber }, 
            (_, i) => `[S${i + 1}]`
        );
        
        selectedSpeaker = availableSpeakers[0];
    }

    function addMessage() {
        if (currentInput.trim()) {
            messages = [...messages, { speaker: selectedSpeaker, text: currentInput.trim() }];
            currentInput = '';
            updateAvailableSpeakers();
        }
    }

    function handleKeyPress(event: KeyboardEvent) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            addMessage();
        }
    }

    function insertSoundEffect() {
        if (selectedEffect) {
            const effect = `(${selectedEffect})`;
            currentInput = currentInput + (currentInput.endsWith(' ') ? '' : ' ') + effect + ' ';
            selectedEffect = '';
        }
    }

    async function handleGenerate() {
        if (messages.length === 0) return;
        
        isProcessing = true;
        generationProgress = 0;
        error = null;
        
        try {
            // Start progress simulation
            progressInterval = setInterval(() => {
                if (generationProgress < 90) {
                    generationProgress += Math.random() * 15;
                    if (generationProgress > 90) generationProgress = 90;
                }
            }, 300);

            // Combine all messages into a single text, maintaining speaker labels
            const combinedText = messages.map(msg => `${msg.speaker}: ${msg.text}`).join('\n');
            
            // First, prepare the form data
            const formData = new FormData();
            formData.append('text', combinedText);
            
            // Add all generation parameters
            formData.append('max_new_tokens', maxNewTokens.toString());
            formData.append('cfg_scale', cfgScale.toString());
            formData.append('temperature', temperature.toString());
            formData.append('top_p', topP.toString());
            formData.append('cfg_filter_top_k', cfgFilterTopK.toString());
            formData.append('speed_factor', speedFactor.toString());
            
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

            // Set progress to 100% when generation is complete
            generationProgress = 100;
            
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
            clearInterval(progressInterval);
            setTimeout(() => {
                isProcessing = false;
                generationProgress = 0;
            }, 500); // Keep 100% visible briefly
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
                <div class="text-input-frame">
                    <div class="frame-header">
                        <h3>Chat Interface</h3>
                        <p class="helper-text">Type messages for different speakers to generate conversation</p>
                    </div>
                    <div class="message-area">
                        {#each messages as message}
                            <div class="message">
                                <span class="speaker-label" data-speaker={message.speaker}>{message.speaker}</span>
                                <p class="message-text">{message.text}</p>
                            </div>
                        {/each}
                    </div>
                    <div class="input-area">
                        <div class="input-container">
                            <select 
                                bind:value={selectedSpeaker}
                                class="speaker-select"
                            >
                                {#each availableSpeakers as speaker}
                                    <option value={speaker}>{speaker}</option>
                                {/each}
                            </select>
                            <textarea
                                bind:value={currentInput}
                                placeholder="Type your message..."
                                rows="1"
                                on:keydown={handleKeyPress}
                            ></textarea>
                            <button 
                                class="send-button"
                                on:click={addMessage}
                                disabled={!currentInput.trim()}
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <line x1="22" y1="2" x2="11" y2="13"></line>
                                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                                </svg>
                            </button>
                        </div>
                        <div class="effect-controls">
                            <select
                                id="effect-select"
                                bind:value={selectedEffect}
                                class="effect-select"
                                on:change={insertSoundEffect}
                            >
                                <option value="">Add sound effect...</option>
                                {#each soundEffects as effect}
                                    <option value={effect}>{effect}</option>
                                {/each}
                            </select>
                        </div>
                    </div>
                </div>

                <div class="audio-input-section">
                    <h3>Reference Audio (optional)</h3>
                    <div class="audio-controls">
                        <div class="audio-button-group">
                            <label class="audio-button" for="audio-file" title="Upload Audio">
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                    <polyline points="17 8 12 3 7 8"/>
                                    <line x1="12" y1="3" x2="12" y2="15"/>
                                </svg>
                                <input
                                    type="file"
                                    id="audio-file"
                                    accept="audio/mp3,audio/mpeg"
                                    on:change={handleFileUpload}
                                    class="hidden-input"
                                />
                            </label>

                            {#if isRecording}
                                <button 
                                    class="audio-button recording"
                                    on:click={stopRecording}
                                    title="Stop Recording"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <rect x="6" y="6" width="12" height="12" rx="2"/>
                                    </svg>
                                </button>
                            {:else}
                                <button 
                                    class="audio-button"
                                    on:click={startRecording}
                                    title="Start Recording"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
                                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                                        <line x1="12" y1="19" x2="12" y2="22"/>
                                    </svg>
                                </button>
                            {/if}
                        </div>

                        {#if uploadedAudioUrl || recordedAudioUrl}
                            <div class="audio-preview">
                                <audio controls src={uploadedAudioUrl || recordedAudioUrl}>
                                    Your browser does not support the audio element.
                                </audio>
                            </div>
                        {/if}
                    </div>
                </div>
            </div>

            <div class="side-controls">
                <div class="generation-settings">
                    <h3>Generation Settings</h3>
                    <div class="settings-panel">
                        <div class="parameter-control">
                            <label for="max-tokens">
                                Max New Tokens ({maxNewTokens})
                                <div class="tooltip-container">
                                    <div class="tooltip-trigger" on:mouseenter={(e) => {
                                        const tooltip = e.currentTarget.nextElementSibling;
                                        const rect = e.currentTarget.getBoundingClientRect();
                                        tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
                                        tooltip.style.left = (rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)) + 'px';
                                    }}>?</div>
                                    <div class="tooltip">Controls the maximum length of generated audio. Higher values allow for longer audio.</div>
                                </div>
                            </label>
                            <input 
                                type="range" 
                                id="max-tokens"
                                bind:value={maxNewTokens}
                                min="860"
                                max="3072"
                                step="1"
                            />
                        </div>

                        <div class="parameter-control">
                            <label for="cfg-scale">
                                CFG Scale ({cfgScale})
                                <div class="tooltip-container">
                                    <div class="tooltip-trigger" on:mouseenter={(e) => {
                                        const tooltip = e.currentTarget.nextElementSibling;
                                        const rect = e.currentTarget.getBoundingClientRect();
                                        tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
                                        tooltip.style.left = (rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)) + 'px';
                                    }}>?</div>
                                    <div class="tooltip">Controls how closely to follow the prompt. Higher values produce more faithful but potentially less natural output.</div>
                                </div>
                            </label>
                            <input 
                                type="range" 
                                id="cfg-scale"
                                bind:value={cfgScale}
                                min="1"
                                max="5"
                                step="0.1"
                            />
                        </div>

                        <div class="parameter-control">
                            <label for="temperature">
                                Temperature ({temperature})
                                <div class="tooltip-container">
                                    <div class="tooltip-trigger" on:mouseenter={(e) => {
                                        const tooltip = e.currentTarget.nextElementSibling;
                                        const rect = e.currentTarget.getBoundingClientRect();
                                        tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
                                        tooltip.style.left = (rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)) + 'px';
                                    }}>?</div>
                                    <div class="tooltip">Controls randomness in generation. Higher values produce more varied but potentially less consistent output.</div>
                                </div>
                            </label>
                            <input 
                                type="range" 
                                id="temperature"
                                bind:value={temperature}
                                min="1"
                                max="1.5"
                                step="0.1"
                            />
                        </div>

                        <div class="parameter-control">
                            <label for="top-p">
                                Top P ({topP})
                                <div class="tooltip-container">
                                    <div class="tooltip-trigger" on:mouseenter={(e) => {
                                        const tooltip = e.currentTarget.nextElementSibling;
                                        const rect = e.currentTarget.getBoundingClientRect();
                                        tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
                                        tooltip.style.left = (rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)) + 'px';
                                    }}>?</div>
                                    <div class="tooltip">Controls diversity in sampling. Higher values allow for more diverse outputs.</div>
                                </div>
                            </label>
                            <input 
                                type="range" 
                                id="top-p"
                                bind:value={topP}
                                min="0.8"
                                max="1"
                                step="0.01"
                            />
                        </div>

                        <div class="parameter-control">
                            <label for="cfg-filter-top-k">
                                CFG Filter Top K ({cfgFilterTopK})
                                <div class="tooltip-container">
                                    <div class="tooltip-trigger" on:mouseenter={(e) => {
                                        const tooltip = e.currentTarget.nextElementSibling;
                                        const rect = e.currentTarget.getBoundingClientRect();
                                        tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
                                        tooltip.style.left = (rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)) + 'px';
                                    }}>?</div>
                                    <div class="tooltip">Controls the number of top tokens to consider during generation. Higher values allow for more variety.</div>
                                </div>
                            </label>
                            <input 
                                type="range" 
                                id="cfg-filter-top-k"
                                bind:value={cfgFilterTopK}
                                min="15"
                                max="50"
                                step="1"
                            />
                        </div>

                        <div class="parameter-control">
                            <label for="speed-factor">
                                Speed Factor ({speedFactor})
                                <div class="tooltip-container">
                                    <div class="tooltip-trigger" on:mouseenter={(e) => {
                                        const tooltip = e.currentTarget.nextElementSibling;
                                        const rect = e.currentTarget.getBoundingClientRect();
                                        tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
                                        tooltip.style.left = (rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)) + 'px';
                                    }}>?</div>
                                    <div class="tooltip">Controls the speed of generated speech. Higher values produce faster speech.</div>
                                </div>
                            </label>
                            <input 
                                type="range" 
                                id="speed-factor"
                                bind:value={speedFactor}
                                min="0.8"
                                max="1"
                                step="0.01"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="controls">
            <button
                class="generate-button"
                class:processing={isProcessing}
                on:click={handleGenerate}
                disabled={!messages.length || isProcessing}
            >
                <span class="button-text">
                    {#if isProcessing}
                        Generating... {Math.round(generationProgress)}%
                    {:else}
                        Generate Audio
                    {/if}
                </span>
                {#if isProcessing}
                    <div class="progress-bar" style="width: {generationProgress}%"></div>
                {/if}
            </button>
        </div>

        <div class="output-container">
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
    :global(body) {
        background-color: white;
        color: #333;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .container {
        max-width: 1400px;
        margin: 0 auto;
        padding: 2.5rem;
    }

    header {
        text-align: center;
        margin-bottom: 3.5rem;
    }

    h1 {
        font-size: 2.2rem;
        color: #333;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }

    .subtitle {
        font-size: 1.1rem;
        color: #666;
    }

    .converter-section {
        background: white;
        border-radius: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        padding: 2rem;
    }

    .main-input-container {
        display: grid;
        grid-template-columns: minmax(300px, 2fr) minmax(250px, 1fr);
        gap: 2rem;
        margin-bottom: 2rem;
        align-items: start;
    }

    .text-input-section {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .text-input-frame {
        background: #fcfcfc;
        border-radius: 16px;
        padding: 1rem;
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 260px;
        border: 1px solid #e5e7eb;
    }

    .frame-header {
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #eee;
        margin-bottom: 0.35rem;
    }

    .frame-header h3 {
        font-size: 0.9rem;
        margin: 0 0 0.35rem 0;
    }

    .helper-text {
        font-size: 0.8rem;
    }

    .message-area {
        flex: 1;
        min-height: 150px;
        max-height: 150px;
        overflow-y: auto;
        padding: 0.35rem 0;
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
    }

    .message {
        display: flex;
        gap: 0.4rem;
        align-items: flex-start;
        animation: fadeIn 0.3s ease;
        padding: 0.25rem;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .speaker-label {
        padding: 0.4rem 0.6rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
        white-space: nowrap;
        color: white;
    }

    /* Speaker colors */
    .speaker-label[data-speaker="[S1]"] {
        background: #6366f1; /* Indigo */
    }

    .speaker-label[data-speaker="[S2]"] {
        background: #ec4899; /* Pink */
    }

    .speaker-label[data-speaker="[S3]"] {
        background: #14b8a6; /* Teal */
    }

    .speaker-label[data-speaker="[S4]"] {
        background: #f59e0b; /* Amber */
    }

    /* Dropdown colors matching speakers */
    .speaker-select option[value="[S1]"] {
        color: #6366f1;
    }

    .speaker-select option[value="[S2]"] {
        color: #ec4899;
    }

    .speaker-select option[value="[S3]"] {
        color: #14b8a6;
    }

    .speaker-select option[value="[S4]"] {
        color: #f59e0b;
    }

    .message-text {
        margin: 0;
        padding: 0.35rem 0.5rem;
        background: #f5f5f5;
        border-radius: 8px;
        font-size: 0.9rem;
        line-height: 1.3;
        flex: 1;
    }

    .input-area {
        margin-top: auto;
        padding-top: 0.5rem;
        border-top: 1px solid #eee;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .input-container {
        display: flex;
        gap: 0.5rem;
        align-items: flex-end;
        background: white;
        border: 1px solid #eee;
        border-radius: 12px;
        padding: 0.5rem;
    }

    .speaker-select {
        width: 70px;
        padding: 0.4rem;
        border: none;
        background: #f5f5f5;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #666;
        cursor: pointer;
        transition: all 0.2s ease;
        -webkit-appearance: none;
        -moz-appearance: none;
        appearance: none;
        background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23666%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E");
        background-repeat: no-repeat;
        background-position: right 0.5rem center;
        background-size: 0.65em auto;
        padding-right: 1.5rem;
    }

    .speaker-select:hover {
        background-color: #efefef;
        color: #333;
    }

    textarea {
        flex: 1;
        padding: 0.5rem;
        border: none;
        border-radius: 8px;
        font-size: 0.95rem;
        resize: none;
        transition: all 0.2s ease;
        background: transparent;
        min-height: 20px;
        max-height: 120px;
        line-height: 1.4;
    }

    textarea:focus {
        outline: none;
        background: transparent;
    }

    .send-button {
        background: #333;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .send-button:hover:not(:disabled) {
        background: #222;
        transform: translateY(-1px);
    }

    .send-button:disabled {
        background: #ddd;
        cursor: not-allowed;
    }

    .audio-input-section {
        background: #fcfcfc;
        border-radius: 16px;
        padding: 1rem;
    }

    .audio-input-section h3 {
        font-size: 0.9rem;
        margin: 0 0 0.75rem 0;
        font-weight: 500;
    }

    .audio-controls {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .audio-button-group {
        display: flex;
        gap: 2.5rem;
        justify-content: center;
        margin-left: 2rem;
    }

    .audio-button {
        width: 130px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: white;
        border: 1px solid #eee;
        border-radius: 8px;
        color: #666;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .audio-button:hover {
        background: #f5f5f5;
        color: #333;
    }

    .audio-button.recording {
        background: #fee2e2;
        border-color: #fecaca;
        color: #dc2626;
    }

    .hidden-input {
        display: none;
    }

    .audio-preview {
        background: white;
        border: 1px solid #eee;
        border-radius: 8px;
        padding: 0.25rem;
    }

    .audio-preview audio {
        width: 100%;
        height: 36px;
        margin: 0;
    }

    .controls {
        padding: 0 0 2rem 0;
    }

    .generate-button {
        background: #333;
        color: white;
        padding: 1.25rem;
        border: none;
        border-radius: 12px;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.2s ease;
        width: 100%;
        font-weight: 500;
        letter-spacing: 0.02em;
        position: relative;
        overflow: hidden;
    }

    .generate-button:hover:not(:disabled) {
        background: #222;
        transform: translateY(-1px);
    }

    .generate-button:disabled:not(.processing) {
        background: #ddd;
        cursor: not-allowed;
    }

    .generate-button.processing {
        cursor: wait;
    }

    .progress-bar {
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        background: #222;
        transition: width 0.3s ease;
        z-index: 1;
    }

    .button-text {
        position: relative;
        z-index: 2;
    }

    .output-container {
        padding: 0;
    }

    .output-audio {
        background: #fcfcfc;
        border-radius: 16px;
        padding: 1rem;
        min-height: 60px;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    audio {
        width: 100%;
        max-width: 500px;
        height: 36px;
    }

    .error-message {
        color: #e53e3e;
        font-weight: 500;
        margin: 0;
        font-size: 0.9rem;
    }

    .placeholder-text {
        color: #666;
        margin: 0;
        font-size: 0.9rem;
    }

    .sound-effects-section {
        display: none;
    }

    .effect-controls {
        display: flex;
        padding: 0;
    }

    .effect-select {
        width: 100%;
        padding: 0.4rem;
        border: none;
        background: #f5f5f5;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #666;
        cursor: pointer;
        transition: all 0.2s ease;
        -webkit-appearance: none;
        -moz-appearance: none;
        appearance: none;
        background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23666%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E");
        background-repeat: no-repeat;
        background-position: right 0.5rem center;
        background-size: 0.65em auto;
        padding-right: 1.5rem;
    }

    .effect-select:hover {
        background-color: #efefef;
        color: #333;
    }

    .effect-select:focus {
        outline: none;
        border-color: #333;
        color: #333;
    }

    .effect-button {
        display: none;
    }

    .generation-settings {
        background: #fcfcfc;
        border-radius: 16px;
        padding: 1rem;
        position: sticky;
        top: 2rem;
        height: calc(260px + 0.5rem + 180px); /* Increased audio section height estimate further */
        display: flex;
        flex-direction: column;
    }

    .settings-panel {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        flex: 1;
        padding-right: 0.25rem;
        overflow: visible;
        position: relative;
    }

    .parameter-control {
        margin-bottom: 0;
        flex-shrink: 0;
        padding: 0.5rem 0;
        position: relative;
    }

    .parameter-control label {
        font-size: 0.85rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .tooltip-container {
        position: relative;
        display: inline-block;
    }

    .tooltip-trigger {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #eee;
        color: #666;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        cursor: help;
        transition: all 0.2s ease;
    }

    .tooltip-trigger:hover {
        background: #e0e0e0;
        color: #333;
    }

    .tooltip {
        display: none;
        position: fixed;
        background: #333;
        color: white;
        padding: 0.6rem 0.8rem;
        border-radius: 8px;
        font-size: 0.85rem;
        width: 220px;
        z-index: 1000;
        pointer-events: none;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    .tooltip-trigger:hover + .tooltip {
        display: block;
    }

    .generation-settings h3 {
        font-size: 0.9rem;
        margin: 0 0 1.5rem 0;
        font-weight: 500;
    }

    .parameter-control input[type="range"] {
        width: 100%;
        height: 2px;
        background: #eee;
        border-radius: 1px;
        outline: none;
        -webkit-appearance: none;
    }

    .parameter-control input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none;
        width: 14px;
        height: 14px;
        background: #333;
        border-radius: 50%;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .parameter-control input[type="range"]::-webkit-slider-thumb:hover {
        transform: scale(1.2);
    }

    .side-controls {
        display: flex;
        flex-direction: column;
    }

    @media (max-width: 1200px) {
        .main-input-container {
            grid-template-columns: minmax(300px, 1.5fr) minmax(250px, 1fr);
            gap: 2rem;
        }
    }

    @media (max-width: 900px) {
        .container {
            padding: 1.5rem;
        }
        
        .converter-section {
            padding: 1.5rem;
        }

        .main-input-container {
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }

        .text-input-section,
        .side-controls {
            position: static;
            width: auto;
            grid-column: 1;
            justify-self: stretch;
        }
    }

    @media (max-height: 900px) {
        .message-area {
            max-height: 150px;
        }
    }

    @media (max-height: 700px) {
        .message-area {
            max-height: 150px;
        }
    }
</style> 