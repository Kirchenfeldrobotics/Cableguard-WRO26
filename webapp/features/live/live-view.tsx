"use client";

import { useEffect, useState } from "react";

import { CameraFeed } from "@/components/camera/camera-feed";
import { RunStatePill } from "@/components/inspection/run-state-pill";
import { findingMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { Button, ButtonLink, RingIcon } from "@/components/ui/button";
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
  formatDistance,
  formatDriveSpeed,
  formatMetres,
  formatNumber,
  formatSpan,
  isRunActive,
} from "@/lib/format";
import { useCurrentSelection, useRopeHistory } from "@/lib/hooks/use-inspection";
import { useNow } from "@/lib/hooks/use-now";
import {
  useFreshDistance,
  useFreshTelemetry,
  useFreshVision,
  useRobotConnected,
  useRobotLink,
} from "@/lib/robot/robot-link";
import { useVideoFeeds } from "@/lib/robot/use-video-feeds";
import { routes } from "@/lib/routes";

const REFRESH_MS = 5_000;
/** How long a command may go without matching telemetry before the operator is warned. */
const CONFIRM_TIMEOUT_MS = 5_000;

const MOTION_LABEL = { scanning: "Scanning", stopped: "Stopped", unknown: "Motion unknown" } as const;

function motionTint(motion: keyof typeof MOTION_LABEL) {
  return motion === "scanning"
    ? "border-success-line bg-linear-to-r from-success-soft to-[#d3f0dd] text-success-ink"
    : "border-line-strong bg-surface text-text-muted";
}

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
 * out once the robot's own telemetry reports it. From then on the motion state on the screen
 * says so, and there is nothing left to report here.
 */
function commandFeedback(
  sent: SentCommand | null,
  telemetry: MotionTelemetryEvent | null,
  telemetryAt: number | null,
  now: number | null,
): { text: string; tone: "muted" | "error" } | null {
  if (!sent) return null;
  const reported = telemetry && telemetryAt !== null && telemetryAt > sent.at ? telemetry : null;
  if (reported && carriedOut(sent, reported)) return null;

  const what = sent.expected === "stop" ? "Stop" : `Start ${sent.expected}`;
  const waited = now === null ? 0 : Math.max(0, now - sent.at);
  return waited <= CONFIRM_TIMEOUT_MS
    ? { text: `${what} sent, waiting for the robot.`, tone: "muted" }
    : { text: `${what} not confirmed.`, tone: "error" };
}

export function LiveView() {
  const { socket, telemetry, telemetryAt, detectionVersion, lastError, send } = useRobotLink();
  const connected = useRobotConnected();
  const fresh = useFreshTelemetry();
  const vision = useFreshVision();
  const distance = useFreshDistance();
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

  // The robot reports whether it is open, so the button says what it will do rather than
  // what was clicked last. Stale telemetry still answers it, and the line below shows a dash
  // for as long as it is stale.
  const open = telemetry?.robot_open ?? false;
  const watch = telemetry?.socket_watch ?? false;
  // Null is an answer of its own: the sensor has nothing to measure against, which is why
  // the robot will not open by itself. Undefined is a robot too old to report it at all.
  const baseline = telemetry?.socket_baseline_m ?? null;

  // Reversing a moving robot on one click is not something the operator should be able to do
  // by accident, so the direction is only picked while it stands still.
  const moving = fresh !== null && fresh.speed !== 0;
  const motion = fresh === null ? "unknown" : moving ? "scanning" : "stopped";
  const feedback = commandFeedback(sent, telemetry, telemetryAt, now);
  const status = lastError ? { text: `Server: ${lastError}`, tone: "error" as const } : feedback;

  const start = () => {
    if (!send({ type: "start", direction })) return;
    setSent({ expected: direction, at: Date.now() });
  };

  const stop = () => {
    if (!send({ type: "stop" })) return;
    setSent({ expected: "stop", at: Date.now() });
  };

  const toggleOpen = () => send({ type: open ? "close" : "open" });
  const toggleWatch = () => send({ type: "socket_watch", enabled: !watch });

  // Hiding the sidebar entry does not stop anyone typing the address, so the screen turns
  // itself away too. Stop stays reachable while the robot reports movement: locking the
  // operator out of the one control that halts a machine on a rope would be far worse
  // than the screen they walked into.
  if (current.data?.run_id == null) {
    return (
      <>
        <PageHeader title="Inspection data">
          <RunStatePill running={false} />
        </PageHeader>

        {moving && <Notice>Robot is moving.</Notice>}

        <StatusMessage>No run selected.</StatusMessage>

        <div className="mt-[18px] flex flex-wrap gap-3.5">
          <ButtonLink href={routes.dashboard} className="flex-[0_1_260px] py-[15px] text-[15px] max-sm:grow">
            Back to the dashboard
          </ButtonLink>
          {moving && (
            <Button
              variant="danger"
              className="flex-[0_1_200px] py-[15px] text-[15px] max-sm:grow"
              disabled={socket !== "open"}
              onClick={stop}
            >
              Stop the robot
            </Button>
          )}
        </div>
      </>
    );
  }

  // On a phone the sections are reordered so what is tracked comes first: numbers, where the
  // robot is on the rope, what the cameras see, then the drive and rope socket controls and the
  // log. Stop and the motion state stay pinned above the tab bar. Desktop keeps the order of
  // the markup.
  return (
    <div className="flex flex-col">
      <PageHeader title="Inspection data">
        <RunStatePill running={running} />
        {rope && <HeadingMeta>{rope.name}</HeadingMeta>}
      </PageHeader>

      <CardGrid className="max-lg:order-1">
        <StatCard
          value={fresh ? formatMetres(fresh.metres) : NOT_AVAILABLE}
          label={`Position on rope of ${formatMetres(rope?.length_m)}`}
          indicator="ring"
        />
        <StatCard
          value={fresh ? formatDriveSpeed(fresh.speed_mps) : NOT_AVAILABLE}
          label="Drive speed"
          indicator="solid"
        />
        <StatCard
          value={vision ? `${formatNumber(vision.inference_ms)} ms` : NOT_AVAILABLE}
          label={vision ? `Detector, ${vision.detections.length} in the last frame` : "Detector"}
          indicator={vision ? "solid" : "muted"}
        />
        <StatCard value={run ? findings.length : NOT_AVAILABLE} label="Findings this run" indicator="warning" />
      </CardGrid>

      <section className="max-lg:order-3">
        <SectionTitle>Cameras</SectionTitle>
        {/* Phones swipe between the cameras, the next one peeks in from the edge. */}
        <div className="-mx-4 flex snap-x snap-mandatory scroll-px-4 gap-3 overflow-x-auto px-4 [scrollbar-width:none] sm:mx-0 sm:flex-wrap sm:gap-3.5 sm:overflow-visible sm:px-0">
          {CAMERAS.map((camera, i) => (
            <CameraFeed
              key={camera.code}
              caption={camera.caption}
              feed={feeds[i]}
              className="max-sm:w-[86%] max-sm:min-w-0 max-sm:flex-none max-sm:snap-start"
            />
          ))}
        </div>
      </section>

      <section className="max-lg:order-2">
        <SectionTitle>Position on rope</SectionTitle>
        <Panel className="px-3 py-4 sm:px-[22px] sm:py-5">
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
      </section>

      {rope && newestFirst.length > 0 && (
        <section className="max-lg:order-6">
          <SectionTitle>Log</SectionTitle>
          <Panel className="flex flex-col gap-[7px] p-4">
            {newestFirst.map((f) => (
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
          </Panel>
        </section>
      )}

      <section className="max-lg:order-4">
        <SectionTitle>Drive</SectionTitle>
        <Panel className="flex flex-col gap-[18px] px-4 py-5 sm:px-[22px]">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-col gap-2">
              <span className="text-[13px] leading-none text-text-muted">Scan speed</span>
              <span className="text-[22px] leading-[1.15] font-bold">
                {fresh ? formatDriveSpeed(fresh.scan_speed_mps) : NOT_AVAILABLE}
              </span>
            </div>
            <div role="group" aria-label="Direction" className="flex gap-2 max-sm:w-full">
              <Button
                variant={direction === "forward" ? "primary" : "secondary"}
                aria-pressed={direction === "forward"}
                className="max-sm:flex-1"
                disabled={moving}
                title={moving ? "Stop first" : undefined}
                onClick={() => setDirection("forward")}
              >
                Forward
              </Button>
              <Button
                variant={direction === "reverse" ? "primary" : "secondary"}
                aria-pressed={direction === "reverse"}
                className="max-sm:flex-1"
                disabled={moving}
                title={moving ? "Stop first" : undefined}
                onClick={() => setDirection("reverse")}
              >
                Reverse
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap gap-3.5">
            <Button className="flex-[1_1_220px]" disabled={!connected || moving} onClick={start}>
              Start scanning {direction}
            </Button>
            {/* On phones Stop lives in the bar pinned above the tabs, so only one is ever in view. */}
            <Button
              variant="secondary"
              className="flex-[1_1_220px] max-lg:hidden"
              disabled={socket !== "open"}
              onClick={stop}
            >
              Stop
            </Button>
          </div>

          <div className="flex flex-col gap-1.5 border-t border-surface-strong pt-4 font-mono text-[13px] leading-[1.4]">
            <div className={fresh ? "text-text-muted" : "text-danger-strong"}>
              {fresh
                ? `Robot reports ${formatDriveSpeed(fresh.speed_mps)} · ${formatMetres(fresh.metres)} · ${formatNumber(fresh.microsteps)} microsteps · seq ${formatNumber(fresh.seq)}`
                : telemetry && telemetryAt !== null && now !== null
                  ? `No fresh telemetry. Last report ${formatAgo(Math.max(0, now - telemetryAt))}: ${formatDriveSpeed(telemetry.speed_mps)}`
                  : "No telemetry from the robot yet"}
            </div>
            <div className="text-text-muted">
              Distance sensor · {distance ? formatDistance(distance.distance_m) : NOT_AVAILABLE}
            </div>
          </div>
        </Panel>
      </section>

      <section className="max-lg:order-5">
        <SectionTitle>Rope socket</SectionTitle>
        <Panel className="flex flex-col gap-[18px] px-4 py-5 sm:px-[22px]">
          <div className="flex flex-wrap items-center gap-3.5">
            <Button size="lg" className="flex-[1_1_260px]" disabled={socket !== "open"} onClick={toggleOpen}>
              {open ? "Close robot" : "Open robot"}
            </Button>
            <Button
              variant="secondary"
              aria-pressed={watch}
              className="max-sm:grow"
              disabled={socket !== "open" || telemetry === null}
              onClick={toggleWatch}
            >
              Sensor opening {watch ? "on" : "off"}
            </Button>
          </div>

          <div className="flex flex-col gap-1.5 border-t border-surface-strong pt-4 font-mono text-[13px] leading-[1.4]">
            <div className="text-text-muted">
              Robot reports {fresh ? (fresh.robot_open ? "open" : "closed") : NOT_AVAILABLE} · sensor
              opening {fresh ? (fresh.socket_watch ? "armed" : "off") : NOT_AVAILABLE}
            </div>
            <div className="text-text-muted">
              {fresh !== null && baseline === null
                ? "Not calibrated"
                : `Calibrated at ${fresh === null ? NOT_AVAILABLE : formatMetres(baseline)}`}
            </div>
          </div>
        </Panel>
      </section>

      <div className="max-lg:hidden">
        <div
          className={cn(
            "mt-[38px] flex h-[58px] items-center justify-center gap-2.5 rounded-control border text-base leading-none font-semibold",
            motionTint(motion),
          )}
        >
          <RingIcon className="border-current" />
          {MOTION_LABEL[motion]}
        </div>

        {status && <StatusMessage tone={status.tone}>{status.text}</StatusMessage>}
      </div>

      {/* Room for the pinned drive bar, so the end of the page scrolls clear of it. */}
      <div aria-hidden className="h-32 max-lg:order-7 lg:hidden" />

      <div className="fixed inset-x-0 bottom-[calc(var(--tabbar-h)+env(safe-area-inset-bottom))] z-20 border-t border-line-strong bg-canvas/95 px-4 py-2.5 backdrop-blur lg:hidden">
        <div className="flex items-center gap-2.5">
          <div
            className={cn(
              "flex h-12 min-w-0 flex-1 items-center gap-2.5 rounded-control border px-3.5 text-[15px] leading-none font-semibold",
              motionTint(motion),
            )}
          >
            <RingIcon className="size-4 flex-none border-current" />
            <span className="truncate">{MOTION_LABEL[motion]}</span>
            {fresh && (
              <span className="ml-auto flex-none font-mono text-[13px] font-medium">
                {formatMetres(fresh.metres)}
              </span>
            )}
          </div>
          <Button
            variant="secondary"
            className="h-12 flex-none px-7 text-[15px]"
            disabled={socket !== "open"}
            onClick={stop}
          >
            Stop
          </Button>
        </div>
        {status && (
          <p
            role="status"
            className={cn(
              "m-0 mt-2 text-xs leading-snug",
              status.tone === "error" ? "text-danger-strong" : "text-text-subtle",
            )}
          >
            {status.text}
          </p>
        )}
      </div>
    </div>
  );
}
