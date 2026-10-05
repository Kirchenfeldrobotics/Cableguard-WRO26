"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/card";
import { FactList } from "@/components/ui/fact-list";
import { Notice, StatusMessage } from "@/components/ui/feedback";
import { PageHeader, SectionTitle } from "@/components/ui/heading";
import { Input } from "@/components/ui/input";
import { Pill } from "@/components/ui/pill";
import { api, ApiError } from "@/lib/api/client";
import type { SettingField, SettingsDocument } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { serverLabel } from "@/lib/config";
import {
  NOT_AVAILABLE,
  formatAgo,
  formatDateTime,
  formatDetectRate,
  formatDriveSpeed,
  formatMetres,
  formatNumber,
} from "@/lib/format";
import { useNow } from "@/lib/hooks/use-now";
import { useRobotSettings } from "@/lib/hooks/use-settings";
import {
  TELEMETRY_STALE_MS,
  useFreshTelemetry,
  useRobotConnected,
  useRobotLink,
} from "@/lib/robot/robot-link";

const MOVING = "Stop the robot before changing its settings";
const NO_SETTINGS = "The server has not answered with the robot's settings";

/** What a field is worth right now: the edit if there is one, otherwise what is stored. */
function shownValue(field: SettingField, draft: Record<string, string>, stored: number): string {
  return draft[field.key] ?? String(stored);
}

/** Why a typed value cannot be sent, or null. */
function reject(field: SettingField, text: string): string | null {
  if (text.trim() === "") return "needs a value";
  const value = Number(text);
  if (Number.isNaN(value)) return "not a number";
  if (field.integer && !Number.isInteger(value)) return "whole numbers only";
  if (value < field.minimum) return `at least ${field.minimum}`;
  if (value > field.maximum) return `at most ${field.maximum}`;
  return null;
}

function SettingRow({
  field,
  stored,
  text,
  disabled,
  onChange,
}: {
  field: SettingField;
  stored: number;
  text: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const problem = reject(field, text);
  const changed = problem === null && Number(text) !== stored;

  return (
    <div className="flex flex-col gap-2 border-b border-surface-strong py-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between sm:gap-5">
      <div className="flex min-w-0 flex-col gap-[5px]">
        <span className="flex flex-wrap items-center gap-2 text-sm leading-[1.3] font-semibold">
          {field.label}
          {changed && <Pill tone="neutral">changed</Pill>}
        </span>
        <span className="text-xs leading-[1.4] text-text-subtle">{field.note}</span>
        {problem && <span className="text-xs leading-[1.4] text-danger-strong">{problem}</span>}
      </div>

      <div className="flex flex-none items-center gap-2.5">
        <Input
          mono
          type="number"
          inputMode="decimal"
          value={text}
          min={field.minimum}
          max={field.maximum}
          step={field.step}
          disabled={disabled}
          aria-label={field.label}
          aria-invalid={problem !== null}
          title={disabled ? MOVING : `Default ${field.default}${field.unit && ` ${field.unit}`}`}
          onChange={(e) => onChange(e.target.value)}
          className={cn("w-28", problem ? "border-danger" : changed && "border-ink")}
        />
        <span className="w-10 font-mono text-xs leading-none text-text-subtle">{field.unit}</span>
      </div>
    </div>
  );
}

export function SettingsView() {
  const settings = useRobotSettings();
  const { telemetry, telemetryAt, lastMessageAt } = useRobotLink();
  const fresh = useFreshTelemetry();
  const connected = useRobotConnected();
  const now = useNow();

  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);

  const doc = settings.data;
  // The same rule the server applies (app/ws/hub.py): a robot that is not connected moves
  // nothing, and one that is connected but has gone quiet has not said that it stands still,
  // so it counts as moving.
  const moving = connected && (fresh === null || fresh.speed !== 0);
  const locked = busy || moving;

  const edited = doc
    ? Object.entries(draft).filter(([key, text]) => {
        const field = doc.fields.find((f) => f.key === key);
        return field !== undefined && reject(field, text) === null && Number(text) !== doc.values[key];
      })
    : [];
  const broken = doc
    ? Object.entries(draft).some(([key, text]) => {
        const field = doc.fields.find((f) => f.key === key);
        return field !== undefined && reject(field, text) !== null;
      })
    : false;

  const run = async (call: () => Promise<SettingsDocument>) => {
    setBusy(true);
    setFailed(null);
    try {
      await call();
      setDraft({});
      setConfirmReset(false);
    } catch (err) {
      setFailed(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
      settings.reload();
    }
  };

  const dirty = edited.length > 0 || broken;
  const changedNote = broken
    ? edited.length === 0
      ? "One value is out of range"
      : `${edited.length} changed, and one value is out of range`
    : `${edited.length} setting${edited.length === 1 ? "" : "s"} changed`;

  const save = () => run(() => api.settings.update(Object.fromEntries(edited.map(([k, v]) => [k, Number(v)]))));
  const reset = () => run(api.settings.reset);

  // The stored version only becomes the robot's once it is standing and has taken it, and
  // the robot says so itself in its telemetry.
  const inForce = doc && telemetry ? telemetry.settings_version === doc.version : null;

  return (
    <div className="max-w-[720px]">
      <PageHeader title="Robot settings" />

      {settings.loading && !doc && <StatusMessage>Loading…</StatusMessage>}
      {settings.error && <StatusMessage tone="error">{settings.error.message}</StatusMessage>}
      {failed && <StatusMessage tone="error">{failed}</StatusMessage>}

      {moving && (
        <Notice>
          The robot is moving. Settings change its drive geometry and the angle its camera ring
          is measured against, so they can only be changed while it stands still.
        </Notice>
      )}

      {doc && (
        <FactList
          className="mt-stack"
          facts={[
            { label: "Stored version", value: `v${doc.version}`, tone: "ink", mono: true },
            {
              label: "Version the robot runs on",
              value: telemetry ? `v${telemetry.settings_version}` : NOT_AVAILABLE,
              tone: inForce === null ? "muted" : inForce ? "success" : "danger",
              mono: true,
            },
            {
              label: "State",
              value:
                inForce === null
                  ? "The robot has not reported"
                  : inForce
                    ? "In force"
                    : "Waiting for the robot to stand still",
              tone: inForce === null ? "muted" : inForce ? "success" : "danger",
            },
            { label: "Last changed", value: formatDateTime(doc.updated_at), mono: true },
          ]}
        />
      )}

      {doc &&
        doc.groups.map((group) => {
          const fields = doc.fields.filter((f) => f.group === group.key);
          if (fields.length === 0) return null;
          return (
            <section key={group.key}>
              <SectionTitle note={group.note}>{group.title}</SectionTitle>
              <Panel pad="list">
                {fields.map((field) => (
                  <SettingRow
                    key={field.key}
                    field={field}
                    stored={doc.values[field.key]}
                    text={shownValue(field, draft, doc.values[field.key])}
                    disabled={locked}
                    onChange={(value) => setDraft((d) => ({ ...d, [field.key]: value }))}
                  />
                ))}
              </Panel>
            </section>
          );
        })}

      {doc && (
        <>
          <SectionTitle>Connection</SectionTitle>
          <FactList
            facts={[
              {
                label: "Link",
                value: connected ? "Connected" : "Lost",
                tone: connected ? "success" : "danger",
              },
              {
                label: "Last packet",
                value:
                  lastMessageAt && now ? formatAgo(Math.max(0, now - lastMessageAt)) : NOT_AVAILABLE,
                tone: connected ? "muted" : "danger",
                mono: true,
              },
              {
                label: "Last telemetry",
                value:
                  telemetryAt !== null && now !== null
                    ? formatAgo(Math.max(0, now - telemetryAt))
                    : NOT_AVAILABLE,
                tone:
                  telemetryAt !== null && now !== null && now - telemetryAt <= TELEMETRY_STALE_MS
                    ? "muted"
                    : "danger",
                mono: true,
              },
              {
                label: "Telemetry sequence",
                value: telemetry ? `seq ${formatNumber(telemetry.seq)}` : NOT_AVAILABLE,
                mono: true,
              },
              {
                label: "Position on rope",
                value: telemetry ? formatMetres(telemetry.metres) : NOT_AVAILABLE,
                mono: true,
              },
              {
                label: "Scan speed the robot chose",
                value: telemetry ? formatDriveSpeed(telemetry.scan_speed_mps) : NOT_AVAILABLE,
                mono: true,
              },
              {
                label: "Detector rate the scan is paced for",
                value: telemetry ? formatDetectRate(telemetry.detect_fps) : NOT_AVAILABLE,
                mono: true,
              },
              { label: "Server", value: now ? serverLabel() : NOT_AVAILABLE, mono: true },
            ]}
          />

          <div className="mt-stack flex flex-wrap gap-3.5">
            <Button
              variant={confirmReset ? "danger" : "secondary"}
              disabled={locked}
              title={moving ? MOVING : "Put every setting back on the value the robot is built with"}
              onClick={() => (confirmReset ? reset() : setConfirmReset(true))}
              onBlur={() => setConfirmReset(false)}
            >
              {confirmReset ? "Confirm reset to defaults" : "Reset to defaults"}
            </Button>
          </div>
        </>
      )}

      {!doc && !settings.loading && <StatusMessage tone="error">{NO_SETTINGS}</StatusMessage>}

      {/* Sticks to the bottom of the screen while the settings scroll under it, and stays
          inside their column: on a phone that is the full width, above the tab bar. */}
      {dirty && (
        <div className="sticky bottom-[calc(var(--tabbar-h)+env(safe-area-inset-bottom))] z-20 -mx-4 mt-stack flex flex-wrap items-center gap-2.5 border-t border-line-strong bg-canvas/95 px-4 py-2.5 backdrop-blur lg:bottom-0 lg:mx-0 lg:px-0">
          <span
            className={cn(
              "min-w-0 flex-1 text-[13px] leading-snug max-sm:basis-full",
              broken ? "text-danger-strong" : "text-text-muted",
            )}
          >
            {changedNote}
          </span>
          <Button variant="secondary" className="max-sm:flex-1" disabled={busy} onClick={() => setDraft({})}>
            Discard
          </Button>
          <Button
            className="max-sm:flex-1"
            disabled={locked || broken || edited.length === 0}
            title={moving ? MOVING : broken ? "One of the values is out of range" : undefined}
            onClick={save}
          >
            {busy ? "Saving…" : "Save and send to the robot"}
          </Button>
        </div>
      )}
    </div>
  );
}
