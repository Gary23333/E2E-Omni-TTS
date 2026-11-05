"""Filename and per-file limits shared by local uploads."""

from pathlib import Path
from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a"}
DOCUMENT_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}


def safe_filename(filename: str, suffixes: set[str]) -> str:
    if (not filename or filename in {".", ".."} or "/" in filename
            or "\\" in filename or any(ord(ch) < 32 for ch in filename)
            or Path(filename).name != filename or Path(filename).suffix.lower() not in suffixes):
        raise HTTPException(400, "Invalid or unsupported filename")
    return filename


def safe_path(directory: Path, filename: str, suffixes: set[str]) -> Path:
    safe_filename(filename, suffixes)
    path = directory / filename
    if path.resolve().parent != directory.resolve() or path.is_symlink():
        raise HTTPException(400, "Invalid file path")
    return path


async def read_upload(file: UploadFile) -> bytes:
    chunks = []
    size = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "File exceeds the 10 MiB limit")
        chunks.append(chunk)
    return b"".join(chunks)
