import { useRef, useCallback, useState } from 'react';

export function useAudioPlayer() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const nextStartTimeRef = useRef(0);
  const activeSourcesRef = useRef(0);
  const carryByteRef = useRef<number | null>(null);

  const getContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext({ sampleRate: 48000 });
    }
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
    return audioContextRef.current;
  }, []);

  const playChunk = useCallback((data: ArrayBuffer) => {
    const ctx = getContext();
    let chunk = new Uint8Array(data);

    if (carryByteRef.current !== null) {
      const combined = new Uint8Array(chunk.length + 1);
      combined[0] = carryByteRef.current;
      combined.set(chunk, 1);
      chunk = combined;
      carryByteRef.current = null;
    }

    if (chunk.length % 2 === 1) {
      carryByteRef.current = chunk[chunk.length - 1];
      chunk = chunk.slice(0, -1);
    }

    if (chunk.length === 0) {
      return;
    }

    const int16View = new Int16Array(chunk.buffer, chunk.byteOffset, chunk.byteLength / 2);
    const float32 = new Float32Array(int16View.length);
    for (let i = 0; i < int16View.length; i++) {
      float32[i] = int16View[i] / 32768.0;
    }

    const audioBuffer = ctx.createBuffer(1, float32.length, 48000);
    audioBuffer.getChannelData(0).set(float32);

    const source = ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(ctx.destination);

    activeSourcesRef.current += 1;
    source.onended = () => {
      activeSourcesRef.current = Math.max(0, activeSourcesRef.current - 1);
      sourcesRef.current = sourcesRef.current.filter((s) => s !== source);
      if (activeSourcesRef.current === 0) {
        nextStartTimeRef.current = 0;
        setIsPlaying(false);
      }
    };

    const startAt = Math.max(ctx.currentTime + 0.04, nextStartTimeRef.current);
    nextStartTimeRef.current = startAt + audioBuffer.duration;
    sourcesRef.current.push(source);
    setIsPlaying(true);
    source.start(startAt);
  }, [getContext]);

  const stop = useCallback(() => {
    for (const source of sourcesRef.current) {
      try { source.stop(); } catch {}
    }
    sourcesRef.current = [];
    activeSourcesRef.current = 0;
    nextStartTimeRef.current = 0;
    carryByteRef.current = null;
    setIsPlaying(false);
  }, []);

  return { playChunk, stop, isPlaying };
}
