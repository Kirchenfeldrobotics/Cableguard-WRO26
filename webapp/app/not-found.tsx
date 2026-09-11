import Link from "next/link";

import { PageHeader } from "@/components/ui/heading";

export default function NotFound() {
  return (
    <>
      <PageHeader title="Not found" />
      <p className="mt-[18px] text-sm text-text-muted">
        This page does not exist.{" "}
        <Link href="/" className="font-semibold underline">
          Back to the dashboard
        </Link>
      </p>
    </>
  );
}
