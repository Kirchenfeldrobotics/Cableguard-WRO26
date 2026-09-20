"use client";

import { DetectionFrame } from "@/components/camera/detection-frame";
import { Button } from "@/components/ui/button";
import { BackLink, StatusMessage } from "@/components/ui/feedback";
import { FactList } from "@/components/ui/fact-list";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { InfoRow } from "@/components/ui/log-row";
import { Table, Td, Th } from "@/components/ui/table";
import { findMatch, findingOf, kindTone } from "@/lib/defects";
import {
  NOT_AVAILABLE,
  defectClassLabel,
  defectTypeLabel,
  formatCamera,
  formatConfidence,
  formatDateTime,
  formatMetres,
  formatSpan,
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

  // The page opens on one detection, but the flaw is the whole group it sits in.
  const finding = findingOf(data.findingsByRun[run.id] ?? [], defect);
  const siblings = finding?.detections ?? [defect];

  // Runs are sorted newest first, so the previous run is the next entry.
  const previousRun = data.runs[runIndex + 1];
  const previous =
    previousRun && finding && findMatch(data.findingsByRun[previousRun.id] ?? [], finding);

  return (
    <>
      <BackLink href={routes.run(data.rope.id, run.id)}>{shortId(run.id)}</BackLink>
      <PageHeader title={defectClassLabel(defect.label)}>
        <HeadingMeta>
          {defectTypeLabel(defect.kind)} · {formatMetres(defect.pos_to_start)}
        </HeadingMeta>
      </PageHeader>

      <div className="mt-5 flex flex-wrap items-start gap-[22px]">
        <figure className="m-0 flex min-w-[290px] flex-[1_1_380px] flex-col gap-2.5">
          <DetectionFrame defect={defect} />
          <figcaption className="text-[13px] leading-none text-text-muted">
            {formatCamera(defect.cam)}, where the detection sat in the frame
          </figcaption>
        </figure>

        <div className="flex min-w-[280px] flex-[1_1_320px] flex-col gap-[18px]">
          <FactList
            facts={[
              { label: "Position", value: formatMetres(defect.pos_to_start), tone: "ink" },
              { label: "Flaw", value: defectClassLabel(defect.label), tone: "ink" },
              { label: "Type", value: `${defectTypeLabel(defect.kind)} (${defect.kind.toUpperCase()})` },
              { label: "Detection confidence", value: formatConfidence(defect.confidence), tone: "ink" },
              { label: "Camera", value: formatCamera(defect.cam) },
              { label: "Status", value: NOT_AVAILABLE },
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
                  tone={kindTone(previous.kind)}
                  label="Position"
                  value={`${previous.pos.toFixed(1)} → ${(finding?.pos ?? defect.pos_to_start).toFixed(1)} m`}
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

      <SectionTitle>
        {siblings.length === 1 ? "The detection" : `${siblings.length} detections of this flaw`}
      </SectionTitle>
      {finding && siblings.length > 1 && (
        <p className="mb-[18px] max-w-[620px] text-[13px] leading-[1.6] text-text-muted">
          The detector saw this spot {siblings.length} times over {formatSpan(finding.from, finding.to)}.
          The page above shows the clearest of them.
        </p>
      )}
      <Table>
        <thead>
          <tr>
            <Th>Position</Th>
            <Th>Flaw</Th>
            <Th align="right">Confidence</Th>
            <Th>Camera</Th>
            <Th>Detected</Th>
          </tr>
        </thead>
        <tbody>
          {siblings.map((d) => (
            <tr key={d.id} className={d.id === defect.id ? "bg-surface-hover" : undefined}>
              <Td mono strong>
                {formatMetres(d.pos_to_start)}
              </Td>
              <Td>{defectClassLabel(d.label)}</Td>
              <Td mono align="right">
                {formatConfidence(d.confidence)}
              </Td>
              <Td muted>{formatCamera(d.cam)}</Td>
              <Td mono muted>
                {formatDateTime(d.created_at)}
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </>
  );
}
