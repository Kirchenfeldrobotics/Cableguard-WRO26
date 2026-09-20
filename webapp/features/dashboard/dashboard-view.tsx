"use client";

import { useState } from "react";
import Link from "next/link";

import { RunStatePill } from "@/components/inspection/run-state-pill";
import { DefectLegend } from "@/components/rope/defect-legend";
import { findingMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { Button, ButtonLink } from "@/components/ui/button";
import { CardGrid, Panel, StatCard } from "@/components/ui/card";
import { Dropdown } from "@/components/ui/dropdown";
import { StatusMessage } from "@/components/ui/feedback";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { api } from "@/lib/api/client";
import { NOT_AVAILABLE, formatDate, isRunActive, shortId } from "@/lib/format";
import { useApi } from "@/lib/hooks/use-api";
import { lastFinishedRun, useCurrentSelection, useRopeHistory } from "@/lib/hooks/use-inspection";
import { useRobotConnected } from "@/lib/robot/robot-link";
import { routes } from "@/lib/routes";

export function DashboardView() {
  const connected = useRobotConnected();
  const current = useCurrentSelection();
  const ropes = useApi("ropes", api.ropes.list);
  const ropeId = current.data?.rope_id ?? null;
  const history = useRopeHistory(ropeId);

  const [selecting, setSelecting] = useState(false);
  const [selectError, setSelectError] = useState<string | null>(null);

  const rope = history.data?.rope;
  const runs = history.data?.runs ?? [];
  const currentRun = runs.find((r) => r.id === current.data?.run_id);
  const running = connected && isRunActive(currentRun);
  const lastRun = lastFinishedRun(runs);
  const lastFindings = lastRun ? (history.data?.findingsByRun[lastRun.id] ?? []) : [];
  const lastRunLabel = lastRun
    ? `${shortId(lastRun.id)} · ${formatDate(lastRun.started_at)}`
    : "no finished run";

  const selectRope = async (nextRopeId: string) => {
    setSelectError(null);
    setSelecting(true);
    try {
      // A run belongs to exactly one rope, so changing rope clears the run.
      await api.current.set({ rope_id: nextRopeId, run_id: null });
      current.reload();
    } catch (err) {
      setSelectError(err instanceof Error ? err.message : String(err));
    } finally {
      setSelecting(false);
    }
  };

  return (
    <>
      <PageHeader title="Inspection status">
        <RunStatePill running={running} />
      </PageHeader>

      <CardGrid>
        <StatCard
          value={connected ? "Connected" : "Link lost"}
          label="Robot link"
          indicator={connected ? "success" : "danger"}
        />
        <StatCard
          value={NOT_AVAILABLE}
          label="Unreviewed defects"
          indicator="muted"
          title="Defect review is not available yet"
        />
        <StatCard value={rope?.name ?? NOT_AVAILABLE} label="Selected rope" indicator="ring" />
        <StatCard
          value={formatDate(lastRun?.finished_at)}
          label="Last inspection"
          indicator="muted"
        />
      </CardGrid>

      <div className="mt-[38px] flex flex-wrap items-center gap-3">
        <SectionTitle className="m-0">Rope</SectionTitle>
        {rope && (
          <>
            <HeadingMeta>{lastRunLabel}</HeadingMeta>
            <Link
              href={routes.rope(rope.id)}
              className="ml-auto text-[13px] leading-none font-semibold hover:text-danger-strong"
            >
              Rope detail
            </Link>
          </>
        )}
      </div>

      <div className="mt-[18px] flex flex-wrap items-center gap-3">
        <Dropdown
          label="Selected rope"
          className="min-w-[240px] flex-[0_1_320px]"
          options={(ropes.data ?? []).map((r) => ({ value: r.id, label: r.name }))}
          value={ropeId}
          onChange={selectRope}
          disabled={selecting}
          placeholder={
            ropes.loading ? "Loading ropes…" : ropes.data?.length ? "Select a rope" : "No ropes yet"
          }
        />
        {selecting && <HeadingMeta>Saving…</HeadingMeta>}
      </div>
      {(selectError || ropes.error) && (
        <StatusMessage tone="error">{selectError ?? "Could not load the rope list."}</StatusMessage>
      )}

      {current.error || history.error ? (
        <StatusMessage tone="error">Could not load data from the server.</StatusMessage>
      ) : current.loading || history.loading ? (
        <StatusMessage>Loading…</StatusMessage>
      ) : !rope ? (
        <StatusMessage>
          {ropes.data?.length === 0 ? (
            <>
              No ropes yet. Add the first one on{" "}
              <Link href={routes.ropes} className="underline">
                Ropes
              </Link>
              .
            </>
          ) : (
            "No rope is selected yet. Choose one from the dropdown above."
          )}
        </StatusMessage>
      ) : (
        <>
          <Panel className="mt-[18px] px-[22px] py-5">
            <RopeStrip length={rope.length_m} marks={findingMarks(rope.id, lastFindings)} />
          </Panel>
          <DefectLegend />
        </>
      )}

      <div className="mt-[38px] flex flex-wrap gap-3.5">
        {connected ? (
          <ButtonLink href={routes.live} size="md" className="flex-[0_1_260px] py-[15px] text-[15px]">
            Open live view
          </ButtonLink>
        ) : (
          <Button disabled className="flex-[0_1_260px] py-[15px] text-[15px]">
            Open live view
          </Button>
        )}
      </div>
    </>
  );
}
