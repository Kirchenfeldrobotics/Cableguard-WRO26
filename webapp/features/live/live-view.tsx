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
import { cn } from "@/lib/cn";
import { kindTone } from "@/lib/defects";
import {
  NOT_AVAILABLE,
  defectTypeLabel,
  formatMetres,
  formatNumber,
  isRunActive,
  shortId,
} from "@/lib/format";
import { useCurrentSelection, useRopeHistory } from "@/lib/hooks/use-inspection";
import { useRobotConnected, useRobotLink } from "@/lib/robot/robot-link";
import { useVideoFeeds } from "@/lib/robot/use-video-feeds";
import { routes } from "@/lib/routes";

const REFRESH_MS = 5_000;

const CAMERAS = [
  { code: "cam a", caption: "Camera A, upper rope surface" },
  { code: "cam b", caption: "Camera B, lower rope surface" },
];

export function LiveView() {
  const { socket, telemetry, lastError, send } = useRobotLink();
  const connected = useRobotConnected();
  const feeds = useVideoFeeds(CAMERAS.length);
  const [stopSent, setStopSent] = useState(false);

  const current = useCurrentSelection();
  const ropeId = current.data?.rope_id ?? null;
  const history = useRopeHistory(ropeId, { refreshMs: REFRESH_MS });

  const rope = history.data?.rope;
  const run = history.data?.runs.find((r) => r.id === current.data?.run_id);
  const running = connected && isRunActive(run);
  const defects = run ? (history.data?.defectsByRun[run.id] ?? []) : [];
  const newestFirst = [...defects].sort((a, b) => b.created_at.localeCompare(a.created_at));

  const emergencyStop = () => setStopSent(send({ type: "stop" }));

  return (
    <>
      <PageHeader title="Inspection data">
        <RunStatePill running={running} />
        {rope && <HeadingMeta>{rope.name}</HeadingMeta>}
      </PageHeader>

      {!connected && (
        <Notice>
          Link to the robot is lost. The values below are the last received state. The robot holds
          its position until the link returns.
        </Notice>
      )}

      <CardGrid>
        <StatCard
          value={NOT_AVAILABLE}
          label="Position on rope"
          indicator="ring"
          title="The robot does not report its position yet"
        />
        <StatCard
          value={telemetry ? `${formatNumber(telemetry.speed)} steps/s` : NOT_AVAILABLE}
          label="Drive speed"
          indicator="solid"
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
          className={cn(
            "flex h-[58px] flex-[1_1_260px] items-center justify-center gap-2.5 rounded-control border text-base leading-none font-semibold",
            running
              ? "border-success-line bg-linear-to-r from-success-soft to-[#d3f0dd] text-success-ink"
              : "border-line-strong bg-surface text-text-muted",
          )}
        >
          <RingIcon className="border-current" />
          {running ? "Running…" : "Stopped"}
        </div>
      </div>

      {lastError ? (
        <StatusMessage tone="error">Server: {lastError}</StatusMessage>
      ) : (
        stopSent && <StatusMessage>Stop command sent to the robot.</StatusMessage>
      )}
    </>
  );
}
