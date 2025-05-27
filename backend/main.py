from typing import Union
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import time

import soundfile as sf
from dia.model import Dia

# Initialize model exactly like test.py
model = Dia.from_pretrained("nari-labs/Dia-1.6B")

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a directory for storing audio files
AUDIO_DIR = Path("audio_files")
AUDIO_DIR.mkdir(exist_ok=True)

class TextToSpeechRequest(BaseModel):
    text: str

@app.post("/api/generate")
async def generate_speech(request: TextToSpeechRequest):
    try:
        # Generate a unique filename
        filename = f"{uuid.uuid4()}.mp3"
        filepath = AUDIO_DIR / filename

        # Generate audio exactly like test.py
        output = model.generate(request.text)
        
        # Save audio exactly like test.py
        sf.write(str(filepath), output, 44100)

        return FileResponse(
            path=str(filepath),
            media_type="audio/mpeg",
            filename=filename
        )

    except Exception as e:
        print(f"Error during generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running"}

# Cleanup old files periodically
def cleanup_old_files():
    try:
        for file in AUDIO_DIR.glob("*.mp3"):
            # Delete files older than 1 hour
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