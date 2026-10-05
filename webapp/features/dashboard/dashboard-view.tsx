"use client";

import { useState } from "react";

import { RunStatePill } from "@/components/inspection/run-state-pill";
import { DefectLegend } from "@/components/rope/defect-legend";
import { findingMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { Button, ButtonLink, TextLink } from "@/components/ui/button";
import { CardGrid, Panel, StatCard } from "@/components/ui/card";
import { Dropdown } from "@/components/ui/dropdown";
import { StatusMessage } from "@/components/ui/feedback";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { api } from "@/lib/api/client";
import { countUnreviewed } from "@/lib/defects";
import { NOT_AVAILABLE, formatDate, formatDateTime, isRunActive, shortId } from "@/lib/format";
import { useApi } from "@/lib/hooks/use-api";
import { lastFinishedRun, useCurrentSelection, useRopeHistory } from "@/lib/hooks/use-inspection";
import { useRobotConnected, useRobotLink } from "@/lib/robot/robot-link";
import { routes } from "@/lib/routes";

export function DashboardView() {
  const connected = useRobotConnected();
  const { send } = useRobotLink();
  const current = useCurrentSelection();
  const ropes = useApi("ropes", api.ropes.list);
  const ropeId = current.data?.rope_id ?? null;
  const history = useRopeHistory(ropeId);

  const [selecting, setSelecting] = useState(false);
  const [selectError, setSelectError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const rope = history.data?.rope;
  const runs = history.data?.runs ?? [];
  // The selection is the server's answer, the run object may still be loading behind it.
  // Reading the id rather than the object keeps the button from flipping back to Start.
  const currentRunId = current.data?.run_id ?? null;
  const currentRun = runs.find((r) => r.id === currentRunId);
  const running = connected && isRunActive(currentRun);
  const lastRun = lastFinishedRun(runs);
  const lastFindings = lastRun ? (history.data?.findingsByRun[lastRun.id] ?? []) : [];
  // Over every run of the rope, the one being recorded included.
  const unreviewed = rope ? countUnreviewed(Object.values(history.data?.findingsByRun ?? {}).flat()) : null;
  const lastRunLabel = lastRun
    ? `${shortId(lastRun.id)} · ${formatDate(lastRun.started_at)}`
    : "no finished run";

  /**
   * A run is created and selected in one step: selecting it is what makes the server zero
   * the robot's position counter, so every defect is measured from where it stands now.
   */
  const startRun = async () => {
    if (!rope) return;
    setRunError(null);
    setBusy(true);
    try {
      const run = await api.runs.create(rope.id, `Run ${formatDateTime(new Date().toISOString())}`);
      await api.current.set({ rope_id: rope.id, run_id: run.id });
      current.reload();
      history.reload();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  /** Closing the run also drops the selection, so nothing is recorded into it afterwards. */
  const finishRun = async () => {
    if (!rope || !currentRunId) return;
    setRunError(null);
    setBusy(true);
    try {
      // Ending the run takes the live screen away with it, so the robot must not be left
      // driving behind it with nothing recording what it sees.
      send({ type: "stop" });
      await api.runs.finish(currentRunId);
      await api.current.set({ rope_id: rope.id, run_id: null });
      current.reload();
      history.reload();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const selectRope = async (nextRopeId: string) => {
    setSelectError(null);
    setSelecting(true);
    try {
      // A run belongs to exactly one rope, so changing rope clears the run. That hides the
      // live screen too, so the same rule applies: do not leave the robot driving.
      if (currentRunId) send({ type: "stop" });
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
      <PageHeader title="Dashboard">
        <RunStatePill running={running} />
      </PageHeader>

      <CardGrid>
        <StatCard
          value={connected ? "Connected" : "Link lost"}
          label="Robot link"
          indicator={connected ? "success" : "danger"}
        />
        <StatCard
          value={unreviewed ?? NOT_AVAILABLE}
          label="Unreviewed findings"
          indicator={unreviewed ? "alert" : "muted"}
        />
        <StatCard value={rope?.name ?? NOT_AVAILABLE} label="Selected rope" indicator="ring" />
        <StatCard
          value={formatDate(lastRun?.finished_at)}
          label="Last inspection"
          indicator="muted"
        />
      </CardGrid>

      <SectionTitle
        meta={rope && <HeadingMeta>{lastRunLabel}</HeadingMeta>}
        actions={rope && <TextLink href={routes.rope(rope.id)}>Rope detail</TextLink>}
      >
        Rope
      </SectionTitle>

      <div className="flex flex-wrap items-center gap-3">
        <Dropdown
          label="Selected rope"
          className="w-full sm:w-auto sm:min-w-[240px] sm:flex-[0_1_320px]"
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
        <StatusMessage tone="error">
          Could not load data from the server. {(current.error ?? history.error)?.message}
        </StatusMessage>
      ) : current.loading || history.loading ? (
        <StatusMessage>Loading…</StatusMessage>
      ) : (
        rope && (
          <>
            <Panel className="mt-stack">
              <RopeStrip length={rope.length_m} marks={findingMarks(rope.id, lastFindings)} />
            </Panel>
            <DefectLegend />
          </>
        )
      )}

      <div className="mt-section flex flex-wrap gap-3.5">
        {currentRunId ? (
          <>
            <ButtonLink href={routes.live} size="lg" className="flex-[0_1_260px] max-sm:grow">
              Open live view
            </ButtonLink>
            <Button
              variant="secondary"
              size="lg"
              disabled={busy}
              onClick={finishRun}
              className="flex-[0_1_200px] max-sm:grow"
            >
              {busy ? "Finishing…" : "Finish run"}
            </Button>
          </>
        ) : (
          <Button
            size="lg"
            disabled={!rope || !connected || busy}
            onClick={startRun}
            className="flex-[0_1_260px] max-sm:grow"
          >
            {busy ? "Starting…" : "Start run"}
          </Button>
        )}
      </div>

      {runError ? (
        <StatusMessage tone="error">{runError}</StatusMessage>
      ) : (
        currentRunId && (
          <StatusMessage>
            Recording into {shortId(currentRunId)}
            {currentRun && `, started ${formatDateTime(currentRun.started_at)}`}.
          </StatusMessage>
        )
      )}
    </>
  );
}
