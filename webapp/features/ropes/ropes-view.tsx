"use client";

import { useState } from "react";

import { RopeLengthInput, parseRopeLength } from "@/components/rope/rope-length-input";
import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/heading";
import { RemoveButton } from "@/components/ui/remove-button";
import { LinkRow, Table, Td, Th } from "@/components/ui/table";
import { api } from "@/lib/api/client";
import { formatDate, formatMetres } from "@/lib/format";
import { lastFinishedRun } from "@/lib/hooks/use-inspection";
import { useApi } from "@/lib/hooks/use-api";
import { routes } from "@/lib/routes";

async function loadOverview() {
  const ropes = await api.ropes.list();
  const runs = await Promise.all(ropes.map((rope) => api.runs.list(rope.id)));
  return ropes.map((rope, i) => ({ rope, runs: runs[i] }));
}

export function RopesView() {
  const overview = useApi("ropes-overview", loadOverview);
  const [adding, setAdding] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const run = async (action: () => Promise<unknown>) => {
    setActionError(null);
    try {
      await action();
      overview.reload();
      return true;
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
      return false;
    }
  };

  return (
    <>
      <PageHeader
        title="Ropes"
        actions={
          !adding && (
            <Button onClick={() => setAdding(true)} className="py-[13px]">
              Add rope
            </Button>
          )
        }
      />

      {adding && (
        <AddRopeForm
          onCancel={() => setAdding(false)}
          onSubmit={async (name, lengthM) => {
            if (await run(() => api.ropes.create(name, lengthM))) setAdding(false);
          }}
        />
      )}
      {actionError && <StatusMessage tone="error">{actionError}</StatusMessage>}

      {overview.error ? (
        <StatusMessage tone="error">Could not load ropes from the server.</StatusMessage>
      ) : overview.loading && !overview.data ? (
        <StatusMessage>Loading…</StatusMessage>
      ) : overview.data?.length === 0 ? (
        <StatusMessage>No ropes yet.</StatusMessage>
      ) : (
        <Table className="mt-[22px]">
          <thead>
            <tr>
              <Th>Rope</Th>
              <Th align="right">Length</Th>
              <Th align="right">Runs</Th>
              <Th>Last inspected</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {overview.data?.map(({ rope, runs }) => (
              <LinkRow key={rope.id} href={routes.rope(rope.id)}>
                <Td strong phone="primary">
                  {rope.name}
                </Td>
                <Td mono align="right" label="Length">
                  {formatMetres(rope.length_m)}
                </Td>
                <Td mono align="right" label="Runs">
                  {runs.length}
                </Td>
                <Td mono muted label="Last inspected">
                  {formatDate(lastFinishedRun(runs)?.finished_at)}
                </Td>
                <Td align="right" phone="end" className="pr-0">
                  <RemoveButton onConfirm={() => run(() => api.ropes.remove(rope.id))} />
                </Td>
              </LinkRow>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}

function AddRopeForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (name: string, lengthM: number) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [length, setLength] = useState("");
  const [saving, setSaving] = useState(false);
  const lengthM = parseRopeLength(length);

  return (
    <form
      className="mt-[22px] flex flex-wrap items-center gap-3 rounded-card bg-surface p-4"
      onSubmit={async (e) => {
        e.preventDefault();
        if (lengthM === null) return;
        setSaving(true);
        await onSubmit(name.trim(), lengthM);
        setSaving(false);
      }}
    >
      <input
        autoFocus
        required
        maxLength={120}
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Rope name"
        aria-label="Rope name"
        className="min-w-0 basis-full rounded-control border border-border bg-white px-3.5 py-3 text-base sm:min-w-[240px] sm:flex-1 sm:basis-auto sm:text-sm"
      />
      <RopeLengthInput value={length} onChange={setLength} />
      <Button type="submit" disabled={saving || !name.trim() || lengthM === null}>
        Save
      </Button>
      <Button variant="secondary" onClick={onCancel}>
        Cancel
      </Button>
    </form>
  );
}
