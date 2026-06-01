import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import agents, rag, skills, config, ws_voice
from core.noise_manager import NOISE_DIR
from core.rag_engine import RAGEngine
from core.json_store import ConfigStore
from schemas.models import GlobalConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Global singleton instances
DEFAULTS = GlobalConfig().model_dump()
config_store = ConfigStore("global_config.json", DEFAULTS)
rag_engine = RAGEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("OmniVoice starting...")

    # Initialize RAG engine with current config
    cfg = GlobalConfig(**config_store.get_all())
    rag_engine.set_config(cfg)

    # Store instances in app state for dependency injection
    app.state.config_store = config_store
    app.state.rag_engine = rag_engine

    yield

    logger.info("OmniVoice shutting down...")


app = FastAPI(title="OmniVoice - End-to-End Voice Agent", version="0.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pass dependencies to routers
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(
    rag.create_router(config_store, rag_engine),
    prefix="/api/rag",
    tags=["rag"]
)
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(
    config.create_router(config_store, rag_engine),
    prefix="/api/config",
    tags=["config"]
)
app.include_router(
    ws_voice.create_router(config_store, rag_engine),
    tags=["voice"]
)

# Mount noise samples for auditioning
NOISE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/config/noise/file", StaticFiles(directory=str(NOISE_DIR)), name="noise_samples")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8900, reload=True)
