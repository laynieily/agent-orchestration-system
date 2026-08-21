import { useEffect, useRef } from "react";

const WS_URL = "ws://127.0.0.1:8000/ws";
const RECONNECT_DELAY_MS = 2000;

/**
 * Subscribes to the backend's /ws broadcast channel and invokes `onMessage`
 * for every event (task created/paused/resolved/completed). Reconnects
 * automatically if the connection drops.
 */
export function useTaskEvents(onMessage: (data: any) => void) {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    function connect() {
      ws = new WebSocket(WS_URL);

      ws.onmessage = (event) => {
        try {
          onMessageRef.current(JSON.parse(event.data));
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!stopped) {
          retryTimeout = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };
    }

    connect();

    return () => {
      stopped = true;
      clearTimeout(retryTimeout);
      ws?.close();
    };
  }, []);
}
