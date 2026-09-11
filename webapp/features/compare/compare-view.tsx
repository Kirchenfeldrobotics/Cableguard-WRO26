"use client";

import { useRouter } from "next/navigation";

import { defectMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { CardGrid, FactCard, Panel } from "@/components/ui/card";
import { StatusMessage } from "@/components/ui/feedback";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { LogRow } from "@/components/ui/log-row";
import type { Run } from "@/lib/api/types";
import { compareRuns, kindTone } from "@/lib/defects";
import { defectTypeLabel, formatDate, formatMetres, shortId } from "@/lib/format";
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
    if (!rope) return <StatusMessage>No rope is selected. Open a rope and choose Compare runs.</StatusMessage>;
    if (!runA || !runB) return <StatusMessage>Comparing needs at least two finished runs.</StatusMessage>;

    const aDefects = history.data?.defectsByRun[runA.id] ?? [];
    const bDefects = history.data?.defectsByRun[runB.id] ?? [];
    const { added, unchanged, resolved } = compareRuns(bDefects, aDefects);
    const addedIds = new Set(added.map((d) => d.id));

    return (
      <>
        <div className="mt-5 flex flex-wrap gap-3.5">
          <RunSelect label="Reference run" value={runB.id} runs={finished} onChange={(v) => select("b", v)} />
          <RunSelect label="Compared run" value={runA.id} runs={finished} onChange={(v) => select("a", v)} />
        </div>

        <CardGrid className="mt-[22px]">
          <FactCard value={added.length} label="New defects" className="text-[26px] leading-none text-danger-strong" />
          <FactCard value={unchanged.length} label="Unchanged" className="text-[26px] leading-none" />
          <FactCard
            value={resolved.length}
            label="No longer detected"
            className="text-[26px] leading-none text-text-muted"
          />
        </CardGrid>

        <Panel className="mt-[26px] flex flex-col gap-7 px-[22px] py-5">
          <StripBlock label={runLabel(runB)} count={bDefects.length}>
            <RopeStrip length={rope.length_m} marks={defectMarks(rope.id, bDefects, "unchanged")} />
          </StripBlock>
          <StripBlock label={runLabel(runA)} count={aDefects.length}>
            <RopeStrip
              length={rope.length_m}
              marks={defectMarks(rope.id, aDefects, (d) => (addedIds.has(d.id) ? "new" : "unchanged"))}
            />
          </StripBlock>
        </Panel>

        <SectionTitle className="mb-4">New defects</SectionTitle>
        {added.length === 0 ? (
          <StatusMessage>No new defects compared to the reference run.</StatusMessage>
        ) : (
          <div className="flex max-w-[760px] flex-col gap-[7px]">
            {added.map((d) => (
              <LogRow
                key={d.id}
                href={routes.defect(rope.id, d.run_id, d.id)}
                tone={kindTone(d.kind)}
                position={formatMetres(d.pos_to_start)}
              >
                {defectTypeLabel(d.kind)} · {shortId(d.id)}
              </LogRow>
            ))}
          </div>
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
    <label className="flex flex-col gap-2">
      <span className="text-xs leading-none text-text-subtle">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-[230px] rounded-control border border-border bg-white px-3.5 py-3 font-mono text-[13px] leading-none font-medium text-ink"
      >
        {runs.map((run) => (
          <option key={run.id} value={run.id}>
            {runLabel(run)}
          </option>
        ))}
      </select>
    </label>
  );
}

function StripBlock({ label, count, children }: { label: string; count: number; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-3.5 flex justify-between gap-4">
        <span className="text-sm leading-none font-semibold">{label}</span>
        <span className="font-mono text-xs leading-none text-text-subtle">{count} defects</span>
      </div>
      {children}
    </div>
  );
}
