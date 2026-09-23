"use client";

import Link from "next/link";

import { DefectLegend } from "@/components/rope/defect-legend";
import { findingMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { CardGrid, FactCard, Panel } from "@/components/ui/card";
import { BackLink, StatusMessage } from "@/components/ui/feedback";
import { PageHeader, SectionTitle } from "@/components/ui/heading";
import { LinkRow, Table, Td, Th } from "@/components/ui/table";
import { cn } from "@/lib/cn";
import {
  NOT_AVAILABLE,
  formatDate,
  formatDateTime,
  formatMetres,
  formatRunDuration,
  shortId,
} from "@/lib/format";
import { lastFinishedRun, useRopeHistory } from "@/lib/hooks/use-inspection";
import { routes } from "@/lib/routes";

export function RopeView({ ropeId }: { ropeId: string }) {
  const { data, error, loading } = useRopeHistory(ropeId);

  if (error) return <StatusMessage tone="error">Could not load the rope from the server.</StatusMessage>;
  if (loading || !data) return <StatusMessage>Loading…</StatusMessage>;
  if (!data.rope) return <StatusMessage>This rope does not exist.</StatusMessage>;

  const { rope, runs, findingsByRun } = data;
  const shownRun = lastFinishedRun(runs) ?? runs[0];
  const finishedOldestFirst = runs.filter((r) => r.finished_at).reverse();
  const counts = finishedOldestFirst.map((r) => findingsByRun[r.id]?.length ?? 0);
  const maxCount = Math.max(1, ...counts);

  return (
    <>
      <BackLink href={routes.ropes}>Ropes</BackLink>
      <PageHeader
        title={rope.name}
        actions={
          <Link
            href={routes.compare(rope.id)}
            className="text-[13px] leading-none font-semibold hover:text-danger-strong"
          >
            Compare runs
          </Link>
        }
      />

      <CardGrid>
        <FactCard value={NOT_AVAILABLE} label="Installed" title="Installation date is not stored yet" />
        <FactCard value={formatMetres(rope.length_m)} label="Rope length" />
        <FactCard value={runs.length} label="Runs recorded" />
        <FactCard value={formatDate(lastFinishedRun(runs)?.finished_at)} label="Last inspected" />
      </CardGrid>

      <SectionTitle>Unrolled rope</SectionTitle>
      <Panel className="px-3 py-4 sm:px-[22px] sm:py-5">
        <RopeStrip
          length={rope.length_m}
          marks={shownRun ? findingMarks(rope.id, findingsByRun[shownRun.id] ?? []) : []}
        />
      </Panel>
      <DefectLegend
        note={shownRun ? `Defects from ${shortId(shownRun.id)} · ${formatDate(shownRun.started_at)}` : "No runs yet"}
      />

      <SectionTitle>Run history</SectionTitle>
      {runs.length === 0 ? (
        <StatusMessage>No runs recorded on this rope yet.</StatusMessage>
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Run</Th>
              <Th>Date</Th>
              <Th align="right">Duration</Th>
              <Th align="right">Distance</Th>
              <Th align="right">Findings</Th>
              <Th align="right">Unreviewed</Th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <LinkRow key={run.id} href={routes.run(rope.id, run.id)}>
                <Td mono strong phone="primary">
                  {shortId(run.id)}
                </Td>
                <Td mono muted label="Date">
                  {formatDateTime(run.started_at)}
                </Td>
                <Td mono align="right" label="Duration">
                  {formatRunDuration(run)}
                </Td>
                <Td mono align="right" phone="hide">
                  {NOT_AVAILABLE}
                </Td>
                <Td mono align="right" label="Findings">
                  {findingsByRun[run.id]?.length ?? 0}
                </Td>
                <Td mono muted align="right" phone="hide">
                  {NOT_AVAILABLE}
                </Td>
              </LinkRow>
            ))}
          </tbody>
        </Table>
      )}

      <SectionTitle>Trend</SectionTitle>
      {counts.length < 2 ? (
        <StatusMessage>The trend needs at least two finished runs.</StatusMessage>
      ) : (
        <>
          <Panel className="flex flex-wrap items-end gap-[26px] p-[22px]">
            {finishedOldestFirst.map((run, i) => (
              <div key={run.id} className="flex h-[132px] w-16 flex-col items-center justify-end gap-2">
                <div className="text-[13px] leading-none font-semibold">{counts[i]}</div>
                <div
                  style={{ height: `${Math.round((counts[i] / maxCount) * 92)}px` }}
                  className={cn(
                    "w-full rounded-t-[6px]",
                    i === counts.length - 1 ? "bg-ink" : "bg-mark-tick",
                  )}
                />
                <div className="font-mono text-[11px] leading-none text-text-subtle">
                  {formatDate(run.started_at).slice(2)}
                </div>
              </div>
            ))}
          </Panel>
          <p className="mt-3.5 max-w-[620px] text-[13px] leading-[1.6] text-text-muted">
            Findings have gone from {counts[0]} to {counts[counts.length - 1]} over {counts.length} runs.
          </p>
        </>
      )}
    </>
  );
}
