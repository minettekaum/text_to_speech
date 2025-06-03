from typing import Union
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import time
import soundfile as sf
import numpy as np
from dia.model import Dia
import logging
import torch

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize model
try:
    logger.info("Initializing Dia model...")
    model = Dia.from_pretrained("nari-labs/Dia-1.6B")
    logger.info("Successfully initialized Dia model")
except Exception as e:
    logger.error(f"Error initializing model: {str(e)}")
    raise

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

class TextToSpeechRequest(BaseModel):
    text: str

async def process_audio_file(file: UploadFile) -> np.ndarray:
    # Save uploaded file temporarily
    temp_path = UPLOADS_DIR / f"{uuid.uuid4()}.mp3"
    try:
        # Log file details
        logger.debug(f"Processing audio file: {file.filename}")
        logger.debug(f"Content type: {file.content_type}")
        
        # Read the content before opening the file
        content = await file.read()
        logger.debug(f"Read content size: {len(content)} bytes")
        
        # Ensure the directory exists
        UPLOADS_DIR.mkdir(exist_ok=True)
        logger.debug(f"Upload directory: {UPLOADS_DIR}")
        
        # Write the content to the file
        temp_path.write_bytes(content)
        logger.debug(f"Written to temporary file: {temp_path}")
        
        # Ensure the file exists before reading
        if not temp_path.exists():
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")
        
        file_size = temp_path.stat().st_size
        logger.debug(f"Temporary file size: {file_size} bytes")
            
        try:
            # Try to read the file first to check if it's valid
            with open(temp_path, 'rb') as f:
                first_bytes = f.read(4)
                logger.debug(f"First bytes of file: {first_bytes.hex()}")
            
            # Load audio file using soundfile
            logger.debug("Attempting to read audio file with soundfile")
            audio_data, sample_rate = sf.read(str(temp_path))
            logger.debug(f"Successfully read audio file. Shape: {audio_data.shape}, Sample rate: {sample_rate}")
            
            # Ensure audio data is valid
            if len(audio_data.shape) == 0 or audio_data.size == 0:
                raise ValueError("Empty audio data")
                
            # Convert to mono if stereo
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                audio_data = np.mean(audio_data, axis=1)
                logger.debug("Converted stereo to mono")
                
            # Ensure float32 format
            audio_data = audio_data.astype(np.float32)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error reading audio file: {str(e)}")
            if "Format not recognized" in str(e):
                raise HTTPException(status_code=400, detail="Audio format not supported. Please use WAV or FLAC format.")
            elif "Empty audio data" in str(e):
                raise HTTPException(status_code=400, detail="Audio file appears to be empty")
            else:
                raise HTTPException(status_code=400, detail=f"Invalid audio file: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing audio file: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {str(e)}")
    finally:
        # Cleanup temporary file
        try:
            if temp_path.exists():
                temp_path.unlink()
                logger.debug("Cleaned up temporary file")
        except Exception as e:
            logger.error(f"Error cleaning up temporary file: {str(e)}")

@app.post("/api/generate")
async def generate_speech(
    text: str = Form(...),
    reference_text: str = Form(None),
    audio: UploadFile = File(None)
):
    try:
        logger.info(f"Generating speech for text: {text[:50]}...")
        
        # Generate a unique filename
        filename = f"{uuid.uuid4()}.mp3"
        filepath = AUDIO_DIR / filename
        logger.debug(f"Output filepath: {filepath}")

        # Process reference audio if provided
        reference_audio = None
        if audio and reference_text:
            logger.info("Processing reference audio")
            try:
                reference_audio = await process_audio_file(audio)
                logger.debug(f"Reference audio shape: {reference_audio.shape}")
                
                # Combine reference text and generation text
                full_text = reference_text + text
                logger.debug(f"Combined text for generation: {full_text[:100]}...")
            except Exception as e:
                logger.error(f"Failed to process reference audio: {str(e)}")
                if isinstance(e, HTTPException):
                    raise e
                raise HTTPException(status_code=400, detail=f"Failed to process reference audio: {str(e)}")
        else:
            full_text = text

        # Generate audio with optional reference
        try:
            logger.info("Generating audio output")
            if reference_audio is not None:
                # Use the reference audio in the generation with specific parameters for voice cloning
                output = model.generate(
                    full_text,
                    audio_prompt=reference_audio,
                    temperature=0.0,
                    top_p=0.5,
                    use_cfg_filter=False,
                    cfg_filter_top_k=100,
                    cfg_scale=4.20
                )
            else:
                # Generate without reference
                output = model.generate(text)
            logger.debug(f"Generated audio shape: {output.shape}")
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate audio: {str(e)}")
        
        # Save audio
        try:
            logger.info("Saving generated audio")
            sf.write(str(filepath), output, 44100)
            logger.debug("Audio saved successfully")
        except Exception as e:
            logger.error(f"Error saving generated audio: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save generated audio: {str(e)}")

        return FileResponse(
            path=str(filepath),
            media_type="audio/mpeg",
            filename=filename
        )

    except Exception as e:
        logger.error(f"Error during generation: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure cleanup happens
        cleanup_old_files()

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running"}

# Cleanup old files periodically
def cleanup_old_files():
    try:
        # Cleanup audio files
        for file in AUDIO_DIR.glob("*.mp3"):
            if file.stat().st_mtime < (time.time() - 3600):
                file.unlink()
        # Cleanup upload files
        for file in UPLOADS_DIR.glob("*"):
            if file.stat().st_mtime < (time.time() - 3600):
                file.unlink()
    except Exception as e:
        print(f"Error during cleanup: {e}")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)