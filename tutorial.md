# Text-to-Speech Application with Dia-1.6B

Dia-1.6B is a text-to-speech model by Nari Labs, known for its natural voice modulation and expressive intonation. This tutorial will guide you through building a full-stack TTS application using Dia-1.6B with a FastAPI backend, a Svelte frontend, and deployment on Koyeb.

![Text-to-Speech App Demo](assets/demo.png)

## Demo

Here is a demo of the app

![Text-to-Speech App Demo](assets/demo_screen_recording.gif)

The prompt was: 
- Speaker 1: I could really use a French coffee right now.
- Speaker 2: Oh! I found this charming French café around the corner. So authentic!
- Speaker 1: Really? Do they have fresh pastries?
- Speaker 2: 'Yes! Their chocolate croissants are amazing! And the owner is from Paris (humming)

And the generation parameters were default except the `Max New Tokens` was set to 2020.

Here you can find the [generated audio](assets/demo_audio.wav) 


## Project Structure

The project consists of two directories:
- `backend/`: Contains the FastAPI server and Dia model implementation
- `frontend/`: Contains the Svelte frontend application

## Deploy on Koyeb and play around

### Requirements 
To be able to run the app, you'll need a Koyeb account 
- A Koyeb account to deploy the application
- The Koyeb CLI is installed to interact with Koyeb from the command line
### Backend
[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=text-to-voice-backend&repository=minettekaum%2Ftext_to_voice&branch=main&workdir=backend&builder=dockerfile&instance_type=gpu-nvidia-a100&regions=na&hc_grace_period%5B8000%5D=300&hc_restart_limit%5B8000%5D=1&hc_timeout%5B8000%5D=300)

Remember to start the backend before the frontend. 
### Frontend 
[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=text-to-voice-frontend&repository=minettekaum%2Ftext_to_voice&branch=main&workdir=frontend&builder=dockerfile&regions=par&ports=4173%3Bhttp%3B%2F&hc_protocol%5B4173%5D=tcp&hc_grace_period%5B4173%5D=5&hc_interval%5B4173%5D=30&hc_restart_limit%5B4173%5D=3&hc_timeout%5B4173%5D=5&hc_path%5B4173%5D=%2F&hc_method%5B4173%5D=get)

## Work on the project locally

### Step 1: Backend Setup

1. **Clone the repository and set up the backend:**
   ```bash
   git clone <repository-url>
   cd text_to_voice/backend
   uv sync
   ```

2. **Test the backend:**
   ```bash
   uv run fastapi dev main.py
   ```

In the backend, there is a `dia` folder from https://github.com/nari-labs/dia.git; it contains the model configuration. The reason for not using `uv add git+https://github.com/nari-labs/dia.git` is that it loads the entire project, which includes features unnecessary for this project.  

The [`main.py`](backend/main.py) file contains FastAPI as a backend wrapper. The model is loaded and initialised, and the connection between the frontend and backend is handled within the script. 

The model can be optimised, and you can use Pruna AI to do that. Check out the [tutorial](https://www.koyeb.com/tutorials/deploy-flux-models-with-pruna-ai-for-8x-faster-inference-on-koyeb) about how to use Pruna AI on a Flux model and follow the same steps.  

### Step 2: Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Start the development server:
   ```bash
   pnpm run dev
   ```
 
The frontend is done with SvelteKit, and it has three parts: 

1. **Main Page (`src/routes/+page.svelte`):**
   - Entry point of the application
   - Handles routing to the home page

2. **Home Page (`src/routes/home.svelte`):**
   - Contains the text-to-speech interface
   - Manages audio recording and playback
   - Handles API communication with the backend

3. **Message Component (`src/components/Message.svelte`):**
   - Displays status messages and errors
   - Provides user feedback during text-to-speech processing




### Deployment on Koyeb

Deploy the app to Koyeb using the control panel or via the [Koyeb CLI](https://www.koyeb.com/tutorials/deploy-flux-models-with-pruna-ai-for-8x-faster-inference-on-koyeb#deploy-the-optimized-model-on-koyeb). You can check the configuration for deploying using the control panel on the buttons above. 

#### Koyeb CLI Backend 
```bash 
koyeb deploy . text_to_voice/backend \
   --instance-type gpu-nvidia-l40s \
   --region na \
   --type web \
   --port 8000:http \
   --archive-builder \
```
#### Koyeb CLI Frontend 
```bash
koyeb deploy . text_to_voice/frontend \
   --instance-type nano \
   --region na \
   --type web \
   --port 8000:http \
   --archive-builder \
```


## Troubleshooting

Common issues and solutions:

1. **Backend Issues:**
   - Check model loading errors
   - Verify environment variables
   - Check audio file permissions

2. **Frontend Issues:**
   - Verify API endpoint configuration
   - Check CORS settings
   - Ensure proper environment variables

3. **Deployment Issues:**
   - Verify Docker image builds
   - Check Koyeb logs
   - Ensure proper networking configuration




