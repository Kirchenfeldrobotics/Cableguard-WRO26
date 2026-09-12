"use client";

import { useState } from "react";

import { CameraFeed } from "@/components/camera/camera-feed";
import { RunStatePill } from "@/components/inspection/run-state-pill";
import { defectMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { Button, RingIcon } from "@/components/ui/button";
import { CardGrid, Panel, StatCard } from "@/components/ui/card";
import { Notice, StatusMessage } from "@/components/ui/feedback";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { LogRow } from "@/components/ui/log-row";
import type { MotionTelemetryEvent } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { MAX_DRIVE_SPEED, MIN_DRIVE_SPEED } from "@/lib/config";
import { kindTone } from "@/lib/defects";
import {
  NOT_AVAILABLE,
  defectTypeLabel,
  formatAgo,
  formatDriveSpeed,
  formatMetres,
  formatNumber,
  isRunActive,
  shortId,
} from "@/lib/format";
import { useCurrentSelection, useRopeHistory } from "@/lib/hooks/use-inspection";
import { useNow } from "@/lib/hooks/use-now";
import { useFreshTelemetry, useRobotConnected, useRobotLink } from "@/lib/robot/robot-link";
import { useVideoFeeds } from "@/lib/robot/use-video-feeds";
import { routes } from "@/lib/routes";

const REFRESH_MS = 5_000;
const SPEED_STEP = 50;
/** How long a command may go without matching telemetry before the operator is warned. */
const CONFIRM_TIMEOUT_MS = 5_000;
const NO_TELEMETRY = "No motion telemetry from the robot in the last 2 seconds";

const CAMERAS = [
  { code: "cam a", caption: "Camera A, upper rope surface" },
  { code: "cam b", caption: "Camera B, lower rope surface" },
];

type Direction = "forward" | "reverse";

interface SentCommand {
  /** Signed speed the robot should settle at, 0 for a stop. */
  expected: number;
  /** Epoch ms when the command was written to the server socket. */
  at: number;
}

/** Speed the robot settles at for a speed command, after its own clamping. */
function settledSpeed(value: number): number {
  const magnitude = Math.min(Math.abs(value), MAX_DRIVE_SPEED);
  return magnitude < MIN_DRIVE_SPEED ? 0 : Math.sign(value) * magnitude;
}

/**
 * Neither the server nor the robot acknowledges commands, so a command only counts as carried
 * out once the robot's own telemetry reports the expected speed.
 */
function commandFeedback(
  sent: SentCommand | null,
  telemetry: MotionTelemetryEvent | null,
  telemetryAt: number | null,
  telemetryFresh: boolean,
  now: number | null,
): { text: string; tone: "muted" | "error" } | null {
  if (!sent) return null;
  const expected = sent.expected === 0 ? "standstill" : formatDriveSpeed(sent.expected);
  const reported = telemetry && telemetryAt !== null && telemetryAt > sent.at ? telemetry : null;
  const reports = telemetryFresh ? "Robot reports" : "Robot last reported";
  const staleNote =
    telemetryFresh || telemetryAt === null || now === null
      ? ""
      : ` ${formatAgo(Math.max(0, now - telemetryAt))}, no telemetry since`;
  if (reported && Math.abs(reported.speed - sent.expected) <= 1) {
    return { text: `${reports} ${expected}${staleNote}.`, tone: telemetryFresh ? "muted" : "error" };
  }
  const waited = now === null ? 0 : Math.max(0, now - sent.at);
  if (waited <= CONFIRM_TIMEOUT_MS) {
    const what = sent.expected === 0 ? "Stop" : `Speed ${expected}`;
    return { text: `${what} sent to the server, waiting for the robot to report it.`, tone: "muted" };
  }
  return {
    tone: "error",
    text: reported
      ? `${reports} ${formatDriveSpeed(reported.speed)}${staleNote}, expected ${expected}.`
      : `No telemetry from the robot since the command was sent ${formatAgo(waited)}. Do not assume it reached ${expected}.`,
  };
}

export function LiveView() {
  const { socket, telemetry, telemetryAt, lastError, send } = useRobotLink();
  const connected = useRobotConnected();
  const fresh = useFreshTelemetry();
  const now = useNow(500);
  const feeds = useVideoFeeds(CAMERAS.length);

  const [magnitude, setMagnitude] = useState(0);
  const [direction, setDirection] = useState<Direction>("forward");
  const [lastDriven, setLastDriven] = useState<number | null>(null);
  const [stopRequested, setStopRequested] = useState(false);
  const [sent, setSent] = useState<SentCommand | null>(null);

  const current = useCurrentSelection();
  const ropeId = current.data?.rope_id ?? null;
  const history = useRopeHistory(ropeId, { refreshMs: REFRESH_MS });

  const rope = history.data?.rope;
  const run = history.data?.runs.find((r) => r.id === current.data?.run_id);
  const running = connected && isRunActive(run);
  const defects = run ? (history.data?.defectsByRun[run.id] ?? []) : [];
  const newestFirst = [...defects].sort((a, b) => b.created_at.localeCompare(a.created_at));

  const target = direction === "forward" ? magnitude : -magnitude;
  const stoppedOnItsOwn =
    fresh?.speed === 0 && sent !== null && now !== null && now - sent.at > CONFIRM_TIMEOUT_MS;
  const resumeSpeed = lastDriven !== null && (stopRequested || stoppedOnItsOwn) ? lastDriven : null;
  const motion = fresh === null ? "unknown" : fresh.speed === 0 ? "stopped" : "moving";
  const feedback = commandFeedback(sent, telemetry, telemetryAt, fresh !== null, now);

  const drive = (speed: number) => {
    if (!send({ type: "speed", value: speed })) return;
    const expected = settledSpeed(speed);
    setSent({ expected, at: Date.now() });
    setLastDriven(expected === 0 ? null : expected);
    setStopRequested(false);
  };

  const emergencyStop = () => {
    if (!send({ type: "stop" })) return;
    setSent({ expected: 0, at: Date.now() });
    setStopRequested(true);
  };

  return (
    <>
      <PageHeader title="Inspection data">
        <RunStatePill running={running} />
        {rope && <HeadingMeta>{rope.name}</HeadingMeta>}
      </PageHeader>

      {socket !== "open" ? (
        <Notice>
          Connection to the server is lost, so no command can be sent. The values below are the last
          received state. The robot keeps executing its last command for as long as its own link to the
          server is up.
        </Notice>
      ) : (
        !connected && (
          <Notice>
            The robot is not reachable. The values below are the last received state. The robot ramps
            down to standstill by itself once it detects the lost link, which can take about 30 seconds.
          </Notice>
        )
      )}

      <CardGrid>
        <StatCard
          value={NOT_AVAILABLE}
          label="Position on rope"
          indicator="ring"
          title="The robot does not report its position yet"
        />
        <StatCard
          value={fresh ? formatDriveSpeed(fresh.speed) : NOT_AVAILABLE}
          label="Drive speed"
          indicator="solid"
          title={fresh ? undefined : NO_TELEMETRY}
        />
        <StatCard
          value={NOT_AVAILABLE}
          label={`Distance covered of ${formatMetres(rope?.length_m)}`}
          indicator="muted"
          title="The robot does not report distance yet"
        />
        <StatCard value={run ? defects.length : NOT_AVAILABLE} label="Defects this run" indicator="warning" />
      </CardGrid>

      <SectionTitle>Cameras</SectionTitle>
      <div className="flex flex-wrap gap-3.5">
        {CAMERAS.map((camera, i) => (
          <CameraFeed key={camera.code} code={camera.code} caption={camera.caption} feed={feeds[i]} />
        ))}
      </div>

      <SectionTitle>Position on rope</SectionTitle>
      <Panel className="px-[22px] py-5">
        {rope ? (
          <RopeStrip length={rope.length_m} marks={defectMarks(rope.id, defects)} />
        ) : (
          <p className="m-0 text-[13px] text-text-subtle">No rope is selected on the server.</p>
        )}
      </Panel>

      <SectionTitle>Log</SectionTitle>
      <Panel className="flex flex-col gap-[7px] p-4">
        {rope &&
          newestFirst.map((d) => (
            <LogRow
              key={d.id}
              href={routes.defect(rope.id, d.run_id, d.id)}
              tone={kindTone(d.kind)}
              position={formatMetres(d.pos_to_start)}
            >
              {defectTypeLabel(d.kind)} · {shortId(d.id)}
            </LogRow>
          ))}
        <div className="px-1 pt-1.5 pb-0.5 text-xs leading-none text-text-subtle">
          {!run
            ? "No run is selected on the server."
            : defects.length === 0
              ? "No detections in this run yet."
              : `Refreshes every ${REFRESH_MS / 1000} s`}
        </div>
      </Panel>

      <SectionTitle>Drive</SectionTitle>
      <Panel className="flex flex-col gap-[18px] px-[22px] py-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-col gap-2">
            <span className="text-[13px] leading-none text-text-muted">Target speed</span>
            <span className="text-[22px] leading-[1.15] font-bold">{formatDriveSpeed(target)}</span>
          </div>
          <div role="group" aria-label="Direction" className="flex gap-2">
            <Button
              variant={direction === "forward" ? "primary" : "secondary"}
              aria-pressed={direction === "forward"}
              onClick={() => setDirection("forward")}
            >
              Forward
            </Button>
            <Button
              variant={direction === "reverse" ? "primary" : "secondary"}
              aria-pressed={direction === "reverse"}
              onClick={() => setDirection("reverse")}
            >
              Reverse
            </Button>
          </div>
        </div>

        <div>
          <input
            type="range"
            min={0}
            max={MAX_DRIVE_SPEED}
            step={SPEED_STEP}
            value={magnitude}
            onChange={(e) => setMagnitude(Number(e.target.value))}
            aria-label="Target speed"
            aria-valuetext={formatDriveSpeed(target)}
            className="w-full accent-ink"
          />
          <div className="mt-2 flex justify-between gap-4 font-mono text-xs leading-none text-text-subtle">
            <span>0</span>
            <span>{formatNumber(MAX_DRIVE_SPEED)} steps/s</span>
          </div>
        </div>

        <p className="m-0 text-xs leading-normal text-text-subtle">
          Nothing is sent until you press Drive. Below {formatNumber(MIN_DRIVE_SPEED)} steps/s the robot
          ramps down to standstill.
        </p>

        <div className="flex flex-wrap gap-3.5">
          <Button
            className="flex-[1_1_220px]"
            disabled={!connected}
            title={connected ? undefined : "The robot is not reachable"}
            onClick={() => drive(target)}
          >
            {settledSpeed(target) === 0 ? "Ramp down to standstill" : `Drive at ${formatDriveSpeed(target)}`}
          </Button>
          <Button
            variant="secondary"
            className="flex-[1_1_220px]"
            disabled={!connected || resumeSpeed === null}
            title={resumeSpeed === null ? "Available after a stop, to drive again at the last speed" : undefined}
            onClick={() => resumeSpeed !== null && drive(resumeSpeed)}
          >
            {resumeSpeed === null ? "Resume" : `Resume at ${formatDriveSpeed(resumeSpeed)}`}
          </Button>
        </div>

        <div
          className={cn(
            "border-t border-surface-strong pt-4 font-mono text-[13px] leading-[1.4]",
            fresh ? "text-text-muted" : "text-danger-strong",
          )}
        >
          {fresh
            ? `Robot reports ${formatDriveSpeed(fresh.speed)} · ${formatNumber(fresh.microsteps)} microsteps · seq ${formatNumber(fresh.seq)}`
            : telemetry && telemetryAt !== null && now !== null
              ? `No fresh telemetry. Last report ${formatAgo(Math.max(0, now - telemetryAt))}: ${formatDriveSpeed(telemetry.speed)}`
              : "No telemetry from the robot yet"}
        </div>
      </Panel>

      <div className="mt-[38px] flex flex-wrap gap-3.5">
        <Button
          variant="danger"
          size="lg"
          className="flex-[1_1_260px]"
          disabled={socket !== "open"}
          onClick={emergencyStop}
        >
          <RingIcon className="border-white" />
          Emergency stop
        </Button>
        <Button
          variant="secondary"
          size="lg"
          className="flex-[1_1_260px]"
          disabled
          title="Session planning is not available yet"
        >
          <RingIcon className="border-current" />
          Plan new session
        </Button>
        <div
          title={motion === "unknown" ? NO_TELEMETRY : undefined}
          className={cn(
            "flex h-[58px] flex-[1_1_260px] items-center justify-center gap-2.5 rounded-control border text-base leading-none font-semibold",
            motion === "moving"
              ? "border-success-line bg-linear-to-r from-success-soft to-[#d3f0dd] text-success-ink"
              : "border-line-strong bg-surface text-text-muted",
          )}
        >
          <RingIcon className="border-current" />
          {motion === "moving" ? "Moving" : motion === "stopped" ? "Stopped" : "Motion unknown"}
        </div>
      </div>

      {lastError ? (
        <StatusMessage tone="error">Server: {lastError}</StatusMessage>
      ) : (
        feedback && <StatusMessage tone={feedback.tone}>{feedback.text}</StatusMessage>
      )}
    </>
  );
}
