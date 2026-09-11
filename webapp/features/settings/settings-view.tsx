"use client";

import { Panel } from "@/components/ui/card";
import { FactList } from "@/components/ui/fact-list";
import { PageHeader, SectionTitle } from "@/components/ui/heading";
import { serverLabel } from "@/lib/config";
import { NOT_AVAILABLE, formatAgo, formatNumber } from "@/lib/format";
import { useNow } from "@/lib/hooks/use-now";
import { useRobotConnected, useRobotLink } from "@/lib/robot/robot-link";

/*
 * The protocol has no command to read or write drive parameters or the
 * detection threshold yet, so those controls are shown but disabled.
 */
const DRIVE_PARAMS = [
  { label: "Microstepping", note: "Steps per full step, NEMA 23 drive", unit: "×" },
  { label: "Wheel circumference", note: "Converts steps to distance on the rope", unit: "mm" },
  { label: "Maximum speed", note: "Upper limit for the drive during a run", unit: "m/s" },
  { label: "Acceleration", note: "Ramp applied on start and stop", unit: "m/s²" },
];

const NOT_CONFIGURABLE = "Not configurable from the webapp yet";

export function SettingsView() {
  const { telemetry, lastMessageAt } = useRobotLink();
  const connected = useRobotConnected();
  const now = useNow();

  return (
    <div className="max-w-[660px]">
      <PageHeader title="Robot settings" />

      <Panel className="mt-5 px-5 py-2">
        {DRIVE_PARAMS.map((param) => (
          <div
            key={param.label}
            className="flex items-center justify-between gap-5 border-b border-surface-strong py-4 last:border-b-0"
          >
            <div className="flex flex-col gap-[5px]">
              <span className="text-sm leading-[1.3] font-semibold">{param.label}</span>
              <span className="text-xs leading-[1.4] text-text-subtle">{param.note}</span>
            </div>
            <div className="flex items-center gap-2.5">
              <input
                disabled
                placeholder={NOT_AVAILABLE}
                title={NOT_CONFIGURABLE}
                aria-label={param.label}
                className="w-24 rounded-control border border-border bg-white px-3 py-2.5 text-right font-mono text-[13px] leading-none font-medium text-ink disabled:cursor-not-allowed"
              />
              <span className="w-10 font-mono text-xs leading-none text-text-subtle">{param.unit}</span>
            </div>
          </div>
        ))}
      </Panel>

      <SectionTitle className="mt-[34px] mb-4">Detection</SectionTitle>
      <Panel className="p-5">
        <div className="flex items-center justify-between gap-5">
          <div className="flex flex-col gap-[5px]">
            <span className="text-sm leading-[1.3] font-semibold">Confidence threshold</span>
            <span className="text-xs leading-[1.4] text-text-subtle">
              Detections below this value are discarded and not logged
            </span>
          </div>
          <span className="text-xl leading-none font-bold">{NOT_AVAILABLE}</span>
        </div>
        <input
          type="range"
          disabled
          min={0.3}
          max={0.95}
          step={0.01}
          defaultValue={0.4}
          aria-label="Confidence threshold"
          title={NOT_CONFIGURABLE}
          className="mt-[18px] w-full accent-ink disabled:cursor-not-allowed disabled:opacity-50"
        />
        <div className="mt-2.5 text-xs leading-normal text-text-subtle">
          The detector does not report confidence values yet.
        </div>
      </Panel>

      <SectionTitle className="mt-[34px] mb-4">Connection</SectionTitle>
      <FactList
        facts={[
          {
            label: "Link",
            value: connected ? "Connected" : "Lost",
            tone: connected ? "success" : "danger",
          },
          { label: "Transport", value: "LTE · SIM module" },
          {
            label: "Last packet",
            value: lastMessageAt && now ? formatAgo(Math.max(0, now - lastMessageAt)) : NOT_AVAILABLE,
            tone: connected ? "muted" : "danger",
          },
          {
            label: "Telemetry sequence",
            value: telemetry ? `seq ${formatNumber(telemetry.seq)}` : NOT_AVAILABLE,
          },
          {
            label: "Microsteps (telemetry)",
            value: telemetry ? formatNumber(telemetry.microsteps) : NOT_AVAILABLE,
          },
          { label: "Server", value: now ? serverLabel() : NOT_AVAILABLE },
        ]}
      />
    </div>
  );
}
