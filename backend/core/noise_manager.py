import os
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Dict

try:
    import librosa
except ImportError:
    librosa = None

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NOISE_DIR = DATA_DIR / "noise_samples"

class NoiseManager:
    """Manages loading and mixing real audio noise samples."""
    
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self._cache: Dict[str, np.ndarray] = {}
        NOISE_DIR.mkdir(parents=True, exist_ok=True)

    def _load_sample(self, noise_type: str, custom_file: Optional[str] = None) -> Optional[np.ndarray]:
        if noise_type == "none":
            return None
            
        cache_key = f"{noise_type}_{custom_file}" if noise_type == "custom" else noise_type
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        file_path = None
        if noise_type == "custom" and custom_file:
            file_path = NOISE_DIR / custom_file
        else:
            # Look for default samples like cafe.wav, office.wav, etc.
            for ext in [".wav", ".mp3", ".m4a"]:
                test_path = NOISE_DIR / f"{noise_type}{ext}"
                if test_path.exists():
                    file_path = test_path
                    break
                    
        if not file_path or not file_path.exists():
            # Fallback to white noise if no file found
            return None
            
        try:
            if librosa:
                audio, _ = librosa.load(str(file_path), sr=self.sample_rate, mono=True)
                self._cache[cache_key] = audio
                return audio
            else:
                logger.warning("librosa not installed, cannot load real noise samples. Falling back to white noise.")
                return None
        except Exception as e:
            logger.error(f"Failed to load noise sample {file_path}: {e}")
            return None

    def mix(self, audio_bytes: bytes, noise_type: str, noise_volume: float, custom_file: Optional[str] = None) -> bytes:
        """Mix background noise with audio."""
        if noise_type == "none" or noise_volume <= 0:
            return audio_bytes

        # Convert input to float32
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        
        sample = self._load_sample(noise_type, custom_file)
        
        if sample is not None:
            # Use real audio sample (looped)
            noise = np.tile(sample, int(np.ceil(len(audio) / len(sample))))[:len(audio)]
        else:
            # Fallback to white noise
            noise = np.random.randn(len(audio)).astype(np.float32)
            
        # Mix
        mixed = audio + (noise * noise_volume)
        mixed = np.clip(mixed, -1.0, 1.0)
        
        return (mixed * 32768).astype(np.int16).tobytes()

# Global instance
noise_manager = NoiseManager()
