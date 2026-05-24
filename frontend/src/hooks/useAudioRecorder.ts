import { useRef, useCallback, useState } from 'react';

/**
 * Advanced Audio Recorder using Web Audio API for raw PCM capture.
 * Ensures compatibility with ASR and Omni models (16kHz, Mono).
 */
export function useAudioRecorder(onChunk: (data: ArrayBuffer) => void, onEnd: () => void) {
  const [isRecording, setIsRecording] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      
      streamRef.current = stream;
      
      // We use a lower sample rate for ASR (16kHz is standard)
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      // ScriptProcessor is deprecated but widely supported for raw PCM streaming in demos
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      
      processor.onaudioprocess = (e) => {
        if (!isRecording) return;
        
        const inputData = e.inputBuffer.getChannelData(0);
        // Convert Float32 to Int16 PCM
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        onChunk(pcmData.buffer);
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      processorRef.current = processor;
      
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording:', err);
    }
  }, [onChunk, isRecording]);

  const stop = useCallback(() => {
    setIsRecording(false);
    
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    onEnd();
  }, [onEnd]);

  return { start, stop, isRecording };
}
