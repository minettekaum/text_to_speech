# Text-to-Speech Application with Dia-1.6B

In general about what text to speach models. 



A full-stack text-to-speech application using the Dia-1.6B model, FastAPI backend, and Svelte frontend. This tutorial will guide you through setting up, developing, and deploying the application.

![Text-to-Speech App Demo](assets/demo.png)

## Requirements 

To successfully follow and complete this guide, you need:

- Python (version 3.10 or higher) installed on your local development environment
- CPU or GPU that supports `torch=>2.6.0` and `torchaudio=>2.6.0`
- A Koyeb account to deploy the application
- The Koyeb CLI installed to interact with Koyeb from the command line
- uv (Python package installer and resolver)

## Steps 


## Project Structure

The project consists of two main directories:
- `backend/`: Contains the FastAPI server and Dia model implementation
- `frontend/`: Contains the Svelte frontend application

## Step 1: Backend Setup

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

## Step 2: Frontend Setup

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

## Start from scratch

Create a project folder for the backend and the frontend and navigate to that folder 
 ```bash
   mkdir text-to-voice-app
    cd text-to-voice-app
```

Use `uv` to install and manage backend dependencies. Get started by initializing the backend project using `uv`:
```bash
`   uv init backend
```
Add to the backend the `dia` folder form https://github.com/nari-labs/dia.git, it contains the model configuration. The reason for not using `uv add git+https://github.com/nari-labs/dia.git` is that it loads the whole project, which has features that are not necessary the backend.  

To the `main.py` containing the following complete implementation of our application. We will in the next section breakdown the different steps.


```
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import tempfile
import time
from typing import Optional, List
from pathlib import Path

import soundfile as sf
import numpy as np
import torch
from dia.model import Dia

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

AUDIO_DIR = Path("audio_files")
AUDIO_DIR.mkdir(exist_ok=True)
UPLOADS_DIR = Path("upload_files")
UPLOADS_DIR.mkdir(exist_ok=True)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

logger.info(f"Using DEVICE: {DEVICE}")

class ModelManager:
    """Manages the loading, unloading and access to the Dia model."""

    def __init__(self):
        self.device = DEVICE
        self.dtype_map = {
            "cpu": "float32",
            "cuda": "float16",  
        }

    def load_model(self):
        """Load the Dia model with appropriate configuration."""
        try:
            dtype = self.dtype_map.get(self.device, "float16")
            logger.info(f"Loading model with {dtype} on {self.device}")
            self.model = Dia.from_pretrained("nari-labs/Dia-1.6B", compute_dtype=dtype, device=self.device)
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def unload_model(self):
        """Cleanup method to properly unload the model."""
        try:
            del self.model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as e:
            logger.error(f"Error unloading model: {e}")

    def get_model(self):
        """Get the current model instance."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        return self.model


model_manager = ModelManager()

class AudioPrompt(BaseModel):
    sample_rate: int
    audio_data: List[float]  

class GenerateRequest(BaseModel):
    text_input: str
    audio_prompt_input: Optional[AudioPrompt] = None
    max_new_tokens: int = 1024
    cfg_scale: float = 3.0
    temperature: float = 1.3
    top_p: float = 0.95
    cfg_filter_top_k: int = 35
    speed_factor: float = 0.94

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Handle model lifecycle during application startup and shutdown."""
    logger.info("Starting up application...")
    model_manager.load_model()
    yield
    logger.info("Shutting down application...")
    model_manager.unload_model()
    logger.info("Application shut down successfully")

app = FastAPI(
    title="Dia Text-to-Voice API",
    description="API for generating voice using Dia model",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://soft-lexine-challenge-d3e578f4.koyeb.app",
        "https://gothic-sara-ann-challenge-8bad5bca.koyeb.app",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running"}

@app.post("/api/generate")
async def run_inference(request: GenerateRequest):
    """
    Runs Nari inference using the model from model_manager and provided inputs.
    Uses temporary files for text and audio prompt compatibility with inference.generate.
    """
    if not request.text_input or request.text_input.isspace():
        raise HTTPException(status_code=400, detail="Text input cannot be empty.")

    temp_txt_file_path = None
    temp_audio_prompt_path = None
    output_filepath = AUDIO_DIR / f"{int(time.time())}.wav"

    try:
        prompt_path_for_generate = None
        if request.audio_prompt_input is not None:
            audio_data = np.array(request.audio_prompt_input.audio_data, dtype=np.float32)
            sr = request.audio_prompt_input.sample_rate

            if audio_data is None or audio_data.size == 0 or audio_data.max() == 0:
                logger.warning("Audio prompt seems empty or silent, ignoring prompt.")
            else:
                logger.info(f"Processing audio prompt: shape={audio_data.shape}, sample_rate={sr}, dtype={audio_data.dtype}")
                with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f_audio:
                    temp_audio_prompt_path = f_audio.name

                    if np.issubdtype(audio_data.dtype, np.integer):
                        max_val = np.iinfo(audio_data.dtype).max
                        audio_data = audio_data.astype(np.float32) / max_val
                    elif not np.issubdtype(audio_data.dtype, np.floating):
                        logger.warning(f"Unsupported audio prompt dtype {audio_data.dtype}, attempting conversion.")
                        try:
                            audio_data = audio_data.astype(np.float32)
                        except Exception as conv_e:
                            raise HTTPException(status_code=400, detail=f"Failed to convert audio prompt to float32: {conv_e}")

                    if audio_data.ndim > 1:
                        if audio_data.shape[0] == 2: 
                            audio_data = np.mean(audio_data, axis=0)
                        elif audio_data.shape[1] == 2: 
                            audio_data = np.mean(audio_data, axis=1)
                        else:
                            logger.warning(f"Audio prompt has unexpected shape {audio_data.shape}, taking first channel/axis.")
                            audio_data = audio_data[0] if audio_data.shape[0] < audio_data.shape[1] else audio_data[:, 0]
                        audio_data = np.ascontiguousarray(audio_data) 

                    try:
                        sf.write(temp_audio_prompt_path, audio_data, sr, subtype="FLOAT") 
                        prompt_path_for_generate = temp_audio_prompt_path
                        logger.info(f"Created temporary audio prompt file: {temp_audio_prompt_path} (orig sr: {sr}, shape: {audio_data.shape}, max: {audio_data.max():.3f}, min: {audio_data.min():.3f})")
                    except Exception as write_e:
                        logger.error(f"Error writing temporary audio file: {write_e}")
                        raise HTTPException(status_code=400, detail=f"Failed to save audio prompt: {write_e}")

        model = model_manager.get_model()

        start_time = time.time()

        with torch.inference_mode():
            logger.info(f"Starting generation with audio prompt: {prompt_path_for_generate}")
            output_audio_np = model.generate(
                request.text_input,
                max_tokens=request.max_new_tokens,
                cfg_scale=request.cfg_scale,
                temperature=request.temperature,
                top_p=request.top_p,
                cfg_filter_top_k=request.cfg_filter_top_k,
                use_torch_compile=False,
                audio_prompt=prompt_path_for_generate,
            )
            logger.info(f"Generation completed. Output shape: {output_audio_np.shape if output_audio_np is not None else None}")

        end_time = time.time()
        logger.info(f"Generation finished in {end_time - start_time:.2f} seconds.")

        if output_audio_np is None:
            raise HTTPException(status_code=500, detail="Model generated no output")

        output_sr = 44100

        original_len = len(output_audio_np)
        speed_factor = max(0.1, min(request.speed_factor, 5.0))
        target_len = int(original_len / speed_factor)
        
        if target_len != original_len and target_len > 0:
            x_original = np.arange(original_len)
            x_resampled = np.linspace(0, original_len - 1, target_len)
            output_audio_np = np.interp(x_resampled, x_original, output_audio_np)
            logger.debug(f"Resampled audio from {original_len} to {target_len} samples")

        output_audio_np = np.clip(output_audio_np, -1.0, 1.0)
        output_audio_np = (output_audio_np * 32767).astype(np.int16)

        sf.write(str(output_filepath), output_audio_np, output_sr)
        logger.info(f"Audio saved to {output_filepath}")

        return FileResponse(
            path=str(output_filepath),
            media_type="audio/wav",
            filename=output_filepath.name
        )

    except Exception as e:
        logger.error(f"Error during inference: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_txt_file_path and Path(temp_txt_file_path).exists():
            try:
                Path(temp_txt_file_path).unlink()
                logger.debug(f"Deleted temporary text file: {temp_txt_file_path}")
            except OSError as e:
                logger.warning(f"Error deleting temporary text file {temp_txt_file_path}: {e}")
        if temp_audio_prompt_path and Path(temp_audio_prompt_path).exists():
            try:
                Path(temp_audio_prompt_path).unlink()
                logger.debug(f"Deleted temporary audio prompt file: {temp_audio_prompt_path}")
            except OSError as e:
                logger.warning(f"Error deleting temporary audio prompt file {temp_audio_prompt_path}: {e}")

```

Let’s through some of the different steps in the code.

#### Loading the model 
In this step we load the dia1.6B model. 
```
def load_model(self):
        """Load the Dia model with appropriate configuration."""
        try:
            dtype = self.dtype_map.get(self.device, "float16")
            logger.info(f"Loading model with {dtype} on {self.device}")
            self.model = Dia.from_pretrained("nari-labs/Dia-1.6B", compute_dtype=dtype, device=self.device)
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
```
#### Defining the paramterers 
We define and preset the paramaters for the app. The user can change these in the frontend. 
```
class GenerateRequest(BaseModel):
    text_input: str
    audio_prompt_input: Optional[AudioPrompt] = None
    max_new_tokens: int = 1024
    cfg_scale: float = 3.0
    temperature: float = 1.3
    top_p: float = 0.95
    cfg_filter_top_k: int = 35
    speed_factor: float = 0.94
```
#### Setting up FastAPI
How to set up Fastapi
```
app = FastAPI(
    title="Dia Text-to-Voice API",
    description="API for generating voice using Dia model",
    version="1.0.0",
    lifespan=lifespan,
)
```
####  CORSMiddleware
In this step we set up the connection between the frontend and the backend. 
```
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://soft-lexine-challenge-d3e578f4.koyeb.app",
        "https://gothic-sara-ann-challenge-8bad5bca.koyeb.app",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Inference and running 
In `run_inference(request: GenerateRequest)` we run the inference and do some clean up. After the `main.py` is setup you can run 
```bash
uv run fastapi dev main.py
```
to check if the backend is working.



### Frontend Developmen`
- Main components are in `frontend/src/`
- Styles can be customized in the respective component files
- API integration is handled in the frontend services


## Step 4: Deployment on Koyeb

1. **Prepare for deployment:**
   - Ensure all environment variables are set
   - Test the application locally
   - Build Docker images for both frontend and backend

2. **Deploy Backend:**
   ```bash
   # Build the backend Docker image
   docker build -t text-to-speech-backend ./backend
   
   # Push to a container registry (e.g., Docker Hub)
   docker tag text-to-speech-backend yourusername/text-to-speech-backend
   docker push yourusername/text-to-speech-backend
   ```

3. **Deploy Frontend:**
   ```bash
   # Build the frontend Docker image
   docker build -t text-to-speech-frontend ./frontend
   
   # Push to container registry
   docker tag text-to-speech-frontend yourusername/text-to-speech-frontend
   docker push yourusername/text-to-speech-frontend
   ```

4. **Deploy on Koyeb:**
   - Create a new app on Koyeb
   - Select "Deploy from Docker image"
   - Configure environment variables
   - Set up the backend service first
   - Deploy the frontend service
   - Configure networking between services

5. **Configure Domain:**
   - Set up custom domains in Koyeb
   - Configure SSL certificates
   - Update DNS settings

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




