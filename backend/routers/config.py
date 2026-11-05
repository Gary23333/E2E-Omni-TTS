import httpx
import os
import uuid
from pathlib import Path
from pydantic import ValidationError
from fastapi import APIRouter, HTTPException, UploadFile, File
from schemas.models import GlobalConfig
from core.json_store import ConfigStore
from core.rag_engine import RAGEngine
from core.noise_manager import NOISE_DIR, noise_manager
from core.asr_client import ASRClient
from core.upload_safety import AUDIO_SUFFIXES, safe_path, safe_filename, read_upload

router = APIRouter()

# These will be set by create_router()
_config_store: ConfigStore = None
_rag_engine: RAGEngine = None


def create_router(config_store: ConfigStore, rag_engine: RAGEngine) -> APIRouter:
    """Create router with injected dependencies."""
    global _config_store, _rag_engine
    _config_store = config_store
    _rag_engine = rag_engine
    return router


def _public_config(config: dict) -> dict:
    result = dict(config)
    for field in ("llmApiKey", "embedApiKey"):
        result[field + "Set"] = bool(result.get(field))
        result[field] = ""
    return result


@router.get("")
async def get_config():
    return _public_config(GlobalConfig(**_config_store.get_all()).model_dump())


@router.put("")
async def update_config(updates: dict):
    updates = dict(updates)
    current = _config_store.get_all()
    for field, endpoint, clear in (
        ("llmApiKey", "llmEndpoint", "clearLlmApiKey"),
        ("embedApiKey", "embedEndpoint", "clearEmbedApiKey"),
    ):
        updates.pop(field + "Set", None)  # Read-only display metadata.
        should_clear = updates.pop(clear, False)
        if type(should_clear) is not bool:
            raise HTTPException(422, "Clear-key flags must be booleans")
        supplied = updates.get(field)
        if supplied is not None and not isinstance(supplied, str):
            raise HTTPException(422, "API keys must be strings")
        if should_clear and supplied:
            raise HTTPException(422, "Cannot clear and replace a key together")
        endpoint_changed = endpoint in updates and updates[endpoint] != current.get(endpoint)
        if should_clear or (endpoint_changed and not supplied):
            updates[field] = ""
        elif not supplied:
            # Blank/redacted forms preserve saved credentials unless explicitly
            # cleared. Never carry a saved key over to a different destination.
            updates.pop(field, None)
    unknown = set(updates) - set(GlobalConfig.model_fields)
    if unknown:
        raise HTTPException(422, "Unknown configuration fields")
    current.update(updates)
    try:
        validated = GlobalConfig(**current).model_dump()
    except ValidationError:
        # Do not echo secret-bearing request values in validation errors.
        raise HTTPException(422, "Invalid configuration") from None
    if validated.get("customNoiseFile"):
        safe_path(NOISE_DIR, validated["customNoiseFile"], AUDIO_SUFFIXES)
    result = _config_store.update(validated)
    if any(k in updates for k in ["embedEndpoint", "embedApiKey", "embedModel"]):
        _rag_engine.set_config(GlobalConfig(**result))
    return _public_config(result)


@router.post("/test_llm")
async def test_llm():
    config = GlobalConfig(**_config_store.get_all())
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(config.llmEndpoint, timeout=5.0)
            return {"status": "ok", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/test_tts")
async def test_tts():
    config = GlobalConfig(**_config_store.get_all())
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(config.ttsEndpoint, timeout=5.0)
            return {"status": "ok", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/test_asr")
async def test_asr():
    config = GlobalConfig(**_config_store.get_all())
    return await ASRClient(config.asrEndpoint).test_connection()


@router.post("/test_embed")
async def test_embed():
    config = GlobalConfig(**_config_store.get_all())
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
    original_name = safe_filename(file.filename or "", AUDIO_SUFFIXES)
    content = await read_upload(file)
    NOISE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{Path(original_name).suffix.lower()}"
    file_path = safe_path(NOISE_DIR, filename, AUDIO_SUFFIXES)
    with file_path.open("xb") as handle:
        handle.write(content)
    return {"filename": filename}


@router.delete("/noise/{filename}")
async def delete_noise_sample(filename: str):
    """Delete a noise sample."""
    file_path = safe_path(NOISE_DIR, filename, AUDIO_SUFFIXES)
    if file_path.is_file():
        file_path.unlink()
        noise_manager._cache.clear()
    return {"ok": True}

