import os
import shutil
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path

from schemas.models import RAGDocument, DocStatus, GlobalConfig
from core.json_store import JsonStore, ConfigStore
from core.rag_engine import RAGEngine, RAG_DIR
from core.upload_safety import DOCUMENT_SUFFIXES, safe_filename, safe_path, read_upload

logger = logging.getLogger(__name__)
router = APIRouter()

doc_store = JsonStore("rag_documents.json", RAGDocument)

# These will be set by create_router()
_config_store: ConfigStore = None
_rag_engine: RAGEngine = None


def create_router(config_store: ConfigStore, rag_engine: RAGEngine) -> APIRouter:
    """Create router with injected dependencies."""
    global _config_store, _rag_engine
    _config_store = config_store
    _rag_engine = rag_engine
    return router


@router.get("")
async def list_documents():
    return doc_store.list_all()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = safe_filename(file.filename or "", DOCUMENT_SUFFIXES)
    content = await read_upload(file)

    # Sync config before processing
    cfg = GlobalConfig(**_config_store.get_all())
    _rag_engine.set_config(cfg)

    doc_id = RAGDocument().id
    doc_dir = RAG_DIR / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    file_path = safe_path(doc_dir, filename, DOCUMENT_SUFFIXES)
    with file_path.open("xb") as handle:
        handle.write(content)

    # Create document record
    doc = RAGDocument(
        id=doc_id,
        filename=filename,
        status=DocStatus.PROCESSING,
        enabled=True,
        uploadedAt=datetime.now().isoformat(),
    )
    doc_store.create(doc)

    # Process
    try:
        chunk_count = _rag_engine.process_document(doc_id, str(file_path), filename)
        doc_store.update(doc_id, {
            "status": DocStatus.READY.value,
            "chunkCount": chunk_count,
        })
    except Exception as e:
        logger.error(f"RAG processing error: {e}")
        doc_store.update(doc_id, {
            "status": DocStatus.ERROR.value,
            "error": str(e),
        })

    return doc_store.get(doc_id)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    doc = doc_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    # Remove files
    doc_dir = RAG_DIR / doc_id
    if doc_dir.exists():
        shutil.rmtree(doc_dir)

    doc_store.delete(doc_id)
    _rag_engine.rebuild_index()
    return {"ok": True}


@router.put("/{doc_id}/toggle")
async def toggle_document(doc_id: str):
    doc = doc_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    new_enabled = not doc.enabled
    doc_store.update(doc_id, {"enabled": new_enabled})

    # Sync config before rebuild
    cfg = GlobalConfig(**_config_store.get_all())
    _rag_engine.set_config(cfg)
    _rag_engine.rebuild_index()
    return doc_store.get(doc_id)

