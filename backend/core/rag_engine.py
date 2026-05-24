import os
import json
import logging
from pathlib import Path
from typing import Optional, List

import numpy as np
import httpx

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAG_DIR = DATA_DIR / "rag_files"
FAISS_DIR = DATA_DIR / "faiss_index"


def _ensure_dirs():
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)


_ensure_dirs()


class RemoteEmbedder:
    """OpenAI-compatible remote embedding client."""
    def __init__(self, endpoint: str, api_key: str, model: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model

    def encode(self, texts: List[str]) -> Optional[np.ndarray]:
        url = f"{self.endpoint}/embeddings"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        body = {"input": texts, "model": self.model}
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                # Sort by index to ensure order
                embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
                return np.array(embeddings)
        except Exception as e:
            logger.error(f"Remote embedding failed: {e}")
            return None


class RAGEngine:
    """RAG pipeline: upload -> extract -> chunk -> embed -> index -> retrieve."""

    def __init__(self):
        self._embedder = None
        self._index = None
        self._doc_meta_path = DATA_DIR / "configs" / "rag_documents.json"
        self._chunk_map: list[dict] = []  # {doc_id, chunk_idx, text}
        self._config = None

    def set_config(self, config):
        """Update embedder based on GlobalConfig."""
        self._config = config
        # Use remote embedder if endpoint is provided
        if config.embedEndpoint:
            self._embedder = RemoteEmbedder(config.embedEndpoint, config.embedApiKey, config.embedModel)
            logger.info(f"RAG using remote embedder: {config.embedEndpoint}")
        else:
            self._ensure_local_embedder()

    def _ensure_local_embedder(self):
        try:
            from sentence_transformers import SentenceTransformer
            model_path = str(DATA_DIR / "embed_model")
            if os.path.exists(model_path):
                self._embedder = SentenceTransformer(model_path)
            else:
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
                self._embedder.save(model_path)
            logger.info("RAG using local embedder")
        except Exception as e:
            logger.warning(f"Local RAG embedder not available: {e}")

    def _load_doc_meta(self) -> list[dict]:
        if self._doc_meta_path.exists():
            with open(self._doc_meta_path, "r") as f:
                return json.load(f)
        return []

    def _save_doc_meta(self, docs: list[dict]):
        self._doc_meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._doc_meta_path, "w") as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)

    def extract_text(self, file_path: str, filename: str) -> str:
        """Extract text from uploaded file."""
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

        if ext == "txt" or ext == "md":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == "pdf":
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as e:
                raise ValueError(f"PDF解析失败: {e}")
        elif ext == "docx":
            try:
                from docx import Document
                doc = Document(file_path)
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception as e:
                raise ValueError(f"DOCX解析失败: {e}")
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
        if not text.strip():
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap
        return chunks

    def embed_texts(self, texts: list[str]) -> Optional[np.ndarray]:
        if not self._embedder or not texts:
            return None
        if hasattr(self._embedder, 'encode'):
            # Works for both Local (sentence-transformers) and Remote
            return self._embedder.encode(texts)
        return None

    def process_document(self, doc_id: str, file_path: str, filename: str) -> int:
        text = self.extract_text(file_path, filename)
        chunks = self.chunk_text(text)
        if not chunks:
            return 0

        embeddings = self.embed_texts(chunks)
        if embeddings is None:
            return 0

        for i, chunk in enumerate(chunks):
            self._chunk_map.append({
                "doc_id": doc_id,
                "chunk_idx": i,
                "text": chunk,
            })

        self._add_to_index(embeddings, doc_id)
        return len(chunks)

    def _add_to_index(self, embeddings: np.ndarray, doc_id: str):
        import faiss
        dim = embeddings.shape[1]
        index_path = FAISS_DIR / "global.index"

        if self._index is None:
            if index_path.exists():
                self._index = faiss.read_index(str(index_path))
            else:
                self._index = faiss.IndexFlatIP(dim)

        faiss.normalize_L2(embeddings)
        self._index.add(embeddings.astype(np.float32))
        faiss.write_index(self._index, str(index_path))

    def rebuild_index(self):
        import faiss
        docs = self._load_doc_meta()
        enabled_ids = {d["id"] for d in docs if d.get("enabled", True)}

        self._chunk_map = []
        all_embeddings = []

        for doc in docs:
            if doc["id"] not in enabled_ids:
                continue
            doc_dir = RAG_DIR / doc["id"]
            file_path = doc_dir / doc["filename"]
            if not file_path.exists():
                continue

            text = self.extract_text(str(file_path), doc["filename"])
            chunks = self.chunk_text(text)
            embeddings = self.embed_texts(chunks)

            if embeddings is not None:
                for i, chunk in enumerate(chunks):
                    self._chunk_map.append({
                        "doc_id": doc["id"],
                        "chunk_idx": i,
                        "text": chunk,
                    })
                all_embeddings.append(embeddings)

        if all_embeddings:
            all_emb = np.vstack(all_embeddings)
            dim = all_emb.shape[1]
            self._index = faiss.IndexFlatIP(dim)
            faiss.normalize_L2(all_emb)
            self._index.add(all_emb.astype(np.float32))
            faiss.write_index(self._index, str(FAISS_DIR / "global.index"))

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        if not self._embedder:
            return []

        import faiss
        index_path = FAISS_DIR / "global.index"
        if not index_path.exists():
            return []

        if self._index is None:
            self._index = faiss.read_index(str(index_path))

        query_emb = self.embed_texts([query])
        if query_emb is None:
            return []

        faiss.normalize_L2(query_emb)
        scores, indices = self._index.search(query_emb.astype(np.float32), min(top_k, len(self._chunk_map)))

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self._chunk_map):
                results.append(self._chunk_map[idx]["text"])
        return results
