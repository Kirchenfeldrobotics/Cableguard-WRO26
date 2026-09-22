"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import type {
  DistanceTelemetryEvent,
  MotionTelemetryEvent,
  RobotCommand,
  ServerEvent,
  VisionTelemetryEvent,
} from "@/lib/api/types";
import { wsUrl } from "@/lib/config";
import { useNow } from "@/lib/hooks/use-now";

export type SocketState = "connecting" | "open" | "closed";

/**
 * The robot sends a heartbeat every 5 s (robot/src/link/client.py). After two missed
 * heartbeats the robot counts as lost, even while the server still reports it online:
 * the server only notices a dead robot link when its pings time out.
 */
export const ROBOT_SILENT_MS = 12_000;

/** The robot sends motion telemetry every 0.5 s (robot/src/app/main.py). */
export const TELEMETRY_STALE_MS = 2_000;

/** The robot sends a distance reading every 0.5 s (robot/src/app/main.py). */
export const DISTANCE_STALE_MS = 2_000;

/**
 * The robot reports one vision frame per camera every DETECT_PERIOD (2 s), so two per cycle.
 * Past this the detector counts as silent, even while the robot itself still answers.
 */
export const VISION_STALE_MS = 8_000;

export interface RobotLinkValue {
  /** Browser <-> server socket. */
  socket: SocketState;
  /** Server <-> robot link, as reported by the server. */
  robotOnline: boolean;
  telemetry: MotionTelemetryEvent | null;
  /** Epoch ms when `telemetry` arrived. */
  telemetryAt: number | null;
  /** Last reading of the robot's distance sensor. */
  distance: DistanceTelemetryEvent | null;
  /** Epoch ms when `distance` arrived. */
  distanceAt: number | null;
  /** Last frame the detector reported, whether or not it found anything. */
  vision: VisionTelemetryEvent | null;
  /** Epoch ms when `vision` arrived. */
  visionAt: number | null;
  /**
   * Increments whenever the robot reports a frame with detections. The socket carries no
   * defect ids, so this only says "something was found": reload the run to get the rows.
   */
  detectionVersion: number;
  /** Epoch ms of the last sign of life from the robot: online status, heartbeat or telemetry. */
  robotSeenAt: number | null;
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
  const [telemetryAt, setTelemetryAt] = useState<number | null>(null);
  const [distance, setDistance] = useState<DistanceTelemetryEvent | null>(null);
  const [distanceAt, setDistanceAt] = useState<number | null>(null);
  const [vision, setVision] = useState<VisionTelemetryEvent | null>(null);
  const [visionAt, setVisionAt] = useState<number | null>(null);
  const [detectionVersion, setDetectionVersion] = useState(0);
  const [robotSeenAt, setRobotSeenAt] = useState<number | null>(null);
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
        const now = Date.now();
        setLastMessageAt(now);
        let event: ServerEvent;
        try {
          event = JSON.parse(e.data);
        } catch {
          return;
        }
        switch (event.type) {
          case "robot_status":
            setRobotOnline(event.online);
            if (event.online) setRobotSeenAt(now);
            break;
          case "alive":
            setRobotSeenAt(now);
            break;
          case "motion_telemetry":
            setTelemetry(event);
            setTelemetryAt(now);
            setRobotSeenAt(now);
            break;
          case "distance_telemetry":
            setDistance(event);
            setDistanceAt(now);
            setRobotSeenAt(now);
            break;
          case "vision_telemetry":
            setVision(event);
            setVisionAt(now);
            setRobotSeenAt(now);
            if (event.detections.length > 0) setDetectionVersion((v) => v + 1);
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
        if (sockRef.current === ws) sockRef.current = null;
        if (disposed) return;
        setRobotOnline(false);
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
      value={{
        socket,
        robotOnline,
        telemetry,
        telemetryAt,
        distance,
        distanceAt,
        vision,
        visionAt,
        detectionVersion,
        robotSeenAt,
        lastMessageAt,
        lastError,
        currentVersion,
        send,
      }}
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

/**
 * True when the browser reaches the server, the server reports the robot online and the
 * robot has been heard from within ROBOT_SILENT_MS.
 */
export function useRobotConnected(): boolean {
  const { socket, robotOnline, robotSeenAt } = useRobotLink();
  const now = useNow();
  const silent = now !== null && robotSeenAt !== null && now - robotSeenAt > ROBOT_SILENT_MS;
  return socket === "open" && robotOnline && !silent;
}

/** The latest telemetry while it is fresh and the robot is connected, otherwise null. */
export function useFreshTelemetry(): MotionTelemetryEvent | null {
  const { telemetry, telemetryAt } = useRobotLink();
  const connected = useRobotConnected();
  const now = useNow(500);
  if (!connected || telemetry === null || telemetryAt === null || now === null) return null;
  return now - telemetryAt <= TELEMETRY_STALE_MS ? telemetry : null;
}

/** The latest distance reading while it is fresh and the robot is connected, otherwise null. */
export function useFreshDistance(): DistanceTelemetryEvent | null {
  const { distance, distanceAt } = useRobotLink();
  const connected = useRobotConnected();
  const now = useNow(500);
  if (!connected || distance === null || distanceAt === null || now === null) return null;
  return now - distanceAt <= DISTANCE_STALE_MS ? distance : null;
}

/** The latest vision frame while the detector is still reporting, otherwise null. */
export function useFreshVision(): VisionTelemetryEvent | null {
  const { vision, visionAt } = useRobotLink();
  const connected = useRobotConnected();
  const now = useNow(500);
  if (!connected || vision === null || visionAt === null || now === null) return null;
  return now - visionAt <= VISION_STALE_MS ? vision : null;
}
