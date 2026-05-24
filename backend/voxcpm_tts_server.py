"""OpenAI-compatible VoxCPM2 speech server for local development."""

from __future__ import annotations

import io
import logging
import os
from typing import AsyncIterator

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from voxcpm import VoxCPM

logger = logging.getLogger("voxcpm_tts_server")
logging.basicConfig(level=logging.INFO)

MODEL_NAME = "openbmb/VoxCPM2"
MODEL_PATH = os.environ.get("VOXCPM_MODEL_PATH", MODEL_NAME)
app = FastAPI(title="VoxCPM2 OpenAI-compatible TTS")
_model: VoxCPM | None = None


class SpeechRequest(BaseModel):
    model: str = MODEL_NAME
    input: str
    voice: str = "default"
    response_format: str = Field(default="pcm")
    stream: bool = False
    cfg_value: float = 2.0
    inference_timesteps: int = 10


def get_model() -> VoxCPM:
    global _model
    if _model is None:
        logger.info("Loading VoxCPM2 model: %s", MODEL_PATH)
        _model = VoxCPM.from_pretrained(MODEL_PATH, load_denoiser=False)
        logger.info("VoxCPM2 loaded")
    return _model


def float_wav_to_pcm16(wav: np.ndarray) -> bytes:
    wav = np.asarray(wav, dtype=np.float32)
    wav = np.clip(wav, -1.0, 1.0)
    return (wav * 32767.0).astype("<i2").tobytes()


def wav_bytes(wav: np.ndarray, sample_rate: int) -> bytes:
    out = io.BytesIO()
    sf.write(out, wav, sample_rate, format="WAV")
    return out.getvalue()


@app.get("/v1/models")
async def models() -> dict:
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "owned_by": "OpenBMB",
            }
        ],
    }


@app.post("/v1/audio/speech")
async def speech(req: SpeechRequest):
    if req.model not in {MODEL_NAME, "voxcpm2"}:
        raise HTTPException(status_code=404, detail=f"Unknown model: {req.model}")

    response_format = req.response_format.lower()
    if response_format not in {"pcm", "wav"}:
        raise HTTPException(status_code=400, detail="response_format must be pcm or wav")

    model = get_model()
    sample_rate = model.tts_model.sample_rate

    if req.stream:
        async def chunks() -> AsyncIterator[bytes]:
            for chunk in model.generate_streaming(
                text=req.input,
                cfg_value=req.cfg_value,
                inference_timesteps=req.inference_timesteps,
            ):
                yield float_wav_to_pcm16(chunk)

        return StreamingResponse(chunks(), media_type="application/octet-stream")

    wav = model.generate(
        text=req.input,
        cfg_value=req.cfg_value,
        inference_timesteps=req.inference_timesteps,
    )

    if response_format == "pcm":
        return Response(float_wav_to_pcm16(wav), media_type="application/octet-stream")
    return Response(wav_bytes(wav, sample_rate), media_type="audio/wav")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "model_loaded": _model is not None}
