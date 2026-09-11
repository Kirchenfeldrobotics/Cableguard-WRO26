"use client";

import Link from "next/link";

import { RunStatePill } from "@/components/inspection/run-state-pill";
import { DefectLegend } from "@/components/rope/defect-legend";
import { defectMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { Button, ButtonLink } from "@/components/ui/button";
import { CardGrid, Panel, StatCard } from "@/components/ui/card";
import { StatusMessage } from "@/components/ui/feedback";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { NOT_AVAILABLE, formatDate, isRunActive, shortId } from "@/lib/format";
import { lastFinishedRun, useCurrentSelection, useRopeHistory } from "@/lib/hooks/use-inspection";
import { useRobotConnected } from "@/lib/robot/robot-link";
import { routes } from "@/lib/routes";

export function DashboardView() {
  const connected = useRobotConnected();
  const current = useCurrentSelection();
  const ropeId = current.data?.rope_id ?? null;
  const history = useRopeHistory(ropeId);

  const rope = history.data?.rope;
  const runs = history.data?.runs ?? [];
  const currentRun = runs.find((r) => r.id === current.data?.run_id);
  const running = connected && isRunActive(currentRun);
  const lastRun = lastFinishedRun(runs);
  const lastDefects = lastRun ? (history.data?.defectsByRun[lastRun.id] ?? []) : [];
  const lastRunLabel = lastRun
    ? `${shortId(lastRun.id)} · ${formatDate(lastRun.started_at)}`
    : "no finished run";

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
        <StatCard
          value={currentRun ? shortId(currentRun.id) : NOT_AVAILABLE}
          label={running ? "Run in progress" : "Selected run"}
          indicator="ring"
        />
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
            <HeadingMeta>
              {rope.name} · {lastRunLabel}
            </HeadingMeta>
            <Link
              href={routes.rope(rope.id)}
              className="ml-auto text-[13px] leading-none font-semibold hover:text-danger-strong"
            >
              Rope detail
            </Link>
          </>
        )}
      </div>

      {current.error || history.error ? (
        <StatusMessage tone="error">Could not load data from the server.</StatusMessage>
      ) : current.loading || history.loading ? (
        <StatusMessage>Loading…</StatusMessage>
      ) : !rope ? (
        <StatusMessage>
          No rope is selected on the server yet. Open{" "}
          <Link href={routes.ropes} className="underline">
            Ropes
          </Link>{" "}
          to see all ropes.
        </StatusMessage>
      ) : (
        <>
          <Panel className="mt-[18px] px-[22px] py-5">
            <RopeStrip length={rope.length_m} marks={defectMarks(rope.id, lastDefects)} />
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
        <Button
          variant="secondary"
          disabled
          title="Session planning is not available yet"
          className="flex-[0_1_260px] py-[15px] text-[15px]"
        >
          Plan new session
        </Button>
      </div>
    </>
  );
}
