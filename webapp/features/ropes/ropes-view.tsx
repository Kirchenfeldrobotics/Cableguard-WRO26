"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/heading";
import { LinkRow, Table, Td, Th } from "@/components/ui/table";
import { api } from "@/lib/api/client";
import { NOT_AVAILABLE, formatDate, formatMetres } from "@/lib/format";
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
          onSubmit={async (name) => {
            if (await run(() => api.ropes.create(name))) setAdding(false);
          }}
        />
      )}
      {actionError && <StatusMessage tone="error">{actionError}</StatusMessage>}

      {overview.error ? (
        <StatusMessage tone="error">Could not load ropes from the server.</StatusMessage>
      ) : overview.loading && !overview.data ? (
        <StatusMessage>Loading…</StatusMessage>
      ) : overview.data?.length === 0 ? (
        <StatusMessage>No ropes yet. Add the first rope to start inspecting.</StatusMessage>
      ) : (
        <Table className="mt-[22px]">
          <thead>
            <tr>
              <Th>Rope</Th>
              <Th>Installed</Th>
              <Th align="right">Length</Th>
              <Th align="right">Runs</Th>
              <Th>Last inspected</Th>
              <Th>Condition</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {overview.data?.map(({ rope, runs }) => (
              <LinkRow key={rope.id} href={routes.rope(rope.id)}>
                <Td strong>{rope.name}</Td>
                <Td mono muted>
                  {NOT_AVAILABLE}
                </Td>
                <Td mono align="right">
                  {formatMetres(rope.length_m)}
                </Td>
                <Td mono align="right">
                  {runs.length}
                </Td>
                <Td mono muted>
                  {formatDate(lastFinishedRun(runs)?.finished_at)}
                </Td>
                <Td muted>{NOT_AVAILABLE}</Td>
                <Td align="right" className="pr-0">
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
  onSubmit: (name: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  return (
    <form
      className="mt-[22px] flex flex-wrap items-center gap-3 rounded-card bg-surface p-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setSaving(true);
        await onSubmit(name.trim());
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
        className="min-w-[240px] flex-1 rounded-control border border-border bg-white px-3.5 py-3 text-sm"
      />
      <Button type="submit" disabled={saving || !name.trim()}>
        Save
      </Button>
      <Button variant="secondary" onClick={onCancel}>
        Cancel
      </Button>
    </form>
  );
}

/** Two-step remove so a rope and its runs are not deleted by a stray click. */
function RemoveButton({ onConfirm }: { onConfirm: () => void }) {
  const [armed, setArmed] = useState(false);

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        if (armed) onConfirm();
        setArmed(!armed);
      }}
      onBlur={() => setArmed(false)}
      onKeyDown={(e) => e.stopPropagation()}
      className={
        armed
          ? "text-xs leading-none font-semibold text-danger-strong"
          : "text-xs leading-none font-medium text-text-subtle hover:text-danger-strong"
      }
    >
      {armed ? "Confirm remove" : "Remove"}
    </button>
  );
}
