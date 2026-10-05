"use client";

import { useRouter } from "next/navigation";

import { findingMarks } from "@/components/rope/defect-marks";
import { RopeStrip, RopeStripSync } from "@/components/rope/rope-strip";
import { CardGrid, FactCard, Panel } from "@/components/ui/card";
import { Dropdown } from "@/components/ui/dropdown";
import { StatusMessage } from "@/components/ui/feedback";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { Field } from "@/components/ui/input";
import { LogRow } from "@/components/ui/log-row";
import type { Run } from "@/lib/api/types";
import { compareRuns, kindTone } from "@/lib/defects";
import { defectClassLabel, formatConfidence, formatDate, formatSpan, shortId } from "@/lib/format";
import { useCurrentSelection, useRopeHistory } from "@/lib/hooks/use-inspection";
import { routes } from "@/lib/routes";

const runLabel = (run: Run) => `${shortId(run.id)} · ${formatDate(run.started_at)}`;

export function CompareView({
  ropeParam,
  compared,
  reference,
}: {
  ropeParam?: string;
  compared?: string;
  reference?: string;
}) {
  const router = useRouter();
  const current = useCurrentSelection();
  const ropeId = ropeParam ?? current.data?.rope_id ?? null;
  const history = useRopeHistory(ropeId);

  const rope = history.data?.rope;
  const finished = (history.data?.runs ?? []).filter((r) => r.finished_at);
  const runA = finished.find((r) => r.id === compared) ?? finished[0];
  const runB = finished.find((r) => r.id === reference) ?? finished[1];

  const select = (key: "a" | "b", value: string) => {
    if (!rope || !runA || !runB) return;
    const params = new URLSearchParams({ rope: rope.id, a: runA.id, b: runB.id, [key]: value });
    router.replace(`/compare?${params}`);
  };

  const body = () => {
    if (current.error || history.error)
      return <StatusMessage tone="error">Could not load runs from the server.</StatusMessage>;
    if (current.loading || history.loading) return <StatusMessage>Loading…</StatusMessage>;
    if (!rope) return <StatusMessage>No rope selected.</StatusMessage>;
    if (!runA || !runB) return <StatusMessage>Comparing needs at least two finished runs.</StatusMessage>;

    // Comparing raw detections would count every repeat sighting, so both runs are
    // grouped into findings first.
    const aFindings = history.data?.findingsByRun[runA.id] ?? [];
    const bFindings = history.data?.findingsByRun[runB.id] ?? [];
    const { added, unchanged, resolved } = compareRuns(bFindings, aFindings);
    const addedIds = new Set(added.map((f) => f.best.id));

    return (
      <>
        <div className="mt-stack grid grid-cols-1 gap-3.5 sm:flex sm:flex-wrap">
          <RunSelect label="Reference run" value={runB.id} runs={finished} onChange={(v) => select("b", v)} />
          <RunSelect label="Compared run" value={runA.id} runs={finished} onChange={(v) => select("a", v)} />
        </div>

        <CardGrid>
          <FactCard value={added.length} label="New findings" className="text-danger-strong" />
          <FactCard value={unchanged.length} label="Unchanged" />
          <FactCard value={resolved.length} label="No longer detected" className="text-text-muted" />
        </CardGrid>

        <Panel className="mt-stack flex flex-col gap-7">
          <RopeStripSync>
            <StripBlock label={runLabel(runB)} count={bFindings.length}>
              <RopeStrip length={rope.length_m} marks={findingMarks(rope.id, bFindings, "unchanged")} />
            </StripBlock>
            <StripBlock label={runLabel(runA)} count={aFindings.length}>
              <RopeStrip
                length={rope.length_m}
                marks={findingMarks(rope.id, aFindings, (f) => (addedIds.has(f.best.id) ? "new" : "unchanged"))}
              />
            </StripBlock>
          </RopeStripSync>
        </Panel>

        {added.length > 0 && (
          <>
            <SectionTitle>New findings</SectionTitle>
            <Panel className="flex flex-col gap-[7px]">
              {added.map((f) => (
                <LogRow
                  key={f.best.id}
                  href={routes.defect(rope.id, f.best.run_id, f.best.id)}
                  tone={kindTone(f.kind)}
                  position={formatSpan(f.from, f.to)}
                >
                  {defectClassLabel(f.best.label)} · {formatConfidence(f.confidence)}
                </LogRow>
              ))}
            </Panel>
          </>
        )}
      </>
    );
  };

  return (
    <>
      <PageHeader title="Compare runs">{rope && <HeadingMeta>{rope.name}</HeadingMeta>}</PageHeader>
      {body()}
    </>
  );
}

function RunSelect({
  label,
  value,
  runs,
  onChange,
}: {
  label: string;
  value: string;
  runs: Run[];
  onChange: (value: string) => void;
}) {
  return (
    <Field label={label} className="sm:min-w-[240px]">
      <Dropdown
        label={label}
        options={runs.map((run) => ({ value: run.id, label: runLabel(run) }))}
        value={value}
        onChange={onChange}
      />
    </Field>
  );
}

function StripBlock({ label, count, children }: { label: string; count: number; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-3.5 flex justify-between gap-4">
        <span className="text-sm leading-none font-semibold">{label}</span>
        <span className="text-xs leading-none text-text-subtle">{count} findings</span>
      </div>
      {children}
    </div>
  );
}
