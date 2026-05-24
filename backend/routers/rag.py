import os
import shutil
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path

from schemas.models import RAGDocument, DocStatus, GlobalConfig
from core.json_store import JsonStore
from core.rag_engine import RAGEngine, RAG_DIR
from routers.ws_voice import config_store

logger = logging.getLogger(__name__)
router = APIRouter()

doc_store = JsonStore("rag_documents.json", RAGDocument)
# Share engine instance or create new one and sync config
rag_engine = RAGEngine()


@router.get("")
async def list_documents():
    return doc_store.list_all()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # Sync config before processing
    cfg = GlobalConfig(**config_store.get_all())
    rag_engine.set_config(cfg)
    
    doc_id = RAGDocument().id
    doc_dir = RAG_DIR / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    file_path = doc_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create document record
    doc = RAGDocument(
        id=doc_id,
        filename=file.filename,
        status=DocStatus.PROCESSING,
        enabled=True,
        uploadedAt=datetime.now().isoformat(),
    )
    doc_store.create(doc)

    # Process
    try:
        chunk_count = rag_engine.process_document(doc_id, str(file_path), file.filename)
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
    rag_engine.rebuild_index()
    return {"ok": True}


@router.put("/{doc_id}/toggle")
async def toggle_document(doc_id: str):
    doc = doc_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    new_enabled = not doc.enabled
    doc_store.update(doc_id, {"enabled": new_enabled})
    
    # Sync config before rebuild
    cfg = GlobalConfig(**config_store.get_all())
    rag_engine.set_config(cfg)
    rag_engine.rebuild_index()
    return doc_store.get(doc_id)
