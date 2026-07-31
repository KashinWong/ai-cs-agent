// 极简 WS 客户端：连接、指数退避重连、JSON 信封收发（T041）。
export type Envelope = { type: string; data: any; ts: number };
export type Handler = (env: Envelope) => void;

export class WidgetSocket {
  private ws: WebSocket | null = null;
  private readonly urlFn: () => string;
  private readonly handler: Handler;
  private retry = 0;
  private closed = false;

  constructor(urlFn: () => string, handler: Handler) {
    this.urlFn = urlFn;
    this.handler = handler;
  }

  connect(): void {
    this.ws = new WebSocket(this.urlFn());
    this.ws.onopen = () => {
      this.retry = 0;
    };
    this.ws.onmessage = (e) => {
      try {
        this.handler(JSON.parse(e.data));
      } catch {
        /* ignore malformed */
      }
    };
    this.ws.onclose = () => {
      if (this.closed) return;
      const backoff = Math.min(1000 * 2 ** this.retry++, 10000);
      setTimeout(() => this.connect(), backoff);
    };
  }

  send(type: string, data: Record<string, unknown> = {}): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data, ts: Date.now() }));
    }
  }

  close(): void {
    this.closed = true;
    this.ws?.close();
  }
}
