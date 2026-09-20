"use client";

import { useEffect, useState } from "react";

import { CameraFeed } from "@/components/camera/camera-feed";
import { RunStatePill } from "@/components/inspection/run-state-pill";
import { findingMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { Button, RingIcon } from "@/components/ui/button";
import { CardGrid, Panel, StatCard } from "@/components/ui/card";
import { Notice, StatusMessage } from "@/components/ui/feedback";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { LogRow } from "@/components/ui/log-row";
import type { DriveDirection, MotionTelemetryEvent } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { kindTone } from "@/lib/defects";
import {
  NOT_AVAILABLE,
  defectClassLabel,
  formatAgo,
  formatConfidence,
  formatDetectRate,
  formatDriveSpeed,
  formatMetres,
  formatNumber,
  formatSpan,
  isRunActive,
} from "@/lib/format";
import { useCurrentSelection, useRopeHistory } from "@/lib/hooks/use-inspection";
import { useNow } from "@/lib/hooks/use-now";
import { useFreshTelemetry, useFreshVision, useRobotConnected, useRobotLink } from "@/lib/robot/robot-link";
import { useVideoFeeds } from "@/lib/robot/use-video-feeds";
import { routes } from "@/lib/routes";

const REFRESH_MS = 5_000;
/** How long a command may go without matching telemetry before the operator is warned. */
const CONFIRM_TIMEOUT_MS = 5_000;
const NO_TELEMETRY = "No motion telemetry from the robot in the last 2 seconds";
const NO_VISION = "The robot has not reported a detector frame recently";

const CAMERAS = [
  { code: "cam a", caption: "Camera A, upper rope surface" },
  { code: "cam b", caption: "Camera B, lower rope surface" },
];

interface SentCommand {
  /** What the robot should be doing: scanning in this direction, or standing still. */
  expected: DriveDirection | "stop";
  /** Epoch ms when the command was written to the server socket. */
  at: number;
}

/** True once the robot's own telemetry shows it doing what the command asked for. */
function carriedOut(sent: SentCommand, telemetry: MotionTelemetryEvent): boolean {
  if (sent.expected === "stop") return telemetry.speed === 0;
  const wanted = sent.expected === "forward" ? 1 : -1;
  return telemetry.speed !== 0 && Math.sign(telemetry.speed) === wanted;
}

/**
 * Neither the server nor the robot acknowledges commands, so a command only counts as carried
 * out once the robot's own telemetry reports it.
 */
function commandFeedback(
  sent: SentCommand | null,
  telemetry: MotionTelemetryEvent | null,
  telemetryAt: number | null,
  telemetryFresh: boolean,
  now: number | null,
): { text: string; tone: "muted" | "error" } | null {
  if (!sent) return null;
  const asked = sent.expected === "stop" ? "standstill" : `scanning ${sent.expected}`;
  const reported = telemetry && telemetryAt !== null && telemetryAt > sent.at ? telemetry : null;
  const reports = telemetryFresh ? "Robot reports" : "Robot last reported";
  const staleNote =
    telemetryFresh || telemetryAt === null || now === null
      ? ""
      : ` ${formatAgo(Math.max(0, now - telemetryAt))}, no telemetry since`;

  if (reported && carriedOut(sent, reported)) {
    const doing = reported.speed === 0 ? "standstill" : formatDriveSpeed(reported.speed_mps);
    return { text: `${reports} ${doing}${staleNote}.`, tone: telemetryFresh ? "muted" : "error" };
  }

  const waited = now === null ? 0 : Math.max(0, now - sent.at);
  if (waited <= CONFIRM_TIMEOUT_MS) {
    const what = sent.expected === "stop" ? "Stop" : `Start ${sent.expected}`;
    return { text: `${what} sent to the server, waiting for the robot to report it.`, tone: "muted" };
  }
  return {
    tone: "error",
    text: reported
      ? `${reports} ${formatDriveSpeed(reported.speed_mps)}${staleNote}, expected ${asked}.`
      : `No telemetry from the robot since the command was sent ${formatAgo(waited)}. Do not assume it is at ${asked}.`,
  };
}

export function LiveView() {
  const { socket, telemetry, telemetryAt, detectionVersion, lastError, send } = useRobotLink();
  const connected = useRobotConnected();
  const fresh = useFreshTelemetry();
  const vision = useFreshVision();
  const now = useNow(500);
  const feeds = useVideoFeeds(CAMERAS.length);

  const [direction, setDirection] = useState<DriveDirection>("forward");
  const [sent, setSent] = useState<SentCommand | null>(null);

  const current = useCurrentSelection();
  const ropeId = current.data?.rope_id ?? null;
  const history = useRopeHistory(ropeId, { refreshMs: REFRESH_MS });

  const rope = history.data?.rope;
  const run = history.data?.runs.find((r) => r.id === current.data?.run_id);
  const running = connected && isRunActive(run);
  const findings = run ? (history.data?.findingsByRun[run.id] ?? []) : [];
  // Newest finding first: the run walks the rope, so the last detection is the newest one.
  const newestFirst = [...findings].sort((a, b) =>
    b.best.created_at.localeCompare(a.best.created_at),
  );

  // The socket says a frame found something but carries no row ids, so the stored run is
  // pulled in right away instead of waiting for the next poll.
  const { reload } = history;
  useEffect(() => {
    if (detectionVersion > 0) reload();
  }, [detectionVersion, reload]);

  // Reversing a moving robot on one click is not something the operator should be able to do
  // by accident, so the direction is only picked while it stands still.
  const moving = fresh !== null && fresh.speed !== 0;
  const motion = fresh === null ? "unknown" : moving ? "scanning" : "stopped";
  const feedback = commandFeedback(sent, telemetry, telemetryAt, fresh !== null, now);

  const start = () => {
    if (!send({ type: "start", direction })) return;
    setSent({ expected: direction, at: Date.now() });
  };

  const stop = () => {
    if (!send({ type: "stop" })) return;
    setSent({ expected: "stop", at: Date.now() });
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
          value={fresh ? formatMetres(fresh.metres) : NOT_AVAILABLE}
          label={`Position on rope of ${formatMetres(rope?.length_m)}`}
          indicator="ring"
          title={fresh ? "Measured from where the robot stood when the run was selected" : NO_TELEMETRY}
        />
        <StatCard
          value={fresh ? formatDriveSpeed(fresh.speed_mps) : NOT_AVAILABLE}
          label="Drive speed"
          indicator="solid"
          title={fresh ? undefined : NO_TELEMETRY}
        />
        <StatCard
          value={vision ? `${formatNumber(vision.inference_ms)} ms` : NOT_AVAILABLE}
          label={vision ? `Detector, ${vision.detections.length} in the last frame` : "Detector"}
          indicator={vision ? "solid" : "muted"}
          title={vision ? undefined : NO_VISION}
        />
        <StatCard value={run ? findings.length : NOT_AVAILABLE} label="Findings this run" indicator="warning" />
      </CardGrid>

      <SectionTitle>Cameras</SectionTitle>
      <div className="flex flex-wrap gap-3.5">
        {CAMERAS.map((camera, i) => (
          <CameraFeed key={camera.code} caption={camera.caption} feed={feeds[i]} />
        ))}
      </div>

      <SectionTitle>Position on rope</SectionTitle>
      <Panel className="px-[22px] py-5">
        {rope ? (
          <RopeStrip
            length={rope.length_m}
            marks={findingMarks(rope.id, findings)}
            livePos={fresh ? fresh.metres : null}
          />
        ) : (
          <p className="m-0 text-[13px] text-text-subtle">No rope is selected on the server.</p>
        )}
      </Panel>

      <SectionTitle>Log</SectionTitle>
      <Panel className="flex flex-col gap-[7px] p-4">
        {rope &&
          newestFirst.map((f) => (
            <LogRow
              key={f.best.id}
              href={routes.defect(rope.id, f.best.run_id, f.best.id)}
              tone={kindTone(f.kind)}
              position={formatSpan(f.from, f.to)}
            >
              {defectClassLabel(f.best.label)} · {formatConfidence(f.confidence)}
              {f.detections.length > 1 && ` · ${f.detections.length}x`}
            </LogRow>
          ))}
        <div className="px-1 pt-1.5 pb-0.5 text-xs leading-none text-text-subtle">
          {!run
            ? "No run is selected on the server."
            : findings.length === 0
              ? "No detections in this run yet."
              : `Updates when the robot reports a detection, otherwise every ${REFRESH_MS / 1000} s`}
        </div>
      </Panel>

      <SectionTitle>Drive</SectionTitle>
      <Panel className="flex flex-col gap-[18px] px-[22px] py-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-col gap-2">
            <span className="text-[13px] leading-none text-text-muted">Scan speed</span>
            <span className="text-[22px] leading-[1.15] font-bold">
              {fresh ? formatDriveSpeed(fresh.scan_speed_mps) : NOT_AVAILABLE}
            </span>
          </div>
          <div role="group" aria-label="Direction" className="flex gap-2">
            <Button
              variant={direction === "forward" ? "primary" : "secondary"}
              aria-pressed={direction === "forward"}
              disabled={moving}
              title={moving ? "Stop the robot before changing direction" : undefined}
              onClick={() => setDirection("forward")}
            >
              Forward
            </Button>
            <Button
              variant={direction === "reverse" ? "primary" : "secondary"}
              aria-pressed={direction === "reverse"}
              disabled={moving}
              title={moving ? "Stop the robot before changing direction" : undefined}
              onClick={() => setDirection("reverse")}
            >
              Reverse
            </Button>
          </div>
        </div>

        <p className="m-0 text-xs leading-normal text-text-subtle">
          The robot sets its own speed: it times its detector at startup and drives exactly fast
          enough for the camera frames to cover the rope end to end.{" "}
          {fresh
            ? `It runs the detector ${formatDetectRate(fresh.detect_fps)} and holds ${formatDriveSpeed(fresh.scan_speed_mps)}.`
            : "Its plan arrives with the motion telemetry."}
        </p>

        <div className="flex flex-wrap gap-3.5">
          <Button
            className="flex-[1_1_220px]"
            disabled={!connected || moving}
            title={
              !connected ? "The robot is not reachable" : moving ? "The robot is already scanning" : undefined
            }
            onClick={start}
          >
            Start scanning {direction}
          </Button>
          <Button
            variant="secondary"
            className="flex-[1_1_220px]"
            disabled={socket !== "open"}
            onClick={stop}
          >
            Stop
          </Button>
        </div>

        <div
          className={cn(
            "border-t border-surface-strong pt-4 font-mono text-[13px] leading-[1.4]",
            fresh ? "text-text-muted" : "text-danger-strong",
          )}
        >
          {fresh
            ? `Robot reports ${formatDriveSpeed(fresh.speed_mps)} · ${formatMetres(fresh.metres)} · ${formatNumber(fresh.microsteps)} microsteps · seq ${formatNumber(fresh.seq)}`
            : telemetry && telemetryAt !== null && now !== null
              ? `No fresh telemetry. Last report ${formatAgo(Math.max(0, now - telemetryAt))}: ${formatDriveSpeed(telemetry.speed_mps)}`
              : "No telemetry from the robot yet"}
        </div>
      </Panel>

      <div className="mt-[38px] flex flex-wrap gap-3.5">
        <Button
          variant="danger"
          size="lg"
          className="flex-[1_1_260px]"
          disabled={socket !== "open"}
          onClick={stop}
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
            motion === "scanning"
              ? "border-success-line bg-linear-to-r from-success-soft to-[#d3f0dd] text-success-ink"
              : "border-line-strong bg-surface text-text-muted",
          )}
        >
          <RingIcon className="border-current" />
          {motion === "scanning" ? "Scanning" : motion === "stopped" ? "Stopped" : "Motion unknown"}
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
