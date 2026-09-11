"use client";

import { Button } from "@/components/ui/button";
import { BackLink, StatusMessage } from "@/components/ui/feedback";
import { FactList } from "@/components/ui/fact-list";
import { HeadingMeta, PageHeader } from "@/components/ui/heading";
import { InfoRow } from "@/components/ui/log-row";
import { findMatch } from "@/lib/defects";
import {
  NOT_AVAILABLE,
  defectTypeLabel,
  formatDateTime,
  formatMetres,
  shortId,
} from "@/lib/format";
import { useRopeHistory } from "@/lib/hooks/use-inspection";
import { routes } from "@/lib/routes";

export function DefectView({
  ropeId,
  runId,
  defectId,
}: {
  ropeId: string;
  runId: string;
  defectId: string;
}) {
  const { data, error, loading } = useRopeHistory(ropeId);

  if (error) return <StatusMessage tone="error">Could not load the defect from the server.</StatusMessage>;
  if (loading || !data) return <StatusMessage>Loading…</StatusMessage>;

  const runIndex = data.runs.findIndex((r) => r.id === runId);
  const run = data.runs[runIndex];
  const defect = run && data.defectsByRun[run.id]?.find((d) => d.id === defectId);
  if (!data.rope || !run || !defect) return <StatusMessage>This defect does not exist.</StatusMessage>;

  // Runs are sorted newest first, so the previous run is the next entry.
  const previousRun = data.runs[runIndex + 1];
  const previous = previousRun && findMatch(data.defectsByRun[previousRun.id] ?? [], defect);

  return (
    <>
      <BackLink href={routes.run(data.rope.id, run.id)}>{shortId(run.id)}</BackLink>
      <PageHeader title={shortId(defect.id)}>
        <HeadingMeta>{defectTypeLabel(defect.kind)}</HeadingMeta>
      </PageHeader>

      <div className="mt-5 flex flex-wrap items-start gap-[22px]">
        <figure className="m-0 flex min-w-[290px] flex-[1_1_460px] flex-col gap-2.5">
          <div className="relative aspect-video rounded-card bg-video-placeholder">
            <div className="absolute top-3.5 left-4 font-mono text-[11px] leading-none text-video-text">
              {defect.kind} · {formatMetres(defect.pos_to_start)} · frame not stored
            </div>
          </div>
          <figcaption className="text-[13px] leading-none text-text-muted">
            Camera A, frame that triggered the detection
          </figcaption>
        </figure>

        <div className="flex min-w-[280px] flex-[1_1_320px] flex-col gap-[18px]">
          <FactList
            facts={[
              { label: "Position", value: formatMetres(defect.pos_to_start), tone: "ink" },
              { label: "Type", value: defect.kind },
              { label: "Detection confidence", value: NOT_AVAILABLE, tone: "ink" },
              { label: "Status", value: NOT_AVAILABLE, tone: "ink" },
              { label: "Run", value: shortId(run.id) },
              { label: "Detected", value: formatDateTime(defect.created_at) },
            ]}
          />

          <div>
            <h2 className="mb-2.5 text-lg leading-none font-extrabold tracking-[-0.01em] uppercase">
              Change since {previousRun ? shortId(previousRun.id) : "earlier runs"}
            </h2>
            <div className="flex flex-col gap-[7px]">
              {!previousRun ? (
                <InfoRow tone="neutral" label="No earlier run" value="first run" />
              ) : previous ? (
                <InfoRow
                  tone="neutral"
                  label="Position"
                  value={`${previous.pos_to_start.toFixed(1)} → ${defect.pos_to_start.toFixed(1)} m`}
                />
              ) : (
                <InfoRow tone="neutral" label="Not detected before" value="first sighting" />
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button disabled title="Defect review is not available yet" className="flex-[1_1_150px] py-3.5">
              Mark reviewed
            </Button>
            <Button
              variant="secondary"
              disabled
              title="Defect review is not available yet"
              className="flex-[1_1_150px] py-3.5"
            >
              Flag false positive
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
