import httpx
import asyncio
import socket
import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File
from schemas.models import GlobalConfig
from core.json_store import ConfigStore
from core.noise_manager import NOISE_DIR

router = APIRouter()

DEFAULTS = GlobalConfig().model_dump()
config_store = ConfigStore("global_config.json", DEFAULTS)


@router.get("")
async def get_config():
    current = GlobalConfig(**config_store.get_all()).model_dump()
    return config_store.update(current)


@router.put("")
async def update_config(updates: dict):
    # Validate against model
    current = config_store.get_all()
    current.update(updates)
    validated = GlobalConfig(**current).model_dump()
    return config_store.update(validated)


@router.post("/test_llm")
async def test_llm():
    config = GlobalConfig(**config_store.get_all())
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(config.llmEndpoint, timeout=5.0)
            return {"status": "ok", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/test_tts")
async def test_tts():
    config = GlobalConfig(**config_store.get_all())
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(config.ttsEndpoint, timeout=5.0)
            return {"status": "ok", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/test_asr")
async def test_asr():
    config = GlobalConfig(**config_store.get_all())
    if not config.asrEndpoint.startswith("ws"):
        return {"status": "error", "message": "Invalid ASR endpoint (must be ws/wss)"}
    
    try:
        host_port = config.asrEndpoint.replace("ws://", "").replace("wss://", "").split("/")[0]
        if ":" in host_port:
            host, port = host_port.split(":")
            port = int(port)
        else:
            host = host_port
            port = 80
            
        loop = asyncio.get_event_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        await asyncio.wait_for(loop.sock_connect(sock, (host, port)), timeout=3.0)
        sock.close()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/test_embed")
async def test_embed():
    config = GlobalConfig(**config_store.get_all())
    try:
        if config.embedEndpoint:
            async with httpx.AsyncClient() as client:
                resp = await client.get(config.embedEndpoint, timeout=5.0)
                return {"status": "ok", "code": resp.status_code}
        else:
            import sentence_transformers
            return {"status": "ok", "mode": "local"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/noise/samples")
async def list_noise_samples():
    """List all available noise files."""
    files = []
    if NOISE_DIR.exists():
        for f in NOISE_DIR.iterdir():
            if f.is_file() and f.suffix.lower() in [".wav", ".mp3", ".m4a"]:
                files.append(f.name)
    return files


@router.post("/noise/upload")
async def upload_noise_sample(file: UploadFile = File(...)):
    """Upload a new noise sample."""
    NOISE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = NOISE_DIR / file.filename
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return {"filename": file.filename}
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {e}")


@router.delete("/noise/{filename}")
async def delete_noise_sample(filename: str):
    """Delete a noise sample."""
    file_path = NOISE_DIR / filename
    if file_path.exists():
        os.remove(file_path)
    return {"ok": True}
