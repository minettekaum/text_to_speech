import uuid
import logging
import sys



from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
from pydantic import BaseModel

import argparse
import tempfile
import time
from typing import Union, Optional, Tuple, List
from pathlib import Path

import soundfile as sf
import numpy as np
import torch
from dia.model import Dia

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

"""
# Parse command line arguments
parser = argparse.ArgumentParser(description="FastAPI server for Nari TTS")
parser.add_argument("--device", type=str, help="Force device (e.g., 'cuda', 'mps', 'cpu')")
parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
args = parser.parse_args()
"""
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

if torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")
"""
# Initialize device
if device: #if args.device:
    device = torch.device(device) #device = torch.device(args.device)
else:
    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
"""
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

class AudioPrompt(BaseModel):
    sample_rate: int
    audio_data: List[float]  # Convert numpy array to list for Pydantic

class GenerateRequest(BaseModel):
    text_input: str
    audio_prompt_input: Optional[AudioPrompt] = None
    max_new_tokens: int = 1024
    cfg_scale: float = 3.0
    temperature: float = 1.3
    top_p: float = 0.95
    cfg_filter_top_k: int = 35
    speed_factor: float = 0.94

@app.post("/api/generate")
async def run_inference(request: GenerateRequest):
    """
    Runs Nari inference using the globally loaded model and provided inputs.
    Uses temporary files for text and audio prompt compatibility with inference.generate.
    """
    global model, device  # Access global model, config, device

    if not request.text_input or request.text_input.isspace():
        raise HTTPException(status_code=400, detail="Text input cannot be empty.")

    temp_txt_file_path = None
    temp_audio_prompt_path = None
    output_filepath = AUDIO_DIR / f"{int(time.time())}.wav"

    try:
        prompt_path_for_generate = None
        if request.audio_prompt_input is not None:
            # Convert list back to numpy array
            audio_data = np.array(request.audio_prompt_input.audio_data, dtype=np.float32)
            sr = request.audio_prompt_input.sample_rate
            
            # Check if audio_data is valid
            if audio_data is None or audio_data.size == 0 or audio_data.max() == 0:  # Check for silence/empty
                logger.warning("Audio prompt seems empty or silent, ignoring prompt.")
            else:
                logger.info(f"Processing audio prompt: shape={audio_data.shape}, sample_rate={sr}, dtype={audio_data.dtype}")
                # Save prompt audio to a temporary WAV file
                with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f_audio:
                    temp_audio_prompt_path = f_audio.name  # Store path for cleanup

                    # Basic audio preprocessing for consistency
                    # Convert to float32 in [-1, 1] range if integer type
                    if np.issubdtype(audio_data.dtype, np.integer):
                        max_val = np.iinfo(audio_data.dtype).max
                        audio_data = audio_data.astype(np.float32) / max_val
                    elif not np.issubdtype(audio_data.dtype, np.floating):
                        logger.warning(f"Unsupported audio prompt dtype {audio_data.dtype}, attempting conversion.")
                        # Attempt conversion, might fail for complex types
                        try:
                            audio_data = audio_data.astype(np.float32)
                        except Exception as conv_e:
                            raise HTTPException(status_code=400, detail=f"Failed to convert audio prompt to float32: {conv_e}")

                    # Ensure mono (average channels if stereo)
                    if audio_data.ndim > 1:
                        if audio_data.shape[0] == 2:  # Assume (2, N)
                            audio_data = np.mean(audio_data, axis=0)
                        elif audio_data.shape[1] == 2:  # Assume (N, 2)
                            audio_data = np.mean(audio_data, axis=1)
                        else:
                            logger.warning(f"Audio prompt has unexpected shape {audio_data.shape}, taking first channel/axis.")
                            audio_data = audio_data[0] if audio_data.shape[0] < audio_data.shape[1] else audio_data[:, 0]
                        audio_data = np.ascontiguousarray(audio_data)  # Ensure contiguous after slicing/mean

                    # Write using soundfile
                    try:
                        sf.write(temp_audio_prompt_path, audio_data, sr, subtype="FLOAT")  # Explicitly use FLOAT subtype
                        prompt_path_for_generate = temp_audio_prompt_path
                        logger.info(f"Created temporary audio prompt file: {temp_audio_prompt_path} (orig sr: {sr}, shape: {audio_data.shape}, max: {audio_data.max():.3f}, min: {audio_data.min():.3f})")
                    except Exception as write_e:
                        logger.error(f"Error writing temporary audio file: {write_e}")
                        raise HTTPException(status_code=400, detail=f"Failed to save audio prompt: {write_e}")

        # 3. Run Generation

        start_time = time.time()

        # Use torch.inference_mode() context manager for the generation call
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

        # 4. Convert Codes to Audio
        if output_audio_np is None:
            raise HTTPException(status_code=500, detail="Model generated no output")

        # Process output audio
        output_sr = 44100  # Fixed sample rate from model

        # Apply speed factor
        original_len = len(output_audio_np)
        speed_factor = max(0.1, min(request.speed_factor, 5.0))  # Safety bounds
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
        logger.error(f"Error during inference: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # 5. Cleanup Temporary Files defensively
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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running"}

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

'''
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
'''