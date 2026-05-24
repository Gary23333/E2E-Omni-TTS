import type { WSMessage } from '../types';

type MessageHandler = (msg: WSMessage) => void;

export class VoiceWSClient {
  private ws: WebSocket | null = null;
  private handlers: MessageHandler[] = [];
  private sessionId: string;
  private reconnectAttempts = 0;
  private maxReconnect = 3;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  onMessage(handler: MessageHandler) {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter(h => h !== handler);
    };
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8900';
      const url = new URL(apiBaseUrl);
      const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = url.host;
      this.ws = new WebSocket(`${protocol}//${host}/ws/voice/${this.sessionId}`);
      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        resolve();
      };

      this.ws.onerror = (e) => {
        console.error('WebSocket error:', e);
        reject(e);
      };

      this.ws.onclose = () => {
        this.ws = null;
      };

      this.ws.onmessage = (event) => {
        if (typeof event.data === 'string') {
          try {
            const msg = JSON.parse(event.data) as WSMessage;
            this.handlers.forEach(h => h(msg));
          } catch {
            console.warn('Invalid WS message:', event.data);
          }
        }
      };
    });
  }

  send(msg: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  sendAudio(data: ArrayBuffer) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
