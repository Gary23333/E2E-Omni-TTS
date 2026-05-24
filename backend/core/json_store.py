"""Simple JSON file-based storage for configs and data."""

import json
import os
import threading
from pathlib import Path
from typing import TypeVar, Generic, Optional
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class JsonStore(Generic[T]):
    """Thread-safe JSON file store for Pydantic models."""

    def __init__(self, filename: str, model_class: type[T]):
        self._path = DATA_DIR / "configs" / filename
        self._model = model_class
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write([])

    def _read(self) -> list[dict]:
        if not self._path.exists():
            return []
        with open(self._path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list_all(self) -> list[T]:
        with self._lock:
            return [self._model(**item) for item in self._read()]

    def get(self, item_id: str) -> Optional[T]:
        with self._lock:
            for item in self._read():
                if item.get("id") == item_id:
                    return self._model(**item)
        return None

    def create(self, item: T) -> T:
        with self._lock:
            data = self._read()
            data.append(item.model_dump())
            self._write(data)
        return item

    def update(self, item_id: str, updates: dict) -> Optional[T]:
        with self._lock:
            data = self._read()
            for i, item in enumerate(data):
                if item.get("id") == item_id:
                    item.update(updates)
                    data[i] = item
                    self._write(data)
                    return self._model(**item)
        return None

    def delete(self, item_id: str) -> bool:
        with self._lock:
            data = self._read()
            new_data = [d for d in data if d.get("id") != item_id]
            if len(new_data) < len(data):
                self._write(new_data)
                return True
        return False


class ConfigStore:
    """Singleton config store for GlobalConfig."""

    def __init__(self, filename: str, defaults: dict):
        self._path = DATA_DIR / "configs" / filename
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write(defaults)

    def _read(self) -> dict:
        if not self._path.exists():
            return {}
        with open(self._path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all(self) -> dict:
        with self._lock:
            return self._read()

    def update(self, updates: dict) -> dict:
        with self._lock:
            data = self._read()
            data.update(updates)
            self._write(data)
            return data
