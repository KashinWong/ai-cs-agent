import { useEffect, useRef } from "react";

import { getToken } from "../api/client";

type Envelope = { type: string; data: any; ts: number };
type Handler = (env: Envelope) => void;

/** 连接 /ws/agent，事件分发 + 指数退避重连（T068）。 */
export function useAgentSocket(onEvent: Handler): void {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    let ws: WebSocket | null = null;
    let retry = 0;
    let closed = false;
    let timer: number | undefined;

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${location.host}/ws/agent?token=${encodeURIComponent(token)}`);
      ws.onopen = () => {
        retry = 0;
      };
      ws.onmessage = (e) => {
        try {
          handlerRef.current(JSON.parse(e.data));
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        if (closed) return;
        const backoff = Math.min(1000 * 2 ** retry++, 10000);
        timer = window.setTimeout(connect, backoff);
      };
    };
    connect();

    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      ws?.close();
    };
  }, []);
}
