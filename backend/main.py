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

def is_audio_empty_or_silent(audio_data: np.ndarray) -> bool:
    """Check if audio data is empty, None, or silent."""
    return audio_data is None or audio_data.size == 0 or audio_data.max() == 0

def normalize_audio_dtype(audio_data: np.ndarray) -> np.ndarray:
    """Convert audio data to float32 format."""
    if np.issubdtype(audio_data.dtype, np.integer):
        max_val = np.iinfo(audio_data.dtype).max
        return audio_data.astype(np.float32) / max_val
    elif not np.issubdtype(audio_data.dtype, np.floating):
        logger.warning(f"Unsupported audio prompt dtype {audio_data.dtype}, attempting conversion.")
        try:
            return audio_data.astype(np.float32)
        except Exception as conv_e:
            raise HTTPException(status_code=400, detail=f"Failed to convert audio prompt to float32: {conv_e}")
    return audio_data

def convert_to_mono(audio_data: np.ndarray) -> np.ndarray:
    """Convert multi-channel audio to mono."""
    if audio_data.ndim > 1:
        if audio_data.shape[0] == 2: 
            audio_data = np.mean(audio_data, axis=0)
        elif audio_data.shape[1] == 2: 
            audio_data = np.mean(audio_data, axis=1)
        else:
            logger.warning(f"Audio prompt has unexpected shape {audio_data.shape}, taking first channel/axis.")
            audio_data = audio_data[0] if audio_data.shape[0] < audio_data.shape[1] else audio_data[:, 0]
        audio_data = np.ascontiguousarray(audio_data)
    return audio_data

def save_audio_to_temp_file(audio_data: np.ndarray, sample_rate: int) -> str:
    """Save audio data to a temporary WAV file and return the file path."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f_audio:
        temp_path = f_audio.name
    
    try:
        sf.write(temp_path, audio_data, sample_rate, subtype="FLOAT")
        logger.info(f"Created temporary audio prompt file: {temp_path} (sr: {sample_rate}, shape: {audio_data.shape}, max: {audio_data.max():.3f}, min: {audio_data.min():.3f})")
        return temp_path
    except Exception as write_e:
        logger.error(f"Error writing temporary audio file: {write_e}")
        raise HTTPException(status_code=400, detail=f"Failed to save audio prompt: {write_e}")

def process_audio_prompt(audio_prompt: AudioPrompt) -> Optional[str]:
    """
    Process the audio prompt input and return the path to the temporary audio file.
    Returns None if the audio is empty or silent.
    """
    audio_data = np.array(audio_prompt.audio_data, dtype=np.float32)
    sample_rate = audio_prompt.sample_rate

    if is_audio_empty_or_silent(audio_data):
        logger.warning("Audio prompt seems empty or silent, ignoring prompt.")
        return None

    logger.info(f"Processing audio prompt: shape={audio_data.shape}, sample_rate={sample_rate}, dtype={audio_data.dtype}")
    
    audio_data = normalize_audio_dtype(audio_data)

    audio_data = convert_to_mono(audio_data)
    
    return save_audio_to_temp_file(audio_data, sample_rate)

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
            prompt_path_for_generate = process_audio_prompt(request.audio_prompt_input)

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

