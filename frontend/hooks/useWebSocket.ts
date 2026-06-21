"use client";
import { useEffect, useRef, useState } from "react";

export type WsMessageType =
  | "connected"
  | "pong"
  | "portfolio_update"
  | "market_event";

export interface WsMessage {
  type:          WsMessageType;
  timestamp?:    string;
  // portfolio_update fields
  portfolio_id?:   number;
  portfolio_name?: string;
  total_value?:    number;
  change_pct?:     number;
  currency?:       string;
  strategy_type?:  string;
  // market_event fields
  source?: string;
  data?:   Record<string, unknown>;
  // connected fields
  message?:     string;
  connections?: number;
}

const WS_URL = "ws://localhost:8000/ws";
const PING_INTERVAL_MS  = 20_000;   // heartbeat every 20 s
const INITIAL_RETRY_MS  = 1_000;
const MAX_RETRY_MS      = 30_000;

/**
 * Reconnecting WebSocket hook.
 *
 * Usage:
 *   const { connected } = useWebSocket((msg) => {
 *     if (msg.type === "portfolio_update") { ... }
 *   });
 *
 * - Auto-reconnects with exponential backoff (1 s → 30 s cap).
 * - Sends a "ping" heartbeat every 20 s to keep the connection alive.
 * - Stable: the `onMessage` callback ref is updated each render so
 *   you can safely pass an inline function without re-subscribing.
 */
export function useWebSocket(onMessage: (msg: WsMessage) => void): {
  connected: boolean;
} {
  const [connected, setConnected] = useState(false);
  const wsRef        = useRef<WebSocket | null>(null);
  const retryMs      = useRef(INITIAL_RETRY_MS);
  const retryTimer   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimer    = useRef<ReturnType<typeof setInterval> | null>(null);
  const unmounted    = useRef(false);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;  // always latest without re-subscribing

  useEffect(() => {
    unmounted.current = false;

    function connect() {
      if (unmounted.current) return;

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retryMs.current = INITIAL_RETRY_MS;

        // Heartbeat ping to keep the connection alive through proxies
        pingTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        }, PING_INTERVAL_MS);
      };

      ws.onmessage = (event) => {
        try {
          const msg: WsMessage = JSON.parse(event.data);
          if (msg.type !== "pong") onMessageRef.current(msg);
        } catch {
          // malformed JSON — ignore
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (pingTimer.current) clearInterval(pingTimer.current);
        if (!unmounted.current) {
          retryTimer.current = setTimeout(() => {
            retryMs.current = Math.min(retryMs.current * 2, MAX_RETRY_MS);
            connect();
          }, retryMs.current);
        }
      };

      ws.onerror = () => {
        ws.close(); // triggers onclose which schedules retry
      };
    }

    connect();

    return () => {
      unmounted.current = true;
      if (pingTimer.current)  clearInterval(pingTimer.current);
      if (retryTimer.current) clearTimeout(retryTimer.current);
      wsRef.current?.close();
    };
  }, []); // only on mount/unmount

  return { connected };
}
