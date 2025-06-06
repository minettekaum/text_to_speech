from typing import Union, Optional, Tuple
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import time
from pydantic import BaseModel
import uuid

import soundfile as sf
import numpy as np
from dia.model import Dia
import logging
import torch

import argparse
import tempfile
import sys
import uvicorn

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories for storing files
AUDIO_DIR = Path("audio_files")
AUDIO_DIR.mkdir(exist_ok=True)
UPLOADS_DIR = Path("upload_files")
UPLOADS_DIR.mkdir(exist_ok=True)

# Initialize device
if torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")

logger.info(f"Using device: {device}")

# Load Nari model and config
logger.info("Loading Nari model...")
try:
    dtype_map = {
        "cpu": "float32",
        "cuda": "float16",  # NVIDIA – better with float16
    }

    dtype = dtype_map.get(device.type, "float16")
    logger.info(f"Using device: {device}, attempting to load model with {dtype}")
    model = Dia.from_pretrained("nari-labs/Dia-1.6B", compute_dtype=dtype, device=device)
except Exception as e:
    logger.error(f"Error loading Nari model: {e}")
    raise

async def process_audio_file(file: UploadFile) -> Tuple[np.ndarray, int]:
    """Process uploaded audio file and return preprocessed audio data and sample rate."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f_audio:
        temp_path = Path(f_audio.name)
        try:
            # Log file details
            logger.debug(f"Processing audio file: {file.filename}")
            content = await file.read()
            f_audio.write(content)
            f_audio.flush()  # Ensure all data is written
            
            # Read and preprocess audio data
            try:
                audio_data, sr = sf.read(str(temp_path))
            except Exception as e:
                # If soundfile fails, try using librosa as a fallback
                try:
                    import librosa
                    audio_data, sr = librosa.load(str(temp_path), sr=None)
                except ImportError:
                    logger.error("librosa not installed. Please install it for better audio format support.")
                    raise HTTPException(status_code=400, detail="Audio format not supported. Please use WAV, MP3, or FLAC format.")
                except Exception as e2:
                    logger.error(f"Both soundfile and librosa failed to read audio: {e2}")
                    raise HTTPException(status_code=400, detail="Failed to process audio. Please ensure the file is a valid audio file.")
            
            # Basic audio preprocessing for consistency
            # Convert to float32 in [-1, 1] range if integer type
            if np.issubdtype(audio_data.dtype, np.integer):
                max_val = np.iinfo(audio_data.dtype).max
                audio_data = audio_data.astype(np.float32) / max_val
            elif not np.issubdtype(audio_data.dtype, np.floating):
                logger.warning(f"Unsupported audio dtype {audio_data.dtype}, attempting conversion")
                audio_data = audio_data.astype(np.float32)

            # Ensure mono (average channels if stereo)
            if audio_data.ndim > 1:
                if audio_data.shape[0] == 2:  # Assume (2, N)
                    audio_data = np.mean(audio_data, axis=0)
                elif audio_data.shape[1] == 2:  # Assume (N, 2)
                    audio_data = np.mean(audio_data, axis=1)
                else:
                    logger.warning(f"Audio has unexpected shape {audio_data.shape}, taking first channel/axis")
                    audio_data = audio_data[0] if audio_data.shape[0] < audio_data.shape[1] else audio_data[:, 0]
                audio_data = np.ascontiguousarray(audio_data)

            # Ensure audio is not empty
            if len(audio_data) == 0:
                raise HTTPException(status_code=400, detail="Audio file appears to be empty")

            # Ensure audio is not too long (e.g., > 30 seconds at 44.1kHz)
            max_samples = 30 * 44100
            if len(audio_data) > max_samples:
                logger.warning(f"Audio too long ({len(audio_data)} samples), truncating to {max_samples} samples")
                audio_data = audio_data[:max_samples]

            return audio_data, sr

        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            if "Format not recognized" in str(e):
                raise HTTPException(status_code=400, detail="Audio format not supported. Please use WAV, MP3, or FLAC format.")
            raise HTTPException(status_code=400, detail=f"Failed to process audio: {str(e)}")
        finally:
            try:
                temp_path.unlink()
                logger.debug("Cleaned up temporary file")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {e}")

@app.post("/api/generate")
async def generate_speech(
    text: str = Form(...),
    audio: UploadFile = File(None),
    max_new_tokens: int = Form(1024),
    cfg_scale: float = Form(3.0),
    temperature: float = Form(1.3),
    top_p: float = Form(0.95),
    cfg_filter_top_k: int = Form(35),
    speed_factor: float = Form(0.94)
):
    """
    FastAPI endpoint for text-to-speech generation with optional audio prompt.
    Uses improved audio processing from test_model.py.
    """
    if not text or text.isspace():
        raise HTTPException(status_code=400, detail="Text input cannot be empty")

    # Parameter validation
    if not (860 <= max_new_tokens <= 3072):
        raise HTTPException(status_code=400, detail="max_new_tokens must be between 860 and 3072")
    if not (1.0 <= temperature <= 1.5):
        raise HTTPException(status_code=400, detail="temperature must be between 1.0 and 1.5")
    if not (0.8 <= top_p <= 1.0):
        raise HTTPException(status_code=400, detail="top_p must be between 0.8 and 1.0")
    if not (1.0 <= cfg_scale <= 5.0):
        raise HTTPException(status_code=400, detail="cfg_scale must be between 1.0 and 5.0")
    if not (15 <= cfg_filter_top_k <= 50):
        raise HTTPException(status_code=400, detail="cfg_filter_top_k must be between 15 and 50")
    if not (0.8 <= speed_factor <= 1.0):
        raise HTTPException(status_code=400, detail="speed_factor must be between 0.8 and 1.0")

    output_filepath = AUDIO_DIR / f"{int(time.time())}.wav"
    audio_prompt = None

    try:
        # Process audio prompt if provided
        if audio:
            logger.info("Processing audio prompt")
            audio_prompt, _ = await process_audio_file(audio)
            logger.debug(f"Audio prompt processed successfully: {audio_prompt.shape}")
            # Ensure audio prompt is in the correct shape for the model
            if audio_prompt is not None:
                # Convert numpy array to PyTorch tensor and move to correct device
                audio_prompt = torch.from_numpy(audio_prompt).to(device)
                # Ensure the audio prompt is the correct length (1 second at 16kHz)
                if len(audio_prompt) > 16000:
                    audio_prompt = audio_prompt[:16000]
                elif len(audio_prompt) < 16000:
                    # Pad with zeros if too short
                    padding = torch.zeros(16000 - len(audio_prompt), device=device)
                    audio_prompt = torch.cat([audio_prompt, padding])
                
                # Take evenly spaced samples to get [9, 9] shape
                indices = torch.linspace(0, len(audio_prompt)-1, 81).long()  # 9x9=81 samples
                audio_prompt = audio_prompt[indices].reshape(9, 9)

        # Generate audio
        start_time = time.time()
        with torch.inference_mode():
            output_audio_np = model.generate(
                text,
                max_tokens=max_new_tokens,
                cfg_scale=cfg_scale,
                temperature=temperature,
                top_p=top_p,
                cfg_filter_top_k=cfg_filter_top_k,
                use_torch_compile=False,
                audio_prompt=audio_prompt,
            )
        logger.info(f"Generation finished in {time.time() - start_time:.2f} seconds")

        if output_audio_np is None:
            raise HTTPException(status_code=500, detail="Model generated no output")

        # Process output audio
        output_sr = 44100  # Fixed sample rate from model

        # Apply speed factor
        original_len = len(output_audio_np)
        speed_factor = max(0.1, min(speed_factor, 5.0))  # Safety bounds
        target_len = int(original_len / speed_factor)
        
        if target_len != original_len and target_len > 0:
            x_original = np.arange(original_len)
            x_resampled = np.linspace(0, original_len - 1, target_len)
            output_audio_np = np.interp(x_resampled, x_original, output_audio_np)
            logger.debug(f"Resampled audio from {original_len} to {target_len} samples")

        # Convert to int16 for WAV file
        output_audio_np = np.clip(output_audio_np, -1.0, 1.0)
        output_audio_np = (output_audio_np * 32767).astype(np.int16)

        # Save the file
        sf.write(str(output_filepath), output_audio_np, output_sr)
        logger.info(f"Audio saved to {output_filepath}")

        return FileResponse(
            path=str(output_filepath),
            media_type="audio/wav",
            filename=output_filepath.name
        )

    except Exception as e:
        logger.error(f"Error during generation: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up old files
        try:
            for file in AUDIO_DIR.glob("*.wav"):
                if file != output_filepath and file.stat().st_mtime < (time.time() - 3600):
                    file.unlink()
            for file in UPLOADS_DIR.glob("*"):
                if file.stat().st_mtime < (time.time() - 3600):
                    file.unlink()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running"}

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

if __name__ == "__main__":
    # Only parse arguments when running the script directly
    parser = argparse.ArgumentParser(description="FastAPI server for Nari TTS")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--device", type=str, help="Force device (e.g., 'cuda', 'mps', 'cpu')")
    args = parser.parse_args()

    # Override device if specified
    if args.device:
        device = torch.device(args.device)
        logger.info(f"Overriding device to: {device}")
        # Reload model with new device
        model = Dia.from_pretrained("nari-labs/Dia-1.6B", 
                                  compute_dtype=dtype_map.get(device.type, "float16"),
                                  device=device)

    uvicorn.run(app, host=args.host, port=args.port)