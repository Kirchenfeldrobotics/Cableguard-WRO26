"use client";

import { useState } from "react";

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
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  if (error) return <StatusMessage tone="error">Could not load the run from the server.</StatusMessage>;
  if (loading || !data) return <StatusMessage>Loading…</StatusMessage>;

  const run = data.runs.find((r) => r.id === runId);
  if (!data.rope || !run) return <StatusMessage>This run does not exist.</StatusMessage>;

  const rope = data.rope;
  const findings = data.findingsByRun[run.id] ?? [];
  const detections = data.defectsByRun[run.id] ?? [];

  const exportReport = async () => {
    setExportError(null);
    setExporting(true);
    try {
      // Loaded on the click, the PDF library is far heavier than the page it is used on.
      const { downloadRunReport } = await import("./run-report");
      await downloadRunReport({ rope, run, findings, detectionCount: detections.length });
    } catch (err) {
      setExportError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <BackLink href={routes.rope(rope.id)}>{rope.name}</BackLink>
      <PageHeader
        title={shortId(run.id)}
        actions={
          <Button variant="secondary" disabled={exporting} onClick={exportReport} className="max-sm:flex-1">
            {exporting ? "Exporting…" : "Export run report"}
          </Button>
        }
      >
        <HeadingMeta>{rope.name}</HeadingMeta>
      </PageHeader>
      {exportError && <StatusMessage tone="error">{exportError}</StatusMessage>}

      <CardGrid>
        <FactCard value={formatDateTime(run.started_at)} label="Started" />
        <FactCard value={formatRunDuration(run)} label="Duration" />
        <FactCard value={findings.length} label="Findings" />
        <FactCard value={detections.length} label="Detections" />
      </CardGrid>

      <Panel className="mt-stack">
        <RopeStrip length={rope.length_m} marks={findingMarks(rope.id, findings)} />
      </Panel>
      <DefectLegend />

      {findings.length > 0 && (
        <>
          <SectionTitle>Findings</SectionTitle>
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
                  <Td mono strong phone="primary">
                    {formatSpan(finding.from, finding.to)}
                  </Td>
                  <Td className="font-medium" label="Flaw">
                    {defectClassLabel(finding.best.label)}
                  </Td>
                  <Td label="Type">
                    <Pill tone={kindTone(finding.kind)}>{defectTypeLabel(finding.kind)}</Pill>
                  </Td>
                  <Td mono align="right" label="Confidence">
                    {formatConfidence(finding.confidence)}
                  </Td>
                  <Td mono muted align="right" label="Detections">
                    {finding.detections.length}
                  </Td>
                  {/* What is still to do stands out, what is done steps back. */}
                  <Td label="Status" className={finding.reviewed ? "text-text-muted" : "font-semibold"}>
                    {finding.reviewed ? "Reviewed" : "Unreviewed"}
                  </Td>
                </LinkRow>
              ))}
            </tbody>
          </Table>
        </>
      )}
    </>
  );
}
