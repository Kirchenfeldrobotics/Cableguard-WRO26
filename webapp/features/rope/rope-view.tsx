"use client";

import { useState } from "react";

import { DefectLegend } from "@/components/rope/defect-legend";
import { findingMarks } from "@/components/rope/defect-marks";
import { RopeLengthInput, parseRopeLength } from "@/components/rope/rope-length-input";
import { RopeStrip } from "@/components/rope/rope-strip";
import { Button, TextLink } from "@/components/ui/button";
import { CardGrid, FactCard, Panel } from "@/components/ui/card";
import { BackLink, StatusMessage } from "@/components/ui/feedback";
import { PageHeader, SectionTitle } from "@/components/ui/heading";
import { RemoveButton } from "@/components/ui/remove-button";
import { LinkRow, Table, Td, Th } from "@/components/ui/table";
import { api } from "@/lib/api/client";
import type { Rope } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { countUnreviewed } from "@/lib/defects";
import { formatDate, formatDateTime, formatMetres, formatRunDuration, shortId } from "@/lib/format";
import { lastFinishedRun, useCurrentSelection, useRopeHistory } from "@/lib/hooks/use-inspection";
import { routes } from "@/lib/routes";

export function RopeView({ ropeId }: { ropeId: string }) {
  const { data, error, loading, reload } = useRopeHistory(ropeId);
  const current = useCurrentSelection();
  const [editing, setEditing] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const removeRun = async (runId: string) => {
    setRemoveError(null);
    try {
      await api.runs.remove(runId);
      reload();
    } catch (err) {
      setRemoveError(err instanceof Error ? err.message : String(err));
    }
  };

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
          <>
            {!editing && <TextLink onClick={() => setEditing(true)}>Edit length</TextLink>}
            <TextLink href={routes.compare(rope.id)}>Compare runs</TextLink>
          </>
        }
      />

      {editing && (
        <EditLengthForm
          rope={rope}
          onCancel={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            reload();
          }}
        />
      )}

      <CardGrid>
        <FactCard value={formatMetres(rope.length_m)} label="Rope length" />
        <FactCard value={runs.length} label="Runs recorded" />
        <FactCard value={formatDate(lastFinishedRun(runs)?.finished_at)} label="Last inspected" />
      </CardGrid>

      <SectionTitle>Unrolled rope</SectionTitle>
      <Panel>
        <RopeStrip
          length={rope.length_m}
          marks={shownRun ? findingMarks(rope.id, findingsByRun[shownRun.id] ?? []) : []}
        />
      </Panel>
      <DefectLegend
        note={shownRun && `Defects from ${shortId(shownRun.id)} · ${formatDate(shownRun.started_at)}`}
      />

      {runs.length > 0 && (
        <>
          <SectionTitle>Run history</SectionTitle>
          {removeError && <StatusMessage tone="error">{removeError}</StatusMessage>}
          <Table>
            <thead>
              <tr>
                <Th>Run</Th>
                <Th>Date</Th>
                <Th align="right">Duration</Th>
                <Th align="right">Findings</Th>
                <Th align="right">Unreviewed</Th>
                <Th />
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
                  <Td mono align="right" label="Findings">
                    {findingsByRun[run.id]?.length ?? 0}
                  </Td>
                  <Td mono muted align="right" label="Unreviewed">
                    {countUnreviewed(findingsByRun[run.id] ?? [])}
                  </Td>
                  {/* The server refuses to delete the run that is being recorded. */}
                  <Td align="right" phone="end" className="pr-0 max-lg:col-span-2">
                    {run.id !== current.data?.run_id && <RemoveButton onConfirm={() => removeRun(run.id)} />}
                  </Td>
                </LinkRow>
              ))}
            </tbody>
          </Table>
        </>
      )}

      <SectionTitle>Trend</SectionTitle>
      {counts.length < 2 ? (
        <StatusMessage>The trend needs at least two finished runs.</StatusMessage>
      ) : (
        <Panel className="flex flex-wrap items-end gap-[26px]">
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
      )}
    </>
  );
}

function EditLengthForm({
  rope,
  onSaved,
  onCancel,
}: {
  rope: Rope;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [length, setLength] = useState(rope.length_m === null ? "" : String(rope.length_m));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lengthM = parseRopeLength(length);

  return (
    <>
      <form
        className="mt-stack"
        onSubmit={async (e) => {
          e.preventDefault();
          if (lengthM === null) return;
          setError(null);
          setSaving(true);
          try {
            await api.ropes.update(rope.id, lengthM);
            onSaved();
          } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
            setSaving(false);
          }
        }}
      >
        <Panel className="flex flex-wrap items-center gap-3">
          <RopeLengthInput autoFocus value={length} onChange={setLength} />
          <Button type="submit" disabled={saving || lengthM === null}>
            Save
          </Button>
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        </Panel>
      </form>
      {error && <StatusMessage tone="error">{error}</StatusMessage>}
    </>
  );
}
