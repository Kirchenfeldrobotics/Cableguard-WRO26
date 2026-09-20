"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/heading";

export default function Error({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <>
      <PageHeader title="Something went wrong" />
      <p className="mt-[18px] mb-6 text-sm text-text-muted">
        The page failed to render. The error was logged to the browser console.
      </p>
      <Button onClick={retry}>Try again</Button>
    </>
  );
}
