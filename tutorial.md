# Text-to-Speech Application with Dia-1.6B

Dia-1.6B is a text-to-speech model by Nari Labs, known for its natural voice modulation and expressive intonation. This tutorial will guide you through building a full-stack TTS application using Dia-1.6B with a FastAPI backend, a Svelte frontend, and deployment on Koyeb.

![Text-to-Speech App Demo](assets/demo.png)

## Steps 
- Demo
- Project structure
- Deployment
- Local Setup
- Truble shootingH
- Summary

## Demo

Experience the app in action:

![Text-to-Speech App Demo](assets/demo_screen_recording.gif)

### Example Prompt:

* **Speaker 1:** I could really use a French coffee right now.
* **Speaker 2:** Oh! I found this charming French café around the corner. So authentic!
* **Speaker 1:** Really? Do they have fresh pastries?
* **Speaker 2:** Yes! Their chocolate croissants are amazing! And the owner is from Paris. *(humming)*

#### Generation Parameters:

Default settings were used except for `Max New Tokens`, which was set to 2020.

[Click here to listen to the generated audio](assets/demo_audio.wav)

<audio controls>
  <source src="assets/demo_audio.wav" type="audio/wav">
  Your browser does not support the audio element.
</audio>

---

## Project Structure

The project consists of two main directories:

* **`backend/`:** Contains the FastAPI server and Dia model implementation.
* **`frontend/`:** Contains the Svelte frontend application.

---

## Deploy on Koyeb

### Requirements

Before deploying the app, ensure you have:

* A [Koyeb](https://www.koyeb.com) account.
* The [Koyeb CLI](https://www.koyeb.com/docs/cli) installed for command-line interaction.

### Backend Deployment

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=text-to-voice-backend&repository=minettekaum%2Ftext_to_voice&branch=main&workdir=backend&builder=dockerfile&instance_type=gpu-nvidia-a100&regions=na&hc_grace_period%5B8000%5D=300&hc_restart_limit%5B8000%5D=1&hc_timeout%5B8000%5D=300)

### Frontend Deployment

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=text-to-voice-frontend&repository=minettekaum%2Ftext_to_voice&branch=main&workdir=frontend&builder=dockerfile&regions=par&ports=4173%3Bhttp%3B%2F&hc_protocol%5B4173%5D=tcp&hc_grace_period%5B4173%5D=5&hc_interval%5B4173%5D=30&hc_restart_limit%5B4173%5D=3&hc_timeout%5B4173%5D=5&hc_path%5B4173%5D=%2F&hc_method%5B4173%5D=get)

---

## Local Setup

### Prerequisites

- Python 3.6 - 3.10
- Node.js 16+
- pnpm
- uv (Python package installer)

### Step 1: Backend Setup

1. **Clone the repository and navigate to the backend directory:**

   ```bash
   git clone https://github.com/minettekaum/text_to_voice.git
   cd text_to_voice/backend
   uv sync
   ```

2. **Run the backend server:**

   ```bash
   uv run fastapi dev main.py
   ```

The `backend/` directory includes a `dia` folder with a trimmed-down version of the Dia model from [Nari Labs](https://github.com/nari-labs/dia.git). This approach avoids loading unnecessary components.

You can optimise the model for faster inference using Pruna AI. Follow this [tutorial](https://www.koyeb.com/tutorials/deploy-flux-models-with-pruna-ai-for-8x-faster-inference-on-koyeb) for guidance.

---

### Step 2: Frontend Setup

1. **Navigate to the frontend directory:**

   ```bash
   cd frontend
   ```

2. **Install dependencies:**

   ```bash
   pnpm install
   ```

3. **Start the development server:**

   ```bash
   pnpm run dev
   ```

The frontend uses SvelteKit with a modular component architecture:

#### Core Components:

* **`ChatInterface.svelte`:** Manages message display, input handling, and speaker selection.
* **`GenerationSettings.svelte`:** Provides controls for AI model parameters with tooltips.
* **`SoundEffectsPanel.svelte`:** Allows sound effect selection and includes example dialogues.
* **`AudioControls.svelte`:** Handles audio recording, file uploads, and playback.
* **`GenerationButton.svelte`:** Facilitates TTS generation and communicates with the backend.
* **`AudioOutput.svelte`:** Displays playback and download options for generated audio.

---

### Deployment on Koyeb

Deploy the app using the Koyeb control panel or the [CLI](https://www.koyeb.com/docs/build-and-deploy/cli/installation).

### CLI Deployment Commands

#### Backend:

```bash
koyeb deploy . text_to_voice/backend \
   --instance-type gpu-nvidia-A100 \
   --region na \
   --type web \
   --port 8000:http \
   --archive-builder
```

#### Frontend:

```bash
koyeb deploy . text_to_voice/frontend \
   --instance-type nano \
   --region na \
   --type web \
   --port 4173:http \
   --archive-builder
```

---

## Troubleshooting

### Backend Issues:

* Ensure the Dia model loads correctly and verify environment variables.
* Check permissions for audio file handling.

### Frontend Issues:

* Verify API endpoint configurations and CORS settings.

### Deployment Issues:

* Inspect Docker image build logs for errors.
* Review Koyeb logs for networking and configuration issues.

For further assistance, go to the [Koyeb Documentation](https://www.koyeb.com/docs).

## Summary
This tutorial has guided you through setting up the backend with FastAPI, creating an interactive frontend with SvelteKit, and deploying the application on Koyeb. You can now explore further customisation, optimise the model for better performance, or expand the app’s features.

For further assistance, go to the [Koyeb Documentation](https://www.koyeb.com/docs) and [Nari Labs](https://huggingface.co/nari-labs/Dia-1.6B).