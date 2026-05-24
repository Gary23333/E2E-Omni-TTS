import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import agents, rag, skills, config, ws_voice
from core.noise_manager import NOISE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Voice CS Demo starting...")
    yield
    logger.info("Voice CS Demo shutting down...")


app = FastAPI(title="Voice Customer Service Demo", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(ws_voice.router, tags=["voice"])

# Mount noise samples for auditioning
NOISE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/config/noise/file", StaticFiles(directory=str(NOISE_DIR)), name="noise_samples")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8900, reload=True)
