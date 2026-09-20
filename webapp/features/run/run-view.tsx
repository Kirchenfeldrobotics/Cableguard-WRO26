"use client";

import { DefectLegend } from "@/components/rope/defect-legend";
import { findingMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { Button } from "@/components/ui/button";
import { CardGrid, FactCard, Panel } from "@/components/ui/card";
import { BackLink, StatusMessage } from "@/components/ui/feedback";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { Pill } from "@/components/ui/pill";
import { LinkRow, Table, Td, Th } from "@/components/ui/table";
import { kindTone } from "@/lib/defects";
import {
  NOT_AVAILABLE,
  defectClassLabel,
  defectTypeLabel,
  formatConfidence,
  formatDateTime,
  formatRunDuration,
  formatSpan,
  shortId,
} from "@/lib/format";
import { useRopeHistory } from "@/lib/hooks/use-inspection";
import { routes } from "@/lib/routes";

export function RunView({ ropeId, runId }: { ropeId: string; runId: string }) {
  const { data, error, loading } = useRopeHistory(ropeId);

  if (error) return <StatusMessage tone="error">Could not load the run from the server.</StatusMessage>;
  if (loading || !data) return <StatusMessage>Loading…</StatusMessage>;

  const run = data.runs.find((r) => r.id === runId);
  if (!data.rope || !run) return <StatusMessage>This run does not exist.</StatusMessage>;

  const rope = data.rope;
  const findings = data.findingsByRun[run.id] ?? [];
  const detections = data.defectsByRun[run.id] ?? [];

  return (
    <>
      <BackLink href={routes.rope(rope.id)}>{rope.name}</BackLink>
      <PageHeader
        title={shortId(run.id)}
        actions={
          <Button variant="secondary" disabled title="Run reports are not available yet" className="py-3">
            Export run report
          </Button>
        }
      >
        <HeadingMeta>{rope.name}</HeadingMeta>
      </PageHeader>

      <CardGrid>
        <FactCard value={formatDateTime(run.started_at)} label="Started" />
        <FactCard value={formatRunDuration(run)} label="Duration" />
        <FactCard value={findings.length} label="Findings" />
        <FactCard value={detections.length} label="Detections" title="Every frame the detector fired on" />
      </CardGrid>

      <Panel className="mt-[26px] px-[22px] py-5">
        <RopeStrip length={rope.length_m} marks={findingMarks(rope.id, findings)} />
      </Panel>
      <DefectLegend />

      <SectionTitle>Findings</SectionTitle>
      {findings.length === 0 ? (
        <StatusMessage>No defects were detected in this run.</StatusMessage>
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Position</Th>
              <Th>Flaw</Th>
              <Th>Type</Th>
              <Th align="right">Confidence</Th>
              <Th align="right">Detections</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {findings.map((finding) => (
              <LinkRow
                key={finding.best.id}
                href={routes.defect(rope.id, finding.best.run_id, finding.best.id)}
              >
                <Td mono strong>
                  {formatSpan(finding.from, finding.to)}
                </Td>
                <Td className="font-medium">{defectClassLabel(finding.best.label)}</Td>
                <Td>
                  <Pill tone={kindTone(finding.kind)}>{defectTypeLabel(finding.kind)}</Pill>
                </Td>
                <Td mono align="right">
                  {formatConfidence(finding.confidence)}
                </Td>
                <Td mono muted align="right">
                  {finding.detections.length}
                </Td>
                <Td muted>{NOT_AVAILABLE}</Td>
              </LinkRow>
            ))}
          </tbody>
        </Table>
      )}

      <p className="mt-3.5 max-w-[620px] text-[13px] leading-[1.6] text-text-muted">
        The detector fires every two seconds on both cameras, so one flaw is usually seen several
        times. {detections.length} detections were grouped into {findings.length}{" "}
        {findings.length === 1 ? "finding" : "findings"}. Position is where the clearest detection
        sat, or the stretch the group covers.
      </p>
    </>
  );
}
