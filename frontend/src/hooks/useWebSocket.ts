import { useRef, useCallback, useEffect } from 'react';
import { VoiceWSClient } from '../api/wsClient';
import { useCallStore } from '../stores/callStore';

export function useWebSocket() {
  const clientRef = useRef<VoiceWSClient | null>(null);

  const connect = useCallback(async (sessionId: string, onAudioChunk?: (data: ArrayBuffer) => void) => {
    if (clientRef.current) {
      clientRef.current.disconnect();
    }

    const client = new VoiceWSClient(sessionId);
    clientRef.current = client;

    client.onMessage((msg) => {
      const store = useCallStore.getState();

      switch (msg.type) {
        case 'call_started':
          store.setStatus('active');
          store.setAgent(msg.agentId as string, msg.agentName as string);
          break;

        case 'call_ended':
          store.setStatus('ended');
          break;

        case 'agent_switch':
          store.setAgent(msg.agentId as string, msg.agentName as string);
          store.addTranscript({
            role: 'system',
            text: `已切换至 ${msg.agentName}`,
          });
          break;

        case 'transcript_entry':
          store.addTranscript({
            role: msg.role as 'user' | 'agent' | 'system',
            text: msg.text as string,
            agentName: msg.agentName as string | undefined,
          });
          break;

        case 'llm_token':
          store.appendLLMToken(msg.text as string);
          break;

        case 'llm_done':
          store.setLLMPartial('');
          break;

        case 'tts_chunk':
          // Audio chunks handled by binary frame callback
          break;

        case 'tts_done':
          store.setTTSPlaying(false);
          break;

        case 'tts_stop':
          store.setTTSPlaying(false);
          store.setLLMPartial('');
          store.setWaiting(false);
          window.dispatchEvent(new CustomEvent('voice:tts_stop'));
          break;

        case 'tool_call_start':
          store.setWaiting(true, msg.message as string);
          break;

        case 'tool_call_end':
          store.setWaiting(false);
          break;

        case 'waiting_start':
          store.setWaiting(true, msg.message as string);
          break;

        case 'waiting_end':
          store.setWaiting(false);
          break;

        case 'error':
          store.addTranscript({ role: 'system', text: `错误: ${msg.message}` });
          break;
      }
    });

    if (onAudioChunk) {
      client.onBinary(onAudioChunk);
    }

    await client.connect();
    return client;
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
    clientRef.current = null;
  }, []);

  const sendText = useCallback((text: string) => {
    clientRef.current?.send({ type: 'text_input', text });
    useCallStore.getState().setLLMPartial('');
  }, []);

  const startCall = useCallback((scenario: string, inputMode: string, agentGroupId: string) => {
    clientRef.current?.send({ type: 'start_call', scenario, inputMode, agentGroupId });
  }, []);

  const endCall = useCallback(() => {
    clientRef.current?.send({ type: 'end_call' });
  }, []);

  const interrupt = useCallback(() => {
    clientRef.current?.send({ type: 'interrupt' });
  }, []);

  const sendAudioChunk = useCallback((data: ArrayBuffer) => {
    clientRef.current?.sendAudio(data);
  }, []);

  const sendAudioEnd = useCallback(() => {
    clientRef.current?.send({ type: 'audio_end' });
  }, []);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  return {
    connect,
    disconnect,
    sendText,
    startCall,
    endCall,
    interrupt,
    sendAudioChunk,
    sendAudioEnd,
    isConnected: () => clientRef.current?.connected ?? false,
  };
}
