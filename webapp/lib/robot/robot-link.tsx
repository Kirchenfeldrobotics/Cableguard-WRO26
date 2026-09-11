"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import type { MotionTelemetryEvent, RobotCommand, ServerEvent } from "@/lib/api/types";
import { wsUrl } from "@/lib/config";

export type SocketState = "connecting" | "open" | "closed";

export interface RobotLinkValue {
  /** Browser <-> server socket. */
  socket: SocketState;
  /** Server <-> robot link, as reported by the server. */
  robotOnline: boolean;
  telemetry: MotionTelemetryEvent | null;
  /** Epoch ms of the last message received from the server. */
  lastMessageAt: number | null;
  /** Last error reported by the server, e.g. "robot offline". */
  lastError: string | null;
  /** Increments on every `current_changed` event, use it to refetch. */
  currentVersion: number;
  /** Sends a command to the robot. Returns false if the socket is not open. */
  send: (command: RobotCommand) => boolean;
}

const RobotLinkContext = createContext<RobotLinkValue | null>(null);

const RETRY_MIN_MS = 1_000;
const RETRY_MAX_MS = 10_000;

/** Holds the single /api/ws/ui connection for the whole app. */
export function RobotLinkProvider({ children }: { children: React.ReactNode }) {
  const [socket, setSocket] = useState<SocketState>("connecting");
  const [robotOnline, setRobotOnline] = useState(false);
  const [telemetry, setTelemetry] = useState<MotionTelemetryEvent | null>(null);
  const [lastMessageAt, setLastMessageAt] = useState<number | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [currentVersion, setCurrentVersion] = useState(0);
  const sockRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let disposed = false;
    let retryMs = RETRY_MIN_MS;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      setSocket("connecting");
      const ws = new WebSocket(wsUrl("/api/ws/ui"));
      sockRef.current = ws;

      ws.onopen = () => {
        retryMs = RETRY_MIN_MS;
        setSocket("open");
      };

      ws.onmessage = (e) => {
        setLastMessageAt(Date.now());
        let event: ServerEvent;
        try {
          event = JSON.parse(e.data);
        } catch {
          return;
        }
        switch (event.type) {
          case "robot_status":
            setRobotOnline(event.online);
            break;
          case "motion_telemetry":
            setTelemetry(event);
            break;
          case "current_changed":
            setCurrentVersion((v) => v + 1);
            break;
          case "error":
            setLastError(event.detail.trim());
            break;
        }
      };

      ws.onclose = () => {
        sockRef.current = null;
        setRobotOnline(false);
        if (disposed) return;
        setSocket("closed");
        retryTimer = setTimeout(connect, retryMs);
        retryMs = Math.min(retryMs * 2, RETRY_MAX_MS);
      };
    };

    connect();

    return () => {
      disposed = true;
      clearTimeout(retryTimer);
      sockRef.current?.close();
    };
  }, []);

  const send = useCallback((command: RobotCommand) => {
    const ws = sockRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    setLastError(null);
    ws.send(JSON.stringify(command));
    return true;
  }, []);

  return (
    <RobotLinkContext.Provider
      value={{ socket, robotOnline, telemetry, lastMessageAt, lastError, currentVersion, send }}
    >
      {children}
    </RobotLinkContext.Provider>
  );
}

export function useRobotLink(): RobotLinkValue {
  const value = useContext(RobotLinkContext);
  if (!value) throw new Error("useRobotLink must be used inside <RobotLinkProvider>");
  return value;
}

/** True when the browser reaches the server and the server reaches the robot. */
export function useRobotConnected(): boolean {
  const { socket, robotOnline } = useRobotLink();
  return socket === "open" && robotOnline;
}
