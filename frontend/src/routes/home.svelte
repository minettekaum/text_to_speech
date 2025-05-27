<script lang="ts">
    let inputText = '';
    let audioUrl: string | null = null;
    let isProcessing = false;
    let selectedEffect = '';
    let error: string | null = null;

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
            const response = await fetch('http://localhost:8000/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: inputText })
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

            // Create a temporary audio element to verify the audio
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
</script>

<main class="container">
    <header>
        <h1>AI Text-to-Speech Generator</h1>
        <p class="subtitle">Transform your text to speech with Dia-1.6B model</p>
    </header>

    <section class="converter-section">
        <div class="input-container">
            <label for="text-input">Enter your text</label>
            <textarea
                id="text-input"
                bind:value={inputText}
                placeholder="Type or paste your text here..."
                rows="6"
            ></textarea>
        </div>

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

    .input-container {
        margin-bottom: 2rem;
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
    }
</style> 