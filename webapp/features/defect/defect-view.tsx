"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { DetectionFrame } from "@/components/camera/detection-frame";
import { Button } from "@/components/ui/button";
import { BackLink, StatusMessage } from "@/components/ui/feedback";
import { FactList } from "@/components/ui/fact-list";
import { HeadingMeta, PageHeader, SectionTitle, SubTitle } from "@/components/ui/heading";
import { InfoRow } from "@/components/ui/log-row";
import { Table, Td, Th } from "@/components/ui/table";
import { api } from "@/lib/api/client";
import { findMatch, findingOf, kindTone } from "@/lib/defects";
import {
  defectClassLabel,
  defectTypeLabel,
  formatCamera,
  formatConfidence,
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
  const router = useRouter();
  const { data, error, loading, reload } = useRopeHistory(ropeId);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);

  if (error) return <StatusMessage tone="error">Could not load the defect from the server.</StatusMessage>;
  if (loading || !data) return <StatusMessage>Loading…</StatusMessage>;

  const runIndex = data.runs.findIndex((r) => r.id === runId);
  const run = data.runs[runIndex];
  const defect = run && data.defectsByRun[run.id]?.find((d) => d.id === defectId);
  if (!data.rope || !run || !defect) return <StatusMessage>This defect does not exist.</StatusMessage>;

  // The page opens on one detection, but the flaw is the whole group it sits in. A review
  // is of the flaw, so it goes to every detection of the group.
  const finding = findingOf(data.findingsByRun[run.id] ?? [], defect);
  const siblings = finding?.detections ?? [defect];
  const reviewed = finding?.reviewed ?? defect.reviewed;
  const ids = siblings.map((d) => d.id);
  const runHref = routes.run(data.rope.id, run.id);

  const setReviewed = async (value: boolean) => {
    setFailed(null);
    setBusy(true);
    try {
      await api.defects.review(ids, value);
      reload();
    } catch (err) {
      setFailed(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  /** A false positive is deleted, so the page it was on is gone with it. */
  const removeFinding = async () => {
    setFailed(null);
    setBusy(true);
    try {
      await api.defects.remove(ids);
      router.replace(runHref);
    } catch (err) {
      setFailed(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  };

  // Runs are sorted newest first, so the previous run is the next entry.
  const previousRun = data.runs[runIndex + 1];
  const previous =
    previousRun && finding && findMatch(data.findingsByRun[previousRun.id] ?? [], finding);

  return (
    <>
      <BackLink href={runHref}>{shortId(run.id)}</BackLink>
      <PageHeader title={defectClassLabel(defect.label)}>
        <HeadingMeta>
          {defectTypeLabel(defect.kind)} · {formatMetres(defect.pos_to_start)}
        </HeadingMeta>
      </PageHeader>

      <div className="mt-stack flex flex-wrap items-start gap-stack">
        <div className="min-w-[290px] flex-[1_1_380px]">
          <DetectionFrame key={defect.id} defect={defect} />
        </div>

        <div className="flex min-w-[280px] flex-[1_1_320px] flex-col gap-stack">
          <FactList
            facts={[
              { label: "Position", value: formatMetres(defect.pos_to_start), tone: "ink", mono: true },
              { label: "Flaw", value: defectClassLabel(defect.label), tone: "ink" },
              { label: "Type", value: `${defectTypeLabel(defect.kind)} (${defect.kind.toUpperCase()})` },
              { label: "Detection confidence", value: formatConfidence(defect.confidence), tone: "ink", mono: true },
              { label: "Camera", value: formatCamera(defect.cam) },
              { label: "Status", value: reviewed ? "Reviewed" : "Unreviewed", tone: reviewed ? "muted" : "ink" },
              { label: "Run", value: shortId(run.id), mono: true },
              { label: "Detected", value: formatDateTime(defect.created_at), mono: true },
            ]}
          />

          <div className="flex flex-col gap-2.5">
            <SubTitle>Change since {previousRun ? shortId(previousRun.id) : "earlier runs"}</SubTitle>
            {!previousRun ? (
              <InfoRow tone="neutral" label="No earlier run" />
            ) : previous ? (
              <InfoRow
                tone={kindTone(previous.kind)}
                label="Position"
                value={`${previous.pos.toFixed(1)} → ${(finding?.pos ?? defect.pos_to_start).toFixed(1)} m`}
              />
            ) : (
              <InfoRow tone="neutral" label="Not detected before" />
            )}
          </div>

          <div className="flex flex-wrap gap-3">
            <Button
              variant={reviewed ? "secondary" : "primary"}
              disabled={busy}
              className="flex-[1_1_150px]"
              onClick={() => setReviewed(!reviewed)}
            >
              {reviewed ? "Mark unreviewed" : "Mark reviewed"}
            </Button>
            <Button
              variant={confirmDelete ? "danger" : "secondary"}
              disabled={busy}
              className="flex-[1_1_150px]"
              onClick={() => (confirmDelete ? removeFinding() : setConfirmDelete(true))}
              onBlur={() => setConfirmDelete(false)}
            >
              {confirmDelete ? "Confirm delete" : "Flag false positive"}
            </Button>
          </div>
          {failed && <StatusMessage tone="error">{failed}</StatusMessage>}
        </div>
      </div>

      <SectionTitle>
        {siblings.length === 1 ? "The detection" : `${siblings.length} detections of this flaw`}
      </SectionTitle>
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
            <tr
              key={d.id}
              aria-current={d.id === defect.id || undefined}
              className={d.id === defect.id ? "bg-surface-hover" : undefined}
            >
              <Td mono strong phone="primary">
                {formatMetres(d.pos_to_start)}
              </Td>
              <Td label="Flaw">{defectClassLabel(d.label)}</Td>
              <Td mono align="right" label="Confidence">
                {formatConfidence(d.confidence)}
              </Td>
              <Td muted label="Camera">
                {formatCamera(d.cam)}
              </Td>
              <Td mono muted label="Detected">
                {formatDateTime(d.created_at)}
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </>
  );
}
