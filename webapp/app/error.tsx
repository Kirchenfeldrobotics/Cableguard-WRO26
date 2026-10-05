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
      <Button onClick={retry} size="lg" className="mt-stack max-sm:w-full sm:w-[260px]">
        Try again
      </Button>
    </>
  );
}
