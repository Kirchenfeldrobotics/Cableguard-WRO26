"use client";

import { defectMarks } from "@/components/rope/defect-marks";
import { RopeStrip } from "@/components/rope/rope-strip";
import { Button } from "@/components/ui/button";
import { CardGrid, FactCard, Panel } from "@/components/ui/card";
import { BackLink, StatusMessage } from "@/components/ui/feedback";
import { HeadingMeta, PageHeader, SectionTitle } from "@/components/ui/heading";
import { LinkRow, Table, Td, Th } from "@/components/ui/table";
import { byPosition } from "@/lib/defects";
import {
  NOT_AVAILABLE,
  defectTypeLabel,
  formatDateTime,
  formatMetres,
  formatRunDuration,
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
  const defects = [...(data.defectsByRun[run.id] ?? [])].sort(byPosition);

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
        <FactCard value={NOT_AVAILABLE} label="Distance covered" title="The robot does not report distance yet" />
        <FactCard value={defects.length} label="Defects" />
      </CardGrid>

      <Panel className="mt-[26px] px-[22px] py-5">
        <RopeStrip length={rope.length_m} marks={defectMarks(rope.id, defects)} />
      </Panel>

      <SectionTitle>Defects</SectionTitle>
      {defects.length === 0 ? (
        <StatusMessage>No defects were detected in this run.</StatusMessage>
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Position</Th>
              <Th>Type</Th>
              <Th align="right">Confidence</Th>
              <Th>Severity</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {defects.map((d) => (
              <LinkRow key={d.id} href={routes.defect(rope.id, run.id, d.id)}>
                <Td mono strong>
                  {formatMetres(d.pos_to_start)}
                </Td>
                <Td className="font-medium">{defectTypeLabel(d.kind)}</Td>
                <Td mono align="right">
                  {NOT_AVAILABLE}
                </Td>
                <Td muted>{NOT_AVAILABLE}</Td>
                <Td muted>{NOT_AVAILABLE}</Td>
              </LinkRow>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}
